from __future__ import annotations

"""Korean chat valence/arousal analysis with explicit evidence handling."""

import math
import re
import unicodedata
from typing import Dict, List, Optional

import pandas as pd

from core.timeline import timeline_bounds


class SentimentAnalyzer:
    """Separates emotional direction (valence) from reaction strength (arousal)."""

    TIMELINE_COLUMNS = [
        "time_seconds",
        "time_str",
        "sentiment_score",
        "valence",
        "arousal",
        "message_count",
        "sentiment_message_count",
        "evidence_count",
        "coverage",
    ]

    PHRASE_SIGNALS = (
        # Negations and negative compounds must run before their positive roots.
        (r"재미\s*없|재미없|노잼|안\s*(?:웃|재밌|좋)|못\s*(?:웃|즐기)", -0.75, 0.55),
        (r"최악|극혐|별로|싫어|싫다|망했|망함", -0.75, 0.65),
        (r"아쉽|안타깝|슬프|속상|우울", -0.55, 0.45),
        (r"레전드|역대급|최고|대박|미쳤|미친|쩐다|지린다", 0.8, 0.75),
        (r"개웃|웃겨|재밌|재미있|꿀잼", 0.7, 0.65),
        (r"좋아|좋다|굿|잘했|멋져|멋있", 0.6, 0.45),
        (r"감동|훈훈|따뜻|고마워|감사", 0.55, 0.4),
        (r"화이팅|파이팅|응원|힘내", 0.55, 0.5),
        (r"헐|우와|뭐야|세상에", 0.15, 0.7),
        # "눈물" alone can be sadness or touching, so keep direction weak.
        (r"눈물", -0.1, 0.5),
    )

    EMOJI_SIGNALS = {
        "😂": (0.8, 0.8), "🤣": (0.85, 0.9), "😄": (0.7, 0.6),
        "😁": (0.7, 0.6), "😆": (0.7, 0.7), "😊": (0.6, 0.4),
        "🥰": (0.7, 0.5), "😍": (0.75, 0.6), "🤩": (0.8, 0.8),
        "👍": (0.65, 0.4), "👏": (0.65, 0.55), "🔥": (0.5, 0.85),
        "🎉": (0.75, 0.8), "✨": (0.5, 0.45),
        "😢": (-0.6, 0.55), "😭": (-0.7, 0.8), "😞": (-0.55, 0.4),
        "😔": (-0.5, 0.35), "😟": (-0.45, 0.45), "😣": (-0.55, 0.6),
        "😖": (-0.6, 0.65), "😱": (-0.25, 0.9), "😮": (0.05, 0.65),
        "😲": (0.05, 0.7), "🤯": (0.1, 0.9),
        "❤️": (0.7, 0.5), "💕": (0.7, 0.5), "💖": (0.7, 0.55),
        "💙": (0.6, 0.4), "💚": (0.6, 0.4), "💛": (0.6, 0.4),
        "💜": (0.6, 0.4),
    }

    def __init__(self):
        self.sentiment_results: Optional[pd.DataFrame] = None
        self.mood_changes: List[Dict] = []
        self.analysis_metadata: Optional[Dict] = None

    def reset(self) -> None:
        self.sentiment_results = None
        self.mood_changes = []
        self.analysis_metadata = None

    def _set_empty_timeline(self, interval_seconds: Optional[int] = None) -> pd.DataFrame:
        self.sentiment_results = pd.DataFrame(columns=self.TIMELINE_COLUMNS)
        self.mood_changes = []
        self.analysis_metadata = {
            "interval_seconds": interval_seconds or 0,
            "message_count": 0,
        }
        return self.sentiment_results

    def analyze_message(self, message: str) -> float:
        """Return valence for compatibility; neutral/no-evidence text returns 0."""
        return float(self.analyze_message_signals(message)["valence"])

    def analyze_message_signals(
        self, message: str, custom_emote_count: int = 0
    ) -> Dict[str, float | int | bool]:
        try:
            custom_emote_count = max(0, int(custom_emote_count))
        except (TypeError, ValueError):
            custom_emote_count = 0
        if pd.isna(message) or not str(message).strip():
            return {
                "valence": 0.0,
                "arousal": min(0.75, 0.25 + custom_emote_count * 0.1) if custom_emote_count else 0.0,
                "evidence_count": 1 if custom_emote_count else 0,
                "has_valence": False,
            }

        text = unicodedata.normalize("NFC", str(message)).casefold()
        valence_signals: List[float] = []
        arousal_signals: List[float] = []
        occupied: List[tuple[int, int]] = []

        def add_signal(start: int, end: int, valence: float, arousal: float) -> None:
            if any(start < used_end and end > used_start for used_start, used_end in occupied):
                return
            occupied.append((start, end))
            valence_signals.append(valence)
            arousal_signals.append(arousal)

        # Repeated chat reactions are one signal, not every overlapping substring.
        for match in re.finditer(r"ㅋ{2,}", text):
            length = len(match.group())
            add_signal(match.start(), match.end(), min(0.9, 0.45 + length * 0.08), min(1.0, 0.45 + length * 0.08))
        for match in re.finditer(r"(?:ㅠ|ㅜ){2,}", text):
            length = len(match.group())
            add_signal(match.start(), match.end(), max(-0.9, -0.35 - length * 0.08), min(1.0, 0.4 + length * 0.08))

        for pattern, valence, arousal in self.PHRASE_SIGNALS:
            for match in re.finditer(pattern, text):
                add_signal(match.start(), match.end(), valence, arousal)

        for emoji, (valence, arousal) in self.EMOJI_SIGNALS.items():
            for match in re.finditer(re.escape(emoji), text):
                add_signal(match.start(), match.end(), valence, arousal)

        punctuation = re.findall(r"[!?]{2,}", text)
        if punctuation:
            arousal_signals.append(min(0.85, 0.35 + max(map(len, punctuation)) * 0.1))

        if custom_emote_count:
            arousal_signals.append(min(0.75, 0.25 + custom_emote_count * 0.1))

        valence = sum(valence_signals) / len(valence_signals) if valence_signals else 0.0
        arousal = max(arousal_signals, default=0.0)
        return {
            "valence": round(max(-1.0, min(1.0, valence)), 4),
            "arousal": round(max(0.0, min(1.0, arousal)), 4),
            "evidence_count": len(valence_signals) + len(arousal_signals),
            "has_valence": bool(valence_signals),
        }

    @staticmethod
    def _validate_interval(interval_minutes: float) -> int:
        try:
            interval_minutes = float(interval_minutes)
        except (TypeError, ValueError) as error:
            raise ValueError("분위기 분석 간격은 숫자로 입력하세요.") from error
        if not math.isfinite(interval_minutes) or interval_minutes <= 0:
            raise ValueError("분위기 분석 간격은 0보다 큰 유한한 값이어야 합니다.")
        return max(1, int(round(interval_minutes * 60)))

    def calculate_message_frequency(
        self, df: pd.DataFrame, interval_seconds: int
    ) -> pd.DataFrame:
        if interval_seconds <= 0:
            raise ValueError("분석 간격은 0보다 커야 합니다.")
        work = df.copy()
        work["time_seconds"] = (
            (work["seconds"].astype(float) // interval_seconds) * interval_seconds
        ).astype(int)
        frequency = work.groupby("time_seconds", observed=False).size().reset_index(name="frequency")
        return frequency

    def analyze_timeline(
        self, df: pd.DataFrame, interval_minutes: float = 1.0
    ) -> pd.DataFrame:
        if df is None or len(df) == 0:
            return self._set_empty_timeline()
        if "seconds" not in df or "clean_message" not in df:
            raise ValueError("분위기 분석에 seconds와 clean_message 열이 필요합니다.")

        interval_seconds = self._validate_interval(interval_minutes)
        non_system = ~df.get("is_system", pd.Series(False, index=df.index)).astype(bool)
        non_blank = df["clean_message"].astype("string").str.strip().ne("")
        work = df.loc[non_system & non_blank].copy()
        if work.empty:
            return self._set_empty_timeline(interval_seconds)

        custom_counts = work.get("custom_emote_count", pd.Series(0, index=work.index))
        sentiment_text = work.get("message_raw", work["clean_message"]).astype("string")
        sentiment_text = sentiment_text.str.replace(r"\{:[^:]+:\}", "", regex=True)
        signals = [
            self.analyze_message_signals(message, custom_count)
            for message, custom_count in zip(sentiment_text, custom_counts)
        ]
        signal_frame = pd.DataFrame(signals, index=work.index)
        work = pd.concat([work, signal_frame], axis=1)
        work["time_seconds"] = (
            (work["seconds"].astype(float) // interval_seconds) * interval_seconds
        ).astype(int)

        final_bin, _ = timeline_bounds(float(work["seconds"].max()), interval_seconds)
        work["valence_weight"] = (0.5 + work["arousal"].astype(float)).where(
            work["has_valence"], 0.0
        )
        work["weighted_valence"] = (
            work["valence"].astype(float) * work["valence_weight"]
        )
        grouped = work.groupby("time_seconds", observed=False).agg(
            message_count=("clean_message", "size"),
            sentiment_message_count=("has_valence", "sum"),
            evidence_count=("evidence_count", "sum"),
            arousal_sum=("arousal", "sum"),
            valence_weight=("valence_weight", "sum"),
            weighted_valence=("weighted_valence", "sum"),
        )
        starts = pd.RangeIndex(0, final_bin + interval_seconds, interval_seconds)
        timeline = pd.DataFrame({"time_seconds": starts}).join(grouped, on="time_seconds")
        integer_columns = ["message_count", "sentiment_message_count", "evidence_count"]
        timeline[integer_columns] = timeline[integer_columns].fillna(0).astype(int)
        populated = timeline["message_count"].gt(0)
        has_valence = timeline["sentiment_message_count"].gt(0)
        timeline["arousal"] = (
            timeline["arousal_sum"] / timeline["message_count"]
        ).where(populated, math.nan)
        timeline["valence"] = (
            timeline["weighted_valence"] / timeline["valence_weight"]
        ).where(has_valence, math.nan)
        timeline["sentiment_score"] = timeline["valence"]
        timeline["coverage"] = (
            timeline["sentiment_message_count"] / timeline["message_count"]
        ).where(populated, 0.0).round(4)
        timeline["time_str"] = timeline["time_seconds"].apply(self._seconds_to_time)
        self.sentiment_results = timeline[self.TIMELINE_COLUMNS]
        self.mood_changes = []
        self.analysis_metadata = {
            "interval_seconds": interval_seconds,
            "message_count": int(len(work)),
        }
        return self.sentiment_results

    def get_summary(self) -> Dict[str, float | int]:
        if self.sentiment_results is None or self.sentiment_results.empty:
            return {
                "valence": math.nan,
                "arousal": math.nan,
                "coverage": 0.0,
                "message_count": 0,
            }
        timeline = self.sentiment_results
        valence_rows = timeline.loc[timeline["sentiment_message_count"].gt(0)]
        if valence_rows.empty:
            valence = math.nan
        else:
            weights = valence_rows["sentiment_message_count"].astype(float)
            valence = float((valence_rows["valence"] * weights).sum() / weights.sum())
        populated = timeline.loc[timeline["message_count"].gt(0)]
        message_count = int(populated["message_count"].sum())
        arousal = (
            float((populated["arousal"] * populated["message_count"]).sum() / message_count)
            if message_count else math.nan
        )
        sentiment_messages = int(populated["sentiment_message_count"].sum())
        return {
            "valence": valence,
            "arousal": arousal,
            "coverage": sentiment_messages / message_count if message_count else 0.0,
            "message_count": message_count,
        }

    def detect_mood_changes(
        self,
        threshold: float = 0.3,
        min_change: float = 0.2,
        min_sentiment_messages: int = 2,
        min_coverage: float = 0.03,
    ) -> List[Dict]:
        if self.sentiment_results is None or len(self.sentiment_results) < 2:
            self.mood_changes = []
            return []
        if threshold < 0 or min_change < 0:
            raise ValueError("변화 감지 기준은 0 이상이어야 합니다.")
        if min_sentiment_messages < 1:
            raise ValueError("최소 정서 근거 메시지 수는 1 이상이어야 합니다.")
        if not math.isfinite(min_coverage) or not 0 <= min_coverage <= 1:
            raise ValueError("최소 정서 근거 커버리지는 0부터 1 사이여야 합니다.")

        changes = []
        df = self.sentiment_results
        interval_seconds = int((self.analysis_metadata or {}).get("interval_seconds", 0))
        for index in range(1, len(df)):
            previous = df.iloc[index - 1]
            current = df.iloc[index]
            if pd.isna(previous["valence"]) or pd.isna(current["valence"]):
                continue
            if any(
                int(row["sentiment_message_count"]) < min_sentiment_messages
                or float(row["coverage"]) < min_coverage
                for row in (previous, current)
            ):
                continue
            if interval_seconds and current["time_seconds"] - previous["time_seconds"] != interval_seconds:
                continue
            change = float(current["valence"] - previous["valence"])
            arousal = 0.0 if pd.isna(current["arousal"]) else float(current["arousal"])
            if abs(change) < min_change:
                continue
            if max(abs(float(current["valence"])), arousal) < threshold:
                continue
            change_type = self._classify_mood_change(float(current["valence"]), change, arousal)
            changes.append({
                "time": current["time_str"],
                "time_seconds": int(current["time_seconds"]),
                "sentiment_score": float(current["valence"]),
                "valence": float(current["valence"]),
                "arousal": arousal,
                "change": change,
                "type": change_type,
                "description": self._get_change_description(change_type, change),
                "evidence_count": int(current["evidence_count"]),
                "sentiment_message_count": int(current["sentiment_message_count"]),
                "coverage": float(current["coverage"]),
            })

        changes.sort(key=lambda item: (abs(item["change"]), item["arousal"]), reverse=True)
        self.mood_changes = changes
        return changes

    @staticmethod
    def _classify_mood_change(score: float, change: float, arousal: float) -> str:
        if change > 0:
            if arousal >= 0.6:
                return "excitement"
            if score > 0.2:
                return "positive"
            return "recovery"
        if score < -0.35:
            return "sadness"
        if score < 0:
            return "negative"
        return "calm"

    @staticmethod
    def _get_change_description(change_type: str, change: float) -> str:
        descriptions = {
            "excitement": "반응 강도가 높은 긍정 전환",
            "positive": "긍정적 분위기 전환",
            "recovery": "분위기 회복",
            "sadness": "슬픈 분위기 전환",
            "negative": "부정적 분위기 전환",
            "calm": "반응 진정",
        }
        intensity = "급격한" if abs(change) > 0.4 else "점진적"
        return f"{intensity} {descriptions.get(change_type, '분위기 변화')}"

    @staticmethod
    def _seconds_to_time(seconds: int | float) -> str:
        seconds = max(0, int(seconds))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def export_mood_markers(self, output_path: str, top_n: int = 10) -> bool:
        if not self.mood_changes:
            return False
        markers = [
            {
                "Marker Name": f"분위기 변화 - {change['type']}",
                "Description": (
                    f"{change['description']} / 정서 {change['valence']:+.2f} / "
                    f"반응 강도 {change['arousal']:.2f} / "
                    f"정서 근거 {change['sentiment_message_count']}개 / "
                    f"커버리지 {change['coverage']:.1%}"
                ),
                "In": change["time"],
                "Out": "",
                "Duration": "",
                "Marker Type": "Comment",
            }
            for change in self.mood_changes[:top_n]
        ]
        pd.DataFrame(markers).to_csv(output_path, index=False, encoding="utf-8-sig")
        return True

    def get_sentiment_timeline(self) -> Optional[pd.DataFrame]:
        return self.sentiment_results

    def get_mood_changes(self) -> List[Dict]:
        return self.mood_changes
