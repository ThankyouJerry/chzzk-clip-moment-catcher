import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import pandas as pd
from matplotlib.figure import Figure
from PIL import Image
from PyQt6.QtTest import QSignalSpy
from PyQt6.QtWidgets import QApplication, QFileDialog, QLabel, QMessageBox, QWidget

from core.errors import TaskCancelled
from ui.main_window import MainWindow, TaskWorker


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    result = MainWindow()
    yield result
    result.close()
    app.processEvents()


def test_window_exposes_unambiguous_editor_exports(window):
    labels = [window.export_format.itemText(index) for index in range(window.export_format.count())]

    assert window.windowTitle() == "치지직 클립 모먼트 캐처"
    assert labels == ["편집 작업표 CSV", "Premiere 교환 XML", "Final Cut FCPXML"]
    assert window.result_tabs.count() == 0
    assert window.minimumWidth() <= 800
    assert window.minimumHeight() <= 600


@pytest.mark.parametrize(
    "slider_value,expected",
    [(10, "낮음 (1.0)"), (20, "보통 (2.0)"), (30, "높음 (3.0)")],
)
def test_sensitivity_label_matches_detection_direction(window, slider_value, expected):
    window.update_sensitivity_label(slider_value)

    assert window.sensitivity_value_label.text() == expected


def test_result_tabs_preserve_history_until_explicitly_cleared(window):
    for title in ("채팅 밀도", "키워드 · ㅋㅋ"):
        figure = Figure()
        figure.add_subplot(111)
        window._add_result_tab(title, "요약", figure, [], [])

    assert window.result_tabs.count() == 2
    assert window.result_tabs.tabText(0) == "채팅 밀도"
    assert window.result_tabs.tabText(1) == "키워드 · ㅋㅋ"

    window.clear_result_history()
    assert window.result_tabs.count() == 0


def test_evidence_table_formats_times_and_confidence(window):
    table = window._make_evidence_table(
        [{"peak_seconds": 90, "confidence": 0.82, "count": 12}],
        [("peak_seconds", "피크"), ("confidence", "신뢰도"), ("count", "채팅")],
    )

    assert table.item(0, 0).text() == "00:01:30"
    assert table.item(0, 1).text() == "82%"
    assert table.item(0, 2).text() == "12"


def test_numeric_readers_reject_nonfinite_values(window):
    window.pre_roll_input.setText("inf")

    with pytest.raises(ValueError, match="0 이상의 유한한"):
        window._read_nonnegative(window.pre_roll_input, "프리롤")


def test_system_only_sentiment_result_renders_without_crashing(window):
    frame = pd.DataFrame([
        {
            "seconds": 15.0,
            "clean_message": "system notice",
            "is_system": True,
        }
    ])
    timeline = window.sentiment_analyzer.analyze_timeline(frame, interval_minutes=1)

    window._show_sentiment_result(timeline, interval=1)

    assert window.result_tabs.count() == 1
    assert window.result_tabs.tabText(0) == "분위기"
    summary_text = "\n".join(
        label.text() for label in window.result_tabs.widget(0).findChildren(QLabel)
    )
    assert "전체 정서 방향 근거 부족" in summary_text
    assert "평균 반응 강도 근거 부족" in summary_text
    assert "nan" not in summary_text.casefold()


def test_single_sentiment_expression_is_labeled_as_insufficient_evidence(window):
    frame = pd.DataFrame([
        {
            "seconds": 1.0,
            "clean_message": "대박",
            "message_raw": "대박",
            "custom_emote_count": 0,
            "is_system": False,
        }
    ])
    timeline = window.sentiment_analyzer.analyze_timeline(frame, interval_minutes=1)

    window._show_sentiment_result(timeline, interval=1)

    summary_text = "\n".join(
        label.text() for label in window.result_tabs.widget(0).findChildren(QLabel)
    )
    assert "전체 정서 방향 근거 부족 (정서 표현 1개)" in summary_text
    assert "전체 정서 방향 +" not in summary_text


def test_cancelled_worker_emits_cancelled_instead_of_success():
    def cooperative_task(cancel_check):
        if cancel_check():
            raise TaskCancelled("cancelled")
        return "result"

    worker = TaskWorker(cooperative_task)
    cancelled = QSignalSpy(worker.cancelled)
    finished = QSignalSpy(worker.finished)

    worker.cancel()
    worker.run()

    assert len(cancelled) == 1
    assert len(finished) == 0


