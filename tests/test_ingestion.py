from pathlib import Path

import pandas as pd
import pytest

from core.analyzer import ChatAnalyzer


def write_csv(path: Path, rows, columns=None):
    pd.DataFrame(rows, columns=columns).to_csv(path, index=False, encoding="utf-8-sig")


def valid_row(time="00:00:00", nickname="001", message="007"):
    return {"재생시간": time, "닉네임": nickname, "id": "000123", "메시지": message}


def test_time_parser_supports_boundaries_and_milliseconds():
    analyzer = ChatAnalyzer()

    assert analyzer.time_to_seconds("00:00:00") == 0
    assert analyzer.time_to_seconds("00:00:59.500") == 59.5
    assert analyzer.time_to_seconds("100:00:00") == 360000


@pytest.mark.parametrize("value", ["bad", "", "-1:00:00", "00:60:00", "00:00:60", None])
def test_time_parser_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        ChatAnalyzer().time_to_seconds(value)


def test_load_preserves_numeric_text_and_normalizes_unicode(tmp_path):
    path = tmp_path / "chat.csv"
    write_csv(path, [valid_row(message="\u200b대박 {:customHi:}")])

    analyzer = ChatAnalyzer()
    assert analyzer.load_csv(path) == 1

    row = analyzer.df.iloc[0]
    assert row["닉네임"] == "001"
    assert row["id"] == "000123"
    assert row["clean_message"] == "대박 customHi"
    assert row["custom_emote_count"] == 1
    assert row["seconds"] == 0


def test_load_rejects_missing_schema_and_empty_data(tmp_path):
    missing = tmp_path / "missing.csv"
    write_csv(missing, [{"재생시간": "00:00:01", "메시지": "hello"}])
    empty = tmp_path / "empty.csv"
    write_csv(empty, [], columns=["재생시간", "닉네임", "메시지"])

    analyzer = ChatAnalyzer()
    with pytest.raises(ValueError, match="필수 열"):
        analyzer.load_csv(missing)
    with pytest.raises(ValueError, match="메시지가 없습니다"):
        analyzer.load_csv(empty)


def test_load_reports_bad_time_instead_of_moving_it_to_zero(tmp_path):
    path = tmp_path / "bad-time.csv"
    write_csv(path, [valid_row(time="not-a-time")])

    with pytest.raises(ValueError, match="올바르지 않은 재생시간"):
        ChatAnalyzer().load_csv(path)


def test_split_csv_parts_are_discovered_and_merged(tmp_path):
    first = tmp_path / "vod_d_p001.csv"
    second = tmp_path / "vod_d_p002.csv"
    write_csv(first, [valid_row(time="00:00:01", message="first")])
    write_csv(second, [valid_row(time="00:00:02", message="second")])

    analyzer = ChatAnalyzer()
    assert analyzer.load_csv(second) == 2
    assert analyzer.session_info["file_count"] == 2
    assert analyzer.df["메시지"].tolist() == ["first", "second"]


def test_legacy_exporter_schema_and_iso_elapsed_time_are_supported(tmp_path):
    source = tmp_path / "legacy.csv"
    write_csv(
        source,
        [{"Timestamp": "1970-01-01T01:02:03.500Z", "User ID": "user", "Message": "chat"}],
    )

    analyzer = ChatAnalyzer()
    assert analyzer.load_csv(str(source)) == 1
    assert analyzer.df.iloc[0]["seconds"] == pytest.approx(3723.5)
    assert analyzer.df.iloc[0]["닉네임"] == "user"
    assert analyzer.df.iloc[0]["메시지"] == "chat"


def test_legacy_exporter_split_parts_are_discovered_and_merged(tmp_path):
    first = tmp_path / "vod_part001.csv"
    second = tmp_path / "vod_part002.csv"
    columns = ["Timestamp", "User ID", "Message"]
    write_csv(first, [["1970-01-01T00:00:01.000Z", "user", "first"]], columns=columns)
    write_csv(second, [["1970-01-01T00:00:02.000Z", "user", "second"]], columns=columns)

    analyzer = ChatAnalyzer()
    assert analyzer.load_csv(str(second)) == 2
    assert analyzer.df["메시지"].tolist() == ["first", "second"]


def test_split_csv_missing_middle_part_is_rejected(tmp_path):
    first = tmp_path / "vod_d_p001.csv"
    third = tmp_path / "vod_d_p003.csv"
    write_csv(first, [valid_row(time="00:00:01")])
    write_csv(third, [valid_row(time="00:00:03")])

    with pytest.raises(ValueError, match="p002"):
        ChatAnalyzer().load_csv(first)


def test_split_csv_must_start_with_first_part(tmp_path):
    second = tmp_path / "vod_d_p002.csv"
    write_csv(second, [valid_row(time="00:00:02")])

    with pytest.raises(ValueError, match="p001"):
        ChatAnalyzer().load_csv(second)


def test_split_csv_schema_mismatch_is_rejected(tmp_path):
    first = tmp_path / "vod_d_p001.csv"
    second = tmp_path / "vod_d_p002.csv"
    write_csv(first, [valid_row(time="00:00:01")])
    write_csv(
        second,
        [{"재생시간": "00:00:02", "닉네임": "user", "메시지": "chat", "extra": "x"}],
    )

    with pytest.raises(ValueError, match="열 구성"):
        ChatAnalyzer().load_csv(first)


def test_bad_time_report_names_its_split_file_and_source_row(tmp_path):
    first = tmp_path / "vod_d_p001.csv"
    second = tmp_path / "vod_d_p002.csv"
    write_csv(first, [valid_row(time="00:00:01")])
    write_csv(second, [valid_row(time="bad")])

    with pytest.raises(ValueError, match=r"vod_d_p002\.csv 2행"):
        ChatAnalyzer().load_csv(first)


def test_wordcloud_collapses_reaction_variants_and_keeps_custom_emote_names(tmp_path):
    path = tmp_path / "chat.csv"
    write_csv(
        path,
        [
            valid_row(time="00:00:01", message="ㅋㅋㅋ"),
            valid_row(time="00:00:02", message="ㅋㅋㅋㅋㅋㅋ"),
            valid_row(time="00:00:03", message="ㅠㅠㅠㅠ"),
            valid_row(time="00:00:04", message="{:customHi:}"),
            valid_row(time="00:00:05", message="https://example.com"),
        ],
    )
    analyzer = ChatAnalyzer()
    analyzer.load_csv(path)

    assert analyzer.get_all_text().split() == ["ㅋㅋ", "ㅋㅋ", "ㅠㅠ", "customhi"]
