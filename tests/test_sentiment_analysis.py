import math

import pandas as pd
import pytest

from core.sentiment_analyzer import SentimentAnalyzer


@pytest.mark.parametrize("message", ["안녕하세요", "고양이", "오늘 방송입니다"])
def test_neutral_korean_words_do_not_match_one_character_substrings(message):
    signals = SentimentAnalyzer().analyze_message_signals(message)

    assert signals["valence"] == 0
    assert signals["has_valence"] is False


@pytest.mark.parametrize("message", ["재미없다", "안 웃겨", "진짜 노잼"])
def test_negation_and_negative_compounds_override_positive_roots(message):
    signals = SentimentAnalyzer().analyze_message_signals(message)

    assert signals["valence"] < 0
    assert signals["has_valence"] is True


@pytest.mark.parametrize(
    "message,expected_sign",
    [
        ("재미있지 않다", -1),
        ("좋아하지 않는다", -1),
        ("감사하지 않습니다", -1),
        ("싫어하지 않아", 1),
        ("싫지는 않다", 1),
    ],
)
def test_postposed_korean_negation_blocks_and_reverses_the_root(message, expected_sign):
    signals = SentimentAnalyzer().analyze_message_signals(message)

    assert math.copysign(1, signals["valence"]) == expected_sign
    assert signals["has_valence"] is True


def test_repeated_laughter_is_one_strong_signal_not_overlapping_substrings():
    signals = SentimentAnalyzer().analyze_message_signals("ㅋㅋㅋㅋㅋ")

    assert signals["valence"] == pytest.approx(0.85)
    assert signals["evidence_count"] == 2  # one valence and one arousal signal


def test_punctuation_and_custom_emotes_raise_arousal_without_fake_valence():
    analyzer = SentimentAnalyzer()
    punctuation = analyzer.analyze_message_signals("진짜???!!!")
    custom_emote = analyzer.analyze_message_signals("", custom_emote_count=2)

    assert punctuation["valence"] == 0
    assert punctuation["arousal"] > 0
    assert punctuation["has_valence"] is False
    assert custom_emote["valence"] == 0
    assert custom_emote["arousal"] > 0


def test_sentiment_timeline_keeps_empty_bins_unknown_and_does_not_bridge_gap():
    frame = pd.DataFrame([
        {
            "seconds": 1.0,
            "clean_message": "최고",
            "message_raw": "최고",
            "custom_emote_count": 0,
            "is_system": False,
        },
        {
            "seconds": 121.0,
            "clean_message": "최악",
            "message_raw": "최악",
            "custom_emote_count": 0,
            "is_system": False,
        },
    ])
    analyzer = SentimentAnalyzer()

    timeline = analyzer.analyze_timeline(frame, interval_minutes=1)
    changes = analyzer.detect_mood_changes(threshold=0.2, min_change=0.1)

    assert timeline["time_seconds"].tolist() == [0, 60, 120]
    assert math.isnan(timeline.iloc[1]["valence"])
    assert timeline.iloc[1]["message_count"] == 0
    assert changes == []


def test_custom_emote_only_message_is_kept_as_arousal_evidence():
    frame = pd.DataFrame([
        {
            "seconds": 0.0,
            "clean_message": "customHi",
            "message_raw": "{:customHi:}",
            "custom_emote_count": 1,
            "is_system": False,
        }
    ])
    analyzer = SentimentAnalyzer()

    timeline = analyzer.analyze_timeline(frame, interval_minutes=1)

    assert math.isnan(timeline.iloc[0]["valence"])
    assert timeline.iloc[0]["arousal"] > 0
    assert timeline.iloc[0]["message_count"] == 1
    assert timeline.iloc[0]["evidence_count"] == 1


def test_blank_messages_are_excluded_from_sentiment_coverage_denominator():
    frame = pd.DataFrame([
        {
            "seconds": 0.0,
            "clean_message": "대박",
            "message_raw": "대박",
            "custom_emote_count": 0,
            "is_system": False,
        },
        {
            "seconds": 1.0,
            "clean_message": "",
            "message_raw": "",
            "custom_emote_count": 0,
            "is_system": False,
        },
    ])

    timeline = SentimentAnalyzer().analyze_timeline(frame, interval_minutes=1)

    assert timeline.iloc[0]["message_count"] == 1
    assert timeline.iloc[0]["coverage"] == 1.0


def test_overall_valence_is_invariant_to_timeline_interval():
    frame = pd.DataFrame([
        {
            "seconds": 1.0,
            "clean_message": "대박",
            "message_raw": "대박",
            "custom_emote_count": 0,
            "is_system": False,
        },
        {
            "seconds": 61.0,
            "clean_message": "아쉽",
            "message_raw": "아쉽",
            "custom_emote_count": 0,
            "is_system": False,
        },
    ])
    analyzer = SentimentAnalyzer()

    analyzer.analyze_timeline(frame, interval_minutes=1)
    one_minute = analyzer.get_summary()["valence"]
    analyzer.analyze_timeline(frame, interval_minutes=2)
    two_minutes = analyzer.get_summary()["valence"]

    assert one_minute == pytest.approx(two_minutes)


