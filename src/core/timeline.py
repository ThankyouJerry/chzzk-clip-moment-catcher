"""Shared timeline sizing helpers for bounded desktop analysis."""

from __future__ import annotations

import math


MAX_TIMELINE_BINS = 20_000


def timeline_bounds(max_seconds: float, interval_seconds: int) -> tuple[int, int]:
    """Return the last bin start and bin count after applying a safety limit."""
    if not math.isfinite(max_seconds) or max_seconds < 0:
        raise ValueError("CSV 재생시간 범위가 올바르지 않습니다.")
    if interval_seconds <= 0:
        raise ValueError("분석 간격은 0보다 커야 합니다.")

    final_bin = int(math.floor(max_seconds / interval_seconds)) * interval_seconds
    bin_count = final_bin // interval_seconds + 1
    if bin_count > MAX_TIMELINE_BINS:
        minimum_interval = max(1, math.ceil(max_seconds / (MAX_TIMELINE_BINS - 1)))
        minimum_minutes = minimum_interval / 60
        raise ValueError(
            f"현재 설정은 시간 구간을 {bin_count:,}개 생성해 분석할 수 없습니다. "
            f"분석 간격을 {minimum_minutes:.3f}분({minimum_interval}초) 이상으로 늘려주세요."
        )
    return final_bin, bin_count