def test_completed_worker_stays_successful_when_cancel_arrives_too_late():
    worker = TaskWorker(lambda cancel_check: "committed result")
    cancelled = QSignalSpy(worker.cancelled)
    finished = QSignalSpy(worker.finished)

    worker.cancel()
    worker.run()

    assert len(cancelled) == 0
    assert len(finished) == 1
    assert finished[0][0] == "committed result"


def test_display_downsampling_bounds_matplotlib_artists(window):
    timeline = pd.DataFrame({
        "time_seconds": range(5_000),
        "count": range(5_000),
        "threshold": [1.0] * 5_000,
        "is_candidate": [False] * 5_000,
    })

    display = window._downsample_timeline(timeline)

    assert len(display) <= window.MAX_DISPLAY_POINTS
    assert display["count"].max() == 4_999


def test_export_uses_the_selected_result_tab_snapshot(window, tmp_path, monkeypatch):
    def result(peak):
        event = {
            "event_id": 1,
            "start_seconds": peak - 5,
            "peak_seconds": peak,
            "end_seconds": peak + 5,
            "time_seconds": peak,
            "time_str": window.analyzer.seconds_to_time(peak),
            "count": 20,
            "peak_window_count": 12,
            "baseline": 4.0,
            "threshold": 8.0,
            "lift": 5.0,
            "score": 5.0,
            "confidence": 0.8,
            "unique_users": 6,
            "top_user_share": 0.2,
            "duplicate_share": 0.0,
        }
        timeline = [
            {
                "time_seconds": index * 60,
                "count": 20 if index == 1 else 4,
                "threshold": 8.0,
                "is_candidate": index == 1,
            }
            for index in range(3)
        ]
        return {
            "timeline": timeline,
            "events": [event],
            "status": "ok",
            "total_count": 28,
            "peak_time": event["time_str"],
            "spike_count": 1,
            "sensitivity": 2.0,
        }

    window._show_flow_result("density", result(30), 1, 2)
    window._show_flow_result("density", result(90), 1, 2)
    window.analyzer.density_results = pd.DataFrame(result(90)["events"])
    window.analyzer.density_metadata = {"kind": "density"}
    window.result_tabs.setCurrentIndex(0)
    output = tmp_path / "selected.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "CSV Files (*.csv)"),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window.export_editor_result()

    frame = pd.read_csv(output, encoding="utf-8-sig")
    assert frame.loc[0, "핵심 시점(초)"] == 30


def test_editor_export_is_blocked_on_a_non_editor_result_tab(window, monkeypatch):
    tab = QWidget()
    window.result_tabs.addTab(tab, "분위기")
    window.result_tabs.setCurrentWidget(tab)
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args, **kwargs: warnings.append(args[2]),
    )
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: pytest.fail("save dialog must not open"),
    )

    window.export_editor_result()

    assert warnings and "편집 결과를 내보낼 수 없습니다" in warnings[0]


def test_mood_export_uses_the_selected_result_tab_snapshot(window, tmp_path, monkeypatch):
    def change(seconds):
        return {
            "type": "positive",
            "description": "긍정적 분위기 전환",
            "valence": 0.5,
            "arousal": 0.4,
            "sentiment_message_count": 4,
            "coverage": 0.5,
            "time": window.analyzer.seconds_to_time(seconds),
        }

    for seconds in (30, 90):
        figure = Figure()
        figure.add_subplot(111)
        window._add_result_tab(
            "분위기",
            "요약",
            figure,
            [],
            [],
            mood_snapshot=[change(seconds)],
        )
    window.result_tabs.setCurrentIndex(0)
    output = tmp_path / "selected-mood.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "CSV Files (*.csv)"),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window.export_mood_markers()

    frame = pd.read_csv(output, encoding="utf-8-sig")
    assert frame.loc[0, "In"] == "00:00:30"


def test_wordcloud_save_uses_the_selected_result_tab_snapshot(window, tmp_path, monkeypatch):
    for color in ((255, 0, 0), (0, 0, 255)):
        figure = Figure()
        figure.add_subplot(111)
        window._add_result_tab(
            "표현 분포",
            "요약",
            figure,
            [],
            [],
            wordcloud_snapshot=Image.new("RGB", (2, 2), color),
        )
    window.result_tabs.setCurrentIndex(0)
    output = tmp_path / "selected-wordcloud.png"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(output), "PNG Files (*.png)"),
    )
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)

    window.save_wordcloud()

    with Image.open(output) as image:
        assert image.getpixel((0, 0)) == (255, 0, 0)
