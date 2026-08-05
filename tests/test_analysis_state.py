from pathlib import Path

import pandas as pd
from core.analyzer import ChatAnalyzer


def write_chat(path: Path, message: str):
    pd.DataFrame([
        {"재생시간": "00:00:01", "닉네임": "user", "id": "id", "메시지": message}
    ]).to_csv(path, index=False, encoding="utf-8-sig")


def test_loading_new_source_discards_every_previous_result(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    write_chat(first, "ㅋㅋ")
    write_chat(second, "대박")

    analyzer = ChatAnalyzer()
    analyzer.load_csv(first)
    analyzer.keyword_results = pd.DataFrame([{"time_seconds": 0, "count": 1}])
    analyzer.density_results = pd.DataFrame([{"time_seconds": 0, "count": 1}])
    analyzer.keyword_timeline = analyzer.keyword_results.copy()
    analyzer.density_timeline = analyzer.density_results.copy()
    analyzer.keyword_metadata = {"keyword": "ㅋㅋ"}
    analyzer.density_metadata = {"interval_minutes": 1}

    analyzer.load_csv(second)

    assert analyzer.keyword_results is None
    assert analyzer.density_results is None
    assert analyzer.keyword_timeline is None
    assert analyzer.density_timeline is None
    assert analyzer.keyword_metadata is None
    assert analyzer.density_metadata is None


def test_keyword_editor_output_uses_immutable_analysis_metadata():
    analyzer = ChatAnalyzer()
    analyzer.keyword_results = pd.DataFrame([
        {
            "event_id": 1,
            "start_seconds": 0,
            "peak_seconds": 30,
            "end_seconds": 60,
            "time_seconds": 30,
            "time_str": "00:00:30",
            "count": 10,
            "peak_window_count": 8,
            "baseline": 2,
            "threshold": 4,
            "lift": 5,
            "score": 4,
            "confidence": 0.8,
            "unique_users": 6,
            "top_user_share": 0.25,
        }
    ])
    analyzer.keyword_metadata = {"kind": "keyword", "keyword": "ㅋㅋ"}
    analyzer.session_info = {"end_seconds": 120}

    moments = analyzer.build_editor_moments("keyword")

    assert moments[0]["keyword"] == "ㅋㅋ"
    assert moments[0]["label"] == "ㅋㅋ 급증 #1"
