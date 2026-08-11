from __future__ import annotations

"""Responsive PyQt interface for evidence-first chat moment analysis."""

import math
import os
import platform
from typing import Callable, Dict, List, Optional

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import pandas as pd
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
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

    def __init__(self, task: Callable[[], object]):
        super().__init__()
        self.task = task

    @pyqtSlot()
    def run(self) -> None:
        try:
            self.finished.emit(self.task())
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = ChatAnalyzer()
        self.wordcloud_gen = WordCloudGenerator()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.current_file: Optional[str] = None
        self._task_thread: Optional[QThread] = None
        self._task_worker: Optional[TaskWorker] = None
        self._task_success_callback: Optional[Callable[[object], None]] = None
        self.action_widgets: List[QWidget] = []
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("치지직 클립 모먼트 캐처")
        self.resize(1240, 860)
        self.setMinimumSize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
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
        status_layout.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMaximumWidth(220)
        self.progress.hide()
        status_layout.addWidget(self.progress)
        main_layout.addLayout(status_layout)

        self.result_tabs = QTabWidget()
        self.result_tabs.setTabsClosable(True)
        self.result_tabs.tabCloseRequested.connect(self._close_result_tab)
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
        keyword_row.addWidget(QLabel("키워드"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("예: ㅋㅋ, 레전드")
        keyword_row.addWidget(self.keyword_input, 1)
        layout.addLayout(keyword_row)

        option_row = QHBoxLayout()
        option_row.addWidget(QLabel("간격(분)"))
        self.interval_input = self._positive_number_input("1")
        option_row.addWidget(self.interval_input)
        option_row.addWidget(QLabel("민감도"))
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(10, 30)
        self.sensitivity_slider.setValue(20)
        self.sensitivity_slider.setMaximumWidth(130)
        self.sensitivity_slider.setToolTip(
            "낮음: 큰 반응만 포착\n보통: 균형 잡힌 감지\n높음: 작은 반응도 포착"
        )
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
        row.addWidget(QLabel("간격(분)"))
        self.sentiment_interval_input = self._positive_number_input("1")
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
        group = QGroupBox("단어 분포")
        layout = QVBoxLayout(group)
        generate_button = QPushButton("워드클라우드 생성")
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
        layout.addWidget(QLabel("결과"))
        self.export_kind = QComboBox()
        self.export_kind.addItem("채팅 밀도", "density")
        self.export_kind.addItem("키워드", "keyword")
        layout.addWidget(self.export_kind)
        layout.addWidget(QLabel("형식"))
        self.export_format = QComboBox()
        self.export_format.addItem("편집 작업표 CSV", "csv")
        self.export_format.addItem("Premiere 교환 XML", "premiere_xml")
        self.export_format.addItem("Final Cut FCPXML", "fcpxml")
        layout.addWidget(self.export_format, 1)
        layout.addWidget(QLabel("프리롤"))
        self.pre_roll_input = self._nonnegative_number_input("15")
        layout.addWidget(self.pre_roll_input)
        layout.addWidget(QLabel("포스트롤"))
        self.post_roll_input = self._nonnegative_number_input("20")
        layout.addWidget(self.post_roll_input)
        layout.addWidget(QLabel("FPS"))
        self.fps_combo = QComboBox()
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
        task: Callable[[], object],
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
        self._task_worker.finished.connect(self._task_worker.deleteLater)
        self._task_worker.failed.connect(self._task_worker.deleteLater)
        self._task_worker.finished.connect(self._task_thread.quit)
        self._task_worker.failed.connect(self._task_thread.quit)
        self._task_thread.finished.connect(self._cleanup_task)
        self._task_thread.start()

    def _set_busy(self, busy: bool, status_text: str) -> None:
        for widget in self.action_widgets:
            widget.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.status_label.setText(status_text)

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
    def _cleanup_task(self) -> None:
        if self._task_thread is not None:
            self._task_thread.deleteLater()
        self._task_worker = None
        self._task_thread = None
        self._task_success_callback = None

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
            self.file_label.setText(
                f"{os.path.basename(file_path)} / {int(count):,}개 채팅{split_note}"
            )
            self.status_label.setText("CSV 로드 완료. 분석 조건을 선택하세요.")
            QMessageBox.information(
                self,
                "CSV 로드 완료",
                f"{int(count):,}개의 채팅을 불러왔습니다.{split_note}",
            )

        self._start_task(
            "CSV 구조와 분할 파일을 확인하는 중...",
            lambda: self.analyzer.load_csv(file_path),
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
            lambda: self.analyzer.analyze_chat_density(interval, sensitivity),
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
            lambda: self.analyzer.analyze_keyword(keyword, interval, sensitivity),
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
        columns = [
            ("event_id", "번호"), ("start_seconds", "사건 시작"),
            ("peak_seconds", "실제 피크"), ("end_seconds", "사건 종료"),
            ("count", count_label), ("peak_window_count", peak_label),
            ("lift", "기준 대비"), ("confidence", "신뢰도"),
            ("unique_users", "닉네임 수"), ("top_user_share", "최다 닉네임 비율"),
        ]
        self._add_result_tab(title, summary, figure, events, columns)

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
        x = timeline["time_seconds"].astype(float) / 60
        width = max(0.1, (x.iloc[1] - x.iloc[0]) * 0.82) if len(x) > 1 else 0.8
        colors = ["#f59e0b" if bool(value) else "#6366f1" for value in timeline["is_candidate"]]
        axis.bar(x, timeline["count"], width=width, color=colors, alpha=0.88, label=count_label)
        if timeline["threshold"].gt(0).any():
            axis.plot(x, timeline["threshold"], color="#a0a0b0", linewidth=1.2, label="지역 임계선")
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
            lambda: self.sentiment_analyzer.analyze_timeline(self.analyzer.df, interval),
            lambda timeline: self._show_sentiment_result(timeline, interval),
        )

    def _show_sentiment_result(self, timeline: object, interval: float) -> None:
        timeline = pd.DataFrame(timeline)
        changes = self.sentiment_analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)
        summary_data = self.sentiment_analyzer.get_summary()
        valence_text = (
            "근거 부족" if math.isnan(float(summary_data["valence"]))
            else f"{float(summary_data['valence']):+.2f}"
        )
        arousal_text = (
            "근거 부족" if math.isnan(float(summary_data["arousal"]))
            else f"{float(summary_data['arousal']):.2f}"
        )
        summary = (
            f"전체 정서 방향 {valence_text} / 평균 반응 강도 {arousal_text} / "
            f"정서 근거 커버리지 {float(summary_data['coverage']):.1%}\n"
            f"분석 채팅 {int(summary_data['message_count']):,}개 / 변화 지점 {len(changes)}개 / 간격 {interval:g}분\n"
            "변화 판정: 인접 구간 모두 정서 근거 2개 이상 · 커버리지 3% 이상"
        )
        figure = self._make_sentiment_figure(timeline, changes)
        columns = [
            ("time_seconds", "시점"), ("type", "유형"),
            ("valence", "정서 방향"), ("arousal", "반응 강도"),
            ("change", "변화량"), ("coverage", "근거 커버리지"),
            ("sentiment_message_count", "정서 근거 메시지"),
            ("evidence_count", "근거 신호"), ("description", "설명"),
        ]
        self._add_result_tab("분위기", summary, figure, changes, columns)

    def _make_sentiment_figure(self, timeline: pd.DataFrame, changes: List[Dict]) -> Figure:
        figure = Figure(figsize=(12, 6.4), facecolor="#2a2a3e")
        valence_axis = figure.add_subplot(211)
        volume_axis = figure.add_subplot(212, sharex=valence_axis)
        self._style_axis(valence_axis)
        self._style_axis(volume_axis)
        x = timeline["time_seconds"].astype(float) / 60
        valence_axis.plot(x, timeline["valence"], color="#10b981", linewidth=2, label="정서 방향")
        valence_axis.plot(x, timeline["arousal"], color="#f59e0b", linewidth=1.5, label="반응 강도")
        valence_axis.axhline(0, color="#a0a0b0", linewidth=0.8, linestyle="--")
        valence_axis.set_ylim(-1.05, 1.05)
        valence_axis.set_ylabel("점수", color="#e0e0e0")
        valence_axis.legend(loc="upper right", fontsize=8)
        for change in changes[:10]:
            marker_x = float(change["time_seconds"]) / 60
            valence_axis.axvline(marker_x, color="#8b5cf6", alpha=0.55, linestyle=":")
            volume_axis.axvline(marker_x, color="#8b5cf6", alpha=0.55, linestyle=":")
        volume_axis.bar(x, timeline["message_count"], color="#6366f1", alpha=0.82)
        volume_axis.set_xlabel("재생 시간(분)", color="#e0e0e0")
        volume_axis.set_ylabel("메시지 수", color="#e0e0e0")
        valence_axis.set_title("정서 방향과 반응 강도", color="#e0e0e0", fontweight="bold")
        figure.tight_layout(pad=2)
        return figure

    def generate_wordcloud(self) -> None:
        if not self._require_source():
            return

        def task() -> bool:
            text = self.analyzer.get_all_text()
            if not text.strip():
                raise ValueError("분석할 텍스트가 없습니다.")
            return self.wordcloud_gen.generate(text)

        self._start_task("단어 분포 이미지를 생성하는 중...", task, self._show_wordcloud_result)

    def _show_wordcloud_result(self, success: object) -> None:
        if not success or self.wordcloud_gen.get_wordcloud() is None:
            QMessageBox.warning(self, "결과", "워드클라우드를 생성하지 못했습니다.")
            return
        figure = Figure(figsize=(12, 5.2), facecolor="#2a2a3e")
        axis = figure.add_subplot(111)
        axis.imshow(self.wordcloud_gen.get_wordcloud(), interpolation="bilinear")
        axis.axis("off")
        axis.set_title("채팅 단어 분포", color="#e0e0e0", fontweight="bold")
        figure.tight_layout(pad=1)
        self._add_result_tab(
            "단어 분포",
            "시스템 메시지를 제외한 정제 텍스트를 사용했습니다.",
            figure,
            [],
            [],
        )

    def save_wordcloud(self) -> None:
        if self.wordcloud_gen.get_wordcloud() is None:
            QMessageBox.warning(self, "결과 없음", "먼저 워드클라우드를 생성하세요.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "워드클라우드 저장", "wordcloud.png", "PNG Files (*.png)"
        )
        if file_path:
            self.wordcloud_gen.save(file_path)
            QMessageBox.information(self, "저장 완료", file_path)

    def export_editor_result(self) -> None:
        kind = str(self.export_kind.currentData())
        export_format = str(self.export_format.currentData())
        try:
            pre_roll = self._read_nonnegative(self.pre_roll_input, "프리롤")
            post_roll = self._read_nonnegative(self.post_roll_input, "포스트롤")
            self.analyzer.build_editor_moments(kind, pre_roll, post_roll)
        except ValueError as error:
            QMessageBox.warning(self, "내보내기 확인", str(error))
            return

        config = {
            "csv": ("editor_moments.csv", "CSV Files (*.csv)"),
            "premiere_xml": ("premiere_markers.xml", "XML Files (*.xml)"),
            "fcpxml": ("final_cut_markers.fcpxml", "FCPXML Files (*.fcpxml)"),
        }
        default_name, file_filter = config[export_format]
        file_path, _ = QFileDialog.getSaveFileName(
            self, "편집 결과 저장", default_name, file_filter
        )
        if not file_path:
            return
        try:
            fps = float(self.fps_combo.currentData())
            if export_format == "csv":
                self.analyzer.export_editor_csv(file_path, kind, pre_roll, post_roll)
            elif export_format == "premiere_xml":
                self.analyzer.export_premiere_xml(file_path, kind, fps, pre_roll, post_roll)
            else:
                self.analyzer.export_fcpxml(file_path, kind, fps, pre_roll, post_roll)
            QMessageBox.information(self, "내보내기 완료", file_path)
        except Exception as error:
            QMessageBox.critical(self, "내보내기 실패", str(error))

    def export_mood_markers(self) -> None:
        if not self.sentiment_analyzer.get_mood_changes():
            QMessageBox.warning(self, "결과 없음", "먼저 분위기 분석을 실행하세요.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "분위기 변화 작업표 저장", "mood_changes.csv", "CSV Files (*.csv)"
        )
        if file_path:
            self.sentiment_analyzer.export_mood_markers(file_path, top_n=20)
            QMessageBox.information(self, "저장 완료", file_path)

    def _add_result_tab(
        self,
        title: str,
        summary: str,
        figure: Figure,
        rows: List[Dict],
        columns: List[tuple[str, str]],
    ) -> None:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setMinimumWidth(900)
        layout = QVBoxLayout(content)
        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary_label)
        if columns:
            table = self._make_evidence_table(rows, columns)
            layout.addWidget(table)
        canvas = FigureCanvasQTAgg(figure)
        canvas.setMinimumSize(900, 430 if len(figure.axes) == 1 else 560)
        layout.addWidget(canvas)
        layout.addStretch()
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        self.result_tabs.addTab(tab, title)
        self.result_tabs.setCurrentWidget(tab)

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
                elif key in {"confidence", "coverage", "top_user_share"} and value != "":
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
            widget.deleteLater()

    def clear_result_history(self) -> None:
        while self.result_tabs.count():
            self._close_result_tab(0)

    def closeEvent(self, event) -> None:
        if self._task_thread is not None and self._task_thread.isRunning():
            QMessageBox.information(self, "작업 중", "현재 분석이 끝난 뒤 앱을 닫아주세요.")
            event.ignore()
            return
        event.accept()


def create_window_for_test() -> MainWindow:
    """Small test seam for headless UI smoke tests."""
    if QApplication.instance() is None:
        QApplication([])
    return MainWindow()
