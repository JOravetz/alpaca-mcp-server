"""Peak and trough analysis tool for day trading signals - Enhanced Version with plot.py integration"""

import logging
import os
import re
import sys
from datetime import datetime, timedelta

import numpy as np
import pytz
import requests
from scipy.signal import filtfilt
from scipy.signal.windows import hann as hanning

# Import global configuration
from ..config import get_technical_config

# Add parent directory to path to import peakdetect
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from peakdetect import peakdetect
except ImportError:
    # Enhanced fallback if peakdetect not found
    def peakdetect(y_axis, x_axis=None, lookahead=1, delta=0):
        """Enhanced fallback peak detection if peakdetect module not available"""
        peaks = []
        troughs = []
        if x_axis is None:
            x_axis = list(range(len(y_axis)))

        for i in range(lookahead, len(y_axis) - lookahead):
            # Check if current point is a peak
            is_peak = True
            is_trough = True

            for j in range(1, lookahead + 1):
                if y_axis[i] <= y_axis[i - j] or y_axis[i] <= y_axis[i + j]:
                    is_peak = False
                if y_axis[i] >= y_axis[i - j] or y_axis[i] >= y_axis[i + j]:
                    is_trough = False

            if is_peak and (not peaks or y_axis[i] - peaks[-1][1] >= delta):
                peaks.append((x_axis[i], y_axis[i]))
            elif is_trough and (not troughs or troughs[-1][1] - y_axis[i] >= delta):
                troughs.append((x_axis[i], y_axis[i]))

        return peaks, troughs


# Get client function from settings module
# try:
#     from ..config import get_stock_historical_client  # Currently unused
# except ImportError:
#     # Try absolute import
#     pass

logger = logging.getLogger(__name__)


