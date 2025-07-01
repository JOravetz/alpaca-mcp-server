#!/usr/bin/env python3
"""
Multi-Symbol Peak Detection Test Script with Plotting
Clean version with all functionality preserved
"""

import logging
import os
import sys
from datetime import datetime, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pytz
import requests
from dateutil import parser as date_parser
from dateutil import tz
from scipy.signal import filtfilt
from scipy.signal.windows import hann as hanning

# Import peakdetect with fallback
try:
    from .peakdetect import peakdetect
except ImportError:
    # Fallback for when running as script
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from peakdetect import peakdetect

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def convert_to_nyc_timezone(timestamp_str):
    """Convert timestamp string to NYC/EDT timezone for plotting"""
    try:
        # Parse the timestamp (handles UTC timestamps from Alpaca API)
        dt = date_parser.parse(timestamp_str)

        # If timezone-naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)

        # Convert to NYC timezone (handles EDT/EST automatically)
        nyc_tz = pytz.timezone("America/New_York")
        dt_nyc = dt.astimezone(nyc_tz)

        return dt_nyc
    except Exception as e:
        logger.warning(f"Failed to convert timestamp {timestamp_str}: {e}")
        # Return the original timestamp as fallback to avoid None values
        try:
            return (
                date_parser.parse(timestamp_str)
                if isinstance(timestamp_str, str)
                else timestamp_str
            )
        except (ValueError, TypeError, AttributeError, OverflowError) as e:
            # Last resort: return current time in NYC timezone
            return datetime.now(pytz.timezone("America/New_York"))


def zero_phase_filter(data, window_len=11):
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


def process_bars_for_peaks(symbol, bars, window_len=11, lookahead=1):
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

        logger.info("Processing %d bars for %s", len(close_prices), symbol)
        logger.info("Close price range: %.4f - %.4f", close_prices.min(), close_prices.max())

        filtered_prices = zero_phase_filter(close_prices, window_len)
        time_axis = np.arange(len(close_prices))

        max_peaks, min_peaks = peakdetect(
            filtered_prices, x_axis=time_axis, lookahead=lookahead, delta=0
        )

        logger.info("Found %d peaks and %d troughs", len(max_peaks), len(min_peaks))

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
        }

        logger.info(
            "Processed %d bars for %s: %d peaks, %d troughs",
            len(bars),
            symbol,
            len(peaks_data),
            len(troughs_data),
        )

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


def print_latest_signals_table(all_results):
    """Print a table showing the latest signal for each symbol"""
    if not all_results:
        return

    print("")
    print("=" * 115)
    print("LATEST PEAK/TROUGH SIGNALS")
    print("=" * 115)

    # Create header line safely
    col_widths = [8, 8, 6, 14, 14, 12, 10, 22]
    header_items = [
        "Symbol",
        "Signal",
        "Ago",
        "Signal $",
        "Current $",
        "Change",
        "Change%",
        "Time (NYC/EDT)",
    ]

    header_line = ""
    for i, (header, width) in enumerate(zip(header_items, col_widths, strict=False)):
        if i == 0:
            header_line += header.rjust(width)
        else:
            header_line += " " + header.rjust(width)

    print(header_line)
    print("-" * 115)

    signals_found = 0

    for results in all_results:
        symbol = results["symbol"]
        latest_signal = get_latest_signal(results)

        if latest_signal:
            signals_found += 1
            signal_type = latest_signal["type"]
            samples_ago = latest_signal["samples_ago"]
            signal_price = latest_signal["signal_price"]
            current_price = latest_signal["current_price"]
            price_change = latest_signal["price_change"]
            price_change_pct = latest_signal["price_change_pct"]
            # Convert timestamp to NYC timezone for display
            raw_timestamp = latest_signal["timestamp"]
            try:
                nyc_timestamp = convert_to_nyc_timezone(raw_timestamp)
                if hasattr(nyc_timestamp, "strftime"):
                    formatted_timestamp = nyc_timestamp.strftime("%H:%M:%S %Z")
                else:
                    formatted_timestamp = raw_timestamp
            except (ValueError, AttributeError, TypeError) as e:
                formatted_timestamp = raw_timestamp

            change_indicator = "+" if price_change >= 0 else "-"
            signal_indicator = "^P" if signal_type == "Peak" else "vT"

            # Format each column safely
            cols = [
                symbol.rjust(col_widths[0]),
                signal_indicator.rjust(col_widths[1]),
                str(samples_ago).rjust(col_widths[2]),
                f"{signal_price:.4f}".rjust(col_widths[3]),
                f"{current_price:.4f}".rjust(col_widths[4]),
                "{}{}".format(change_indicator, f"{abs(price_change):.4f}").rjust(col_widths[5]),
                f"{price_change_pct:.2f}%".rjust(col_widths[6]),
                formatted_timestamp.rjust(col_widths[7]),
            ]

            print(" ".join(cols))
        else:
            # No signal row
            cols = [
                symbol.rjust(col_widths[0]),
                "None".rjust(col_widths[1]),
                "-".rjust(col_widths[2]),
                "-".rjust(col_widths[3]),
                "-".rjust(col_widths[4]),
                "-".rjust(col_widths[5]),
                "-".rjust(col_widths[6]),
                "-".rjust(col_widths[7]),
            ]

            print(" ".join(cols))

    print("-" * 115)
    print(f"Signals found: {signals_found}/{len(all_results)} symbols")
    print("=" * 115)