def test_system_only_timeline_keeps_empty_result_schema():
    frame = pd.DataFrame([
        {
            "seconds": 15.0,
            "clean_message": "system notice",
            "is_system": True,
        }
    ])
    analyzer = SentimentAnalyzer()

    timeline = analyzer.analyze_timeline(frame, interval_minutes=1)

    assert timeline.empty
    assert timeline.columns.tolist() == SentimentAnalyzer.TIMELINE_COLUMNS
    assert analyzer.get_summary()["message_count"] == 0
    assert analyzer.detect_mood_changes() == []


def test_threshold_is_applied_when_detecting_mood_changes():
    analyzer = SentimentAnalyzer()
    analyzer.sentiment_results = pd.DataFrame([
        {
            "time_seconds": 0,
            "time_str": "00:00:00",
            "valence": 0.1,
            "sentiment_score": 0.1,
            "arousal": 0.1,
            "sentiment_message_count": 2,
            "evidence_count": 2,
            "coverage": 1.0,
        },
        {
            "time_seconds": 60,
            "time_str": "00:01:00",
            "valence": 0.35,
            "sentiment_score": 0.35,
            "arousal": 0.2,
            "sentiment_message_count": 2,
            "evidence_count": 2,
            "coverage": 1.0,
        },
    ])
    analyzer.analysis_metadata = {"interval_seconds": 60}

    assert analyzer.detect_mood_changes(threshold=0.4, min_change=0.2) == []
    assert len(analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)) == 1


def test_large_transition_into_quiet_state_is_not_suppressed():
    analyzer = SentimentAnalyzer()
    analyzer.sentiment_results = pd.DataFrame([
        {
            "time_seconds": 0,
            "time_str": "00:00:00",
            "valence": 0.8,
            "sentiment_score": 0.8,
            "arousal": 0.7,
            "sentiment_message_count": 3,
            "evidence_count": 3,
            "coverage": 0.5,
        },
        {
            "time_seconds": 60,
            "time_str": "00:01:00",
            "valence": 0.15,
            "sentiment_score": 0.15,
            "arousal": 0.1,
            "sentiment_message_count": 3,
            "evidence_count": 3,
            "coverage": 0.5,
        },
    ])
    analyzer.analysis_metadata = {"interval_seconds": 60}

    changes = analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)

    assert len(changes) == 1
    assert changes[0]["type"] == "calm"


def test_mood_change_requires_enough_evidence_in_both_bins():
    rows = []
    for bin_start, signal in ((0, "최고"), (60, "최악")):
        for index in range(100):
            message = signal if index == 0 else "일반채팅"
            rows.append({
                "seconds": bin_start + index * 0.5,
                "clean_message": message,
                "message_raw": message,
                "custom_emote_count": 0,
                "is_system": False,
            })
    analyzer = SentimentAnalyzer()

    timeline = analyzer.analyze_timeline(pd.DataFrame(rows), interval_minutes=1)

    assert timeline["coverage"].tolist() == [0.01, 0.01]
    assert analyzer.detect_mood_changes(threshold=0.3, min_change=0.2) == []


def test_mood_change_is_kept_when_evidence_gate_is_met():
    rows = []
    for bin_start, signal in ((0, "최고"), (60, "최악")):
        for index in range(20):
            message = signal if index < 2 else "일반채팅"
            rows.append({
                "seconds": bin_start + index,
                "clean_message": message,
                "message_raw": message,
                "custom_emote_count": 0,
                "is_system": False,
            })
    analyzer = SentimentAnalyzer()

    analyzer.analyze_timeline(pd.DataFrame(rows), interval_minutes=1)
    changes = analyzer.detect_mood_changes(threshold=0.3, min_change=0.2)

    assert len(changes) == 1
    assert changes[0]["sentiment_message_count"] == 2
    assert changes[0]["coverage"] == 0.1


@pytest.mark.parametrize("interval", [0, -1, float("nan"), float("inf")])
def test_sentiment_interval_must_be_positive_and_finite(interval):
    frame = pd.DataFrame([
        {"seconds": 1.0, "clean_message": "대박", "is_system": False}
    ])

    with pytest.raises(ValueError, match="0보다 큰 유한한"):
        SentimentAnalyzer().analyze_timeline(frame, interval)


def test_sentiment_timeline_rejects_an_unbounded_number_of_bins():
    frame = pd.DataFrame([
        {
            "seconds": 3_599_996_400.0,
            "clean_message": "대박",
            "message_raw": "대박",
            "custom_emote_count": 0,
            "is_system": False,
        }
    ])

    with pytest.raises(ValueError, match="시간 구간을 .*개 생성"):
        SentimentAnalyzer().analyze_timeline(frame, interval_minutes=1 / 60)
