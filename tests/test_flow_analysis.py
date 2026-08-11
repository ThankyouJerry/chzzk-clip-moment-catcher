from pathlib import Path

import pandas as pd
import pytest

from core.analyzer import ChatAnalyzer


def load_rows(tmp_path: Path, rows) -> ChatAnalyzer:
    path = tmp_path / "chat.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
    analyzer = ChatAnalyzer()
    analyzer.load_csv(path)
    return analyzer


def row(seconds: float, nickname: str = "user", message: str = "chat"):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    time_text = f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    return {"재생시간": time_text, "닉네임": nickname, "메시지": message}


@pytest.mark.parametrize("interval", [0, -1, float("nan"), float("inf")])
def test_interval_must_be_positive_and_finite(tmp_path, interval):
    analyzer = load_rows(tmp_path, [row(1)])

    with pytest.raises(ValueError, match="0보다 큰 유한한"):
        analyzer.analyze_chat_density(interval)


def test_half_open_bins_keep_zero_and_put_boundaries_in_next_bin(tmp_path):
    analyzer = load_rows(
        tmp_path,
        [row(0), row(59.999), row(60), row(119.999), row(120)],
    )

    result = analyzer.analyze_chat_density(1)

    assert [item["time_seconds"] for item in result["timeline"]] == [0, 60, 120]
    assert [item["count"] for item in result["timeline"]] == [2, 2, 1]


def test_short_timeline_is_reported_as_insufficient_not_as_a_peak(tmp_path):
    analyzer = load_rows(tmp_path, [row(1), row(61)])

    result = analyzer.analyze_chat_density(1, sensitivity=3)

    assert result["status"] == "insufficient_data"
    assert result["events"] == []
    assert result["peak_time"] is None


def test_uniform_chat_volume_does_not_mark_every_bin(tmp_path):
    rows = [row(bin_start + offset, f"u{offset}") for bin_start in range(0, 300, 60) for offset in range(4)]
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=3)

    assert result["status"] == "no_events"
    assert result["events"] == []
    assert not analyzer.get_density_timeline()["is_candidate"].any()


def test_higher_sensitivity_never_detects_fewer_moderate_events(tmp_path):
    counts = [10, 10, 15, 10, 10]
    rows = [
        row(bin_index * 60 + index, f"u{index % 6}")
        for bin_index, count in enumerate(counts)
        for index in range(count)
    ]
    analyzer = load_rows(tmp_path, rows)

    low = analyzer.analyze_chat_density(1, sensitivity=1)
    high = analyzer.analyze_chat_density(1, sensitivity=3)

    assert len(high["events"]) >= len(low["events"])
    assert len(high["events"]) == 1


def test_adjacent_spike_bins_merge_and_marker_uses_raw_peak_time(tmp_path):
    counts = [10, 10, 10, 30, 28, 10, 10]
    rows = []
    for bin_index, count in enumerate(counts):
        for index in range(count):
            if bin_index == 3:
                seconds = 220 + (index % 5) * 0.2
            elif bin_index == 4:
                seconds = 270 + (index % 20)
            else:
                seconds = bin_index * 60 + index
            nickname = "boundary-user" if bin_index == 5 and index == 0 else f"u{index % 10}"
            rows.append(row(seconds, nickname))
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=2)

    assert result["status"] == "ok"
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["start_seconds"] == 180
    assert event["end_seconds"] == 300
    assert 220 <= event["peak_seconds"] <= 221
    assert event["time_seconds"] == event["peak_seconds"]
    assert event["unique_users"] == 10


def test_merged_event_counts_the_gap_bin_used_for_participants_and_confidence(tmp_path):
    counts = [10, 10, 30, 10, 30, 10, 10]
    rows = []
    for bin_index, count in enumerate(counts):
        for index in range(count):
            nickname = "gap-only" if bin_index == 3 else f"u{index % 10}"
            rows.append(row(bin_index * 60 + index, nickname))
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=2)

    assert result["status"] == "ok"
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["start_seconds"] == 120
    assert event["end_seconds"] == 300
    assert event["count"] == 70
    assert event["baseline"] == pytest.approx(13.333)
    assert event["lift"] == pytest.approx(1.75)
    assert event["unique_users"] == 11
    assert event["top_user_share"] == pytest.approx(0.143)
    assert event["confidence"] == pytest.approx(0.826)
    event_bins = analyzer.get_density_timeline().iloc[2:5]
    assert event_bins["event_id"].eq(1).all()