def plot_single_symbol(results, save_plot=False, output_dir=".", dpi=400):
    """Create a professional plot for a single symbol with auto-positioned legend and stats"""
    if not results:
        logger.error("No results to plot")
        return

    # Set matplotlib timezone to NYC
    import matplotlib

    matplotlib.rcParams["timezone"] = "America/New_York"

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(14, 8))

    # Set timezone for x-axis BEFORE plotting
    nyc_tz = tz.gettz("America/New_York")
    ax.xaxis_date(tz=nyc_tz)

    # Parse timestamps and convert to NYC/EDT timezone
    try:
        timestamps = [convert_to_nyc_timezone(ts) for ts in results["timestamps"]]
        # Verify we have the right number of timestamps
        if len(timestamps) != len(results["original_prices"]):
            logger.warning("Timestamp count mismatch, using indices for x-axis")
            timestamps = range(len(results["original_prices"]))
    except Exception as e:
        logger.warning(f"Could not parse timestamps: {e}, using indices for x-axis")
        timestamps = range(len(results["original_prices"]))

    # Extract data
    original_prices = np.array(results["original_prices"])
    filtered_prices = np.array(results["filtered_prices"])
    peaks = results["peaks"]
    troughs = results["troughs"]

    # Main price lines
    ax.plot(
        timestamps,
        original_prices,
        color="#2E86AB",
        linewidth=1.5,
        alpha=0.7,
        label="Original Close Prices",
        zorder=1,
    )

    ax.plot(
        timestamps,
        filtered_prices,
        color="#A23B72",
        linewidth=2.5,
        label="Filtered (Hanning w={})".format(results["filter_params"]["window_len"]),
        zorder=2,
    )

    # Plot peaks at original prices with actual price annotations
    if peaks:
        peak_times = [
            (
                convert_to_nyc_timezone(peak["timestamp"])
                if isinstance(timestamps[0], datetime)
                else peak["index"]
            )
            for peak in peaks
        ]
        peak_original_prices = [peak["original_price"] for peak in peaks]

        ax.scatter(
            peak_times,
            peak_original_prices,
            color="#F18F01",
            s=80,
            marker="^",
            label=f"Peaks ({len(peaks)})",
            zorder=4,
            edgecolors="none",
            linewidths=0,
        )

        # Add peak annotations with actual prices
        for i, (time, price) in enumerate(zip(peak_times, peak_original_prices, strict=False)):
            ax.annotate(
                f"P{i + 1}: ${price:.4f}",
                (time, price),
                xytext=(5, 15),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color="#F18F01",
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
            )

    # Plot troughs at original prices with actual price annotations
    if troughs:
        trough_times = [
            (
                convert_to_nyc_timezone(trough["timestamp"])
                if isinstance(timestamps[0], datetime)
                else trough["index"]
            )
            for trough in troughs
        ]
        trough_original_prices = [trough["original_price"] for trough in troughs]

        ax.scatter(
            trough_times,
            trough_original_prices,
            color="#C73E1D",
            s=80,
            marker="v",
            label=f"Troughs ({len(troughs)})",
            zorder=4,
            edgecolors="none",
            linewidths=0,
        )

        # Add trough annotations with actual prices
        for i, (time, price) in enumerate(zip(trough_times, trough_original_prices, strict=False)):
            ax.annotate(
                f"T{i + 1}: ${price:.4f}",
                (time, price),
                xytext=(5, -20),
                textcoords="offset points",
                fontsize=9,
                fontweight="bold",
                color="#C73E1D",
                bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "alpha": 0.8},
            )

    # Styling
    ax.set_ylabel("Price ($)", fontsize=12, fontweight="bold")

    # Create title
    symbol = results["symbol"]
    total_bars = results["total_bars"]
    window_len = results["filter_params"]["window_len"]
    lookahead = results["filter_params"]["lookahead"]

    title = (
        f"{symbol} - Peak & Trough Detection\n"
        f"Bars: {total_bars} | Filter: Hanning(w={window_len}) | "
        f"Lookahead: {lookahead} | Peaks: {len(peaks)} | Troughs: {len(troughs)}"
    )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)

    # Format x-axis for datetime with NYC/EDT timezone
    if isinstance(timestamps[0], datetime):
        # Create timezone-aware formatter (timezone already set above)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=nyc_tz))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

        # Add timezone label to x-axis
        ax.set_xlabel("Time (NYC/EDT)", fontsize=12, fontweight="bold")
    else:
        ax.set_xlabel("Time", fontsize=12, fontweight="bold")

    # Grid
    ax.grid(True, linestyle="--", alpha=0.7, color="gray")

    # Set axis limits with padding
    y_min, y_max = ax.get_ylim()
    y_range = y_max - y_min
    ax.set_ylim(y_min - 0.02 * y_range, y_max + 0.02 * y_range)

    # Calculate stats for text box
    price_min = original_prices.min()
    price_max = original_prices.max()
    noise_reduction = (original_prices.std() - filtered_prices.std()) / original_prices.std() * 100

    stats_text = (
        f"Price Range: ${price_min:.4f} - ${price_max:.4f}\n"
        f"Filter Smoothing: {noise_reduction:.1f}%\n"
        f"Peak/Trough Ratio: {len(peaks)}/{len(troughs)}"
    )

    # Auto-position legend and stats box to avoid overlap
    # Try different legend positions and find best fit

    # Determine which corner has least data density for better positioning
    data_density = {
        "upper_left": 0,
        "upper_right": 0,
        "lower_left": 0,
        "lower_right": 0,
    }

    # Check peak/trough density in each corner (simplified heuristic)
    x_mid = len(timestamps) // 2
    y_mid = (y_min + y_max) / 2

    for peak in peaks:
        if peak["index"] < x_mid and peak["original_price"] > y_mid:
            data_density["upper_left"] += 1
        elif peak["index"] >= x_mid and peak["original_price"] > y_mid:
            data_density["upper_right"] += 1
        elif peak["index"] < x_mid and peak["original_price"] <= y_mid:
            data_density["lower_left"] += 1
        else:
            data_density["lower_right"] += 1

    for trough in troughs:
        if trough["index"] < x_mid and trough["original_price"] > y_mid:
            data_density["upper_left"] += 1
        elif trough["index"] >= x_mid and trough["original_price"] > y_mid:
            data_density["upper_right"] += 1
        elif trough["index"] < x_mid and trough["original_price"] <= y_mid:
            data_density["lower_left"] += 1
        else:
            data_density["lower_right"] += 1

    # Find corner with least density
    min_density_corner = min(data_density, key=data_density.get)

    # Set legend and stats positions based on least dense corner
    if min_density_corner == "upper_left":
        legend_loc = "upper left"
        stats_pos = (0.02, 0.35)  # Lower left for stats
    elif min_density_corner == "upper_right":
        legend_loc = "upper right"
        stats_pos = (0.02, 0.98)  # Upper left for stats
    elif min_density_corner == "lower_left":
        legend_loc = "lower left"
        stats_pos = (0.02, 0.98)  # Upper left for stats
    else:  # lower_right
        legend_loc = "lower right"
        stats_pos = (0.02, 0.98)  # Upper left for stats

    # Create legend with auto-positioning
    legend = ax.legend(
        loc=legend_loc,
        frameon=True,
        fancybox=True,
        shadow=True,
        fontsize=11,
        framealpha=0.9,
    )

    # Add stats text box with auto-positioning
    stats_box = ax.text(
        stats_pos[0],
        stats_pos[1],
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.8},
    )

    # Additional check: if legend and stats would still overlap, move stats to opposite corner
    legend_bbox = legend.get_window_extent(fig.canvas.get_renderer())
    stats_bbox = stats_box.get_window_extent(fig.canvas.get_renderer())

    # Convert to axes coordinates for comparison
    legend_bbox_ax = legend_bbox.transformed(ax.transAxes.inverted())
    stats_bbox_ax = stats_bbox.transformed(ax.transAxes.inverted())

    # Check for overlap (simplified intersection test)
    overlap = not (
        legend_bbox_ax.x1 < stats_bbox_ax.x0
        or legend_bbox_ax.x0 > stats_bbox_ax.x1
        or legend_bbox_ax.y1 < stats_bbox_ax.y0
        or legend_bbox_ax.y0 > stats_bbox_ax.y1
    )

    if overlap:
        # Move stats to opposite corner
        if stats_pos[1] > 0.5:  # Stats was in upper area
            new_stats_pos = (0.02, 0.25)  # Move to lower
        else:  # Stats was in lower area
            new_stats_pos = (0.02, 0.98)  # Move to upper

        # Remove old stats box and create new one
        stats_box.remove()
        ax.text(
            new_stats_pos[0],
            new_stats_pos[1],
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.8},
        )

    plt.tight_layout()

    # Save plot if requested
    if save_plot:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"{symbol}_peak_detection_{timestamp}.png")
        plt.savefig(filename, dpi=dpi, bbox_inches="tight", facecolor="white")
        logger.info("Plot saved as %s", filename)

    plt.show()
    return fig


