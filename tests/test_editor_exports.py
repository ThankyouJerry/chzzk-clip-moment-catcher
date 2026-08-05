import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from core.analyzer import ChatAnalyzer


def event(peak: float, start: float = 0, end: float = 60):
    return {
        "event_id": 1,
        "start_seconds": start,
        "peak_seconds": peak,
        "end_seconds": end,
        "time_seconds": peak,
        "time_str": ChatAnalyzer().seconds_to_time(peak),
        "count": 40,
        "peak_window_count": 20,
        "baseline": 10.0,
        "threshold": 16.0,
        "lift": 4.0,
        "score": 6.0,
        "confidence": 0.9,
        "unique_users": 12,
        "top_user_share": 0.2,
    }


def analyzer_with_density_events(*events):
    analyzer = ChatAnalyzer()
    analyzer.density_results = pd.DataFrame(events)
    analyzer.density_metadata = {"kind": "density", "source_files": ["chat.csv"]}
    analyzer.session_info = {"end_seconds": 100.0, "source_files": ["chat.csv"]}
    return analyzer


def test_editor_moments_clip_pre_and_post_roll_at_media_boundaries():
    analyzer = analyzer_with_density_events(
        event(5, 0, 20),
        {**event(95, 80, 100), "event_id": 2},
    )

    moments = analyzer.build_editor_moments("density", 15, 20)

    assert moments[0]["clip_start_seconds"] == 0
    assert moments[0]["peak_seconds"] == 5
    assert moments[0]["clip_end_seconds"] == 25
    assert moments[0]["pre_roll_seconds"] == 5
    assert moments[1]["clip_start_seconds"] == 80
    assert moments[1]["clip_end_seconds"] == 100
    assert moments[1]["post_roll_seconds"] == 5


def test_editor_csv_is_a_labeled_work_table(tmp_path):
    analyzer = analyzer_with_density_events(event(30))
    path = tmp_path / "work-table.csv"

    assert analyzer.export_editor_csv(path, "density") is True

    frame = pd.read_csv(path, encoding="utf-8-sig")
    assert frame.loc[0, "분석 유형"] == "density"
    assert frame.loc[0, "추천 시작"] == "00:00:15"
    assert frame.loc[0, "핵심 시점"] == "00:00:30"
    assert frame.loc[0, "추천 종료"] == "00:00:50"
    assert frame.loc[0, "신뢰도"] == pytest.approx(0.9)


def test_premiere_xml_uses_actual_peak_frame_and_escapes_text(tmp_path):
    analyzer = ChatAnalyzer()
    analyzer.keyword_results = pd.DataFrame([event(5)])
    analyzer.keyword_metadata = {"kind": "keyword", "keyword": "wow & fun"}
    analyzer.session_info = {"end_seconds": 100.0}
    path = tmp_path / "premiere.xml"

    assert analyzer.export_premiere_xml(path, "keyword", fps=30) is True

    root = ET.parse(path).getroot()
    marker = root.find("./sequence/marker")
    assert marker is not None
    assert marker.findtext("name") == "wow & fun 급증 #1"
    assert marker.findtext("in") == "150"
    assert marker.findtext("out") == "151"
    assert root.findtext("./sequence/rate/timebase") == "30"
    assert root.findtext("./sequence/rate/ntsc") == "FALSE"


def test_fcpxml_contains_marker_on_gap_at_actual_peak(tmp_path):
    analyzer = analyzer_with_density_events(event(5))
    path = tmp_path / "markers.fcpxml"

    assert analyzer.export_fcpxml(path, "density", fps=30) is True

    root = ET.parse(path).getroot()
    marker = root.find("./library/event/project/sequence/spine/gap/marker")
    assert root.tag == "fcpxml"
    assert marker is not None
    assert marker.attrib["start"] == "150/30s"
    assert marker.attrib["duration"] == "1/30s"
    assert marker.attrib["value"] == "채팅 급증 #1"


def test_ntsc_rate_uses_exact_rational_time(tmp_path):
    analyzer = analyzer_with_density_events(event(10))
    path = tmp_path / "markers.fcpxml"

    analyzer.export_fcpxml(path, "density", fps=29.97)

    root = ET.parse(path).getroot()
    format_node = root.find("./resources/format")
    marker = root.find("./library/event/project/sequence/spine/gap/marker")
    assert format_node.attrib["frameDuration"] == "1001/30000s"
    assert marker.attrib["start"] == "300300/30000s"


@pytest.mark.parametrize("fps", [0, 27, float("nan"), "bad"])
def test_exports_reject_unsupported_frame_rates(tmp_path, fps):
    analyzer = analyzer_with_density_events(event(10))

    with pytest.raises(ValueError, match="프레임 레이트"):
        analyzer.export_fcpxml(tmp_path / "bad.fcpxml", fps=fps)


@pytest.mark.parametrize("pre_roll,post_roll", [(-1, 1), (1, -1), (float("inf"), 1)])
def test_editor_ranges_reject_invalid_roll_values(pre_roll, post_roll):
    analyzer = analyzer_with_density_events(event(10))

    with pytest.raises(ValueError, match="0 이상의 유한한"):
        analyzer.build_editor_moments("density", pre_roll, post_roll)
