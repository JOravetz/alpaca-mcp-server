"""Peak and trough analysis tool for day trading signals.

This module provides professional technical analysis for identifying precise entry/exit points
using zero-phase Hanning filtering and peak/trough detection algorithms.

Key features:
- Zero-phase low-pass filtering to remove noise while preserving signal timing
- Peak/trough detection on filtered data with original price reporting for trading
- Integration with plot.py for accurate, synchronized analysis
- Support for AUTO mode to analyze current scanner results
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
import pytz
import requests
from scipy.signal import filtfilt  # type: ignore[import-untyped]
from scipy.signal.windows import hann as hanning  # type: ignore[import-untyped]

from ..config import get_scanner_config, get_technical_config, get_trading_config

if TYPE_CHECKING:
    from numpy.typing import NDArray

# Add parent directory to path for peakdetect import
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)

try:
    from peakdetect import peakdetect
except ImportError:
    from .peakdetect_fallback import peakdetect

logger = logging.getLogger(__name__)

# Constants
NYC_TIMEZONE = pytz.timezone("America/New_York")
ALPACA_DATA_URL = "https://data.alpaca.markets/v2/stocks/bars"
ALPACA_CALENDAR_URL = "https://paper-api.alpaca.markets/v2/calendar"

# Excluded keywords when parsing scanner output
SCANNER_EXCLUDED_KEYWORDS = frozenset(
    {"SELL", "STRONG", "ACTIVE", "READY", "MARKET", "SCAN", "DAY"}
)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PeakTroughPoint:
    """Represents a detected peak or trough point."""

    index: int
    timestamp: str
    filtered_price: float
    original_price: float
    volume: int


@dataclass
class LatestSignal:
    """Represents the most recent trading signal."""

    signal_type: str  # "Peak" or "Trough"
    index: int
    timestamp: str
    signal_price: float
    filtered_price: float
    volume: int
    samples_ago: int
    current_price: float
    price_change: float
    price_change_pct: float


@dataclass
class SymbolAnalysisResult:
    """Complete analysis result for a single symbol."""

    symbol: str
    total_bars: int
    timestamps: list[str]
    original_prices: list[float]
    filtered_prices: list[float]
    peaks: list[PeakTroughPoint]
    troughs: list[PeakTroughPoint]
    filter_params: dict[str, int]
    stats: dict[str, float]


# =============================================================================
# Fallback Peak Detection
# =============================================================================


def _fallback_peakdetect(
    y_axis: Sequence[Any],
    x_axis: Sequence[int] | None = None,
    lookahead: int = 1,
    delta: float = 0,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Enhanced fallback peak detection if peakdetect module not available."""
    peaks: list[tuple[int, float]] = []
    troughs: list[tuple[int, float]] = []

    y_values: list[float] = [float(v) for v in y_axis]
    if x_axis is None:
        x_values: list[int] = list(range(len(y_values)))
    else:
        x_values = list(x_axis)

    for i in range(lookahead, len(y_values) - lookahead):
        is_peak = True
        is_trough = True

        for j in range(1, lookahead + 1):
            if y_values[i] <= y_values[i - j] or y_values[i] <= y_values[i + j]:
                is_peak = False
            if y_values[i] >= y_values[i - j] or y_values[i] >= y_values[i + j]:
                is_trough = False

        if is_peak and (not peaks or y_values[i] - peaks[-1][1] >= delta):
            peaks.append((x_values[i], y_values[i]))
        elif is_trough and (not troughs or troughs[-1][1] - y_values[i] >= delta):
            troughs.append((x_values[i], y_values[i]))

    return peaks, troughs


# Override if import failed
try:
    from peakdetect import peakdetect  # noqa: F811
except ImportError:
    peakdetect = _fallback_peakdetect  # type: ignore[misc]


# =============================================================================
# Timezone Utilities
# =============================================================================


def convert_to_nyc_timezone(timestamp_input: str | datetime) -> datetime | str:
    """Convert timestamp to NYC/EDT timezone for display.

    Args:
        timestamp_input: A timestamp string or datetime object.

    Returns:
        Datetime object in NYC timezone, or original input if conversion fails.
    """
    try:
        dt = _parse_timestamp(timestamp_input)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        return dt.astimezone(NYC_TIMEZONE)

    except Exception as e:
        logger.warning(f"Failed to convert timestamp {timestamp_input} to NYC timezone: {e}")
        return _fallback_timezone_conversion(timestamp_input)