def plot_combined_subplots(all_results, save_plot=False, output_dir=".", dpi=400):
    """Create combined subplots for multiple symbols"""
    if not all_results:
        logger.error("No results to plot")
        return

    # Set matplotlib timezone to NYC
    import matplotlib

    matplotlib.rcParams["timezone"] = "America/New_York"

    num_symbols = len(all_results)
    rows = (num_symbols + 1) // 2
    cols = 2 if num_symbols > 1 else 1

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(rows, cols, figsize=(16, 6 * rows))

    axes = [axes] if num_symbols == 1 or rows == 1 else axes.flatten()

    # Set timezone for all subplots
    nyc_tz = tz.gettz("America/New_York")

    for idx, results in enumerate(all_results):
        ax = axes[idx]

        # Set timezone for this subplot BEFORE plotting
        ax.xaxis_date(tz=nyc_tz)

        # Parse timestamps and convert to NYC/EDT timezone
        try:
            timestamps = [convert_to_nyc_timezone(ts) for ts in results["timestamps"]]
            # Verify we have the right number of timestamps
            if len(timestamps) != len(results["original_prices"]):
                timestamps = range(len(results["original_prices"]))
        except (KeyError, ValueError, TypeError) as e:
            timestamps = range(len(results["original_prices"]))

        # Extract data
        original_prices = np.array(results["original_prices"])
        filtered_prices = np.array(results["filtered_prices"])
        peaks = results["peaks"]
        troughs = results["troughs"]

        # Plot lines
        ax.plot(
            timestamps,
            original_prices,
            color="#2E86AB",
            linewidth=1.5,
            alpha=0.7,
            label="Original",
        )
        ax.plot(timestamps, filtered_prices, color="#A23B72", linewidth=2, label="Filtered")

        # Plot peaks and troughs at original prices with price annotations
        if peaks:
            peak_times = [
                (
                    convert_to_nyc_timezone(peak["timestamp"])
                    if isinstance(timestamps[0], datetime)
                    else peak["index"]
                )
                for peak in peaks
            ]
            peak_original_prices = [peak["original_price"] for peak in peaks]
            ax.scatter(
                peak_times,
                peak_original_prices,
                color="#F18F01",
                s=60,
                marker="^",
                label=f"Peaks ({len(peaks)})",
                zorder=4,
                edgecolors="none",
                linewidths=0,
            )

            # Add price annotations for peaks
            for _i, (time, price) in enumerate(zip(peak_times, peak_original_prices, strict=False)):
                ax.annotate(
                    f"${price:.4f}",
                    (time, price),
                    xytext=(0, 10),
                    textcoords="offset points",
                    fontsize=8,
                    ha="center",
                    color="#F18F01",
                )

        if troughs:
            trough_times = [
                (
                    convert_to_nyc_timezone(trough["timestamp"])
                    if isinstance(timestamps[0], datetime)
                    else trough["index"]
                )
                for trough in troughs
            ]
            trough_original_prices = [trough["original_price"] for trough in troughs]
            ax.scatter(
                trough_times,
                trough_original_prices,
                color="#C73E1D",
                s=60,
                marker="v",
                label=f"Troughs ({len(troughs)})",
                zorder=4,
                edgecolors="none",
                linewidths=0,
            )

            # Add price annotations for troughs
            for _i, (time, price) in enumerate(
                zip(trough_times, trough_original_prices, strict=False)
            ):
                ax.annotate(
                    f"${price:.4f}",
                    (time, price),
                    xytext=(0, -15),
                    textcoords="offset points",
                    fontsize=8,
                    ha="center",
                    color="#C73E1D",
                )

        # Styling
        symbol = results["symbol"]
        ax.set_title(f"{symbol} (P:{len(peaks)} T:{len(troughs)})", fontweight="bold")
        ax.set_ylabel("Price ($)")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(fontsize=9)

        # Format x-axis with NYC/EDT timezone
        if isinstance(timestamps[0], datetime):
            # Timezone already set above, just format
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=nyc_tz))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            ax.set_xlabel("Time (NYC/EDT)", fontsize=10)

    # Hide empty subplots
    for idx in range(num_symbols, len(axes)):
        axes[idx].set_visible(False)

    # Overall title
    window_len = all_results[0]["filter_params"]["window_len"]
    lookahead = all_results[0]["filter_params"]["lookahead"]
    fig.suptitle(
        f"Multi-Symbol Peak Detection (Hanning w={window_len}, Lookahead={lookahead})",
        fontsize=16,
        fontweight="bold",
    )

    plt.tight_layout()

    # Save plot if requested
    if save_plot:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbols_str = "_".join([r["symbol"] for r in all_results])
        filename = os.path.join(output_dir, f"multi_symbol_{symbols_str}_{timestamp}.png")
        plt.savefig(filename, dpi=dpi, bbox_inches="tight", facecolor="white")
        logger.info("Combined plot saved as %s", filename)

    plt.show()
    return fig