def convert_to_nyc_timezone(timestamp_str):
    """Convert timestamp string to NYC/EDT timezone for display"""
    try:
        # Parse the timestamp (handles UTC timestamps from Alpaca API)
        if isinstance(timestamp_str, str):
            # Handle different timestamp formats
            if timestamp_str.endswith("Z"):
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            elif "+" in timestamp_str or timestamp_str.endswith("UTC"):
                from dateutil import parser as date_parser

                dt = date_parser.parse(timestamp_str)
            else:
                # Try direct parsing first
                try:
                    dt = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    from dateutil import parser as date_parser

                    dt = date_parser.parse(timestamp_str)
        else:
            dt = timestamp_str

        # If timezone-naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        # Convert to NYC timezone (handles EDT/EST automatically)
        nyc_tz = pytz.timezone("America/New_York")
        dt_nyc = dt.astimezone(nyc_tz)

        return dt_nyc
    except Exception as e:
        logger.warning(f"Failed to convert timestamp {timestamp_str} to NYC timezone: {e}")
        # Return a fallback datetime object in NYC timezone
        try:
            # If all else fails, assume it's a UTC timestamp and manually convert
            if isinstance(timestamp_str, str):
                # Try to extract basic time info
                from dateutil import parser as date_parser

                dt = date_parser.parse(timestamp_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                return dt.astimezone(pytz.timezone("America/New_York"))
        except (AttributeError, TypeError, ValueError, pytz.exceptions.UnknownTimeZoneError):
            pass
        return timestamp_str


def zero_phase_filter(data, window_len=None):
    """Apply zero-phase Hanning filter with global config defaults"""
    if window_len is None:
        window_len = get_technical_config().hanning_window_samples
    """Apply zero-phase low-pass filter using Hanning window"""
    data = np.array(data)

    min_required_length = window_len * 3
    if len(data) < min_required_length:
        if len(data) < 5:
            return data
        else:
            window_len = max(3, len(data) // 3)
            if window_len % 2 == 0:
                window_len -= 1

    if window_len % 2 == 0:
        window_len += 1

    window = hanning(window_len)
    window = window / window.sum()

    pad_len = window_len // 2
    padded = np.pad(data, pad_len, mode="edge")
    filtered_padded = filtfilt(window, 1.0, padded)
    filtered = filtered_padded[pad_len:-pad_len]

    return filtered


class HistoricalDataFetcher:
    """Fetch historical bar data from Alpaca API"""

    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update(
            {"APCA-API-KEY-ID": self.api_key, "APCA-API-SECRET-KEY": self.api_secret}
        )

    def get_trading_days(self, days):
        """Get the last N trading days"""
        now = datetime.now()
        start_date = now - timedelta(days=days * 3)

        url = "https://paper-api.alpaca.markets/v2/calendar"
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
        }

        try:
            response = self.session.get(url, params=params, timeout=15)
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

    def fetch_historical_bars(self, symbols, timeframe, start_date, end_date, feed="sip"):
        """Fetch historical bar data for multiple symbols in one API call"""
        if not symbols:
            logger.warning("No symbols provided for historical data fetch")
            return None

        url = "https://data.alpaca.markets/v2/stocks/bars"
        params = {
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

            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                logger.error("Invalid response format from bars API")
                return None

            if "bars" not in data:
                logger.warning("No 'bars' key in API response")
                return None

            bars_data = data["bars"]
            total_bars = 0

            for symbol, bars in bars_data.items():
                if bars:
                    total_bars += len(bars)
                else:
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


def process_bars_for_peaks(symbol, bars, window_len=None, lookahead=None):
    """Process bars with global config defaults"""
    if window_len is None:
        window_len = get_technical_config().hanning_window_samples
    if lookahead is None:
        lookahead = get_technical_config().peak_trough_lookahead
    """Process bars to compute filtered close prices and detect peaks/troughs"""
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

        peaks_data = []
        for peak_idx, peak_value in max_peaks:
            idx = int(peak_idx)
            if 0 <= idx < len(bars):
                peaks_data.append(
                    {
                        "index": idx,
                        "timestamp": timestamps[idx],
                        "filtered_price": float(peak_value),
                        "original_price": float(close_prices[idx]),
                        "volume": int(bars[idx]["v"]),
                    }
                )

        troughs_data = []
        for trough_idx, trough_value in min_peaks:
            idx = int(trough_idx)
            if 0 <= idx < len(bars):
                troughs_data.append(
                    {
                        "index": idx,
                        "timestamp": timestamps[idx],
                        "filtered_price": float(trough_value),
                        "original_price": float(close_prices[idx]),
                        "volume": int(bars[idx]["v"]),
                    }
                )

        results = {
            "symbol": symbol,
            "total_bars": len(bars),
            "timestamps": timestamps,
            "original_prices": close_prices.tolist(),
            "filtered_prices": filtered_prices.tolist(),
            "peaks": peaks_data,
            "troughs": troughs_data,
            "filter_params": {"window_len": window_len, "lookahead": lookahead},
            "stats": {
                "price_min": float(close_prices.min()),
                "price_max": float(close_prices.max()),
                "price_mean": float(close_prices.mean()),
                "price_std": float(close_prices.std()),
                "filtered_std": float(filtered_prices.std()),
                "noise_reduction_pct": float(
                    (close_prices.std() - filtered_prices.std()) / close_prices.std() * 100
                ),
            },
        }

        return results

    except Exception as e:
        logger.error("Error processing bars for peaks in %s: %s", symbol, e)
        return None


def get_latest_signal(results):
    """Get the most recent peak or trough signal for a symbol"""
    if not results:
        return None

    peaks = results["peaks"]
    troughs = results["troughs"]

    if not peaks and not troughs:
        return None

    latest_signal = None
    latest_index = -1

    for peak in peaks:
        if peak["index"] > latest_index:
            latest_index = peak["index"]
            latest_signal = {
                "type": "Peak",
                "index": peak["index"],
                "timestamp": peak["timestamp"],
                "signal_price": peak["original_price"],
                "filtered_price": peak["filtered_price"],
                "volume": peak["volume"],
            }

    for trough in troughs:
        if trough["index"] > latest_index:
            latest_index = trough["index"]
            latest_signal = {
                "type": "Trough",
                "index": trough["index"],
                "timestamp": trough["timestamp"],
                "signal_price": trough["original_price"],
                "filtered_price": trough["filtered_price"],
                "volume": trough["volume"],
            }

    if latest_signal:
        total_bars = results["total_bars"]
        samples_ago = total_bars - 1 - latest_signal["index"]
        current_price = results["original_prices"][-1]

        latest_signal["samples_ago"] = samples_ago
        latest_signal["current_price"] = current_price
        latest_signal["price_change"] = current_price - latest_signal["signal_price"]
        latest_signal["price_change_pct"] = (
            latest_signal["price_change"] / latest_signal["signal_price"]
        ) * 100

    return latest_signal


async def analyze_peaks_and_troughs(
    symbols: str = "AUTO",
    timeframe: str = "1Min",
    days: int = 1,
    limit: int = 1000,
    window_len: int = None,
    lookahead: int = None,
    delta: float = 0.0,
    min_peak_distance: int = None,
) -> str:
    """
    Enhanced peak and trough analysis for day trading signals using zero-phase filtering.

    This tool applies professional technical analysis to identify precise entry/exit points:
    1. Fetches historical intraday bar data using proper trading calendar
    2. Applies zero-phase low-pass Hanning filtering to remove noise while preserving timing
    3. Detects peaks/troughs on filtered data but reports ORIGINAL prices for trading
    4. Returns actionable trading signals with sample indices and distances

    Key improvements:
    - Uses trading calendar for accurate date ranges
    - Reports original (unfiltered) prices at peak/trough locations
    - Shows sample indices for verification
    - Enhanced signal interpretation based on proximity to latest signals

    Args:
        symbols: Stock symbols - use "AUTO" for current scanner results, or comma-separated list (e.g., "AAPL,MSFT,NVDA")
        timeframe: Bar timeframe - "1Min", "5Min", "15Min", "30Min", "1Hour" (default: "1Min")
        days: Number of trading days of historical data (default: 1, max: 30 for intraday, 2520 for daily)
        limit: Maximum number of bars to fetch (default: 1000, max: 10000)
        window_len: Hanning filter window length - controls smoothing (default: 21, must be odd, range: 3-101)
        lookahead: Peak detection lookahead parameter (default: 1, range: 1-50)
        delta: Minimum peak/trough amplitude threshold (default: 0.0, use 0 for penny stocks)
        min_peak_distance: Minimum bars between peaks for filtering noise (default: 5)

    Returns:
        Formatted string with comprehensive peak/trough analysis including:
        - Technical summary with price ranges and bar counts
        - Recent peaks (resistance/sell signals) with sample indices and original prices
        - Recent troughs (support/buy signals) with sample indices and original prices
        - Trading signal recommendations with distance analysis
        - Clear BUY/SELL signals based on proximity to latest trough/peak

    Examples:
        analyze_peaks_and_troughs()  # Auto-analyze current scanner results (default)
        analyze_peaks_and_troughs("AUTO")  # Explicit auto mode
        analyze_peaks_and_troughs("AAPL,MSFT", timeframe="5Min", days=2)  # Manual symbols, 5min bars, 2 days
        analyze_peaks_and_troughs("NVDA", window_len=21, lookahead=3)  # More smoothing, wider lookahead
    """
    try:
        # Smart symbol resolution - AUTO mode extracts from current scanner results
        if symbols.upper() == "AUTO":
            try:
                # Import the day trading scanner function
                # Get current active stocks from scanner using global config
                from ..config import get_scanner_config, get_trading_config
                from .day_trading_scanner import scan_day_trading_opportunities

                trading_config = get_trading_config()
                scanner_config = get_scanner_config()

                scanner_result = await scan_day_trading_opportunities(
                    symbols="ALL",
                    min_trades_per_minute=trading_config.trades_per_minute_threshold,
                    min_percent_change=1.0,  # Lower threshold to get more symbols for analysis
                    max_symbols=scanner_config.max_watchlist_size,
                    sort_by=scanner_config.scanner_sort_method,
                )

                # Extract symbols from scanner output using improved regex pattern
                # Look for lines like "   1 SRM        9,004 +   297.2% $  5.760"
                symbol_pattern = r"^\s*\d+\s+([A-Z]{2,5})\s+"
                symbol_list = []

                for line in scanner_result.split("\n"):
                    match = re.match(symbol_pattern, line)
                    if match:
                        symbol_list.append(match.group(1))

                if not symbol_list:
                    # Fallback to parse different format if needed
                    logger.warning(
                        "Failed to extract symbols from scanner, trying alternative parsing"
                    )
                    # Look for mentions of symbols in various formats
                    symbol_mentions = re.findall(r"\b([A-Z]{2,5})\b", scanner_result)
                    # Filter to likely stock symbols (2-5 chars, common patterns)
                    likely_symbols = [
                        s
                        for s in symbol_mentions
                        if 2 <= len(s) <= 5
                        and s not in ["SELL", "STRONG", "ACTIVE", "READY", "MARKET", "SCAN", "DAY"]
                    ]
                    symbol_list = list(dict.fromkeys(likely_symbols))[
                        :20
                    ]  # Remove duplicates, limit to 20

                if symbol_list:
                    logger.info(
                        f"AUTO mode: Extracted {len(symbol_list)} symbols from scanner: {symbol_list}"
                    )
                    symbols = ",".join(symbol_list)  # Convert back to comma-separated string
                    # Add debug info to output
                    debug_info = f"AUTO mode detected {len(symbol_list)} symbols: {symbol_list[:5]}{'...' if len(symbol_list) > 5 else ''}\n\n"
                else:
                    logger.warning("AUTO mode: No symbols found in scanner results")
                    # Debug: show scanner output format for troubleshooting
                    sample_lines = scanner_result.split("\n")[:10]
                    debug_lines = "\n".join(sample_lines)
                    return f"Error: AUTO mode failed - no active symbols found in scanner results.\n\nDebug - Scanner output sample:\n{debug_lines}\n\nPlease run scanner first or specify symbols manually."

            except Exception as e:
                logger.error(f"AUTO mode failed: {e}")
                return f"Error: AUTO mode failed - {str(e)}. Please specify symbols manually."

        # Parse symbols (now resolved from AUTO or provided manually)
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            return "Error: No valid symbols provided"

        # Load global config defaults for None parameters
        config = get_technical_config()
        if window_len is None:
            window_len = config.hanning_window_samples
        if lookahead is None:
            lookahead = config.peak_trough_lookahead
        if min_peak_distance is None:
            min_peak_distance = config.peak_trough_min_distance

        # Validate parameters
        if limit < 1 or limit > 10000:
            limit = min(max(limit, 1), 10000)

        # Timeframe-aware days validation
        if timeframe == "1Day":
            max_days = 2520  # ~10 years for daily analysis
        elif timeframe in ["1Hour", "2Hour", "4Hour"]:
            max_days = 90  # 3 months for hourly
        else:  # Intraday timeframes (1Min, 5Min, etc.)
            max_days = 30  # Current limit for intraday

        if days < 1 or days > max_days:
            days = min(max(days, 1), max_days)

        if window_len < 3 or window_len > 101:
            window_len = config.hanning_window_samples
        if window_len % 2 == 0:
            window_len += 1

        if lookahead < 1 or lookahead > 50:
            lookahead = min(max(lookahead, 1), 50)

        if delta < 0:
            delta = 0.0

        if min_peak_distance < 1:
            min_peak_distance = config.peak_trough_min_distance

        # Get API credentials for enhanced data fetching
        try:
            from ..config.settings import settings

            api_key = settings.api_key
            api_secret = settings.api_secret
        except Exception as e:
            logger.error(f"Failed to get API credentials: {e}")
            return f"Error: Failed to get API credentials - {str(e)}"

        # Create data fetcher instance
        fetcher = HistoricalDataFetcher(api_key, api_secret)

        # Get trading days using calendar API
        trading_days = fetcher.get_trading_days(days)
        if not trading_days:
            logger.warning("No trading days found, falling back to date calculation")
            now = datetime.now()
            start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
        else:
            start_date = trading_days[-1]  # Oldest day
            end_date = trading_days[0]  # Most recent day

        # Fetch bars using enhanced API method
        bars_data = fetcher.fetch_historical_bars(symbol_list, timeframe, start_date, end_date)

        if not bars_data:
            return "Error: No historical data received from API"

        # Process each symbol
        results = []
        results.append("# Peak and Trough Analysis for Day Trading\n")

        # Add AUTO mode debug info if applicable
        if "debug_info" in locals():
            results.append(debug_info)

        results.append(
            f"Parameters: {timeframe} bars, {days} days, Window: {window_len}, Lookahead: {lookahead}\n"
        )
        results.append(f"Delta: {delta}, Min Peak Distance: {min_peak_distance}\n")
        # Show analysis time in NYC timezone - FORCE timezone conversion
        try:
            from datetime import datetime

            import pytz

            utc_now = datetime.now(pytz.UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_now = utc_now.astimezone(nyc_tz)

            # Force EDT/EST display
            tz_name = nyc_now.strftime("%Z")  # This will be EDT or EST
            results.append(f"Analysis Time: {nyc_now.strftime('%Y-%m-%d %H:%M:%S')} {tz_name}\n")
        except Exception as e:
            logger.warning(f"Failed to format analysis time with timezone: {e}")
            # Fallback with manual EDT calculation
            from datetime import datetime

            utc_now = datetime.utcnow()
            # EDT is UTC-4, EST is UTC-5. In June, it's EDT
            edt_hour = (utc_now.hour - 4) % 24
            edt_time = utc_now.replace(hour=edt_hour)
            results.append(f"Analysis Time: {edt_time.strftime('%Y-%m-%d %H:%M:%S')} EDT\n")
        results.append("=" * 80 + "\n")

        for symbol in symbol_list:
            results.append(f"\n## {symbol}\n")

            # Get bars for this symbol
            if symbol not in bars_data:
                results.append(f"No data available for {symbol}\n")
                continue

            symbol_bars = bars_data[symbol]
            if not symbol_bars:
                results.append(f"No bars found for {symbol}\n")
                continue

            # Extract close prices and timestamps from API format
            close_prices_list = []
            timestamps = []
            for bar in symbol_bars:
                close_prices_list.append(float(bar["c"]))  # Close price
                timestamps.append(bar["t"])  # Timestamp

            close_prices = np.array(close_prices_list)

            if len(close_prices) < lookahead * 2:
                results.append(
                    f"Insufficient data for {symbol} (need at least {lookahead * 2} bars)\n"
                )
                continue

            results.append(f"Total bars analyzed: {len(close_prices)}\n")
            results.append(f"Price range: ${min(close_prices):.4f} - ${max(close_prices):.4f}\n")
            results.append(f"Current price: ${close_prices[-1]:.4f}\n\n")

            # Apply zero-phase Hanning filter
            filtered_prices = zero_phase_filter(close_prices, window_len)

            # Create time axis (indices)
            time_axis = np.arange(len(close_prices))

            # Detect peaks and troughs on filtered data
            max_peaks, min_peaks = peakdetect(
                filtered_prices, x_axis=time_axis, lookahead=lookahead, delta=delta
            )

            # Filter peaks/troughs by minimum distance if specified
            if min_peak_distance > 1:
                # Filter peaks that are too close together
                filtered_max_peaks = []
                filtered_min_peaks = []

                for i, (idx, value) in enumerate(max_peaks):
                    if i == 0 or (idx - max_peaks[i - 1][0]) >= min_peak_distance:
                        filtered_max_peaks.append((idx, value))

                for i, (idx, value) in enumerate(min_peaks):
                    if i == 0 or (idx - min_peaks[i - 1][0]) >= min_peak_distance:
                        filtered_min_peaks.append((idx, value))

                max_peaks = filtered_max_peaks
                min_peaks = filtered_min_peaks

            # Peaks (potential sell signals) - Report ORIGINAL prices
            results.append(f"### Peaks (Resistance/Sell Signals): {len(max_peaks)}\n")
            if max_peaks:
                # Get last 5 peaks
                recent_peaks = max_peaks[-5:] if len(max_peaks) > 5 else max_peaks
                for idx, filtered_value in recent_peaks:
                    idx = int(idx)
                    if 0 <= idx < len(timestamps):
                        # Parse timestamp for display in NYC/EDT timezone - FORCE timezone conversion
                        raw_ts = timestamps[idx]
                        try:
                            # Force timezone conversion regardless of environment
                            if isinstance(raw_ts, str):
                                from dateutil import parser as date_parser

                                dt = date_parser.parse(raw_ts)
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=pytz.UTC)
                                nyc_dt = dt.astimezone(pytz.timezone("America/New_York"))
                                peak_time = nyc_dt.strftime("%H:%M:%S")
                            else:
                                # Handle datetime objects
                                if hasattr(raw_ts, "tzinfo"):
                                    if raw_ts.tzinfo is None:
                                        raw_ts = raw_ts.replace(tzinfo=pytz.UTC)
                                    nyc_dt = raw_ts.astimezone(pytz.timezone("America/New_York"))
                                    peak_time = nyc_dt.strftime("%H:%M:%S")
                                else:
                                    peak_time = f"Bar_{idx}"
                        except Exception as e:
                            logger.warning(
                                f"Timezone conversion failed for peak timestamp {raw_ts}: {e}"
                            )
                            peak_time = f"Bar_{idx}"

                        original_price = close_prices[idx]  # ORIGINAL unfiltered price
                        results.append(
                            f"  - Sample {idx}, {peak_time}: ${original_price:.4f} (filtered: ${filtered_value:.4f})\n"
                        )

                # Latest peak analysis
                if max_peaks:
                    latest_peak_idx = int(max_peaks[-1][0])
                    latest_peak_price = close_prices[latest_peak_idx]  # ORIGINAL price
                    current_price = close_prices[-1]
                    peak_distance = len(close_prices) - 1 - latest_peak_idx

                    results.append(
                        f"\nLatest peak: Sample {latest_peak_idx}, ${latest_peak_price:.4f} ({peak_distance} bars ago)\n"
                    )

            # Troughs (potential buy signals) - Report ORIGINAL prices
            results.append(f"\n### Troughs (Support/Buy Signals): {len(min_peaks)}\n")
            if min_peaks:
                # Get last 5 troughs
                recent_troughs = min_peaks[-5:] if len(min_peaks) > 5 else min_peaks
                for idx, filtered_value in recent_troughs:
                    idx = int(idx)
                    if 0 <= idx < len(timestamps):
                        # Parse timestamp for display in NYC/EDT timezone - FORCE timezone conversion
                        raw_ts = timestamps[idx]
                        try:
                            # Force timezone conversion regardless of environment
                            if isinstance(raw_ts, str):
                                from dateutil import parser as date_parser

                                dt = date_parser.parse(raw_ts)
                                if dt.tzinfo is None:
                                    dt = dt.replace(tzinfo=pytz.UTC)
                                nyc_dt = dt.astimezone(pytz.timezone("America/New_York"))
                                trough_time = nyc_dt.strftime("%H:%M:%S")
                            else:
                                # Handle datetime objects
                                if hasattr(raw_ts, "tzinfo"):
                                    if raw_ts.tzinfo is None:
                                        raw_ts = raw_ts.replace(tzinfo=pytz.UTC)
                                    nyc_dt = raw_ts.astimezone(pytz.timezone("America/New_York"))
                                    trough_time = nyc_dt.strftime("%H:%M:%S")
                                else:
                                    trough_time = f"Bar_{idx}"
                        except Exception as e:
                            logger.warning(
                                f"Timezone conversion failed for trough timestamp {raw_ts}: {e}"
                            )
                            trough_time = f"Bar_{idx}"

                        original_price = close_prices[idx]  # ORIGINAL unfiltered price
                        results.append(
                            f"  - Sample {idx}, {trough_time}: ${original_price:.4f} (filtered: ${filtered_value:.4f})\n"
                        )

                # Latest trough analysis
                if min_peaks:
                    latest_trough_idx = int(min_peaks[-1][0])
                    latest_trough_price = close_prices[latest_trough_idx]  # ORIGINAL price
                    current_price = close_prices[-1]
                    trough_distance = len(close_prices) - 1 - latest_trough_idx

                    results.append(
                        f"\nLatest trough: Sample {latest_trough_idx}, ${latest_trough_price:.4f} ({trough_distance} bars ago)\n"
                    )

            # Enhanced Trading signals summary
            results.append("\n### Trading Signal Summary:\n")

            # Determine current position relative to peaks/troughs
            if max_peaks and min_peaks:
                latest_peak_idx = int(max_peaks[-1][0])
                latest_trough_idx = int(min_peaks[-1][0])
                current_price = close_prices[-1]

                if latest_peak_idx > latest_trough_idx:
                    # Last signal was a peak - use ORIGINAL price
                    peak_price = close_prices[latest_peak_idx]
                    price_from_peak = ((current_price - peak_price) / peak_price) * 100
                    bars_since_peak = len(close_prices) - 1 - latest_peak_idx

                    results.append(
                        f"📊 Last signal: PEAK at sample {latest_peak_idx} (${peak_price:.4f})\n"
                    )
                    results.append(
                        f"📍 Current position: {price_from_peak:+.2f}% from peak ({bars_since_peak} bars ago)\n"
                    )

                    if bars_since_peak <= 3 and abs(price_from_peak) <= 2.0:
                        results.append("🔴 SELL/SHORT Signal - Near recent peak, good exit point\n")
                    elif price_from_peak < -2.0:
                        results.append("⚠️ Watch - Price declining from peak, potential reversal\n")
                    else:
                        results.append("➡️ Neutral - Monitor for direction\n")
                else:
                    # Last signal was a trough - use ORIGINAL price
                    trough_price = close_prices[latest_trough_idx]
                    price_from_trough = ((current_price - trough_price) / trough_price) * 100
                    bars_since_trough = len(close_prices) - 1 - latest_trough_idx

                    results.append(
                        f"📊 Last signal: TROUGH at sample {latest_trough_idx} (${trough_price:.4f})\n"
                    )
                    results.append(
                        f"📍 Current position: {price_from_trough:+.2f}% from trough ({bars_since_trough} bars ago)\n"
                    )

                    if bars_since_trough <= 3 and abs(price_from_trough) <= 2.0:
                        results.append(
                            "🟢 BUY/LONG Signal - Near recent trough, good entry point\n"
                        )
                    elif price_from_trough > 2.0:
                        results.append("⚠️ Watch - Price rising from trough, potential reversal\n")
                    else:
                        results.append("➡️ Neutral - Monitor for direction\n")

            elif min_peaks:
                # Only troughs found
                latest_trough_idx = int(min_peaks[-1][0])
                trough_price = close_prices[latest_trough_idx]
                bars_since = len(close_prices) - 1 - latest_trough_idx
                if bars_since <= 3:
                    results.append("🟢 BUY Signal - Recent trough detected\n")

            elif max_peaks:
                # Only peaks found
                latest_peak_idx = int(max_peaks[-1][0])
                peak_price = close_prices[latest_peak_idx]
                bars_since = len(close_prices) - 1 - latest_peak_idx
                if bars_since <= 3:
                    results.append("🔴 SELL Signal - Recent peak detected\n")

            results.append("-" * 40 + "\n")

        return "".join(results)

    except Exception as e:
        logger.error(f"Error in analyze_peaks_and_troughs: {e}")
        return f"Error analyzing peaks and troughs: {str(e)}"


async def analyze_peaks_and_troughs_with_plot_py(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1,
    window_len: int = None,
    lookahead: int = None,
    delta: float = 0.0,
    min_peak_distance: int = 5,
) -> str:
    """
    Use plot.py with --no-plot option for accurate peak/trough analysis.

    This function uses the same data source and analysis as the plotting tool
    to fix the data synchronization issue where charts show fresh signals
    but analysis tools don't detect them.

    Args:
        symbols: Comma-separated symbols (e.g., "AAPL,MSFT")
        timeframe: Bar timeframe ("1Min", "5Min", etc.)
        days: Number of trading days to analyze
        window_len: Hanning filter window length (uses global config if None)
        lookahead: Peak detection sensitivity (uses global config if None)
        delta: Minimum peak amplitude (default: 0.0)
        min_peak_distance: Minimum bars between peaks (default: 5)

    Returns:
        Analysis result string with peak/trough signals
    """
    try:
        # Get current global config if parameters not provided
        if window_len is None or lookahead is None:
            tech_config = get_technical_config()
            if window_len is None:
                window_len = tech_config.hanning_window_samples
            if lookahead is None:
                lookahead = tech_config.peak_trough_lookahead

        # Path to plot.py
        os.path.join(os.path.dirname(__file__), "plot.py")

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
            "--no-plot",  # Skip plotting, only analysis
            "--verbose",  # Get detailed output
        ]

        logger.info(f"Running plot.py analysis: {' '.join(cmd)}")

        # Execute plot.py with --no-plot using asyncio subprocess
        import asyncio

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # Project root
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=30
            )  # Reduced timeout
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

        # Return the analysis output
        analysis_output = result_stdout

        logger.info(f"plot.py analysis completed successfully for {symbols}")
        return analysis_output

    except Exception as e:
        logger.error(f"Error running plot.py analysis: {e}")
        return f"Error running plot.py analysis: {str(e)}"