def _parse_timestamp(timestamp_input: str | datetime) -> datetime:
    """Parse various timestamp formats into a datetime object."""
    if isinstance(timestamp_input, datetime):
        return timestamp_input

    timestamp_str = timestamp_input

    if timestamp_str.endswith("Z"):
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    if "+" in timestamp_str or timestamp_str.endswith("UTC"):
        from dateutil import parser as date_parser  # type: ignore[import-untyped]

        return date_parser.parse(timestamp_str)

    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        from dateutil import parser as date_parser  # type: ignore[import-untyped]

        return date_parser.parse(timestamp_str)


def _fallback_timezone_conversion(timestamp_input: str | datetime) -> datetime | str:
    """Fallback timezone conversion when primary method fails."""
    try:
        if isinstance(timestamp_input, str):
            from dateutil import parser as date_parser  # type: ignore[import-untyped]

            dt = date_parser.parse(timestamp_input)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            return dt.astimezone(NYC_TIMEZONE)
    except Exception:
        pass
    return timestamp_input


def format_timestamp_for_display(raw_ts: str | datetime, fallback_index: int) -> str:
    """Format a timestamp for display, with fallback to bar index."""
    try:
        if isinstance(raw_ts, str):
            from dateutil import parser as date_parser  # type: ignore[import-untyped]

            dt = date_parser.parse(raw_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            nyc_dt = dt.astimezone(NYC_TIMEZONE)
            return nyc_dt.strftime("%H:%M:%S")

        if hasattr(raw_ts, "tzinfo"):
            if raw_ts.tzinfo is None:
                raw_ts = raw_ts.replace(tzinfo=pytz.UTC)
            nyc_dt = raw_ts.astimezone(NYC_TIMEZONE)
            return nyc_dt.strftime("%H:%M:%S")

        return f"Bar_{fallback_index}"
    except Exception as e:
        logger.warning(f"Timezone conversion failed for timestamp {raw_ts}: {e}")
        return f"Bar_{fallback_index}"


def get_current_nyc_time() -> tuple[str, str]:
    """Get current time in NYC timezone.

    Returns:
        Tuple of (formatted_time, timezone_name).
    """
    try:
        utc_now = datetime.now(pytz.UTC)
        nyc_now = utc_now.astimezone(NYC_TIMEZONE)
        tz_name = nyc_now.strftime("%Z")
        formatted_time = nyc_now.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time, tz_name
    except Exception as e:
        logger.warning(f"Failed to format analysis time with timezone: {e}")
        utc_now = datetime.utcnow()
        edt_hour = (utc_now.hour - 4) % 24
        edt_time = utc_now.replace(hour=edt_hour)
        return edt_time.strftime("%Y-%m-%d %H:%M:%S"), "EDT"


# =============================================================================
# Signal Processing
# =============================================================================


def zero_phase_filter(
    data: list[float] | NDArray[np.floating],
    window_len: int | None = None,
) -> NDArray[np.floating]:
    """Apply zero-phase low-pass filter using Hanning window.

    This filter preserves signal timing (no phase shift) while smoothing noise.

    Args:
        data: Input price data.
        window_len: Hanning window length (uses global config if None).

    Returns:
        Filtered data as numpy array.
    """
    if window_len is None:
        window_len = get_technical_config().hanning_window_samples

    data_array = np.array(data)

    # Validate minimum data length
    min_required_length = window_len * 3
    if len(data_array) < min_required_length:
        if len(data_array) < 5:
            return data_array
        window_len = max(3, len(data_array) // 3)
        if window_len % 2 == 0:
            window_len -= 1

    # Ensure odd window length
    if window_len % 2 == 0:
        window_len += 1

    # Create and normalize Hanning window
    window = hanning(window_len)
    window = window / window.sum()

    # Apply zero-phase filter with edge padding
    pad_len = window_len // 2
    padded = np.pad(data_array, pad_len, mode="edge")
    filtered_padded = filtfilt(window, 1.0, padded)
    filtered = filtered_padded[pad_len:-pad_len]

    return filtered


# =============================================================================
# Historical Data Fetcher
# =============================================================================


class HistoricalDataFetcher:
    """Fetch historical bar data from Alpaca API."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }
        )

    def get_trading_days(self, days: int) -> list[str]:
        """Get the last N trading days from Alpaca calendar API.

        Args:
            days: Number of trading days to retrieve.

        Returns:
            List of trading day dates in YYYY-MM-DD format, sorted newest first.
        """
        now = datetime.now()
        start_date = now - timedelta(days=days * 3)  # Buffer for weekends/holidays

        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
        }

        try:
            response = self.session.get(ALPACA_CALENDAR_URL, params=params, timeout=15)
            response.raise_for_status()

            calendar_data = response.json()
            if not calendar_data:
                logger.warning("No trading calendar data received")
                return []

            trading_days = [day["date"] for day in calendar_data if day.get("date")]

            if len(trading_days) < days:
                logger.warning(
                    "Only %s trading days available, requested %s",
                    len(trading_days),
                    days,
                )

            # Return most recent N days, sorted newest first
            trading_days = trading_days[-days:] if trading_days else []
            trading_days.sort(reverse=True)

            logger.info("Retrieved %s trading days", len(trading_days))
            return trading_days

        except requests.exceptions.RequestException as e:
            logger.error("Request error retrieving trading calendar: %s", e)
            return []
        except Exception as e:
            logger.error("Error retrieving trading calendar: %s", e)
            return []

    def fetch_historical_bars(
        self,
        symbols: list[str],
        timeframe: str,
        start_date: str,
        end_date: str,
        feed: str = "sip",
    ) -> dict[str, list[dict]] | None:
        """Fetch historical bar data for multiple symbols.

        Args:
            symbols: List of stock symbols.
            timeframe: Bar timeframe (e.g., "1Min", "5Min").
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            feed: Data feed source (default: "sip").

        Returns:
            Dictionary mapping symbols to their bar data, or None on error.
        """
        if not symbols:
            logger.warning("No symbols provided for historical data fetch")
            return None

        params: dict[str, str | int] = {
            "symbols": ",".join(symbols),
            "timeframe": timeframe,
            "start": start_date,
            "end": end_date,
            "limit": 10000,
            "adjustment": "split",
            "feed": feed,
            "sort": "asc",
        }

        try:
            logger.info(
                "Fetching historical bars: %s symbols, %s, %s to %s",
                len(symbols),
                timeframe,
                start_date,
                end_date,
            )

            response = self.session.get(ALPACA_DATA_URL, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict) or "bars" not in data:
                logger.warning("Invalid response format from bars API")
                return None

            bars_data = data["bars"]
            total_bars = sum(len(bars) for bars in bars_data.values() if bars)

            for symbol, bars in bars_data.items():
                if not bars:
                    logger.warning("No bars received for symbol %s", symbol)

            logger.info(
                "Successfully fetched %s bars for %s symbols",
                total_bars,
                len(bars_data),
            )
            return bars_data

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching historical bars")
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Request error fetching historical bars: %s", e)
            return None
        except Exception as e:
            logger.error("Error fetching historical bars: %s", e)
            return None


# =============================================================================
# Peak/Trough Processing
# =============================================================================


def process_bars_for_peaks(
    symbol: str,
    bars: list[dict],
    window_len: int | None = None,
    lookahead: int | None = None,
) -> SymbolAnalysisResult | None:
    """Process bars to compute filtered prices and detect peaks/troughs.

    Args:
        symbol: Stock symbol.
        bars: List of bar data from API.
        window_len: Hanning filter window length.
        lookahead: Peak detection lookahead parameter.

    Returns:
        SymbolAnalysisResult with all analysis data, or None on error.
    """
    config = get_technical_config()
    if window_len is None:
        window_len = config.hanning_window_samples
    if lookahead is None:
        lookahead = config.peak_trough_lookahead

    try:
        if not bars or len(bars) < lookahead * 2:
            logger.warning(
                "Not enough bars for %s to detect peaks (need at least %d)",
                symbol,
                lookahead * 2,
            )
            return None

        close_prices = np.array([float(bar["c"]) for bar in bars])
        timestamps = [bar["t"] for bar in bars]

        logger.debug("Processing %d bars for %s", len(close_prices), symbol)
        logger.debug("Close price range: %.4f - %.4f", close_prices.min(), close_prices.max())

        filtered_prices = zero_phase_filter(close_prices, window_len)
        time_axis = np.arange(len(close_prices))

        max_peaks, min_peaks = peakdetect(
            filtered_prices, x_axis=time_axis, lookahead=lookahead, delta=0
        )

        logger.info(
            "Found %d peaks and %d troughs for %s",
            len(max_peaks),
            len(min_peaks),
            symbol,
        )

        # Build peak data points
        peaks_data = []
        for peak_idx, peak_value in max_peaks:
            idx = int(peak_idx)
            if 0 <= idx < len(bars):
                peaks_data.append(
                    PeakTroughPoint(
                        index=idx,
                        timestamp=timestamps[idx],
                        filtered_price=float(peak_value),
                        original_price=float(close_prices[idx]),
                        volume=int(bars[idx]["v"]),
                    )
                )

        # Build trough data points
        troughs_data = []
        for trough_idx, trough_value in min_peaks:
            idx = int(trough_idx)
            if 0 <= idx < len(bars):
                troughs_data.append(
                    PeakTroughPoint(
                        index=idx,
                        timestamp=timestamps[idx],
                        filtered_price=float(trough_value),
                        original_price=float(close_prices[idx]),
                        volume=int(bars[idx]["v"]),
                    )
                )

        # Calculate statistics
        noise_reduction = (close_prices.std() - filtered_prices.std()) / close_prices.std() * 100

        return SymbolAnalysisResult(
            symbol=symbol,
            total_bars=len(bars),
            timestamps=timestamps,
            original_prices=close_prices.tolist(),
            filtered_prices=filtered_prices.tolist(),
            peaks=peaks_data,
            troughs=troughs_data,
            filter_params={"window_len": window_len, "lookahead": lookahead},
            stats={
                "price_min": float(close_prices.min()),
                "price_max": float(close_prices.max()),
                "price_mean": float(close_prices.mean()),
                "price_std": float(close_prices.std()),
                "filtered_std": float(filtered_prices.std()),
                "noise_reduction_pct": float(noise_reduction),
            },
        )

    except Exception as e:
        logger.error("Error processing bars for peaks in %s: %s", symbol, e)
        return None


def get_latest_signal(result: SymbolAnalysisResult | None) -> LatestSignal | None:
    """Get the most recent peak or trough signal for a symbol.

    Args:
        result: Analysis result for a symbol.

    Returns:
        LatestSignal with signal details, or None if no signals found.
    """
    if not result or (not result.peaks and not result.troughs):
        return None

    latest_signal_data: dict = {}
    latest_index = -1

    # Check peaks
    for peak in result.peaks:
        if peak.index > latest_index:
            latest_index = peak.index
            latest_signal_data = {
                "signal_type": "Peak",
                "index": peak.index,
                "timestamp": peak.timestamp,
                "signal_price": peak.original_price,
                "filtered_price": peak.filtered_price,
                "volume": peak.volume,
            }

    # Check troughs
    for trough in result.troughs:
        if trough.index > latest_index:
            latest_index = trough.index
            latest_signal_data = {
                "signal_type": "Trough",
                "index": trough.index,
                "timestamp": trough.timestamp,
                "signal_price": trough.original_price,
                "filtered_price": trough.filtered_price,
                "volume": trough.volume,
            }

    if not latest_signal_data:
        return None

    # Calculate additional metrics
    total_bars = result.total_bars
    samples_ago = total_bars - 1 - latest_index
    current_price = result.original_prices[-1]
    price_change = current_price - latest_signal_data["signal_price"]
    price_change_pct = (price_change / latest_signal_data["signal_price"]) * 100

    return LatestSignal(
        signal_type=latest_signal_data["signal_type"],
        index=latest_signal_data["index"],
        timestamp=latest_signal_data["timestamp"],
        signal_price=latest_signal_data["signal_price"],
        filtered_price=latest_signal_data["filtered_price"],
        volume=latest_signal_data["volume"],
        samples_ago=samples_ago,
        current_price=current_price,
        price_change=price_change,
        price_change_pct=price_change_pct,
    )


# =============================================================================
# Symbol Resolution
# =============================================================================


async def resolve_auto_symbols() -> tuple[list[str], str]:
    """Resolve symbols from AUTO mode using scanner results.

    Returns:
        Tuple of (symbol_list, debug_info_string).

    Raises:
        ValueError: If no symbols could be extracted from scanner.
    """
    from .day_trading_scanner import scan_day_trading_opportunities

    trading_config = get_trading_config()
    scanner_config = get_scanner_config()

    scanner_result = await scan_day_trading_opportunities(
        symbols="ALL",
        min_trades_per_minute=trading_config.trades_per_minute_threshold,
        min_percent_change=1.0,  # Lower threshold for more symbols
        max_symbols=scanner_config.max_watchlist_size,
        sort_by=scanner_config.scanner_sort_method,
    )

    # Extract symbols using pattern matching
    symbol_pattern = r"^\s*\d+\s+([A-Z]{2,5})\s+"
    symbol_list = []

    for line in scanner_result.split("\n"):
        match = re.match(symbol_pattern, line)
        if match:
            symbol_list.append(match.group(1))

    if not symbol_list:
        # Fallback parsing for different formats
        logger.warning("Failed to extract symbols from scanner, trying alternative parsing")
        symbol_mentions = re.findall(r"\b([A-Z]{2,5})\b", scanner_result)
        likely_symbols = [
            s for s in symbol_mentions if 2 <= len(s) <= 5 and s not in SCANNER_EXCLUDED_KEYWORDS
        ]
        symbol_list = list(dict.fromkeys(likely_symbols))[:20]

    if not symbol_list:
        sample_lines = scanner_result.split("\n")[:10]
        debug_lines = "\n".join(sample_lines)
        raise ValueError(
            f"AUTO mode failed - no active symbols found in scanner results.\n\n"
            f"Debug - Scanner output sample:\n{debug_lines}"
        )

    logger.info(f"AUTO mode: Extracted {len(symbol_list)} symbols: {symbol_list}")

    preview = symbol_list[:5]
    ellipsis = "..." if len(symbol_list) > 5 else ""
    debug_info = f"AUTO mode detected {len(symbol_list)} symbols: {preview}{ellipsis}\n\n"

    return symbol_list, debug_info


def validate_and_normalize_params(
    days: int,
    limit: int,
    window_len: int | None,
    lookahead: int | None,
    delta: float,
    min_peak_distance: int | None,
    timeframe: str,
) -> tuple[int, int, int, int, float, int]:
    """Validate and normalize analysis parameters.

    Returns:
        Tuple of (days, limit, window_len, lookahead, delta, min_peak_distance).
    """
    config = get_technical_config()

    # Apply defaults from config
    if window_len is None:
        window_len = config.hanning_window_samples
    if lookahead is None:
        lookahead = config.peak_trough_lookahead
    if min_peak_distance is None:
        min_peak_distance = config.peak_trough_min_distance

    # Validate limit
    limit = min(max(limit, 1), 10000)

    # Timeframe-aware days validation
    if timeframe == "1Day":
        max_days = 2520  # ~10 years
    elif timeframe in ("1Hour", "2Hour", "4Hour"):
        max_days = 90  # 3 months
    else:
        max_days = 30  # Intraday

    days = min(max(days, 1), max_days)

    # Validate window_len
    if window_len < 3 or window_len > 101:
        window_len = config.hanning_window_samples
    if window_len % 2 == 0:
        window_len += 1

    # Validate lookahead
    lookahead = min(max(lookahead, 1), 50)

    # Validate delta
    delta = max(delta, 0.0)

    # Validate min_peak_distance
    if min_peak_distance < 1:
        min_peak_distance = config.peak_trough_min_distance

    return days, limit, window_len, lookahead, delta, min_peak_distance


# =============================================================================
# Output Formatting
# =============================================================================


class AnalysisOutputBuilder:
    """Builder for formatting analysis output."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def add(self, text: str) -> None:
        """Add a line of text."""
        self.lines.append(text)

    def add_header(
        self,
        timeframe: str,
        days: int,
        window_len: int,
        lookahead: int,
        delta: float,
        min_peak_distance: int,
        debug_info: str = "",
    ) -> None:
        """Add the analysis header section."""
        self.add("# Peak and Trough Analysis for Day Trading\n")

        if debug_info:
            self.add(debug_info)

        self.add(
            f"Parameters: {timeframe} bars, {days} days, "
            f"Window: {window_len}, Lookahead: {lookahead}\n"
        )
        self.add(f"Delta: {delta}, Min Peak Distance: {min_peak_distance}\n")

        formatted_time, tz_name = get_current_nyc_time()
        self.add(f"Analysis Time: {formatted_time} {tz_name}\n")
        self.add("=" * 80 + "\n")

    def add_symbol_section(
        self,
        symbol: str,
        close_prices: NDArray[np.floating[Any]],
        timestamps: list[str],
        max_peaks: list[tuple[int, float]],
        min_peaks: list[tuple[int, float]],
    ) -> None:
        """Add analysis section for a single symbol."""
        self.add(f"\n## {symbol}\n")
        self.add(f"Total bars analyzed: {len(close_prices)}\n")
        self.add(
            f"Price range: ${float(close_prices.min()):.4f} - ${float(close_prices.max()):.4f}\n"
        )
        self.add(f"Current price: ${float(close_prices[-1]):.4f}\n\n")

        # Peaks section
        self._add_peaks_section(close_prices, timestamps, max_peaks)

        # Troughs section
        self._add_troughs_section(close_prices, timestamps, min_peaks)

        # Trading signal summary
        self._add_signal_summary(close_prices, max_peaks, min_peaks)

        self.add("-" * 40 + "\n")

    def _add_peaks_section(
        self,
        close_prices: NDArray[np.floating[Any]],
        timestamps: list[str],
        max_peaks: list[tuple[int, float]],
    ) -> None:
        """Add peaks (resistance/sell signals) section."""
        self.add(f"### Peaks (Resistance/Sell Signals): {len(max_peaks)}\n")

        if not max_peaks:
            return

        recent_peaks = max_peaks[-5:] if len(max_peaks) > 5 else max_peaks
        for idx, filtered_value in recent_peaks:
            idx = int(idx)
            if 0 <= idx < len(timestamps):
                peak_time = format_timestamp_for_display(timestamps[idx], idx)
                original_price = close_prices[idx]
                self.add(
                    f"  - Sample {idx}, {peak_time}: "
                    f"${original_price:.4f} (filtered: ${filtered_value:.4f})\n"
                )

        latest_peak_idx = int(max_peaks[-1][0])
        latest_peak_price = close_prices[latest_peak_idx]
        peak_distance = len(close_prices) - 1 - latest_peak_idx
        self.add(
            f"\nLatest peak: Sample {latest_peak_idx}, "
            f"${latest_peak_price:.4f} ({peak_distance} bars ago)\n"
        )

    def _add_troughs_section(
        self,
        close_prices: NDArray[np.floating[Any]],
        timestamps: list[str],
        min_peaks: list[tuple[int, float]],
    ) -> None:
        """Add troughs (support/buy signals) section."""
        self.add(f"\n### Troughs (Support/Buy Signals): {len(min_peaks)}\n")

        if not min_peaks:
            return

        recent_troughs = min_peaks[-5:] if len(min_peaks) > 5 else min_peaks
        for idx, filtered_value in recent_troughs:
            idx = int(idx)
            if 0 <= idx < len(timestamps):
                trough_time = format_timestamp_for_display(timestamps[idx], idx)
                original_price = close_prices[idx]
                self.add(
                    f"  - Sample {idx}, {trough_time}: "
                    f"${original_price:.4f} (filtered: ${filtered_value:.4f})\n"
                )

        latest_trough_idx = int(min_peaks[-1][0])
        latest_trough_price = close_prices[latest_trough_idx]
        trough_distance = len(close_prices) - 1 - latest_trough_idx
        self.add(
            f"\nLatest trough: Sample {latest_trough_idx}, "
            f"${latest_trough_price:.4f} ({trough_distance} bars ago)\n"
        )

    def _add_signal_summary(
        self,
        close_prices: NDArray[np.floating[Any]],
        max_peaks: list[tuple[int, float]],
        min_peaks: list[tuple[int, float]],
    ) -> None:
        """Add trading signal summary section."""
        self.add("\n### Trading Signal Summary:\n")

        if max_peaks and min_peaks:
            self._add_combined_signal_analysis(close_prices, max_peaks, min_peaks)
        elif min_peaks:
            self._add_trough_only_signal(close_prices, min_peaks)
        elif max_peaks:
            self._add_peak_only_signal(close_prices, max_peaks)

    def _add_combined_signal_analysis(
        self,
        close_prices: NDArray[np.floating[Any]],
        max_peaks: list[tuple[int, float]],
        min_peaks: list[tuple[int, float]],
    ) -> None:
        """Add signal analysis when both peaks and troughs exist."""
        latest_peak_idx = int(max_peaks[-1][0])
        latest_trough_idx = int(min_peaks[-1][0])
        current_price = close_prices[-1]

        if latest_peak_idx > latest_trough_idx:
            # Last signal was a peak
            peak_price = close_prices[latest_peak_idx]
            price_from_peak = ((current_price - peak_price) / peak_price) * 100
            bars_since = len(close_prices) - 1 - latest_peak_idx

            self.add(f"📊 Last signal: PEAK at sample {latest_peak_idx} (${peak_price:.4f})\n")
            self.add(
                f"📍 Current position: {price_from_peak:+.2f}% from peak ({bars_since} bars ago)\n"
            )

            if bars_since <= 3 and abs(price_from_peak) <= 2.0:
                self.add("🔴 SELL/SHORT Signal - Near recent peak, good exit point\n")
            elif price_from_peak < -2.0:
                self.add("⚠️ Watch - Price declining from peak, potential reversal\n")
            else:
                self.add("➡️ Neutral - Monitor for direction\n")
        else:
            # Last signal was a trough
            trough_price = close_prices[latest_trough_idx]
            price_from_trough = ((current_price - trough_price) / trough_price) * 100
            bars_since = len(close_prices) - 1 - latest_trough_idx

            self.add(
                f"📊 Last signal: TROUGH at sample {latest_trough_idx} (${trough_price:.4f})\n"
            )
            self.add(
                f"📍 Current position: {price_from_trough:+.2f}% from trough ({bars_since} bars ago)\n"
            )

            if bars_since <= 3 and abs(price_from_trough) <= 2.0:
                self.add("🟢 BUY/LONG Signal - Near recent trough, good entry point\n")
            elif price_from_trough > 2.0:
                self.add("⚠️ Watch - Price rising from trough, potential reversal\n")
            else:
                self.add("➡️ Neutral - Monitor for direction\n")

    def _add_trough_only_signal(
        self,
        close_prices: NDArray[np.floating[Any]],
        min_peaks: list[tuple[int, float]],
    ) -> None:
        """Add signal when only troughs exist."""
        latest_trough_idx = int(min_peaks[-1][0])
        bars_since = len(close_prices) - 1 - latest_trough_idx
        if bars_since <= 3:
            self.add("🟢 BUY Signal - Recent trough detected\n")

    def _add_peak_only_signal(
        self,
        close_prices: NDArray[np.floating[Any]],
        max_peaks: list[tuple[int, float]],
    ) -> None:
        """Add signal when only peaks exist."""
        latest_peak_idx = int(max_peaks[-1][0])
        bars_since = len(close_prices) - 1 - latest_peak_idx
        if bars_since <= 3:
            self.add("🔴 SELL Signal - Recent peak detected\n")

    def build(self) -> str:
        """Build and return the complete output string."""
        return "".join(self.lines)


# =============================================================================
# Main Analysis Functions
# =============================================================================


async def analyze_peaks_and_troughs(
    symbols: str = "AUTO",
    timeframe: str = "1Min",
    days: int = 1,
    limit: int = 1000,
    window_len: int | None = None,
    lookahead: int | None = None,
    delta: float = 0.0,
    min_peak_distance: int | None = None,
) -> str:
    """Enhanced peak and trough analysis for day trading signals.

    This tool applies professional technical analysis to identify precise entry/exit points:
    1. Fetches historical intraday bar data using proper trading calendar
    2. Applies zero-phase low-pass Hanning filtering to remove noise while preserving timing
    3. Detects peaks/troughs on filtered data but reports ORIGINAL prices for trading
    4. Returns actionable trading signals with sample indices and distances

    Args:
        symbols: Stock symbols - use "AUTO" for current scanner results,
            or comma-separated list (e.g., "AAPL,MSFT,NVDA").
        timeframe: Bar timeframe - "1Min", "5Min", "15Min", "30Min", "1Hour".
        days: Number of trading days of historical data (max: 30 intraday, 2520 daily).
        limit: Maximum number of bars to fetch (max: 10000).
        window_len: Hanning filter window length for smoothing (3-101, must be odd).
        lookahead: Peak detection lookahead parameter (1-50).
        delta: Minimum peak/trough amplitude threshold.
        min_peak_distance: Minimum bars between peaks for filtering noise.

    Returns:
        Formatted string with comprehensive peak/trough analysis including:
        - Technical summary with price ranges and bar counts
        - Recent peaks (resistance/sell signals) with sample indices
        - Recent troughs (support/buy signals) with sample indices
        - Trading signal recommendations with distance analysis
    """
    try:
        debug_info = ""

        # Resolve AUTO mode symbols
        if symbols.upper() == "AUTO":
            try:
                symbol_list, debug_info = await resolve_auto_symbols()
                symbols = ",".join(symbol_list)
            except ValueError as e:
                return str(e)
            except Exception as e:
                logger.error(f"AUTO mode failed: {e}")
                return f"Error: AUTO mode failed - {e}. Please specify symbols manually."

        # Parse symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return "Error: No valid symbols provided"

        # Validate parameters
        days, limit, window_len, lookahead, delta, min_peak_distance = (
            validate_and_normalize_params(
                days, limit, window_len, lookahead, delta, min_peak_distance, timeframe
            )
        )

        # Get API credentials
        try:
            from ..config.settings import settings

            api_key = settings.api_key
            api_secret = settings.api_secret
            if not api_key or not api_secret:
                return "Error: API credentials not configured"
        except Exception as e:
            logger.error(f"Failed to get API credentials: {e}")
            return f"Error: Failed to get API credentials - {e}"

        # Fetch historical data
        fetcher = HistoricalDataFetcher(api_key, api_secret)

        trading_days = fetcher.get_trading_days(days)
        if trading_days:
            start_date = trading_days[-1]  # Oldest
            end_date = trading_days[0]  # Most recent
        else:
            logger.warning("No trading days found, falling back to date calculation")
            now = datetime.now()
            start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")

        bars_data = fetcher.fetch_historical_bars(symbol_list, timeframe, start_date, end_date)

        if not bars_data:
            return "Error: No historical data received from API"

        # Build output
        output = AnalysisOutputBuilder()
        output.add_header(
            timeframe, days, window_len, lookahead, delta, min_peak_distance, debug_info
        )

        for symbol in symbol_list:
            if symbol not in bars_data or not bars_data[symbol]:
                output.add(f"\n## {symbol}\n")
                output.add(f"No data available for {symbol}\n")
                continue

            symbol_bars = bars_data[symbol]
            close_prices = np.array([float(bar["c"]) for bar in symbol_bars])
            timestamps = [bar["t"] for bar in symbol_bars]

            if len(close_prices) < lookahead * 2:
                output.add(f"\n## {symbol}\n")
                output.add(f"Insufficient data for {symbol} (need at least {lookahead * 2} bars)\n")
                continue

            # Apply filter and detect peaks/troughs
            filtered_prices = zero_phase_filter(close_prices, window_len)
            time_axis = np.arange(len(close_prices))

            max_peaks, min_peaks = peakdetect(
                filtered_prices, x_axis=time_axis, lookahead=lookahead, delta=delta
            )

            # Filter by minimum distance
            if min_peak_distance > 1:
                max_peaks = _filter_by_distance(max_peaks, min_peak_distance)
                min_peaks = _filter_by_distance(min_peaks, min_peak_distance)

            output.add_symbol_section(symbol, close_prices, timestamps, max_peaks, min_peaks)

        return output.build()

    except Exception as e:
        logger.error(f"Error in analyze_peaks_and_troughs: {e}")
        return f"Error analyzing peaks and troughs: {e}"


def _filter_by_distance(
    peaks: list[tuple[int, float]],
    min_distance: int,
) -> list[tuple[int, float]]:
    """Filter peaks/troughs that are too close together."""
    filtered = []
    for i, (idx, value) in enumerate(peaks):
        if i == 0 or (idx - peaks[i - 1][0]) >= min_distance:
            filtered.append((idx, value))
    return filtered


async def analyze_peaks_and_troughs_with_plot_py(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1,
    window_len: int | None = None,
    lookahead: int | None = None,
    delta: float = 0.0,
    min_peak_distance: int = 5,
) -> str:
    """Use plot.py with --no-plot option for accurate peak/trough analysis.

    This function uses the same data source and analysis as the plotting tool
    to ensure data synchronization between charts and analysis output.

    Args:
        symbols: Comma-separated symbols (e.g., "AAPL,MSFT").
        timeframe: Bar timeframe ("1Min", "5Min", etc.).
        days: Number of trading days to analyze.
        window_len: Hanning filter window length (uses global config if None).
        lookahead: Peak detection sensitivity (uses global config if None).
        delta: Minimum peak amplitude.
        min_peak_distance: Minimum bars between peaks.

    Returns:
        Analysis result string with peak/trough signals.
    """
    try:
        # Get config defaults
        config = get_technical_config()
        if window_len is None:
            window_len = config.hanning_window_samples
        if lookahead is None:
            lookahead = config.peak_trough_lookahead

        # Build command
        cmd = [
            sys.executable,
            "-m",
            "alpaca_mcp_server.tools.plot",
            "--symbols",
            symbols,
            "--timeframe",
            timeframe,
            "--days",
            str(days),
            "--window",
            str(window_len),
            "--lookahead",
            str(lookahead),
            "--no-plot",
            "--verbose",
        ]

        logger.info(f"Running plot.py analysis: {' '.join(cmd)}")

        # Execute as subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_root,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            result_stdout = stdout.decode() if stdout else ""
            result_stderr = stderr.decode() if stderr else ""
            returncode = proc.returncode
        except TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("plot.py analysis timed out after 30 seconds")
            return "Error: Analysis timed out"

        if returncode != 0:
            error_msg = f"plot.py failed with return code {returncode}"
            if result_stderr:
                error_msg += f": {result_stderr}"
            logger.error(error_msg)
            return f"Error running plot.py analysis: {error_msg}"

        logger.info(f"plot.py analysis completed successfully for {symbols}")
        return result_stdout

    except Exception as e:
        logger.error(f"Error running plot.py analysis: {e}")
        return f"Error running plot.py analysis: {e}"