def plot_overlay(all_results, save_plot=False, output_dir=".", dpi=400):
    """Create overlay plot with normalized prices"""
    if not all_results:
        logger.error("No results to plot")
        return

    # Set matplotlib timezone to NYC
    import matplotlib

    matplotlib.rcParams["timezone"] = "America/New_York"

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, ax = plt.subplots(figsize=(16, 10))

    # Set timezone for x-axis BEFORE plotting
    nyc_tz = tz.gettz("America/New_York")
    ax.xaxis_date(tz=nyc_tz)

    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3A5F8A", "#8B5A5C"]

    for idx, results in enumerate(all_results):
        color = colors[idx % len(colors)]
        symbol = results["symbol"]

        # Parse timestamps and convert to NYC/EDT timezone
        try:
            timestamps = [convert_to_nyc_timezone(ts) for ts in results["timestamps"]]
            # Verify we have the right number of timestamps
            if len(timestamps) != len(results["original_prices"]):
                timestamps = range(len(results["original_prices"]))
        except (KeyError, ValueError, TypeError) as e:
            timestamps = range(len(results["original_prices"]))

        # Normalize prices to percentage change from first price
        original_prices = np.array(results["original_prices"])
        normalized_prices = (original_prices / original_prices[0] - 1) * 100

        filtered_prices = np.array(results["filtered_prices"])
        normalized_filtered = (filtered_prices / original_prices[0] - 1) * 100

        # Plot lines
        ax.plot(
            timestamps,
            normalized_prices,
            color=color,
            linewidth=1.5,
            alpha=0.7,
            label=f"{symbol} Original",
        )
        ax.plot(
            timestamps,
            normalized_filtered,
            color=color,
            linewidth=2.5,
            label=f"{symbol} Filtered",
            linestyle="--",
        )

        # Plot peaks and troughs with actual price annotations
        peaks = results["peaks"]
        troughs = results["troughs"]

        if peaks:
            peak_times = [
                (
                    convert_to_nyc_timezone(peak["timestamp"])
                    if isinstance(timestamps[0], datetime)
                    else peak["index"]
                )
                for peak in peaks
            ]
            peak_normalized = [
                (peak["original_price"] / original_prices[0] - 1) * 100 for peak in peaks
            ]
            ax.scatter(
                peak_times,
                peak_normalized,
                color=color,
                s=80,
                marker="^",
                edgecolors="none",
                linewidths=0,
                zorder=4,
            )

            # Add actual price annotations
            for _i, (time, norm_price, actual_price) in enumerate(
                zip(peak_times, peak_normalized, [p["original_price"] for p in peaks], strict=False)
            ):
                ax.annotate(
                    f"${actual_price:.4f}",
                    (time, norm_price),
                    xytext=(5, 10),
                    textcoords="offset points",
                    fontsize=8,
                    color=color,
                )

        if troughs:
            trough_times = [
                (
                    convert_to_nyc_timezone(trough["timestamp"])
                    if isinstance(timestamps[0], datetime)
                    else trough["index"]
                )
                for trough in troughs
            ]
            trough_normalized = [
                (trough["original_price"] / original_prices[0] - 1) * 100 for trough in troughs
            ]
            ax.scatter(
                trough_times,
                trough_normalized,
                color=color,
                s=80,
                marker="v",
                edgecolors="none",
                linewidths=0,
                zorder=4,
            )

            # Add actual price annotations
            for _i, (time, norm_price, actual_price) in enumerate(
                zip(
                    trough_times,
                    trough_normalized,
                    [t["original_price"] for t in troughs],
                    strict=False,
                )
            ):
                ax.annotate(
                    f"${actual_price:.4f}",
                    (time, norm_price),
                    xytext=(5, -15),
                    textcoords="offset points",
                    fontsize=8,
                    color=color,
                )

    # Styling
    ax.set_ylabel("Normalized Return (%)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Multi-Symbol Overlay (Normalized Returns with Actual Prices)",
        fontsize=14,
        fontweight="bold",
    )
    ax.grid(True, linestyle="--", alpha=0.7)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)

    # Format x-axis with NYC/EDT timezone
    if len(all_results) > 0:
        try:
            timestamps = [convert_to_nyc_timezone(ts) for ts in all_results[0]["timestamps"]]
            # Timezone already set above, just format
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=nyc_tz))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            ax.set_xlabel("Time (NYC/EDT)", fontsize=12, fontweight="bold")
        except (ImportError, AttributeError, ValueError) as e:
            ax.set_xlabel("Time", fontsize=12, fontweight="bold")

    plt.tight_layout()

    # Save plot if requested
    if save_plot:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbols_str = "_".join([r["symbol"] for r in all_results])
        filename = os.path.join(output_dir, f"overlay_{symbols_str}_{timestamp}.png")
        plt.savefig(filename, dpi=dpi, bbox_inches="tight", facecolor="white")
        logger.info("Overlay plot saved as %s", filename)

    plt.show()
    return fig


