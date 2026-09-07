from __future__ import annotations

"""Responsive PyQt interface for evidence-first chat moment analysis."""

import math
import os
import platform
import threading
from typing import Callable, Dict, List, Optional

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import pandas as pd
from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.analyzer import ChatAnalyzer
from core.errors import TaskCancelled
from core.sentiment_analyzer import SentimentAnalyzer
from core.wordcloud_gen import WordCloudGenerator


def setup_korean_font() -> None:
    system = platform.system()
    if system == "Darwin":
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        if os.path.exists(font_path):
            plt.rcParams["font.family"] = fm.FontProperties(fname=font_path).get_name()
    elif system == "Windows":
        plt.rcParams["font.family"] = "Malgun Gothic"
    else:
        plt.rcParams["font.family"] = "NanumGothic"
    plt.rcParams["axes.unicode_minus"] = False


setup_korean_font()


class TaskWorker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, task: Callable[[Callable[[], bool]], object]):
        super().__init__()
        self.task = task
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self.task(self.cancel_event.is_set)
            # Cooperative tasks raise TaskCancelled when they honor a request.
            # A task that already committed and returned must remain a success so
            # the visible UI cannot diverge from the core state.
            self.finished.emit(result)
        except TaskCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    MAX_RESULT_TABS = 12
    MAX_DISPLAY_POINTS = 2_000

    def __init__(self):
        super().__init__()
        self.analyzer = ChatAnalyzer()
        self.wordcloud_gen = WordCloudGenerator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.current_file: Optional[str] = None
        self._task_thread: Optional[QThread] = None
        self._task_worker: Optional[TaskWorker] = None
        self._task_success_callback: Optional[Callable[[object], None]] = None
        self._close_when_idle = False
        self.action_widgets: List[QWidget] = []
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("치지직 클립 모먼트 캐처")
        self.resize(1240, 860)
        self.setMinimumSize(760, 560)

        outer_scroll = QScrollArea()
        outer_scroll.setWidgetResizable(True)
        outer_scroll.setObjectName("mainScrollArea")
        central_widget = QWidget()
        central_widget.setMinimumWidth(720)
        outer_scroll.setWidget(central_widget)
        self.setCentralWidget(outer_scroll)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel("치지직 클립 모먼트 캐처")
        title.setObjectName("titleLabel")
        main_layout.addWidget(title)
        main_layout.addWidget(self.create_file_group())

        controls = QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.create_moment_group(), 2)
        controls.addWidget(self.create_sentiment_group(), 1)
        controls.addWidget(self.create_wordcloud_group(), 1)
        main_layout.addLayout(controls)
        main_layout.addWidget(self.create_export_group())

        status_layout = QHBoxLayout()
        self.status_label = QLabel("CSV를 불러오면 분석을 시작할 수 있습니다.")
        self.status_label.setObjectName("subtitleLabel")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        status_layout.addWidget(self.progress)
        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setAccessibleName("현재 작업 취소")
        self.cancel_button.clicked.connect(self.cancel_current_task)
        self.cancel_button.hide()
        status_layout.addWidget(self.cancel_button)
        main_layout.addLayout(status_layout)

        self.result_tabs = QTabWidget()
        self.result_tabs.setTabsClosable(True)
        self.result_tabs.tabCloseRequested.connect(self._close_result_tab)
        self.result_tabs.currentChanged.connect(self._sync_export_kind_to_tab)
        self.result_tabs.setMinimumHeight(420)
        main_layout.addWidget(self.result_tabs, 1)

    def create_file_group(self) -> QGroupBox:
        group = QGroupBox("CSV 파일")
        layout = QHBoxLayout(group)
        self.file_label = QLabel("파일을 선택하세요")
        self.file_label.setObjectName("subtitleLabel")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label, 1)
        button = QPushButton("파일 선택")
        button.clicked.connect(self.load_csv)
        layout.addWidget(button)
        self.action_widgets.append(button)
        return group

    def _positive_number_input(self, default: str, maximum: float = 1440.0) -> QLineEdit:
        line_edit = QLineEdit(default)
        line_edit.setValidator(QDoubleValidator(0.01, maximum, 3, line_edit))
        line_edit.setMaximumWidth(80)
        return line_edit

    def _nonnegative_number_input(self, default: str, maximum: float = 600.0) -> QLineEdit:
        line_edit = QLineEdit(default)
        line_edit.setValidator(QDoubleValidator(0.0, maximum, 3, line_edit))
        line_edit.setMaximumWidth(70)
        return line_edit

    def create_moment_group(self) -> QGroupBox:
        group = QGroupBox("하이라이트 탐색")
        layout = QVBoxLayout(group)
        keyword_row = QHBoxLayout()
        keyword_label = QLabel("키워드")
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("예: ㅋㅋ")
        self.keyword_input.setAccessibleName("검색 키워드")
        keyword_label.setBuddy(self.keyword_input)
        keyword_row.addWidget(keyword_label)
        keyword_row.addWidget(self.keyword_input, 1)
        layout.addLayout(keyword_row)

        option_row = QHBoxLayout()
        interval_label = QLabel("간격(분)")
        self.interval_input = self._positive_number_input("1")
        self.interval_input.setAccessibleName("하이라이트 분석 간격(분)")
        interval_label.setBuddy(self.interval_input)
        option_row.addWidget(interval_label)
        option_row.addWidget(self.interval_input)
        sensitivity_label = QLabel("민감도")
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 30)
        self.sensitivity_slider.setValue(20)
        self.sensitivity_slider.setMaximumWidth(130)
        self.sensitivity_slider.setToolTip(
            "낮음: 큰 반응만 포착\n보통: 균형 잡힌 감지\n높음: 작은 반응도 포착"
        )
        self.sensitivity_slider.setAccessibleName("하이라이트 탐지 민감도")
        self.sensitivity_slider.setAccessibleDescription(
            "1.0은 큰 반응 위주, 3.0은 작은 반응까지 탐지합니다."
        )
        sensitivity_label.setBuddy(self.sensitivity_slider)
        option_row.addWidget(sensitivity_label)
        self.sensitivity_slider.valueChanged.connect(self.update_sensitivity_label)
        option_row.addWidget(self.sensitivity_slider)
        self.sensitivity_value_label = QLabel("보통 (2.0)")
        option_row.addWidget(self.sensitivity_value_label)
        option_row.addStretch()
        layout.addLayout(option_row)

        button_row = QHBoxLayout()
        keyword_button = QPushButton("키워드 분석")
        keyword_button.clicked.connect(self.analyze_keyword)
        density_button = QPushButton("채팅 밀도 분석")
        density_button.setObjectName("secondaryButton")
        density_button.clicked.connect(self.analyze_chat_density)
        button_row.addWidget(keyword_button)
        button_row.addWidget(density_button)
        layout.addLayout(button_row)
        self.action_widgets.extend([keyword_button, density_button])
        return group

    def create_sentiment_group(self) -> QGroupBox:
        group = QGroupBox("분위기 분석")
        layout = QVBoxLayout(group)
        row = QHBoxLayout()
        interval_label = QLabel("간격(분)")
        self.sentiment_interval_input = self._positive_number_input("1")
        self.sentiment_interval_input.setAccessibleName("분위기 분석 간격(분)")
        interval_label.setBuddy(self.sentiment_interval_input)
        row.addWidget(interval_label)
        row.addWidget(self.sentiment_interval_input)
        row.addStretch()
        layout.addLayout(row)
        button = QPushButton("정서·반응 강도 분석")
        button.clicked.connect(self.analyze_sentiment)
        layout.addWidget(button)
        mood_export = QPushButton("변화 작업표 저장")
        mood_export.setObjectName("secondaryButton")
        mood_export.clicked.connect(self.export_mood_markers)
        layout.addWidget(mood_export)
        self.action_widgets.extend([button, mood_export])
        return group

    def create_wordcloud_group(self) -> QGroupBox:
        group = QGroupBox("표현 분포")
        layout = QVBoxLayout(group)
        generate_button = QPushButton("표현 분포 생성")
        generate_button.clicked.connect(self.generate_wordcloud)
        save_button = QPushButton("이미지 저장")
        save_button.setObjectName("secondaryButton")
        save_button.clicked.connect(self.save_wordcloud)
        layout.addWidget(generate_button)
        layout.addWidget(save_button)
        self.action_widgets.extend([generate_button, save_button])
        return group

    def create_export_group(self) -> QGroupBox:
        group = QGroupBox("편집 연동")
        layout = QHBoxLayout(group)
        result_label = QLabel("결과")
        self.export_kind = QComboBox()
        result_label.setBuddy(self.export_kind)
        layout.addWidget(result_label)
        self.export_kind.addItem("채팅 밀도", "density")
        self.export_kind.addItem("키워드", "keyword")
        layout.addWidget(self.export_kind)
        format_label = QLabel("형식")
        self.export_format = QComboBox()
        format_label.setBuddy(self.export_format)
        layout.addWidget(format_label)
        self.export_format.addItem("편집 작업표 CSV", "csv")
        self.export_format.addItem("Premiere 교환 XML", "premiere_xml")
        self.export_format.addItem("Final Cut FCPXML", "fcpxml")
        layout.addWidget(self.export_format, 1)
        pre_roll_label = QLabel("프리롤")
        self.pre_roll_input = self._nonnegative_number_input("15")
        pre_roll_label.setBuddy(self.pre_roll_input)
        layout.addWidget(pre_roll_label)
        layout.addWidget(self.pre_roll_input)
        post_roll_label = QLabel("포스트롤")
        self.post_roll_input = self._nonnegative_number_input("20")
        post_roll_label.setBuddy(self.post_roll_input)
        layout.addWidget(post_roll_label)
        layout.addWidget(self.post_roll_input)
        fps_label = QLabel("FPS")
        self.fps_combo = QComboBox()
        fps_label.setBuddy(self.fps_combo)
        layout.addWidget(fps_label)
        for fps in (23.976, 24, 25, 29.97, 30, 50, 59.94, 60):
            self.fps_combo.addItem(str(fps), fps)
        self.fps_combo.setCurrentText("30")
        layout.addWidget(self.fps_combo)
        export_button = QPushButton("내보내기")
        export_button.clicked.connect(self.export_editor_result)
        layout.addWidget(export_button)
        self.action_widgets.append(export_button)
        return group

    def update_sensitivity_label(self, value: int) -> None:
        sensitivity = value / 10.0
        if sensitivity <= 1.5:
            label = "낮음"
        elif sensitivity <= 2.5:
            label = "보통"
        else:
            label = "높음"
        self.sensitivity_value_label.setText(f"{label} ({sensitivity:.1f})")

    def _read_positive(self, widget: QLineEdit, label: str) -> float:
        try:
            value = float(widget.text())
        except ValueError as error:
            raise ValueError(f"{label}은 숫자로 입력하세요.") from error
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{label}은 0보다 큰 유한한 값이어야 합니다.")
        return value

    def _read_nonnegative(self, widget: QLineEdit, label: str) -> float:
        try:
            value = float(widget.text())
        except ValueError as error:
            raise ValueError(f"{label}은 숫자로 입력하세요.") from error
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{label}은 0 이상의 유한한 값이어야 합니다.")
        return value

    def _require_source(self) -> bool:
        if self.analyzer.df is None:
            QMessageBox.warning(self, "CSV 필요", "먼저 CSV 파일을 불러오세요.")
            return False
        return True

    def _start_task(
        self,
        status_text: str,
        task: Callable[[Callable[[], bool]], object],
        success_callback: Callable[[object], None],
    ) -> None:
        if self._task_thread is not None:
            QMessageBox.information(self, "작업 중", "현재 작업이 끝난 뒤 다시 시도하세요.")
            return
        self._set_busy(True, status_text)
        self._task_success_callback = success_callback
        self._task_thread = QThread(self)
        self._task_worker = TaskWorker(task)
        self._task_worker.moveToThread(self._task_thread)
        self._task_thread.started.connect(self._task_worker.run)
        self._task_worker.finished.connect(self._handle_task_success)
        self._task_worker.failed.connect(self._handle_task_failure)
        self._task_worker.cancelled.connect(self._handle_task_cancelled)
        self._task_worker.finished.connect(self._task_worker.deleteLater)
        self._task_worker.failed.connect(self._task_worker.deleteLater)
        self._task_worker.cancelled.connect(self._task_worker.deleteLater)
        self._task_worker.finished.connect(self._task_thread.quit)
        self._task_worker.failed.connect(self._task_thread.quit)
        self._task_worker.cancelled.connect(self._task_thread.quit)
        self._task_thread.finished.connect(self._cleanup_task)
        self._task_thread.start()

    def _set_busy(self, busy: bool, status_text: str) -> None:
        for widget in self.action_widgets:
            widget.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        self.status_label.setText(status_text)

    def cancel_current_task(self) -> None:
        if self._task_worker is None:
            return
        self._task_worker.cancel()
        self.cancel_button.setEnabled(False)
        self.status_label.setText("작업 취소를 요청했습니다. 안전하게 정리하는 중...")

    @pyqtSlot(object)
    def _handle_task_success(self, result: object) -> None:
        callback = self._task_success_callback
        try:
            if callback is not None:
                callback(result)
            self._set_busy(False, "작업이 완료되었습니다.")
        except Exception as error:
            self._set_busy(False, "결과를 표시하지 못했습니다.")
            QMessageBox.critical(self, "결과 표시 실패", str(error))

    @pyqtSlot(str)
    def _handle_task_failure(self, message: str) -> None:
        self._set_busy(False, "작업에 실패했습니다.")
        QMessageBox.critical(self, "오류", message)

    @pyqtSlot()
    def _handle_task_cancelled(self) -> None:
        self._set_busy(False, "작업을 취소했습니다.")

    @pyqtSlot()
    def _cleanup_task(self) -> None:
        if self._task_thread is not None:
            self._task_thread.deleteLater()
        self._task_worker = None
        self._task_thread = None
        self._task_success_callback = None
        if self._close_when_idle:
            self._close_when_idle = False
            QTimer.singleShot(0, self.close)

    def load_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSV 파일 선택", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        def loaded(count: object) -> None:
            self.sentiment_analyzer.reset()
            self.wordcloud_gen.reset()
            self.clear_result_history()
            self.current_file = file_path
            info = self.analyzer.session_info
            split_note = f" / 분할 파일 {info['file_count']}개 자동 병합" if info["file_count"] > 1 else ""
            warnings = list(info.get("quality_warnings", []))
            quality_note = f" / 품질 경고 {len(warnings)}개" if warnings else ""
            self.file_label.setText(
                f"{os.path.basename(file_path)} / {int(count):,}개 채팅{split_note}{quality_note}"
            )
            if warnings:
                self.status_label.setText(
                    "CSV를 불러왔지만 품질 경고가 있습니다. 결과를 편집 전에 확인하세요."
                )
                QMessageBox.warning(
                    self,
                    "CSV 로드 완료 - 품질 확인",
                    f"{int(count):,}개의 채팅을 불러왔습니다.{split_note}\n\n"
                    + "\n".join(f"- {warning}" for warning in warnings),
                )
            else:
                self.status_label.setText("CSV 로드 완료. 분석 조건을 선택하세요.")
                QMessageBox.information(
                    self,
                    "CSV 로드 완료",
                    f"{int(count):,}개의 채팅을 불러왔습니다.{split_note}",
                )

        self._start_task(
            "CSV 구조와 분할 파일을 확인하는 중...",
            lambda cancel_check: self.analyzer.load_csv(
                file_path,
                cancel_check=cancel_check,
            ),
            loaded,
        )

    def analyze_chat_density(self) -> None:
        if not self._require_source():
            return
        try:
            interval = self._read_positive(self.interval_input, "분석 간격")
        except ValueError as error:
            QMessageBox.warning(self, "입력 확인", str(error))
            return
        sensitivity = self.sensitivity_slider.value() / 10.0
        self._start_task(
            "채팅 흐름과 실제 피크를 분석하는 중...",
            lambda cancel_check: self.analyzer.analyze_chat_density(
                interval,
                sensitivity,
                cancel_check=cancel_check,
            ),
            lambda result: self._show_flow_result("density", result, interval, sensitivity),
        )

    def analyze_keyword(self) -> None:
        if not self._require_source():
            return
        keyword = self.keyword_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "입력 확인", "검색 키워드를 입력하세요.")
            return
        try:
            interval = self._read_positive(self.interval_input, "분석 간격")
        except ValueError as error:
            QMessageBox.warning(self, "입력 확인", str(error))
            return
        sensitivity = self.sensitivity_slider.value() / 10.0
        self._start_task(
            f"'{keyword}' 키워드 흐름을 분석하는 중...",
            lambda cancel_check: self.analyzer.analyze_keyword(
                keyword,
                interval,
                sensitivity,
                cancel_check=cancel_check,
            ),
            lambda result: self._show_flow_result("keyword", result, interval, sensitivity, keyword),
        )

    def _show_flow_result(
        self,
        kind: str,
        result: Dict,
        interval: float,
        sensitivity: float,
        keyword: str = "",
    ) -> None:
        timeline = pd.DataFrame(result["timeline"])
        events = list(result["events"])
        status_text = {
            "ok": "통계적으로 구분되는 사건을 찾았습니다.",
            "no_events": "현재 조건에서 뚜렷한 사건을 찾지 못했습니다.",
            "no_evidence": "분석할 일반 채팅이 없어 통계 판정을 보류했습니다.",
            "insufficient_data": "시간 구간이 3개 미만이라 통계 판정을 보류했습니다.",
        }.get(result["status"], result["status"])
        if kind == "keyword":
            summary = (
                f"키워드: {keyword} / 포함 메시지 {result['total_count']:,}개 / "
                f"실제 출현 {result['occurrence_count']:,}회 / 사건 {len(events)}개\n"
                f"간격 {interval:g}분 / 민감도 {sensitivity:.1f} / {status_text}"
            )
            title = f"키워드 · {keyword}"
        else:
            summary = (
                f"비시스템 채팅 {result['total_count']:,}개 / 사건 {len(events)}개 / "
                f"간격 {interval:g}분 / 민감도 {sensitivity:.1f}\n{status_text}"
            )
            title = "채팅 밀도"
        count_label = "키워드 출현" if kind == "keyword" else "채팅 수"
        peak_label = "피크 15초 출현" if kind == "keyword" else "피크 15초 채팅"
        figure = self._make_flow_figure(timeline, events, title, count_label)
        if len(timeline) > self.MAX_DISPLAY_POINTS:
            summary += (
                f"\n화면 그래프는 {len(timeline):,}개 구간을 "
                f"최대 {self.MAX_DISPLAY_POINTS:,}개 점으로 축약했으며 분석·내보내기 값은 원본을 사용합니다."
            )
        columns = [
            ("event_id", "번호"), ("start_seconds", "사건 시작"),
            ("peak_seconds", "실제 피크"), ("end_seconds", "사건 종료"),
            ("count", count_label), ("peak_window_count", peak_label),
            ("lift", "기준 대비"), ("confidence", "신뢰도"),
            ("unique_users", "고유 참여자"),
            ("top_user_share", "최다 참여자 점유율"),
            ("duplicate_share", "동일 행 비율"),
            ("participant_dispersion", "참여자 분산도"),
            ("reaction_scope", "반응 범위"),
        ]
        metadata = {
            "kind": kind,
            "keyword": keyword,
            "interval_minutes": interval,
            "sensitivity": sensitivity,
        }
        self._add_result_tab(
            title,
            summary,
            figure,
            events,
            columns,
            editor_snapshot={
                "kind": kind,
                "events": pd.DataFrame(events).copy(deep=True),
                "metadata": metadata,
            },
        )

    def _make_flow_figure(
        self,
        timeline: pd.DataFrame,
        events: List[Dict],
        title: str,
        count_label: str,
    ) -> Figure:
        figure = Figure(figsize=(12, 5.2), facecolor="#2a2a3e")
        axis = figure.add_subplot(111)
        self._style_axis(axis)
        display_timeline = self._downsample_timeline(timeline)
        x = display_timeline["time_seconds"].astype(float) / 60
        width = max(0.1, (x.iloc[1] - x.iloc[0]) * 0.82) if len(x) > 1 else 0.8
        colors = [
            "#f59e0b" if bool(value) else "#6366f1"
            for value in display_timeline["is_candidate"]
        ]
        axis.bar(
            x,
            display_timeline["count"],
            width=width,
            color=colors,
            alpha=0.88,
            label=count_label,
        )
        if display_timeline["threshold"].gt(0).any():
            axis.plot(
                x,
                display_timeline["threshold"],
                color="#a0a0b0",
                linewidth=1.2,
                label="지역 임계선",
            )
        for event in events:
            peak_minutes = float(event["peak_seconds"]) / 60
            axis.axvline(peak_minutes, color="#10b981", linewidth=1.6, linestyle="--")
            axis.annotate(
                self.analyzer.seconds_to_time(event["peak_seconds"]),
                (peak_minutes, max(1, event["peak_window_count"])),
                xytext=(4, 8),
                textcoords="offset points",
                color="#10b981",
                fontsize=8,
            )
        axis.set_title(title, color="#e0e0e0", fontsize=13, fontweight="bold")
        axis.set_xlabel("재생 시간(분)", color="#e0e0e0")
        axis.set_ylabel(count_label, color="#e0e0e0")
        axis.legend(loc="upper right", fontsize=8)
        figure.tight_layout(pad=2)
        return figure

    def _downsample_timeline(self, timeline: pd.DataFrame) -> pd.DataFrame:
        """Bound display artists while preserving the strongest value in each block."""
        if len(timeline) <= self.MAX_DISPLAY_POINTS:
            return timeline
        stride = math.ceil(len(timeline) / self.MAX_DISPLAY_POINTS)
        work = timeline.copy()
        work["_display_group"] = range(len(work))
        work["_display_group"] //= stride
        aggregations = {
            "time_seconds": "first",
            "count": "max",
            "threshold": "max",
            "is_candidate": "max",
        }
        return work.groupby("_display_group", observed=False).agg(aggregations).reset_index(drop=True)

    def analyze_sentiment(self) -> None:
        if not self._require_source():
            return
        try:
            interval = self._read_positive(self.sentiment_interval_input, "분석 간격")
        except ValueError as error:
            QMessageBox.warning(self, "입력 확인", str(error))
            return
        self._start_task(
            "정서 방향과 반응 강도를 분리해 분석하는 중...",
            lambda cancel_check: self.sentiment_analyzer.analyze_timeline(
                self.analyzer.df,
                interval,
                cancel_check=cancel_check,
            ),
            lambda timeline: self._show_sentiment_result(timeline, interval),
        )

    def _show_sentiment_result(self, timeline: object, interval: float) -> None:
        timeline = pd.DataFrame(timeline)
        changes = self.sentiment_analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)
        summary_data = self.sentiment_analyzer.get_summary()
        sentiment_evidence = int(summary_data.get("sentiment_message_count", 0))
        coverage = float(summary_data["coverage"])
        valence_is_supported = (
            not math.isnan(float(summary_data["valence"]))
            and sentiment_evidence >= 3
            and coverage >= 0.03
        )
        valence_text = (
            f"{float(summary_data['valence']):+.2f}"
            if valence_is_supported
            else f"근거 부족 (정서 표현 {sentiment_evidence}개)"
        )
        arousal_text = (
            "근거 부족" if math.isnan(float(summary_data["arousal"]))
            else f"{float(summary_data['arousal']):.2f}"
        )
        summary = (
            f"전체 정서 방향 {valence_text} / 평균 반응 강도 {arousal_text} / "
            f"정서 근거 커버리지 {coverage:.1%}\n"
            f"분석 채팅 {int(summary_data['message_count']):,}개 / 변화 지점 {len(changes)}개 / 간격 {interval:g}분\n"
            "변화 판정: 인접 구간 모두 정서 근거 2개 이상 · 커버리지 3% 이상"
        )
        figure = self._make_sentiment_figure(timeline, changes)
        if len(timeline) > self.MAX_DISPLAY_POINTS:
            summary += (
                f"\n화면 그래프는 {len(timeline):,}개 구간을 표시용으로 축약했으며 "
                "변화 판정은 원본 구간을 사용합니다."
            )
        columns = [
            ("time_seconds", "시점"), ("type", "유형"),
            ("valence", "정서 방향"), ("arousal", "반응 강도"),
            ("change", "변화량"), ("coverage", "근거 커버리지"),
            ("sentiment_message_count", "정서 근거 메시지"),
            ("evidence_count", "근거 신호"), ("description", "설명"),
        ]
        self._add_result_tab(
            "분위기",
            summary,
            figure,
            changes,
            columns,
            mood_snapshot=[dict(change) for change in changes],
        )

    def _make_sentiment_figure(self, timeline: pd.DataFrame, changes: List[Dict]) -> Figure:
        figure = Figure(figsize=(12, 6.4), facecolor="#2a2a3e")
        valence_axis = figure.add_subplot(211)
        volume_axis = figure.add_subplot(212, sharex=valence_axis)
        self._style_axis(valence_axis)
        self._style_axis(volume_axis)
        display_timeline = self._downsample_sentiment_timeline(timeline)
        x = display_timeline["time_seconds"].astype(float) / 60
        valence_axis.plot(
            x,
            display_timeline["valence"],
            color="#10b981",
            linewidth=2,
            label="정서 방향",
        )
        valence_axis.plot(
            x,
            display_timeline["arousal"],
            color="#f59e0b",
            linewidth=1.5,
            label="반응 강도",
        )
        valence_axis.axhline(0, color="#a0a0b0", linewidth=0.8, linestyle="--")
        valence_axis.set_ylim(-1.05, 1.05)
        valence_axis.set_ylabel("점수", color="#e0e0e0")
        valence_axis.legend(loc="upper right", fontsize=8)
        for change in changes[:10]:
            marker_x = float(change["time_seconds"]) / 60
            valence_axis.axvline(marker_x, color="#8b5cf6", alpha=0.55, linestyle=":")
            volume_axis.axvline(marker_x, color="#8b5cf6", alpha=0.55, linestyle=":")
        volume_axis.bar(
            x,
            display_timeline["message_count"],
            color="#6366f1",
            alpha=0.82,
        )
        volume_axis.set_xlabel("재생 시간(분)", color="#e0e0e0")
        volume_axis.set_ylabel("메시지 수", color="#e0e0e0")
        valence_axis.set_title("정서 방향과 반응 강도", color="#e0e0e0", fontweight="bold")
        figure.tight_layout(pad=2)
        return figure

    def _downsample_sentiment_timeline(self, timeline: pd.DataFrame) -> pd.DataFrame:
        if len(timeline) <= self.MAX_DISPLAY_POINTS:
            return timeline
        stride = math.ceil(len(timeline) / self.MAX_DISPLAY_POINTS)
        work = timeline.copy()
        work["_display_group"] = range(len(work))
        work["_display_group"] //= stride
        return (
            work.groupby("_display_group", observed=False)
            .agg(
                time_seconds=("time_seconds", "first"),
                valence=("valence", "mean"),
                arousal=("arousal", "mean"),
                message_count=("message_count", "sum"),
            )
            .reset_index(drop=True)
        )

    def generate_wordcloud(self) -> None:
        if not self._require_source():
            return

        def task(cancel_check: Callable[[], bool]) -> bool:
            text = self.analyzer.get_all_text()
            if not text.strip():
                raise ValueError("분석할 텍스트가 없습니다.")
            return self.wordcloud_gen.generate(text, cancel_check=cancel_check)

        self._start_task("표현 분포 이미지를 생성하는 중...", task, self._show_wordcloud_result)

    def _show_wordcloud_result(self, success: object) -> None:
        if not success or self.wordcloud_gen.get_wordcloud() is None:
            QMessageBox.warning(self, "결과", "표현 분포 이미지를 생성하지 못했습니다.")
            return
        figure = Figure(figsize=(12, 5.2), facecolor="#2a2a3e")
        axis = figure.add_subplot(111)
        axis.imshow(self.wordcloud_gen.get_wordcloud(), interpolation="bilinear")
        axis.axis("off")
        axis.set_title("채팅 표현 분포", color="#e0e0e0", fontweight="bold")
        figure.tight_layout(pad=1)
        image_snapshot = self.wordcloud_gen.get_wordcloud().to_image().copy()
        self._add_result_tab(
            "표현 분포",
            "시스템 메시지를 제외한 공백 기준 표현을 사용했습니다. 형태소 분석 결과가 아닙니다.",
            figure,
            [],
            [],
            wordcloud_snapshot=image_snapshot,
        )

    def save_wordcloud(self) -> None:
        tab = self.result_tabs.currentWidget()
        snapshot = getattr(tab, "wordcloud_snapshot", None) if tab is not None else None
        if snapshot is None:
            QMessageBox.warning(
                self,
                "결과 없음",
                "저장할 표현 분포 결과 탭을 선택하세요.",
            )
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "표현 분포 이미지 저장", "wordcloud.png", "PNG Files (*.png)"
        )
        if file_path:
            file_path = self._ensure_extension(file_path, ".png")
            try:
                self.wordcloud_gen.save(file_path, image=snapshot)
                QMessageBox.information(self, "저장 완료", file_path)
            except Exception as error:
                QMessageBox.critical(self, "저장 실패", str(error))

    @staticmethod
    def _ensure_extension(file_path: str, extension: str) -> str:
        return file_path if file_path.casefold().endswith(extension.casefold()) else file_path + extension

    def _selected_editor_snapshot(self, kind: str) -> Optional[Dict]:
        tab = self.result_tabs.currentWidget()
        snapshot = getattr(tab, "editor_snapshot", None) if tab is not None else None
        if isinstance(snapshot, dict) and snapshot.get("kind") == kind:
            return snapshot
        return None

    def _sync_export_kind_to_tab(self, index: int) -> None:
        tab = self.result_tabs.widget(index) if index >= 0 else None
        snapshot = getattr(tab, "editor_snapshot", None) if tab is not None else None
        if not isinstance(snapshot, dict):
            return
        combo_index = self.export_kind.findData(snapshot.get("kind"))
        if combo_index >= 0:
            self.export_kind.setCurrentIndex(combo_index)

    def export_editor_result(self) -> None:
        kind = str(self.export_kind.currentData())
        export_format = str(self.export_format.currentData())
        snapshot = self._selected_editor_snapshot(kind)
        snapshot_kwargs = {}
        if snapshot is not None:
            snapshot_kwargs = {
                "events": snapshot["events"],
                "metadata": snapshot["metadata"],
            }
        try:
            pre_roll = self._read_nonnegative(self.pre_roll_input, "프리롤")
            post_roll = self._read_nonnegative(self.post_roll_input, "포스트롤")
            self.analyzer.build_editor_moments(
                kind,
                pre_roll,
                post_roll,
                **snapshot_kwargs,
            )
        except ValueError as error:
            QMessageBox.warning(self, "내보내기 확인", str(error))
            return

        config = {
            "csv": ("editor_moments.csv", "CSV Files (*.csv)", ".csv"),
            "premiere_xml": ("premiere_markers.xml", "XML Files (*.xml)", ".xml"),
            "fcpxml": ("final_cut_markers.fcpxml", "FCPXML Files (*.fcpxml)", ".fcpxml"),
        }
        default_name, file_filter, extension = config[export_format]
        file_path, _ = QFileDialog.getSaveFileName(
            self, "편집 결과 저장", default_name, file_filter
        )
        if not file_path:
            return
        file_path = self._ensure_extension(file_path, extension)
        try:
            fps = float(self.fps_combo.currentData())
            if export_format == "csv":
                self.analyzer.export_editor_csv(
                    file_path,
                    kind,
                    pre_roll,
                    post_roll,
                    **snapshot_kwargs,
                )
            elif export_format == "premiere_xml":
                self.analyzer.export_premiere_xml(
                    file_path,
                    kind,
                    fps,
                    pre_roll,
                    post_roll,
                    **snapshot_kwargs,
                )
            else:
                self.analyzer.export_fcpxml(
                    file_path,
                    kind,
                    fps,
                    pre_roll,
                    post_roll,
                    **snapshot_kwargs,
                )
            QMessageBox.information(self, "내보내기 완료", file_path)
        except Exception as error:
            QMessageBox.critical(self, "내보내기 실패", str(error))

    def export_mood_markers(self) -> None:
        tab = self.result_tabs.currentWidget()
        changes = getattr(tab, "mood_snapshot", None) if tab is not None else None
        if not changes:
            QMessageBox.warning(
                self,
                "결과 없음",
                "저장할 분위기 결과 탭을 선택하세요.",
            )
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "분위기 변화 작업표 저장", "mood_changes.csv", "CSV Files (*.csv)"
        )
        if file_path:
            file_path = self._ensure_extension(file_path, ".csv")
            try:
                self.sentiment_analyzer.export_mood_markers(
                    file_path,
                    top_n=20,
                    changes=changes,
                )
                QMessageBox.information(self, "저장 완료", file_path)
            except Exception as error:
                QMessageBox.critical(self, "저장 실패", str(error))

    def _add_result_tab(
        self,
        title: str,
        summary: str,
        figure: Figure,
        rows: List[Dict],
        columns: List[tuple[str, str]],
        editor_snapshot: Optional[Dict] = None,
        mood_snapshot: Optional[List[Dict]] = None,
        wordcloud_snapshot: object = None,
    ) -> QWidget:
        while self.result_tabs.count() >= self.MAX_RESULT_TABS:
            self._close_result_tab(0)
        tab = QWidget()
        tab.editor_snapshot = editor_snapshot
        tab.mood_snapshot = mood_snapshot
        tab.wordcloud_snapshot = wordcloud_snapshot
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setMinimumWidth(700)
        layout = QVBoxLayout(content)
        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary_label)
        if columns:
            table = self._make_evidence_table(rows, columns)
            layout.addWidget(table)
        canvas = FigureCanvasQTAgg(figure)
        canvas.setMinimumSize(700, 430 if len(figure.axes) == 1 else 560)
        layout.addWidget(canvas)
        layout.addStretch()
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        self.result_tabs.addTab(tab, title)
        self.result_tabs.setCurrentWidget(tab)
        return tab

    def _make_evidence_table(
        self, rows: List[Dict], columns: List[tuple[str, str]]
    ) -> QTableWidget:
        table = QTableWidget(len(rows), len(columns))
        table.setHorizontalHeaderLabels([label for _, label in columns])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        for row_index, row in enumerate(rows):
            for column_index, (key, _) in enumerate(columns):
                value = row.get(key, "")
                if key.endswith("seconds") and value != "":
                    value = self.analyzer.seconds_to_time(float(value))
                elif key in {
                    "confidence",
                    "coverage",
                    "top_user_share",
                    "duplicate_share",
                    "participant_dispersion",
                } and value != "":
                    value = f"{float(value):.0%}"
                elif isinstance(value, float):
                    value = f"{value:.2f}"
                table.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if columns:
            table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(min(260, 76 + len(rows) * 28))
        return table

    @staticmethod
    def _style_axis(axis) -> None:
        axis.set_facecolor("#2a2a3e")
        axis.tick_params(axis="both", colors="#e0e0e0", labelsize=8)
        axis.grid(axis="y", alpha=0.18, color="#e0e0e0", linestyle="--", linewidth=0.5)
        axis.spines["bottom"].set_color("#3a3a4e")
        axis.spines["left"].set_color("#3a3a4e")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)

    def _close_result_tab(self, index: int) -> None:
        widget = self.result_tabs.widget(index)
        self.result_tabs.removeTab(index)
        if widget is not None:
            for canvas in widget.findChildren(FigureCanvasQTAgg):
                canvas.figure.clear()
                canvas.close()
            widget.deleteLater()

    def clear_result_history(self) -> None:
        while self.result_tabs.count():
            self._close_result_tab(0)

    def closeEvent(self, event) -> None:
        if self._task_thread is not None and self._task_thread.isRunning():
            answer = QMessageBox.question(
                self,
                "작업 취소 후 종료",
                "현재 작업을 취소하고 안전하게 정리한 뒤 앱을 닫을까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._close_when_idle = True
                self.cancel_current_task()
            event.ignore()
            return
        event.accept()


def create_window_for_test() -> MainWindow:
    """Small test seam for headless UI smoke tests."""
    if QApplication.instance() is None:
        QApplication([])
    return MainWindow()
