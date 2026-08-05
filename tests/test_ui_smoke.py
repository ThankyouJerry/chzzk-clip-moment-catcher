import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import pandas as pd
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QApplication, QLabel

from ui.main_window import MainWindow


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