def print_summary(results):
    """Print summary for a single symbol"""
    if not results:
        return

    symbol = results["symbol"]
    print(f"\n📊 RESULTS SUMMARY for {symbol}:")
    print("   • Total bars processed: {}".format(results["total_bars"]))
    print(
        "   • Filter parameters: window_len={}, lookahead={}".format(
            results["filter_params"]["window_len"],
            results["filter_params"]["lookahead"],
        )
    )
    print(
        "   • Price range: ${:.4f} - ${:.4f}".format(
            min(results["original_prices"]), max(results["original_prices"])
        )
    )
    print("   • Peaks detected: {} (at original close prices)".format(len(results["peaks"])))
    print("   • Troughs detected: {} (at original close prices)".format(len(results["troughs"])))

    if results["peaks"] or results["troughs"]:
        if results["peaks"]:
            print("   PEAKS (at original close prices):")
            for i, peak in enumerate(results["peaks"]):
                print(
                    "     P{}: Index {}, ${:.4f} (filtered: ${:.4f})".format(
                        i + 1,
                        peak["index"],
                        peak["original_price"],
                        peak["filtered_price"],
                    )
                )

        if results["troughs"]:
            print("   TROUGHS (at original close prices):")
            for i, trough in enumerate(results["troughs"]):
                print(
                    "     T{}: Index {}, ${:.4f} (filtered: ${:.4f})".format(
                        i + 1,
                        trough["index"],
                        trough["original_price"],
                        trough["filtered_price"],
                    )
                )


