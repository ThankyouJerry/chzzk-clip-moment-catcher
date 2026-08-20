from __future__ import annotations

"""
Chat Analyzer - Core Analysis Logic
"""
import csv
from collections import Counter
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import unicodedata
from typing import Callable, Optional, Dict, List, Sequence
import xml.etree.ElementTree as ET

import pandas as pd

from core.errors import TaskCancelled
from core.file_io import atomic_save
from core.timeline import timeline_bounds


class ChatAnalyzer:
    """Analyzes Chzzk chat CSV files"""

    REQUIRED_COLUMNS = ("재생시간", "닉네임", "메시지")
    LEGACY_COLUMN_ALIASES = {
        "Timestamp": "재생시간",
        "User ID": "닉네임",
        "Message": "메시지",
    }
    SPLIT_FILE_PATTERNS = (
        (re.compile(r"^(?P<base>.+)_d_p(?P<part>\d{3})\.csv$", re.IGNORECASE), "p"),
        (re.compile(r"^(?P<base>.+)_part(?P<part>\d{3})\.csv$", re.IGNORECASE), "part"),
    )
    TIME_PATTERN = re.compile(
        r"^\s*(?P<hours>\d+):(?P<minutes>[0-5]\d):(?P<seconds>[0-5]\d)"
        r"(?:\.(?P<fraction>\d{1,3}))?\s*$"
    )
    LEGACY_TIME_PATTERN = re.compile(
        r"^1970-01-(?P<day>0[1-9]|[12]\d|3[01])T"
        r"(?P<hours>[0-2]\d):(?P<minutes>[0-5]\d):(?P<seconds>[0-5]\d)"
        r"(?:\.(?P<fraction>\d{1,6}))?Z$"
    )
    MAX_TOTAL_INPUT_BYTES = 512 * 1024 * 1024
    MAX_INPUT_ROWS = 5_000_000
    MAX_COLUMNS = 64
    MAX_CELL_CHARACTERS = 262_144
    INVALID_CELL_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.keyword_results: Optional[pd.DataFrame] = None
        self.density_results: Optional[pd.DataFrame] = None
        self.keyword_timeline: Optional[pd.DataFrame] = None
        self.density_timeline: Optional[pd.DataFrame] = None
        self.keyword_metadata: Optional[Dict] = None
        self.density_metadata: Optional[Dict] = None
        self.session_info: Dict = {}

    def reset_results(self) -> None:
        """Discard every result tied to the previously loaded source."""
        self.keyword_results = None
        self.density_results = None
        self.keyword_timeline = None
        self.density_timeline = None
        self.keyword_metadata = None
        self.density_metadata = None
    
    @staticmethod
    def _cancel_if_requested(
        cancel_check: Optional[Callable[[], bool]],
    ) -> None:
        if cancel_check is not None and cancel_check():
            raise TaskCancelled("작업이 취소되었습니다.")

    def load_csv(
        self,
        file_path: str,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> int:
        """
        Load CSV file and return number of messages
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Number of messages loaded
        """
        file_paths = self._discover_csv_parts(Path(file_path))
        return self.load_csv_files(file_paths, cancel_check=cancel_check)

    def load_csv_files(
        self,
        file_paths: Sequence[Path | str],
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> int:
        """Load and validate one CSV or a contiguous exporter part set."""
        paths = [Path(path).expanduser().resolve() for path in file_paths]
        if not paths:
            raise ValueError("선택된 CSV 파일이 없습니다.")

        total_bytes = 0
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")
            total_bytes += path.stat().st_size
        if total_bytes > self.MAX_TOTAL_INPUT_BYTES:
            limit_mib = self.MAX_TOTAL_INPUT_BYTES / (1024 * 1024)
            raise ValueError(
                f"분할 파일을 합친 크기가 {limit_mib:,.0f} MiB 제한을 초과합니다. "
                "필요한 방송 단위로 CSV를 나눠 분석하세요."
            )

        frames = []
        encodings = []
        canonical_columns = None
        validated_rows = 0
        for path in paths:
            self._cancel_if_requested(cancel_check)
            encoding, row_count = self._validate_csv_structure(
                path,
                cancel_check=cancel_check,
            )
            validated_rows += row_count
            if validated_rows > self.MAX_INPUT_ROWS:
                raise ValueError(
                    f"분할 파일을 합친 행 수가 {self.MAX_INPUT_ROWS:,}행 제한을 초과합니다. "
                    "필요한 방송 단위로 CSV를 나눠 분석하세요."
                )
            frame, encoding = self._read_csv_preserving_text(path, encoding)
            frame.columns = [str(column).lstrip("\ufeff").strip() for column in frame.columns]
            collisions = [
                f"{source}/{target}"
                for source, target in self.LEGACY_COLUMN_ALIASES.items()
                if source in frame.columns and target in frame.columns
            ]
            if collisions:
                raise ValueError(
                    f"{path.name}: 이전 열과 현재 열이 함께 있어 해석할 수 없습니다: "
                    f"{', '.join(collisions)}"
                )
            frame = self._normalize_exporter_columns(frame)
            current_columns = list(frame.columns)
            if canonical_columns is None:
                canonical_columns = current_columns
            elif current_columns != canonical_columns:
                raise ValueError(
                    f"{path.name}: 분할 CSV 열 구성이 첫 파일과 다릅니다.\n"
                    "모든 분할 파일은 같은 순서와 이름의 열을 가져야 합니다."
                )
            missing = [column for column in self.REQUIRED_COLUMNS if column not in frame.columns]
            if missing:
                raise ValueError(
                    f"{path.name}: 필수 열이 없습니다: {', '.join(missing)}\n"
                    "필요한 열: 재생시간, 닉네임, 메시지"
                )
            frame["_source_file"] = path.name
            frame["_source_row"] = range(2, len(frame) + 2)
            frames.append(frame)
            encodings.append(encoding)

        combined = pd.concat(frames, ignore_index=True)
        if combined.empty:
            raise ValueError("CSV에 분석할 채팅 메시지가 없습니다.")

        parsed_seconds = []
        invalid_times = []
        for position, value in enumerate(combined["재생시간"]):
            if position % 5_000 == 0:
                self._cancel_if_requested(cancel_check)
            try:
                parsed_seconds.append(self.time_to_seconds(value))
            except ValueError:
                parsed_seconds.append(math.nan)
                if len(invalid_times) < 5:
                    source = combined.iloc[position]
                    invalid_times.append(
                        f"{source['_source_file']} {source['_source_row']}행: {value!r}"
                    )

        if invalid_times:
            detail = "\n".join(invalid_times)
            raise ValueError(
                "올바르지 않은 재생시간이 있습니다. HH:MM:SS 또는 지원되는 exporter 형식을 사용하세요.\n"
                f"{detail}"
            )

        combined["seconds"] = pd.Series(parsed_seconds, dtype="float64")
        combined["메시지"] = (
            combined["메시지"]
            .astype("string")
            .str.replace("\r\n", "\n", regex=False)
            .str.replace("\r", "\n", regex=False)
        )
        combined["message_raw"] = combined["메시지"]
        combined["clean_message"] = combined["message_raw"].apply(self.clean_message)
        combined["custom_emote_count"] = combined["message_raw"].apply(
            lambda value: len(re.findall(r"\{:[^:]+:\}", str(value)))
        )
        combined["is_system"] = combined["닉네임"].str.strip().eq("[SYSTEM]")
        identifier = (
            combined["id"].astype("string").str.strip()
            if "id" in combined.columns
            else pd.Series("", index=combined.index, dtype="string")
        )
        nickname = combined["닉네임"].astype("string").str.strip().str.casefold()
        combined["participant_key"] = (
            "id:" + identifier.str.casefold()
        ).where(identifier.ne(""), "nickname:" + nickname)

        duplicate_columns = list(self.REQUIRED_COLUMNS)
        if "id" in combined.columns:
            duplicate_columns.insert(2, "id")
        duplicate_rows = int(combined[duplicate_columns].duplicated().sum())
        time_regressions = int(combined["seconds"].diff().lt(0).sum())
        quality_warnings = []
        if duplicate_rows:
            quality_warnings.append(
                f"완전히 같은 채팅 행 {duplicate_rows:,}개가 포함되어 분석 신뢰도가 낮아질 수 있습니다."
            )
        if time_regressions:
            quality_warnings.append(
                f"재생시간이 이전 행보다 뒤로 간 지점 {time_regressions:,}개를 확인하세요."
            )

        self.df = combined
        self.reset_results()
        self.session_info = {
            "source_files": [str(path) for path in paths],
            "file_count": len(paths),
            "row_count": len(combined),
            "duplicate_rows": duplicate_rows,
            "duplicate_ratio": duplicate_rows / len(combined),
            "time_regressions": time_regressions,
            "quality_warnings": quality_warnings,
            "system_rows": int(combined["is_system"].sum()),
            "blank_messages": int(combined["message_raw"].str.strip().eq("").sum()),
            "blank_clean_messages": int(combined["clean_message"].str.strip().eq("").sum()),
            "custom_emote_rows": int(combined["custom_emote_count"].gt(0).sum()),
            "start_seconds": float(combined["seconds"].min()),
            "end_seconds": float(combined["seconds"].max()),
            "encodings": encodings,
        }
        return len(self.df)

    def _discover_csv_parts(self, selected_path: Path) -> List[Path]:
        """Return all contiguous exporter parts when a split file is selected."""
        matched_pattern = None
        match = None
        part_label = "p"
        for pattern, label in self.SPLIT_FILE_PATTERNS:
            match = pattern.match(selected_path.name)
            if match:
                matched_pattern = pattern
                part_label = label
                break
        if match is None or matched_pattern is None:
            return [selected_path]

        base = match.group("base")
        candidates = []
        for candidate in selected_path.parent.iterdir():
            if not candidate.is_file() or candidate.suffix.casefold() != ".csv":
                continue
            candidate_match = matched_pattern.match(candidate.name)
            if (
                candidate_match
                and candidate_match.group("base").casefold() == base.casefold()
            ):
                candidates.append((int(candidate_match.group("part")), candidate))

        candidates.sort(key=lambda item: item[0])
        if not candidates:
            return [selected_path]

        parts = [part for part, _ in candidates]
        expected = list(range(1, parts[-1] + 1))
        if parts != expected:
            missing = sorted(set(expected) - set(parts))
            missing_text = ", ".join(f"{part_label}{part:03d}" for part in missing)
            raise ValueError(f"분할 CSV 일부가 없습니다: {missing_text}")
        return [path for _, path in candidates]

    def _normalize_exporter_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Normalize current and legacy chzzk-chat-exporter column names."""
        rename_map = {
            source: target
            for source, target in self.LEGACY_COLUMN_ALIASES.items()
            if source in frame.columns and target not in frame.columns
        }
        return frame.rename(columns=rename_map)

    def _validate_csv_structure(
        self,
        path: Path,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> tuple[str, int]:
        """Stream every record so malformed CSV cannot become plausible evidence."""
        last_decode_error = None
        for encoding in ("utf-8-sig", "utf-8", "cp949"):
            try:
                return encoding, self._validate_csv_structure_with_encoding(
                    path,
                    encoding,
                    cancel_check,
                )
            except UnicodeDecodeError as error:
                last_decode_error = error
        raise ValueError(f"{path.name}: 지원하지 않는 CSV 인코딩입니다.") from last_decode_error

    def _validate_csv_structure_with_encoding(
        self,
        path: Path,
        encoding: str,
        cancel_check: Optional[Callable[[], bool]],
    ) -> int:
        previous_limit = csv.field_size_limit()
        csv.field_size_limit(self.MAX_CELL_CHARACTERS)
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                reader = csv.reader(stream, strict=True)
                try:
                    columns = next(reader)
                except StopIteration as error:
                    raise ValueError(f"{path.name}: CSV 헤더를 읽을 수 없습니다.") from error
                normalized = [column.lstrip("\ufeff").strip() for column in columns]
                if not normalized or any(not column for column in normalized):
                    raise ValueError(f"{path.name}: 비어 있는 열 이름이 있습니다.")
                if len(normalized) > self.MAX_COLUMNS:
                    raise ValueError(
                        f"{path.name}: 열이 {len(normalized):,}개로 {self.MAX_COLUMNS}개 제한을 초과합니다."
                    )
                duplicates = sorted(
                    column for column, count in Counter(normalized).items() if count > 1
                )
                if duplicates:
                    raise ValueError(
                        f"{path.name}: 중복된 열 이름이 있습니다: {', '.join(duplicates)}"
                    )

                row_count = 0
                for row_count, row in enumerate(reader, start=1):
                    if row_count % 5_000 == 0:
                        self._cancel_if_requested(cancel_check)
                    if len(row) != len(normalized):
                        raise ValueError(
                            f"{path.name} {reader.line_num}행: 열 수가 헤더와 다릅니다 "
                            f"({len(row)}개, 예상 {len(normalized)}개)."
                        )
                    for cell in row:
                        if len(cell) > self.MAX_CELL_CHARACTERS:
                            raise ValueError(
                                f"{path.name} {reader.line_num}행: 셀이 허용 길이를 초과합니다."
                            )
                        if self.INVALID_CELL_CONTROLS.search(cell):
                            raise ValueError(
                                f"{path.name} {reader.line_num}행: NUL 또는 허용되지 않는 제어문자가 있습니다."
                            )
                    if row_count > self.MAX_INPUT_ROWS:
                        raise ValueError(
                            f"{path.name}: {self.MAX_INPUT_ROWS:,}행 제한을 초과합니다."
                        )
                return row_count
        except csv.Error as error:
            if "NUL" in str(error).upper():
                raise ValueError(
                    f"{path.name}: NUL 또는 허용되지 않는 제어문자가 있습니다."
                ) from error
            raise ValueError(
                f"{path.name}: CSV 인용 부호 또는 셀 형식이 올바르지 않습니다."
            ) from error
        finally:
            csv.field_size_limit(previous_limit)

    def _read_csv_preserving_text(
        self,
        path: Path,
        encoding: str,
    ) -> tuple[pd.DataFrame, str]:
        frame = pd.read_csv(
            path,
            encoding=encoding,
            dtype="string",
            keep_default_na=False,
            index_col=False,
            on_bad_lines="error",
        )
        return frame, encoding
    
    def time_to_seconds(self, time_str: str) -> float:
        """Convert a validated HH:MM:SS[.sss] timestamp to seconds."""
        value = str(time_str).strip()
        match = self.TIME_PATTERN.fullmatch(value)
        legacy_match = self.LEGACY_TIME_PATTERN.fullmatch(value)
        if not match and legacy_match:
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                seconds = (
                    parsed.astimezone(timezone.utc)
                    - datetime(1970, 1, 1, tzinfo=timezone.utc)
                ).total_seconds()
                if seconds >= 0:
                    return seconds
            except ValueError:
                pass
        if not match:
            raise ValueError(f"올바르지 않은 재생시간: {time_str!r}")
        fraction = match.group("fraction") or ""
        fraction_seconds = int(fraction.ljust(3, "0")) / 1000 if fraction else 0.0
        return (
            int(match.group("hours")) * 3600
            + int(match.group("minutes")) * 60
            + int(match.group("seconds"))
            + fraction_seconds
        )
    
    def seconds_to_time(self, seconds: int | float) -> str:
        """Convert seconds to HH:MM:SS, preserving milliseconds when present."""
        total_milliseconds = max(0, int(round(float(seconds) * 1000)))
        hours, remainder = divmod(total_milliseconds, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        secs, milliseconds = divmod(remainder, 1000)
        result = f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{result}.{milliseconds:03d}" if milliseconds else result
    
    def clean_message(self, message) -> str:
        """Normalize chat text while preserving custom-emote names as evidence."""
        if pd.isna(message):
            return ""

        text = unicodedata.normalize("NFC", str(message))
        text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
        text = re.sub(r"\{:([^:]+):\}", r" \1 ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    def analyze_keyword(
        self,
        keyword: str,
        interval_minutes: float,
        sensitivity: float = 2.0,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict:
        """Find sustained keyword bursts without sharing density-analysis state."""
        self._require_loaded()
        interval_seconds, sensitivity = self._validate_analysis_params(
            interval_minutes, sensitivity
        )
        keyword = str(keyword).strip()
        if not keyword:
            raise ValueError("검색 키워드를 입력하세요.")
        self._cancel_if_requested(cancel_check)

        analysis_rows = self._get_analysis_rows()
        folded_keyword = keyword.casefold()
        folded_messages = analysis_rows["clean_message"].str.casefold()
        match_mask = folded_messages.str.contains(
            re.escape(folded_keyword), regex=True, na=False
        )
        matched_rows = analysis_rows.loc[match_mask].copy()
        matched_rows["occurrence_count"] = folded_messages.loc[match_mask].str.count(
            re.escape(folded_keyword)
        )

        timeline = self._build_count_timeline(
            matched_rows,
            interval_seconds,
            count_column="occurrence_count",
        )
        events, status = self._detect_events(
            timeline,
            matched_rows,
            interval_seconds,
            sensitivity,
            minimum_count=2,
            minimum_excess=1,
            cancel_check=cancel_check,
        )
        self.keyword_timeline = timeline
        self.keyword_results = events
        self.keyword_metadata = {
            "kind": "keyword",
            "keyword": keyword,
            "interval_minutes": float(interval_seconds / 60),
            "sensitivity": sensitivity,
            "source_files": list(self.session_info.get("source_files", [])),
        }

        peak_time = self._strongest_event_time(events)
        return {
            "total_count": int(len(matched_rows)),
            "occurrence_count": int(matched_rows["occurrence_count"].sum()),
            "peak_time": peak_time,
            "timeline": timeline.to_dict("records"),
            "events": events.to_dict("records"),
            "spike_count": int(len(events)),
            "status": status,
            "sensitivity": sensitivity,
        }
    
    def analyze_chat_density(
        self,
        interval_minutes: float,
        sensitivity: float = 2.0,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict:
        """Find chat-volume events using a robust local baseline."""
        self._require_loaded()
        interval_seconds, sensitivity = self._validate_analysis_params(
            interval_minutes, sensitivity
        )
        self._cancel_if_requested(cancel_check)
        analysis_rows = self._get_analysis_rows()
        timeline = self._build_count_timeline(analysis_rows, interval_seconds)
        events, status = self._detect_events(
            timeline,
            analysis_rows,
            interval_seconds,
            sensitivity,
            minimum_count=3,
            minimum_excess=2,
            empty_status="no_evidence",
            cancel_check=cancel_check,
        )
        self.density_timeline = timeline
        self.density_results = events
        self.density_metadata = {
            "kind": "density",
            "interval_minutes": float(interval_seconds / 60),
            "sensitivity": sensitivity,
            "source_files": list(self.session_info.get("source_files", [])),
        }

        return {
            "total_count": int(len(analysis_rows)),
            "peak_time": self._strongest_event_time(events),
            "timeline": timeline.to_dict("records"),
            "events": events.to_dict("records"),
            "sensitivity": sensitivity,
            "spike_count": int(len(events)),
            "status": status,
        }

    def _require_loaded(self) -> None:
        if self.df is None:
            raise ValueError("먼저 CSV 파일을 불러오세요.")

    def _get_analysis_rows(self) -> pd.DataFrame:
        """Return non-system rows that contain usable normalized chat text."""
        self._require_loaded()
        return self.df.loc[self._analysis_mask()].copy()

    def _analysis_mask(self) -> pd.Series:
        """Identify rows that can contribute actual chat evidence."""
        self._require_loaded()
        return ~self.df["is_system"] & self.df["clean_message"].str.strip().ne("")

    def _validate_analysis_params(
        self, interval_minutes: float, sensitivity: float
    ) -> tuple[int, float]:
        try:
            interval_minutes = float(interval_minutes)
            sensitivity = float(sensitivity)
        except (TypeError, ValueError) as error:
            raise ValueError("분석 간격과 민감도는 숫자로 입력하세요.") from error
        if not math.isfinite(interval_minutes) or interval_minutes <= 0:
            raise ValueError("분석 간격은 0보다 큰 유한한 값이어야 합니다.")
        if not math.isfinite(sensitivity) or not 1.0 <= sensitivity <= 3.0:
            raise ValueError("민감도는 1.0부터 3.0 사이여야 합니다.")
        interval_seconds = max(1, int(round(interval_minutes * 60)))
        return interval_seconds, sensitivity

    def _build_count_timeline(
        self,
        rows: pd.DataFrame,
        interval_seconds: int,
        count_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """Build zero-filled half-open bins: [start, start + interval)."""
        max_seconds = float(self.df["seconds"].max())
        final_bin, _ = timeline_bounds(max_seconds, interval_seconds)
        starts = pd.RangeIndex(0, final_bin + interval_seconds, interval_seconds)
        timeline = pd.DataFrame({"time_seconds": starts})

        if rows.empty:
            counts = pd.Series(dtype="int64")
        else:
            bin_start = (
                (rows["seconds"].astype(float) // interval_seconds) * interval_seconds
            ).astype(int)
            if count_column is None:
                counts = bin_start.value_counts().sort_index()
            else:
                counts = rows.groupby(bin_start, observed=False)[count_column].sum()

        timeline["count"] = (
            timeline["time_seconds"].map(counts).fillna(0).astype(int)
        )
        timeline["time_str"] = timeline["time_seconds"].apply(self.seconds_to_time)
        return timeline

    def _detect_events(
        self,
        timeline: pd.DataFrame,
        source_rows: pd.DataFrame,
        interval_seconds: int,
        sensitivity: float,
        minimum_count: int,
        minimum_excess: int,
        empty_status: str = "no_events",
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> tuple[pd.DataFrame, str]:
        """Detect and merge local spikes, then locate their peak in raw chat time."""
        event_columns = [
            "event_id", "start_seconds", "peak_seconds", "end_seconds",
            "time_seconds", "time_str", "count", "peak_window_count",
            "baseline", "threshold", "lift", "score", "confidence",
            "unique_users", "top_user_share", "duplicate_share",
        ]
        timeline["baseline"] = 0.0
        timeline["threshold"] = 0.0
        timeline["score"] = 0.0
        timeline["is_candidate"] = False
        timeline["event_id"] = pd.Series([pd.NA] * len(timeline), dtype="Int64")

        if source_rows.empty:
            return pd.DataFrame(columns=event_columns), empty_status
        if len(timeline) < 3:
            return pd.DataFrame(columns=event_columns), "insufficient_data"

        counts = timeline["count"].astype(float).tolist()
        if len(set(counts)) <= 1:
            return pd.DataFrame(columns=event_columns), "no_events"

        # Higher sensitivity deliberately lowers the required deviation.
        deviation_multiplier = 4.0 - sensitivity
        local_radius = min(6, max(2, len(counts) // 4))
        candidates = []
        for index, count in enumerate(counts):
            if index % 1_000 == 0:
                self._cancel_if_requested(cancel_check)
            left = counts[max(0, index - local_radius):index]
            right = counts[index + 1:min(len(counts), index + local_radius + 1)]
            neighbors = left + right
            if not neighbors:
                continue
            ordered = sorted(neighbors)
            baseline = self._quantile(ordered, 0.40)
            background_values = [value for value in neighbors if value <= baseline]
            deviations = sorted(abs(value - baseline) for value in background_values)
            mad = self._median(deviations)
            scale = max(1.0, 1.4826 * mad, math.sqrt(max(baseline, 0.0) + 1.0))
            threshold = baseline + deviation_multiplier * scale
            excess = count - baseline
            lift = count / max(baseline, 1.0)
            score = excess / scale
            is_candidate = (
                count > baseline
                and count >= minimum_count
                and excess >= minimum_excess
                and count >= math.ceil(threshold)
                and (baseline == 0 or lift >= 1.35)
            )
            timeline.at[index, "baseline"] = round(baseline, 3)
            timeline.at[index, "threshold"] = round(threshold, 3)
            timeline.at[index, "score"] = round(score, 3)
            timeline.at[index, "is_candidate"] = bool(is_candidate)
            if is_candidate:
                candidates.append(index)

        if not candidates:
            return pd.DataFrame(columns=event_columns), "no_events"

        groups: List[List[int]] = []
        for index in candidates:
            if groups and index == groups[-1][-1] + 1:
                groups[-1].append(index)
            elif groups and index == groups[-1][-1] + 2:
                previous = groups[-1][-1]
                valley = previous + 1
                valley_count = counts[valley]
                valley_baseline = float(timeline.iloc[valley]["baseline"])
                bridge_level = 0.70 * min(counts[previous], counts[index])
                if (
                    valley_count >= minimum_count
                    and valley_count >= bridge_level
                    and valley_count > valley_baseline
                    and (valley_baseline == 0 or valley_count / valley_baseline >= 1.35)
                ):
                    groups[-1].append(index)
                else:
                    groups.append([index])
            else:
                groups.append([index])

        events = []
        source_end = float(self.df["seconds"].max())
        for event_number, group in enumerate(groups, start=1):
            self._cancel_if_requested(cancel_check)
            first_index = group[0]
            last_index = group[-1]
            event_indices = list(range(first_index, last_index + 1))
            start_seconds = int(timeline.iloc[first_index]["time_seconds"])
            natural_end = int(timeline.iloc[last_index]["time_seconds"]) + interval_seconds
            end_seconds = min(
                source_end,
                natural_end,
            )
            end_mask = (
                source_rows["seconds"].le(end_seconds)
                if source_end < natural_end
                else source_rows["seconds"].lt(end_seconds)
            )
            event_rows = source_rows.loc[
                source_rows["seconds"].ge(start_seconds)
                & end_mask
            ]
            peak_count_column = (
                "occurrence_count" if "occurrence_count" in event_rows.columns else None
            )
            peak_seconds, peak_window_count = self._find_actual_peak(
                event_rows,
                count_column=peak_count_column,
            )
            event_timeline = timeline.iloc[event_indices]
            count = int(event_timeline["count"].sum())
            baseline = float(event_timeline["baseline"].mean())
            threshold = float(event_timeline["threshold"].mean())
            score = float(event_timeline["score"].max())
            lift = count / max(baseline * len(event_indices), 1.0)
            identity_column = (
                "participant_key" if "participant_key" in event_rows.columns else "닉네임"
            )
            unique_users = int(event_rows[identity_column].nunique()) if not event_rows.empty else 0
            if event_rows.empty:
                top_user_share = 0.0
            else:
                if peak_count_column is None:
                    user_weights = event_rows[identity_column].value_counts()
                else:
                    user_weights = event_rows.groupby(identity_column, observed=False)[
                        peak_count_column
                    ].sum()
                top_user_share = float(user_weights.max() / max(user_weights.sum(), 1))
            duplicate_columns = ["seconds", identity_column, "message_raw"]
            duplicate_columns = [
                column for column in duplicate_columns if column in event_rows.columns
            ]
            duplicate_share = (
                float(event_rows.duplicated(subset=duplicate_columns).mean())
                if duplicate_columns and not event_rows.empty
                else 0.0
            )
            diversity_factor = min(1.0, unique_users / 5.0) * (1.0 - top_user_share)
            confidence = (1.0 - min(0.75, duplicate_share)) * min(
                1.0,
                max(0.0, 0.45 * min(score / 5.0, 1.0)
                    + 0.35 * min(lift / 3.0, 1.0)
                    + 0.20 * diversity_factor),
            )
            timeline.loc[event_indices, "event_id"] = event_number
            events.append({
                "event_id": event_number,
                "start_seconds": start_seconds,
                "peak_seconds": round(peak_seconds, 3),
                "end_seconds": round(float(end_seconds), 3),
                "time_seconds": round(peak_seconds, 3),
                "time_str": self.seconds_to_time(peak_seconds),
                "count": count,
                "peak_window_count": peak_window_count,
                "baseline": round(baseline, 3),
                "threshold": round(threshold, 3),
                "lift": round(lift, 3),
                "score": round(score, 3),
                "confidence": round(confidence, 3),
                "unique_users": unique_users,
                "top_user_share": round(top_user_share, 3),
                "duplicate_share": round(duplicate_share, 3),
            })

        return pd.DataFrame(events, columns=event_columns), "ok"

    @staticmethod
    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        middle = len(values) // 2
        if len(values) % 2:
            return float(values[middle])
        return float((values[middle - 1] + values[middle]) / 2)

    @staticmethod
    def _quantile(values: List[float], probability: float) -> float:
        """Return a conservative lower quantile from an already sorted list."""
        if not values:
            return 0.0
        position = (len(values) - 1) * probability
        return float(values[int(math.floor(position))])

    def _find_actual_peak(
        self,
        rows: pd.DataFrame,
        window_seconds: float = 15.0,
        count_column: Optional[str] = None,
    ) -> tuple[float, int]:
        if rows.empty:
            return 0.0, 0
        ordered = rows.sort_values("seconds")
        times = [float(value) for value in ordered["seconds"]]
        if count_column is None:
            weights = [1] * len(ordered)
        else:
            weights = [max(0, int(value)) for value in ordered[count_column]]
        best_left = 0
        best_right = 0
        best_count = -1
        right = 0
        window_count = 0
        for left, start in enumerate(times):
            right = max(right, left)
            while right < len(times) and times[right] < start + window_seconds:
                window_count += weights[right]
                right += 1
            if window_count > best_count:
                best_left, best_right = left, right
                best_count = window_count
            window_count -= weights[left]
        peak_times = times[best_left:best_right]
        peak_weights = weights[best_left:best_right]
        return self._weighted_median(peak_times, peak_weights), max(0, best_count)

    @staticmethod
    def _weighted_median(values: List[float], weights: List[int]) -> float:
        total = sum(weights)
        if not values or total <= 0:
            return 0.0
        midpoint = total / 2
        cumulative = 0
        for index, (value, weight) in enumerate(zip(values, weights)):
            cumulative += weight
            if cumulative > midpoint:
                return float(value)
            if cumulative == midpoint:
                next_value = next(
                    (
                        candidate
                        for candidate, candidate_weight in zip(
                            values[index + 1:], weights[index + 1:]
                        )
                        if candidate_weight > 0
                    ),
                    value,
                )
                return float((value + next_value) / 2)
        return float(values[-1])

    @staticmethod
    def _strongest_event_time(events: pd.DataFrame) -> Optional[str]:
        if events.empty:
            return None
        strongest = events.sort_values(
            ["score", "peak_window_count"], ascending=False
        ).iloc[0]
        return str(strongest["time_str"])
    
    def get_keyword_timeline(self) -> Optional[pd.DataFrame]:
        """Get keyword analysis timeline"""
        return self.keyword_timeline

    def get_density_timeline(self) -> Optional[pd.DataFrame]:
        """Get density analysis timeline without exposing keyword state."""
        return self.density_timeline

    def build_editor_moments(
        self,
        kind: str = "density",
        pre_roll_seconds: float = 15.0,
        post_roll_seconds: float = 20.0,
        *,
        events: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict] = None,
        media_duration_seconds: Optional[float] = None,
    ) -> List[Dict]:
        """Create editor-ready ranges around each event's raw-chat peak."""
        if kind not in {"density", "keyword"}:
            raise ValueError("분석 유형은 density 또는 keyword여야 합니다.")
        try:
            pre_roll_seconds = float(pre_roll_seconds)
            post_roll_seconds = float(post_roll_seconds)
        except (TypeError, ValueError) as error:
            raise ValueError("프리롤과 포스트롤은 숫자여야 합니다.") from error
        if (
            not math.isfinite(pre_roll_seconds)
            or not math.isfinite(post_roll_seconds)
            or pre_roll_seconds < 0
            or post_roll_seconds < 0
        ):
            raise ValueError("프리롤과 포스트롤은 0 이상의 유한한 값이어야 합니다.")

        if events is None:
            events = self.density_results if kind == "density" else self.keyword_results
        if metadata is None:
            metadata = self.density_metadata if kind == "density" else self.keyword_metadata
        if events is None or metadata is None:
            raise ValueError("먼저 해당 분석을 실행하세요.")
        if events.empty:
            return []

        if media_duration_seconds is not None:
            try:
                media_duration_seconds = float(media_duration_seconds)
            except (TypeError, ValueError) as error:
                raise ValueError("미디어 길이는 숫자여야 합니다.") from error
            if not math.isfinite(media_duration_seconds) or media_duration_seconds <= 0:
                raise ValueError("미디어 길이는 0보다 큰 유한한 값이어야 합니다.")
        keyword = str(metadata.get("keyword", ""))
        moments = []
        for number, (_, event) in enumerate(events.iterrows(), start=1):
            peak_seconds = float(event["peak_seconds"])
            clip_start = max(0.0, peak_seconds - pre_roll_seconds)
            clip_end = peak_seconds + post_roll_seconds
            if media_duration_seconds is not None:
                clip_end = min(media_duration_seconds, clip_end)
            label = (
                f"{keyword} 급증 #{number}" if kind == "keyword"
                else f"채팅 급증 #{number}"
            )
            moments.append({
                "moment_id": f"{kind}-{number:03d}",
                "kind": kind,
                "keyword": keyword,
                "label": label,
                "clip_start_seconds": round(clip_start, 3),
                "peak_seconds": round(peak_seconds, 3),
                "clip_end_seconds": round(clip_end, 3),
                "event_start_seconds": round(float(event["start_seconds"]), 3),
                "event_end_seconds": round(float(event["end_seconds"]), 3),
                "clip_start_time": self.seconds_to_time(clip_start),
                "peak_time": self.seconds_to_time(peak_seconds),
                "clip_end_time": self.seconds_to_time(clip_end),
                "pre_roll_seconds": round(peak_seconds - clip_start, 3),
                "post_roll_seconds": round(clip_end - peak_seconds, 3),
                "count": int(event["count"]),
                "peak_window_count": int(event["peak_window_count"]),
                "lift": float(event["lift"]),
                "score": float(event["score"]),
                "confidence": float(event["confidence"]),
                "unique_users": int(event["unique_users"]),
                "top_user_share": float(event["top_user_share"]),
                "duplicate_share": float(event.get("duplicate_share", 0.0)),
            })
        return moments

    def export_editor_csv(
        self,
        output_path: str,
        kind: str = "density",
        pre_roll_seconds: float = 15.0,
        post_roll_seconds: float = 20.0,
        *,
        events: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict] = None,
        media_duration_seconds: Optional[float] = None,
    ) -> bool:
        """Export a human-readable editor work table, not a native NLE project."""
        moments = self.build_editor_moments(
            kind,
            pre_roll_seconds,
            post_roll_seconds,
            events=events,
            metadata=metadata,
            media_duration_seconds=media_duration_seconds,
        )
        count_label = "키워드 출현 횟수" if kind == "keyword" else "이벤트 채팅 수"
        peak_count_label = "피크 15초 키워드 출현" if kind == "keyword" else "피크 15초 채팅 수"
        columns = {
            "moment_id": "구간 ID",
            "kind": "분석 유형",
            "keyword": "키워드",
            "label": "구간 이름",
            "clip_start_time": "추천 시작",
            "clip_start_seconds": "추천 시작(초)",
            "peak_time": "핵심 시점",
            "peak_seconds": "핵심 시점(초)",
            "clip_end_time": "추천 종료",
            "clip_end_seconds": "추천 종료(초)",
            "pre_roll_seconds": "프리롤(초)",
            "post_roll_seconds": "포스트롤(초)",
            "count": count_label,
            "peak_window_count": peak_count_label,
            "lift": "기준 대비 배수",
            "confidence": "신뢰도",
            "unique_users": "ID 우선 참여자 수",
            "top_user_share": "최다 참여자 비율",
            "duplicate_share": "동일 행 비율",
        }
        frame = pd.DataFrame(moments)
        if frame.empty:
            frame = pd.DataFrame(columns=list(columns))
        frame = frame[list(columns)].rename(columns=columns)
        for column in frame.select_dtypes(include=["object", "string"]).columns:
            frame[column] = frame[column].map(self._spreadsheet_safe_text)
        atomic_save(
            output_path,
            lambda temporary: frame.to_csv(
                temporary,
                index=False,
                encoding="utf-8-sig",
            ),
        )
        return True

    @staticmethod
    def _spreadsheet_safe_text(value: object) -> object:
        if not isinstance(value, str) or not value:
            return value
        if value[0] in "=+-@\t\r\n":
            return "'" + value
        return value

    @staticmethod
    def _rate_info(fps: float) -> tuple[int, bool, float, str]:
        try:
            fps = float(fps)
        except (TypeError, ValueError) as error:
            raise ValueError("프레임 레이트는 숫자여야 합니다.") from error
        supported = {
            23.976: (24, True, 24000 / 1001, "1001/24000s"),
            24.0: (24, False, 24.0, "1/24s"),
            25.0: (25, False, 25.0, "1/25s"),
            29.97: (30, True, 30000 / 1001, "1001/30000s"),
            30.0: (30, False, 30.0, "1/30s"),
            50.0: (50, False, 50.0, "1/50s"),
            59.94: (60, True, 60000 / 1001, "1001/60000s"),
            60.0: (60, False, 60.0, "1/60s"),
        }
        for candidate, info in supported.items():
            if abs(fps - candidate) < 0.002:
                return info
        raise ValueError("지원 프레임 레이트: 23.976, 24, 25, 29.97, 30, 50, 59.94, 60")

    def export_premiere_xml(
        self,
        output_path: str,
        kind: str = "density",
        fps: float = 30.0,
        pre_roll_seconds: float = 15.0,
        post_roll_seconds: float = 20.0,
        *,
        events: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict] = None,
        media_duration_seconds: Optional[float] = None,
    ) -> bool:
        """Export Final Cut Pro 7 XML, which Premiere can exchange with markers."""
        moments = self.build_editor_moments(
            kind,
            pre_roll_seconds,
            post_roll_seconds,
            events=events,
            metadata=metadata,
            media_duration_seconds=media_duration_seconds,
        )
        timebase, ntsc, actual_fps, _ = self._rate_info(fps)
        duration_seconds = max(
            float(self.session_info.get("end_seconds", 0.0)),
            max((item["clip_end_seconds"] for item in moments), default=0.0),
        )

        root = ET.Element("xmeml", version="5")
        sequence = ET.SubElement(root, "sequence")
        ET.SubElement(sequence, "name").text = "Clip Moment Markers"
        ET.SubElement(sequence, "duration").text = str(round(duration_seconds * actual_fps))
        rate = ET.SubElement(sequence, "rate")
        ET.SubElement(rate, "timebase").text = str(timebase)
        ET.SubElement(rate, "ntsc").text = "TRUE" if ntsc else "FALSE"
        timecode = ET.SubElement(sequence, "timecode")
        tc_rate = ET.SubElement(timecode, "rate")
        ET.SubElement(tc_rate, "timebase").text = str(timebase)
        ET.SubElement(tc_rate, "ntsc").text = "TRUE" if ntsc else "FALSE"
        ET.SubElement(timecode, "string").text = "00:00:00:00"
        ET.SubElement(timecode, "frame").text = "0"
        ET.SubElement(timecode, "displayformat").text = "NDF"

        for moment in moments:
            marker_frame = round(moment["peak_seconds"] * actual_fps)
            marker = ET.SubElement(sequence, "marker")
            ET.SubElement(marker, "name").text = moment["label"]
            ET.SubElement(marker, "comment").text = (
                f"추천 {moment['clip_start_time']} - {moment['clip_end_time']} / "
                f"신뢰도 {moment['confidence']:.2f}"
            )
            ET.SubElement(marker, "in").text = str(marker_frame)
            ET.SubElement(marker, "out").text = str(marker_frame + 1)

        media = ET.SubElement(sequence, "media")
        video = ET.SubElement(media, "video")
        fmt = ET.SubElement(video, "format")
        characteristics = ET.SubElement(fmt, "samplecharacteristics")
        format_rate = ET.SubElement(characteristics, "rate")
        ET.SubElement(format_rate, "timebase").text = str(timebase)
        ET.SubElement(format_rate, "ntsc").text = "TRUE" if ntsc else "FALSE"
        ET.SubElement(characteristics, "width").text = "1920"
        ET.SubElement(characteristics, "height").text = "1080"
        ET.SubElement(characteristics, "anamorphic").text = "FALSE"
        ET.indent(root, space="  ")
        atomic_save(
            output_path,
            lambda temporary: ET.ElementTree(root).write(
                temporary,
                encoding="utf-8",
                xml_declaration=True,
            ),
        )
        return True

    def export_fcpxml(
        self,
        output_path: str,
        kind: str = "density",
        fps: float = 30.0,
        pre_roll_seconds: float = 15.0,
        post_roll_seconds: float = 20.0,
        *,
        events: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict] = None,
        media_duration_seconds: Optional[float] = None,
    ) -> bool:
        """Export a marker-only FCPXML project for Final Cut Pro."""
        moments = self.build_editor_moments(
            kind,
            pre_roll_seconds,
            post_roll_seconds,
            events=events,
            metadata=metadata,
            media_duration_seconds=media_duration_seconds,
        )
        _, _, actual_fps, frame_duration = self._rate_info(fps)
        duration_seconds = max(
            float(self.session_info.get("end_seconds", 0.0)),
            max((item["clip_end_seconds"] for item in moments), default=0.0),
            1.0 / actual_fps,
        )
        duration_frames = max(1, round(duration_seconds * actual_fps))
        denominator = 24000 if abs(actual_fps - 24000 / 1001) < 0.01 else (
            30000 if abs(actual_fps - 30000 / 1001) < 0.01 else (
                60000 if abs(actual_fps - 60000 / 1001) < 0.01 else round(actual_fps)
            )
        )
        numerator_per_frame = 1001 if denominator in {24000, 30000, 60000} else 1
        duration_value = f"{duration_frames * numerator_per_frame}/{denominator}s"

        root = ET.Element("fcpxml", version="1.10")
        resources = ET.SubElement(root, "resources")
        ET.SubElement(
            resources,
            "format",
            id="r1",
            name="FFVideoFormatRateUndefined",
            frameDuration=frame_duration,
            width="1920",
            height="1080",
        )
        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", name="Clip Moment Markers")
        project = ET.SubElement(event, "project", name="Clip Moment Markers")
        sequence = ET.SubElement(
            project,
            "sequence",
            format="r1",
            duration=duration_value,
            tcStart="0s",
            tcFormat="NDF",
        )
        spine = ET.SubElement(sequence, "spine")
        gap = ET.SubElement(
            spine,
            "gap",
            name="Clip Moment Timeline",
            offset="0s",
            start="0s",
            duration=sequence.attrib["duration"],
        )
        for moment in moments:
            frame = round(moment["peak_seconds"] * actual_fps)
            marker = ET.SubElement(
                gap,
                "marker",
                start=f"{frame * numerator_per_frame}/{denominator}s",
                duration=frame_duration,
                value=moment["label"],
                note=(
                    f"추천 {moment['clip_start_time']} - {moment['clip_end_time']} / "
                    f"신뢰도 {moment['confidence']:.2f}"
                ),
            )

        ET.indent(root, space="  ")
        atomic_save(
            output_path,
            lambda temporary: ET.ElementTree(root).write(
                temporary,
                encoding="utf-8",
                xml_declaration=True,
            ),
        )
        return True
    
    def get_all_text(self) -> str:
        """Get whitespace-based expressions without reaction-variant flooding."""
        if self.df is None:
            return ""

        tokens = []
        for message in self.df.loc[self._analysis_mask(), "clean_message"]:
            text = str(message)
            text = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"(ㅋ{2,}|ㅠ{2,}|ㅜ{2,})", r" \1 ", text)
            text = re.sub(r"ㅋ{3,}", "ㅋㅋ", text)
            text = re.sub(r"ㅠ{3,}", "ㅠㅠ", text)
            text = re.sub(r"ㅜ{3,}", "ㅜㅜ", text)
            text = re.sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ_]+", " ", text)
            for token in text.split():
                normalized = token.casefold()
                if (
                    (len(normalized) < 2 and normalized not in {"와", "헐"})
                    or normalized.isdigit()
                ):
                    continue
                tokens.append(normalized)
        return " ".join(tokens)