def test_event_end_at_source_boundary_excludes_the_next_bin_row(tmp_path):
    counts = [10, 10, 30, 10, 30]
    rows = []
    for bin_index, count in enumerate(counts):
        for index in range(count):
            nickname = "gap-only" if bin_index == 3 else f"u{index % 10}"
            rows.append(row(bin_index * 60 + index, nickname))
    rows.append(row(300, "boundary-only"))
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=3)

    assert result["status"] == "ok"
    assert len(result["events"]) == 1
    event = result["events"][0]
    assert event["start_seconds"] == 120
    assert event["end_seconds"] == 300
    assert event["count"] == 70
    assert event["unique_users"] == 11
    assert event["top_user_share"] == pytest.approx(0.143)
    timeline = analyzer.get_density_timeline()
    assert timeline.iloc[2:5]["event_id"].eq(1).all()
    assert pd.isna(timeline.iloc[5]["event_id"])


def test_actual_peak_uses_half_open_window_and_keyword_occurrence_weights():
    analyzer = ChatAnalyzer()
    keyword_rows = pd.DataFrame({
        "seconds": [0.0, 1.0, 16.0],
        "occurrence_count": [5, 1, 20],
    })

    peak_seconds, peak_count = analyzer._find_actual_peak(
        keyword_rows,
        count_column="occurrence_count",
    )

    assert peak_seconds == 16
    assert peak_count == 20

    boundary_rows = pd.DataFrame({"seconds": [0.0, 15.0]})
    _, boundary_count = analyzer._find_actual_peak(boundary_rows)
    assert boundary_count == 1


def test_system_messages_are_not_density_evidence(tmp_path):
    rows = [row(5, "human"), row(65, "human")]
    rows += [row(125 + index * 0.01, "[SYSTEM]") for index in range(100)]
    rows += [row(185, "human"), row(245, "human")]
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=3)

    assert result["total_count"] == 4
    assert [item["count"] for item in result["timeline"]] == [1, 1, 0, 1, 1]
    assert result["events"] == []


def test_blank_messages_are_not_density_evidence_or_false_highlights(tmp_path):
    rows = []
    for bin_index, count in enumerate([1, 1, 20, 1, 1]):
        for index in range(count):
            message = "" if bin_index == 2 else "chat"
            rows.append(row(bin_index * 60 + index, f"u{index}", message))
    analyzer = load_rows(tmp_path, rows)

    result = analyzer.analyze_chat_density(1, sensitivity=3)

    assert analyzer.session_info["blank_messages"] == 20
    assert result["total_count"] == 4
    assert [item["count"] for item in result["timeline"]] == [1, 1, 0, 1, 1]
    assert result["events"] == []


def test_density_with_no_usable_chat_reports_no_evidence(tmp_path):
    analyzer = load_rows(
        tmp_path,
        [row(1, "[SYSTEM]", "notice"), row(241, "user", "")],
    )

    result = analyzer.analyze_chat_density(1)

    assert result["total_count"] == 0
    assert result["status"] == "no_evidence"
    assert result["events"] == []


def test_timeline_rejects_an_unbounded_number_of_bins(tmp_path):
    analyzer = load_rows(tmp_path, [row(3_599_996_400)])

    with pytest.raises(ValueError, match="시간 구간을 .*개 생성"):
        analyzer.analyze_chat_density(1 / 60)


def test_keyword_reports_message_and_occurrence_counts_separately(tmp_path):
    analyzer = load_rows(
        tmp_path,
        [row(1, message="WOW wow"), row(61, message="wow"), row(121, message="other")],
    )

    result = analyzer.analyze_keyword("wow", 1)

    assert result["total_count"] == 2
    assert result["occurrence_count"] == 3
    assert [item["count"] for item in result["timeline"]] == [2, 1, 0]
    assert analyzer.density_results is None