def main():
    """Main test function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test zero-phase filtering and peak detection on multiple stock symbols",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--symbols",
        "-s",
        type=str,
        required=True,
        help="Comma-delimited stock symbols to analyze (e.g., 'AAPL,TSLA,MSFT')",
    )

    parser.add_argument(
        "--timeframe",
        "-t",
        type=str,
        default="1Min",
        choices=[
            "1Min",
            "2Min",
            "5Min",
            "15Min",
            "30Min",
            "1Hour",
            "2Hour",
            "4Hour",
            "1Day",
        ],
        help="Bar timeframe",
    )

    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=1,
        help="Number of trading days to fetch (1-30 for intraday, 1-2520 for daily)",
    )

    parser.add_argument(
        "--window",
        "-w",
        type=int,
        default=11,
        help="Hanning filter window length (must be odd, 3-101)",
    )

    parser.add_argument(
        "--lookahead",
        "-l",
        type=int,
        default=1,
        help="Peak detection lookahead parameter (1-50)",
    )

    parser.add_argument(
        "--feed",
        "-f",
        type=str,
        default="sip",
        choices=["iex", "sip", "otc"],
        help="Data feed to use",
    )

    parser.add_argument(
        "--plot-mode",
        type=str,
        default="single",
        choices=["single", "combined", "overlay", "all"],
        help="Plotting mode: single plots, combined subplots, overlay, or all modes",
    )

    parser.add_argument(
        "--save-plots",
        "-p",
        action="store_true",
        help="Save plots as PNG files with timestamp",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=".",
        help="Output directory for saved plots",
    )

    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip plotting (useful for batch processing)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments - timeframe-aware limits
    if args.timeframe == "1Day":
        max_days = 2520  # ~10 years for daily analysis
    elif args.timeframe in ["1Hour", "2Hour", "4Hour"]:
        max_days = 90  # 3 months for hourly
    else:  # Intraday timeframes (1Min, 5Min, etc.)
        max_days = 30  # Current limit for intraday

    if args.days < 1 or args.days > max_days:
        logger.error(f"Days must be between 1 and {max_days} for {args.timeframe} timeframe")
        sys.exit(1)

    if args.window < 3 or args.window > 101:
        logger.error("Window length must be between 3 and 101")
        sys.exit(1)

    # Ensure window length is odd
    if args.window % 2 == 0:
        args.window += 1
        logger.info("Window length adjusted to %d (must be odd)", args.window)

    if args.lookahead < 1 or args.lookahead > 50:
        logger.error("Lookahead must be between 1 and 50")
        sys.exit(1)

    # Check for required environment variables
    api_key = os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("APCA_API_SECRET_KEY")

    if not api_key or not api_secret:
        logger.error("APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables must be set")
        sys.exit(1)

    # Extract and validate symbols
    if not args.symbols:
        logger.error("No symbols provided")
        sys.exit(1)

    # Parse comma-delimited symbols and convert to uppercase
    test_symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

    if not test_symbols:
        logger.error("No valid symbols found")
        sys.exit(1)

    if len(test_symbols) > 20:
        logger.error("Too many symbols (max 20)")
        sys.exit(1)

    days = args.days
    timeframe = args.timeframe
    feed = args.feed
    window_len = args.window
    lookahead = args.lookahead

    # Create output directory if it doesn't exist
    if args.save_plots and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        logger.info("Created output directory: %s", args.output_dir)

    logger.info("Starting multi-symbol peak detection test...")
    logger.info("Symbols: %s", test_symbols)
    logger.info("Days: %d, Timeframe: %s, Feed: %s", days, timeframe, feed)
    logger.info("Filter params: window_len=%d, lookahead=%d", window_len, lookahead)
    logger.info("Plot mode: %s", args.plot_mode)

    try:
        # Initialize data fetcher
        fetcher = HistoricalDataFetcher(api_key, api_secret)

        # Get trading days
        trading_days = fetcher.get_trading_days(days)
        if not trading_days:
            logger.error("No trading days found")
            return

        start_date = trading_days[-1]
        end_date = trading_days[0]

        logger.info("Fetching data from %s to %s", start_date, end_date)

        # Fetch historical data for all symbols in one API call
        bars_data = fetcher.fetch_historical_bars(
            test_symbols, timeframe, start_date, end_date, feed
        )

        if not bars_data:
            logger.error("No historical data received")
            return

        # Process each symbol
        all_results = []
        for symbol in test_symbols:
            if symbol not in bars_data:
                logger.warning("No data for symbol %s", symbol)
                continue

            bars = bars_data[symbol]
            if not bars:
                logger.warning("No bars for symbol %s", symbol)
                continue

            # Process bars for peaks
            results = process_bars_for_peaks(symbol, bars, window_len, lookahead)

            if results:
                all_results.append(results)

                # Print summary for each symbol
                print_summary(results)
            else:
                logger.error("Failed to process %s", symbol)

        if not all_results:
            logger.error("No symbols processed successfully")
            return

        # Print latest signals table (same as no-plot version)
        print_latest_signals_table(all_results)

        # Generate plots if not disabled
        if not args.no_plot:
            if args.plot_mode == "single" or args.plot_mode == "all":
                logger.info("Creating individual plots...")
                for results in all_results:
                    plot_single_symbol(
                        results, save_plot=args.save_plots, output_dir=args.output_dir
                    )

            if (args.plot_mode == "combined" or args.plot_mode == "all") and len(all_results) > 1:
                logger.info("Creating combined subplot...")
                plot_combined_subplots(
                    all_results, save_plot=args.save_plots, output_dir=args.output_dir
                )

            if (args.plot_mode == "overlay" or args.plot_mode == "all") and len(all_results) > 1:
                logger.info("Creating overlay plot...")
                plot_overlay(all_results, save_plot=args.save_plots, output_dir=args.output_dir)
        else:
            logger.info("Plotting skipped")

        # Print overall summary
        print("\n🎯 OVERALL SUMMARY:")
        print(f"   • Symbols processed: {len(all_results)}/{len(test_symbols)}")
        print("   • Total peaks found: {}".format(sum(len(r["peaks"]) for r in all_results)))
        print("   • Total troughs found: {}".format(sum(len(r["troughs"]) for r in all_results)))

        if all_results:
            avg_bars = np.mean([r["total_bars"] for r in all_results])
            print(f"   • Average bars per symbol: {avg_bars:.0f}")

        logger.info("Multi-symbol peak detection test completed")

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error("Test failed: %s", e)
        raise


if __name__ == "__main__":
    main()
