"""Fallback peak detection implementation.

This module provides a fallback peak detection algorithm when the external
peakdetect module is not available. It implements basic local extrema detection
using a lookahead window approach.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


def peakdetect(
    y_axis: Sequence[Any],
    x_axis: Sequence[int] | None = None,
    lookahead: int = 1,
    delta: float = 0,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Detect peaks and troughs in a time series.

    This is a fallback implementation that identifies local maxima (peaks)
    and local minima (troughs) by comparing each point with its neighbors
    within a lookahead window.

    Args:
        y_axis: The data values to analyze.
        x_axis: Optional x-axis values (defaults to indices).
        lookahead: Number of samples to look ahead/behind for comparison.
        delta: Minimum amplitude difference required between consecutive extrema.

    Returns:
        Tuple of (peaks, troughs) where each is a list of (x, y) tuples.
    """
    peaks: list[tuple[int, float]] = []
    troughs: list[tuple[int, float]] = []

    y_values: list[float] = [float(v) for v in y_axis]
    if x_axis is None:
        x_values: list[int] = list(range(len(y_values)))
    else:
        x_values = list(x_axis)

    if len(y_values) < lookahead * 2 + 1:
        return peaks, troughs

    for i in range(lookahead, len(y_values) - lookahead):
        is_peak = True
        is_trough = True

        # Compare with all neighbors within lookahead range
        for j in range(1, lookahead + 1):
            if y_values[i] <= y_values[i - j] or y_values[i] <= y_values[i + j]:
                is_peak = False
            if y_values[i] >= y_values[i - j] or y_values[i] >= y_values[i + j]:
                is_trough = False

        # Apply delta threshold
        if is_peak and (not peaks or y_values[i] - peaks[-1][1] >= delta):
            peaks.append((x_values[i], y_values[i]))
        elif is_trough and (not troughs or troughs[-1][1] - y_values[i] >= delta):
            troughs.append((x_values[i], y_values[i]))

    return peaks, troughs
