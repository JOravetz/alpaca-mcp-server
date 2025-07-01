#!/usr/bin/env python3
"""
Multi-Symbol Peak Detection Script with NumPy Arrays and Date/Time Display
Restructured to use numpy arrays instead of pandas and display actual dates/times
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import requests
import subprocess
import tempfile
import threading
import webbrowser
from datetime import datetime, timedelta
from scipy.signal import filtfilt
from scipy.signal.windows import hann as hanning
try:
    import pandas_market_calendars as mcal
    HAS_MARKET_CALENDARS = True
except ImportError:
    print("⚠️  pandas-market-calendars not available. Install with:")
    print("   pip install pandas-market-calendars --break-system-packages")
    print("   or use: pipx install pandas-market-calendars")
    print("   Falling back to simple interpolation...")
    HAS_MARKET_CALENDARS = False
    mcal = None

# Set matplotlib backend BEFORE any other matplotlib imports
import matplotlib
# Default to headless for server environments - backend selection happens after arg parsing
matplotlib.use('Agg')
INTERACTIVE_BACKEND = False

def setup_backend_for_args(no_plot=False):
    """Setup backend based on user arguments"""
    global INTERACTIVE_BACKEND
    if no_plot:
        matplotlib.use('Agg', force=True)
        INTERACTIVE_BACKEND = False
    else:
        # Use Agg backend for headless environments, save files for ImageMagick display
        matplotlib.use('Agg', force=True)
        INTERACTIVE_BACKEND = False

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dateutil import parser as date_parser
from dateutil import tz
import pytz

# Add current directory to path to import peakdetect
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from peakdetect import peakdetect

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global plot manager for MCP server
class MCPPlotManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix='alpaca_plots_')
        self.generated_plots = []
        self.display_processes = []
        logger.info(f"Plot temp directory: {self.temp_dir}")
    
    def generate_filename(self, symbol, plot_type="peak_detection"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{symbol}_{plot_type}_{timestamp}.png"
        return os.path.join(self.temp_dir, filename)
    
    def save_and_display(self, fig, filepath):
        try:
            if INTERACTIVE_BACKEND:
                # For interactive plots, just show directly
                logger.info(f"Displaying interactive plot for {filepath}")
                plt.show(block=False)  # Non-blocking show for interactive display
            else:
                # For non-interactive backends, save to file and open in browser
                logger.info(f"Saving plot to {filepath}")
                fig.savefig(filepath, dpi=100, 
                           facecolor='#212529', edgecolor='#212529', transparent=False)
                plt.close(fig)  # Close figure to free memory
                # Open in browser for better display
                try:
                    webbrowser.open(f'file://{filepath}')
                    logger.info(f"Opened plot in browser: {filepath}")
                except Exception as e:
                    logger.warning(f"Could not open browser: {e}")
            self.generated_plots.append(filepath)
            return True
        except Exception as e:
            logger.error(f"Failed to display/save plot: {e}")
            return False
    
    def _schedule_cleanup_on_close(self, process):
        """Monitor display process and cleanup when it closes"""
        def monitor_and_cleanup():
            try:
                # Wait for the display process to terminate
                process.wait()
                logger.info(f"Display process {process.pid} closed, cleaning up temp directory")
                self.cleanup()
            except Exception as e:
                logger.error(f"Error monitoring display process: {e}")
        
        # Start monitoring in background thread
        cleanup_thread = threading.Thread(target=monitor_and_cleanup, daemon=True)
        cleanup_thread.start()
    
    def cleanup(self):
        """Clean up temporary directory and all plot files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
            self.generated_plots.clear()
        except Exception as e:
            logger.error(f"Failed to cleanup temp directory: {e}")
    
    def force_cleanup(self):
        """Force cleanup of all display processes and temp files"""
        # Terminate any remaining display processes
        for process in self.display_processes:
            try:
                if process.poll() is None:  # Process still running
                    process.terminate()
                    logger.info(f"Terminated display process {process.pid}")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
        
        self.display_processes.clear()
        self.cleanup()

# Global instance
mcp_plot_manager = MCPPlotManager()


def parse_timestamp_to_datetime(timestamp_str):
    """Parse timestamp string to datetime object"""
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
        logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
        # Return current time in NYC timezone as fallback
        return datetime.now(pytz.timezone("America/New_York"))


def format_datetime_for_display(dt):
    """Format datetime for display in dd/mm/yyyy hh:mm format"""
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return str(dt)


def create_market_calendar_dataframe(timestamps, timeframe):
    """
    Create a pandas DataFrame with market calendar for NYSE/NASDAQ 4 AM to 8 PM NYC/EDT
    using regular sampling intervals only during trading hours.
    """
    if not HAS_MARKET_CALENDARS:
        # Fallback: simple uniform grid without market calendar
        return create_simple_uniform_grid(timestamps, timeframe)
    
    # Convert timestamps to datetime objects
    dt_objects = [parse_timestamp_to_datetime(ts) for ts in timestamps]
    start_time = dt_objects[0]
    end_time = dt_objects[-1]
    
    # Parse timeframe to get interval in minutes
    if timeframe.endswith('Min'):
        interval_minutes = int(timeframe[:-3])
    elif timeframe == '1Hour':
        interval_minutes = 60
    elif timeframe == '1Day':
        interval_minutes = 1440
    else:
        interval_minutes = 15
    
    # Create NYSE calendar (covers most US stocks)
    nyse = mcal.get_calendar('NYSE')
    
    # Convert times to NYC timezone
    nyc_tz = pytz.timezone('America/New_York')
    start_nyc = start_time.astimezone(nyc_tz).date()
    end_nyc = end_time.astimezone(nyc_tz).date()
    
    # Get trading days
    trading_days = nyse.schedule(start_date=start_nyc, end_date=end_nyc)
    
    # Create extended hours schedule (4 AM to 8 PM NYC/EDT)
    extended_schedule = []
    for date, row in trading_days.iterrows():
        # Create 4 AM to 8 PM schedule for each trading day
        trading_date = date.date()
        market_open = nyc_tz.localize(datetime.combine(trading_date, datetime.min.time().replace(hour=4)))
        market_close = nyc_tz.localize(datetime.combine(trading_date, datetime.min.time().replace(hour=20)))
        
        # Generate time range for this trading day
        time_range = pd.date_range(
            start=market_open,
            end=market_close,
            freq=f'{interval_minutes}min',  # min = minutes
            tz=nyc_tz
        )
        extended_schedule.extend(time_range)
    
    # Convert to DataFrame with price column
    if extended_schedule:
        market_df = pd.DataFrame({
            'timestamp': extended_schedule,
            'close': np.nan
        })
        market_df.set_index('timestamp', inplace=True)
        market_df.sort_index(inplace=True)
        
        logger.info(f"Created market calendar DataFrame with {len(market_df)} time points from {market_df.index[0]} to {market_df.index[-1]}")
        return market_df
    else:
        logger.warning("No trading days found in the specified range")
        return pd.DataFrame()

def create_simple_uniform_grid(timestamps, timeframe):
    """
    Fallback: create a simple uniform grid without market calendar
    """
    # Convert timestamps to datetime objects
    dt_objects = [parse_timestamp_to_datetime(ts) for ts in timestamps]
    start_time = dt_objects[0]
    end_time = dt_objects[-1]
    
    # Parse timeframe to get interval in minutes
    if timeframe.endswith('Min'):
        interval_minutes = int(timeframe[:-3])
    elif timeframe == '1Hour':
        interval_minutes = 60
    elif timeframe == '1Day':
        interval_minutes = 1440
    else:
        interval_minutes = 15
    
    # Create simple uniform time grid
    uniform_times = pd.date_range(
        start=start_time,
        end=end_time,
        freq=f'{interval_minutes}min'
    )
    
    # Convert to DataFrame
    market_df = pd.DataFrame({
        'timestamp': uniform_times,
        'close': np.nan
    })
    market_df.set_index('timestamp', inplace=True)
    
    logger.info(f"Created simple uniform grid with {len(market_df)} time points")
    return market_df


def interpolate_to_uniform_grid(timestamps, prices, timeframe):
    """
    Use pandas market calendar to create uniform sampling during market hours,
    then fill gaps using forward/backward fill methods.
    
    For daily timeframes, skip interpolation and use original data directly.
    """
    # Convert timestamps to datetime objects with timezone
    original_times = [parse_timestamp_to_datetime(ts) for ts in timestamps]
    
    # For daily timeframes, skip market calendar interpolation
    if timeframe == '1Day':
        logger.info(f"Daily timeframe detected - using original data without interpolation")
        return timestamps, prices, original_times
    
    # Create market calendar DataFrame for intraday timeframes only
    market_df = create_market_calendar_dataframe(timestamps, timeframe)
    
    if market_df.empty:
        logger.warning("Empty market calendar - falling back to original data")
        return timestamps, prices, original_times
    
    # Create DataFrame from original data with NYC timezone
    nyc_tz = pytz.timezone('America/New_York')
    original_df = pd.DataFrame({
        'timestamp': [dt.astimezone(nyc_tz) for dt in original_times],
        'close': prices
    })
    original_df.set_index('timestamp', inplace=True)
    
    # Copy original values to market calendar DataFrame where they exist
    for timestamp in original_df.index:
        if timestamp in market_df.index:
            market_df.loc[timestamp, 'close'] = original_df.loc[timestamp, 'close']
    
    # Forward fill then backward fill to interpolate missing values
    market_df['close'] = market_df['close'].ffill().bfill()
    
    # Extract interpolated data
    uniform_timestamps = [dt.isoformat() + 'Z' for dt in market_df.index.tz_convert('UTC')]
    interpolated_prices = market_df['close'].values
    uniform_datetimes = market_df.index.tolist()
    
    logger.info(f"Interpolated {len(original_times)} irregular samples to {len(market_df)} uniform market-hours samples")
    
    return uniform_timestamps, interpolated_prices, uniform_datetimes


def zero_phase_filter(data, window_len=11):
    """Apply zero-phase low-pass filter using Hanning window - numpy only"""
    data = np.array(data, dtype=np.float64)

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

    def get_asset_info(self, symbol):
        """Get asset information including company name"""
        url = f"https://paper-api.alpaca.markets/v2/assets/{symbol}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            asset_data = response.json()
            company_name = asset_data.get("name", symbol)
            
            logger.info(f"Retrieved company name for {symbol}: {company_name}")
            return company_name
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get company name for {symbol}: {e}")
            return symbol
        except Exception as e:
            logger.warning(f"Error getting company name for {symbol}: {e}")
            return symbol

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

    def fetch_historical_bars(
        self, symbols, timeframe, start_date, end_date, feed="sip"
    ):
        """Fetch historical bar data for multiple symbols with pagination support"""
        if not symbols:
            logger.warning("No symbols provided for historical data fetch")
            return None

        url = "https://data.alpaca.markets/v2/stocks/bars"
        all_bars_data = {}
        next_page_token = None
        page_count = 0
        max_pages = 50  # Safety limit to prevent infinite loops
        
        # Initialize data structure for all symbols
        for symbol in symbols:
            all_bars_data[symbol] = []

        try:
            logger.info(
                "Fetching historical bars: %s symbols, %s, %s to %s",
                len(symbols),
                timeframe,
                start_date,
                end_date,
            )

            while page_count < max_pages:
                page_count += 1
                
                params = {
                    "symbols": ",".join(symbols),
                    "timeframe": timeframe,
                    "start": start_date,
                    "end": end_date,
                    "limit": 10000,  # Maximum bars per page
                    "adjustment": "split",
                    "feed": feed,
                    "sort": "asc",
                }
                
                # Add page token if this is not the first request
                if next_page_token:
                    params["page_token"] = next_page_token
                    logger.debug(f"Fetching page {page_count} with token: {next_page_token[:20]}...")

                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()

                data = response.json()

                if not isinstance(data, dict):
                    logger.error("Invalid response format from bars API")
                    return None

                if "bars" not in data:
                    logger.warning("No 'bars' key in API response")
                    return None

                # Merge bars data from this page
                page_bars_data = data["bars"]
                page_total_bars = 0
                
                for symbol, bars in page_bars_data.items():
                    if bars:
                        all_bars_data[symbol].extend(bars)
                        page_total_bars += len(bars)
                    elif symbol not in all_bars_data:
                        # Initialize empty list for symbols with no data
                        all_bars_data[symbol] = []

                logger.info(f"Page {page_count}: fetched {page_total_bars} bars")

                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    logger.info("No more pages available")
                    break
                    
                logger.debug(f"Found next_page_token, continuing to page {page_count + 1}")

            # Calculate total bars across all symbols and pages
            total_bars = 0
            symbols_with_data = 0
            
            for symbol, bars in all_bars_data.items():
                if bars:
                    total_bars += len(bars)
                    symbols_with_data += 1
                else:
                    logger.warning("No bars received for symbol %s", symbol)

            logger.info(
                "Successfully fetched %s bars for %s/%s symbols across %s pages",
                total_bars,
                symbols_with_data,
                len(symbols),
                page_count,
            )
            
            # Return only symbols that have data
            return {symbol: bars for symbol, bars in all_bars_data.items() if bars}

        except requests.exceptions.Timeout:
            logger.error("Timeout fetching historical bars")
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Request error fetching historical bars: %s", e)
            return None
        except Exception as e:
            logger.error("Error fetching historical bars: %s", e)
            return None


def process_bars_for_peaks(symbol, bars, window_len=11, lookahead=1, company_name=None, timeframe="15Min"):
    """Process bars to compute filtered close prices and detect peaks/troughs - numpy arrays only"""
    try:
        if not bars or len(bars) < lookahead * 2:
            logger.warning(
                "Not enough bars for %s to detect peaks (need at least %d)",
                symbol,
                lookahead * 2,
            )
            return None

        # Extract data into numpy arrays
        close_prices = np.array([float(bar["c"]) for bar in bars], dtype=np.float64)
        timestamps_raw = [bar["t"] for bar in bars]
        
        logger.info("Processing %d bars for %s", len(close_prices), symbol)
        logger.info(
            "Close price range: %.4f - %.4f", close_prices.min(), close_prices.max()
        )

        # CRITICAL: Linear interpolation before digital signal processing
        # This ensures uniform time sampling required for proper filter frequency response
        uniform_timestamps, interpolated_prices, uniform_datetimes = interpolate_to_uniform_grid(
            timestamps_raw, close_prices, timeframe
        )
        
        # Create datetime lookup table using interpolated data
        datetime_objects = uniform_datetimes
        datetime_lookup = {i: dt for i, dt in enumerate(datetime_objects)}
        
        # Create formatted time strings for display
        formatted_times = [format_datetime_for_display(dt) for dt in datetime_objects]

        # Apply zero-phase filter to uniformly sampled data
        filtered_prices = zero_phase_filter(interpolated_prices, window_len)
        
        # Use interpolated data for all subsequent processing
        close_prices = interpolated_prices
        timestamps_raw = uniform_timestamps
        
        # Create sample index array
        sample_indices = np.arange(len(close_prices))

        # Detect peaks and troughs using filtered prices
        max_peaks, min_peaks = peakdetect(
            filtered_prices, x_axis=sample_indices, lookahead=lookahead, delta=0
        )

        logger.info("Found %d peaks and %d troughs", len(max_peaks), len(min_peaks))

        # Process peaks
        peaks_data = []
        for peak_idx, peak_value in max_peaks:
            idx = int(peak_idx)
            if 0 <= idx < len(close_prices):  # Check against interpolated data length
                # For volume, try to find closest original bar or use 0
                volume = 0
                if idx < len(bars):
                    volume = int(bars[idx]["v"])
                
                peaks_data.append({
                    "sample_index": idx,
                    "timestamp_raw": timestamps_raw[idx],
                    "datetime_object": datetime_objects[idx],
                    "formatted_time": formatted_times[idx],
                    "filtered_price": float(peak_value),
                    "original_price": float(close_prices[idx]),
                    "volume": volume,
                })

        # Process troughs
        troughs_data = []
        for trough_idx, trough_value in min_peaks:
            idx = int(trough_idx)
            if 0 <= idx < len(close_prices):  # Check against interpolated data length
                # For volume, try to find closest original bar or use 0
                volume = 0
                if idx < len(bars):
                    volume = int(bars[idx]["v"])
                
                troughs_data.append({
                    "sample_index": idx,
                    "timestamp_raw": timestamps_raw[idx],
                    "datetime_object": datetime_objects[idx],
                    "formatted_time": formatted_times[idx],
                    "filtered_price": float(trough_value),
                    "original_price": float(close_prices[idx]),
                    "volume": volume,
                })

        # Return results with numpy arrays and lookup table
        results = {
            "symbol": symbol,
            "company_name": company_name or symbol,
            "total_bars": len(bars),
            "sample_indices": sample_indices,
            "timestamps_raw": timestamps_raw,
            "datetime_objects": datetime_objects,
            "datetime_lookup": datetime_lookup,
            "formatted_times": formatted_times,
            "original_prices": close_prices,
            "filtered_prices": filtered_prices,
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

    # Check peaks
    for peak in peaks:
        if peak["sample_index"] > latest_index:
            latest_index = peak["sample_index"]
            latest_signal = {
                "type": "Peak",
                "sample_index": peak["sample_index"],
                "timestamp_raw": peak["timestamp_raw"],
                "formatted_time": peak["formatted_time"],
                "signal_price": peak["original_price"],
                "filtered_price": peak["filtered_price"],
                "volume": peak["volume"],
            }

    # Check troughs
    for trough in troughs:
        if trough["sample_index"] > latest_index:
            latest_index = trough["sample_index"]
            latest_signal = {
                "type": "Trough",
                "sample_index": trough["sample_index"],
                "timestamp_raw": trough["timestamp_raw"],
                "formatted_time": trough["formatted_time"],
                "signal_price": trough["original_price"],
                "filtered_price": trough["filtered_price"],
                "volume": trough["volume"],
            }

    if latest_signal:
        total_bars = results["total_bars"]
        samples_ago = total_bars - 1 - latest_signal["sample_index"]
        current_price = float(results["original_prices"][-1])

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
    print("=" * 130)
    print("LATEST PEAK/TROUGH SIGNALS")
    print("=" * 130)

    # Create header line
    col_widths = [8, 8, 6, 14, 14, 12, 10, 22]
    header_items = [
        "Symbol",
        "Signal",
        "Ago",
        "Signal $",
        "Current $",
        "Change",
        "Change%",
        "Time (dd/mm/yyyy hh:mm)",
    ]

    header_line = ""
    for i, (header, width) in enumerate(zip(header_items, col_widths)):
        if i == 0:
            header_line += header.rjust(width)
        else:
            header_line += " " + header.rjust(width)

    print(header_line)
    print("-" * 130)

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
            formatted_time = latest_signal["formatted_time"]

            change_indicator = "+" if price_change >= 0 else "-"
            signal_indicator = "^P" if signal_type == "Peak" else "vT"

            # Format each column
            cols = [
                symbol.rjust(col_widths[0]),
                signal_indicator.rjust(col_widths[1]),
                str(samples_ago).rjust(col_widths[2]),
                "{:.4f}".format(signal_price).rjust(col_widths[3]),
                "{:.4f}".format(current_price).rjust(col_widths[4]),
                "{}{}".format(
                    change_indicator, "{:.4f}".format(abs(price_change))
                ).rjust(col_widths[5]),
                "{:.2f}%".format(price_change_pct).rjust(col_widths[6]),
                formatted_time.rjust(col_widths[7]),
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

    print("-" * 130)
    print("Signals found: {}/{} symbols".format(signals_found, len(all_results)))
    print("=" * 130)


def generate_html_report(all_results, test_symbols, analysis_params, sort_by="signal_age"):
    """Generate comprehensive HTML report for batch analysis results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S EST")
    
    # Calculate summary statistics
    total_symbols = len(test_symbols)
    processed_symbols = len(all_results)
    total_peaks = sum(len(r["peaks"]) for r in all_results)
    total_troughs = sum(len(r["troughs"]) for r in all_results)
    avg_bars = np.mean([r["total_bars"] for r in all_results]) if all_results else 0
    
    # Collect signals for analysis
    buy_signals = []  # Trough signals (buy opportunities)
    sell_signals = []  # Peak signals (sell opportunities)
    no_signals = []
    
    for results in all_results:
        symbol = results["symbol"]
        company_name = results.get("company_name", symbol)
        latest_signal = get_latest_signal(results)
        
        if latest_signal:
            signal_data = {
                'symbol': symbol,
                'company_name': company_name,
                'signal_type': latest_signal["type"],
                'samples_ago': latest_signal["samples_ago"],
                'signal_price': latest_signal["signal_price"],
                'current_price': latest_signal["current_price"],
                'price_change': latest_signal["price_change"],
                'price_change_pct': latest_signal["price_change_pct"],
                'formatted_time': latest_signal["formatted_time"]
            }
            
            if latest_signal["type"] == "Trough":
                buy_signals.append(signal_data)
            else:
                sell_signals.append(signal_data)
        else:
            no_signals.append({'symbol': symbol, 'company_name': company_name})
    
    # Define sort functions
    sort_functions = {
        'signal_age': lambda x: x['samples_ago'],  # Ascending (freshest first)
        'symbol': lambda x: x['symbol'],  # Ascending (alphabetical)
        'signal_price': lambda x: x['signal_price'],  # Ascending
        'current_price': lambda x: x['current_price'],  # Ascending
        'price_change': lambda x: x['price_change'],  # Descending (biggest gains first)
        'price_change_pct': lambda x: x['price_change_pct']  # Descending (biggest % gains first)
    }
    
    # Define sort order (True = descending, False = ascending)
    sort_reverse = {
        'signal_age': False,  # Ascending - freshest signals (smallest numbers) first
        'symbol': False,  # Ascending - alphabetical
        'signal_price': False,  # Ascending - lowest prices first
        'current_price': False,  # Ascending - lowest prices first
        'price_change': True,  # Descending - biggest $ gains first
        'price_change_pct': True  # Descending - biggest % gains first
    }
    
    # Sort signals according to specified column
    if sort_by in sort_functions:
        buy_signals.sort(key=sort_functions[sort_by], reverse=sort_reverse[sort_by])
        sell_signals.sort(key=sort_functions[sort_by], reverse=sort_reverse[sort_by])
    else:
        # Default fallback: sort by signal age (freshest first)
        buy_signals.sort(key=lambda x: x['samples_ago'])
        sell_signals.sort(key=lambda x: x['samples_ago'])
    
    # Generate HTML report
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Peak/Trough Analysis Report - {timestamp}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #212529;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #007bff;
            text-align: center;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        h2 {{
            color: #343a40;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin-top: 30px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #007bff;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #343a40;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        .numeric {{
            text-align: right;
        }}
        th {{
            background-color: #007bff;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .buy-signal {{
            background-color: #d4edda !important;
            border-left: 4px solid #28a745;
        }}
        .sell-signal {{
            background-color: #f8d7da !important;
            border-left: 4px solid #dc3545;
        }}
        .positive {{
            color: #28a745;
            font-weight: bold;
        }}
        .negative {{
            color: #dc3545;
            font-weight: bold;
        }}
        .params {{
            background: #e9ecef;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }}
        .top-opportunities {{
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .top-opportunities h3 {{
            margin-top: 0;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Peak/Trough Technical Analysis Report</h1>
        
        <div class="params">
            <strong>Analysis Parameters:</strong>
            Symbols: {total_symbols} | Days: {analysis_params['days']} | 
            Timeframe: {analysis_params['timeframe']} | Feed: {analysis_params['feed']} | 
            Window: {analysis_params['window_len']} | Lookahead: {analysis_params['lookahead']}
            <br><strong>Generated:</strong> {timestamp}
        </div>

        <h2>📈 Executive Summary</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Symbols Processed</h3>
                <div class="value">{processed_symbols}/{total_symbols}</div>
            </div>
            <div class="summary-card">
                <h3>Buy Signals</h3>
                <div class="value">{len(buy_signals)}</div>
            </div>
            <div class="summary-card">
                <h3>Sell Signals</h3>
                <div class="value">{len(sell_signals)}</div>
            </div>
            <div class="summary-card">
                <h3>Total Signals</h3>
                <div class="value">{len(buy_signals) + len(sell_signals)}</div>
            </div>
            <div class="summary-card">
                <h3>Peaks Detected</h3>
                <div class="value">{total_peaks}</div>
            </div>
            <div class="summary-card">
                <h3>Troughs Detected</h3>
                <div class="value">{total_troughs}</div>
            </div>
        </div>
"""

    if buy_signals:
        html_content += f"""
        <h2>🟢 BUY OPPORTUNITIES (Trough Signals)</h2>
        <div class="top-opportunities">
            <h3>🎯 Top 3 Buy Opportunities</h3>
            {" | ".join([f"<strong>{signal['symbol']}</strong> (+{signal['price_change_pct']:.2f}%)" for signal in buy_signals[:3]])}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Signal Age</th>
                    <th>Signal Price</th>
                    <th>Current Price</th>
                    <th>Price Change</th>
                    <th>Change %</th>
                    <th>Signal Time</th>
                </tr>
            </thead>
            <tbody>
"""
        for signal in buy_signals:
            change_class = "positive" if signal['price_change'] >= 0 else "negative"
            change_sign = "+" if signal['price_change'] >= 0 else ""
            
            html_content += f"""
                <tr class="buy-signal">
                    <td><strong>{signal['symbol']}</strong></td>
                    <td>{signal['company_name']}</td>
                    <td class="numeric">{signal['samples_ago']} bars ago</td>
                    <td class="numeric">${signal['signal_price']:.4f}</td>
                    <td class="numeric">${signal['current_price']:.4f}</td>
                    <td class="numeric {change_class}">{change_sign}${abs(signal['price_change']):.4f}</td>
                    <td class="numeric {change_class}">{signal['price_change_pct']:.2f}%</td>
                    <td>{signal['formatted_time']}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""

    if sell_signals:
        html_content += f"""
        <h2>🔴 SELL SIGNALS (Peak Signals)</h2>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Signal Age</th>
                    <th>Signal Price</th>
                    <th>Current Price</th>
                    <th>Price Change</th>
                    <th>Change %</th>
                    <th>Signal Time</th>
                </tr>
            </thead>
            <tbody>
"""
        for signal in sell_signals:
            change_class = "positive" if signal['price_change'] >= 0 else "negative"
            change_sign = "+" if signal['price_change'] >= 0 else ""
            
            html_content += f"""
                <tr class="sell-signal">
                    <td><strong>{signal['symbol']}</strong></td>
                    <td>{signal['company_name']}</td>
                    <td class="numeric">{signal['samples_ago']} bars ago</td>
                    <td class="numeric">${signal['signal_price']:.4f}</td>
                    <td class="numeric">${signal['current_price']:.4f}</td>
                    <td class="numeric {change_class}">{change_sign}${abs(signal['price_change']):.4f}</td>
                    <td class="numeric {change_class}">{signal['price_change_pct']:.2f}%</td>
                    <td>{signal['formatted_time']}</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""

    if no_signals:
        html_content += f"""
        <h2>⚪ NO RECENT SIGNALS</h2>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Company</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
        for item in no_signals:
            html_content += f"""
                <tr>
                    <td><strong>{item['symbol']}</strong></td>
                    <td>{item['company_name']}</td>
                    <td>No recent signals detected</td>
                </tr>
"""
        html_content += """
            </tbody>
        </table>
"""

    html_content += f"""
        <h2>📊 Technical Analysis Details</h2>
        <p><strong>Analysis Method:</strong> Zero-phase Hanning window filtering with peak/trough detection</p>
        <p><strong>Signal Definitions:</strong></p>
        <ul>
            <li><strong>Trough (BUY):</strong> Potential support level - price bouncing up from local minimum</li>
            <li><strong>Peak (SELL):</strong> Potential resistance level - price falling from local maximum</li>
        </ul>
        <p><strong>Signal Freshness:</strong> Only signals from the last 10 bars are considered "recent" and actionable.</p>
        
        <div class="footer">
            <p>Generated by Peak/Trough Analysis Tool | {timestamp}</p>
            <p>⚠️ This report is for informational purposes only. Always conduct your own research before making trading decisions.</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Save report to file
    report_filename = f"peak_trough_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n📝 HTML Report Generated: {report_filename}")
        print(f"📊 Summary: {len(buy_signals)} buy signals, {len(sell_signals)} sell signals")
        if buy_signals:
            print(f"🎯 Top buy opportunity: {buy_signals[0]['symbol']} (+{buy_signals[0]['price_change_pct']:.2f}%)")
        
        # Automatically open the report in the default browser
        try:
            # Get absolute path for reliable browser opening
            report_path = os.path.abspath(report_filename)
            
            # Open in browser using file:// URL
            webbrowser.open(f'file://{report_path}')
            print(f"🌐 Report opened in browser: file://{report_path}")
            
        except Exception as browser_error:
            logger.warning(f"Could not automatically open browser: {browser_error}")
            print(f"💼 Please open {report_filename} manually in your browser")
        
        return report_filename
        
    except Exception as e:
        logger.error(f"Failed to generate HTML report: {e}")
        return None


def plot_single_symbol(results):
    """Create plot for single symbol with continuous sample indices and date/time annotations"""
    if not results:
        logger.error("No results to plot")
        return None

    # Professional dark bootstrap theme
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(16, 10), facecolor='#212529')
    fig.patch.set_facecolor('#212529')  # Ensure figure background is solid
    ax.set_facecolor('#343a40')

    # Use continuous sample indices for x-axis (no time gaps)
    sample_indices = results["sample_indices"]
    original_prices = results["original_prices"]
    filtered_prices = results["filtered_prices"]
    peaks = results["peaks"]
    troughs = results["troughs"]
    datetime_objects = results["datetime_objects"]

    # Professional bootstrap-inspired color scheme
    bootstrap_colors = {
        'primary': '#007bff',      # Bootstrap blue
        'success': '#28a745',      # Bootstrap green  
        'info': '#17a2b8',         # Bootstrap cyan
        'warning': '#ffc107',      # Bootstrap yellow
        'danger': '#dc3545',       # Bootstrap red
        'light': '#f8f9fa',        # Bootstrap light
        'dark': '#343a40',         # Bootstrap dark
        'secondary': '#6c757d',    # Bootstrap gray
        'accent': '#fd7e14',       # Bootstrap orange
        'purple': '#6f42c1'        # Bootstrap purple
    }
    
    # Main price lines with professional styling
    ax.plot(
        sample_indices,
        original_prices,
        color=bootstrap_colors['info'],
        linewidth=2.0,
        alpha=0.9,
        label="Original Close Prices",
        zorder=1,
        linestyle='-'
    )

    ax.plot(
        sample_indices,
        filtered_prices,
        color=bootstrap_colors['primary'],
        linewidth=3.0,
        alpha=0.95,
        label="Filtered (Hanning w={})".format(results["filter_params"]["window_len"]),
        zorder=2,
        linestyle='-'
    )

    # Plot peaks with professional bootstrap styling
    if peaks:
        peak_indices = [peak["sample_index"] for peak in peaks]
        peak_original_prices = [peak["original_price"] for peak in peaks]

        ax.scatter(
            peak_indices,
            peak_original_prices,
            color=bootstrap_colors['warning'],
            s=120,
            marker="^",
            label="Peaks ({})".format(len(peaks)),
            zorder=4,
            edgecolors=bootstrap_colors['dark'],
            linewidth=2,
            alpha=0.9
        )

        # Add peak annotations with bootstrap styling
        for i, (idx, price) in enumerate(zip(peak_indices, peak_original_prices)):
            ax.annotate(
                "P{}: ${:.4f}".format(i + 1, price),
                (idx, price),
                xytext=(8, 18),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
                color=bootstrap_colors['light'],
                bbox=dict(
                    boxstyle="round,pad=0.5", 
                    facecolor=bootstrap_colors['warning'], 
                    alpha=0.9,
                    edgecolor=bootstrap_colors['dark'],
                    linewidth=1.5
                ),
                arrowprops=dict(
                    arrowstyle='->', 
                    color=bootstrap_colors['warning'],
                    alpha=0.7
                )
            )

    # Plot troughs with professional bootstrap styling
    if troughs:
        trough_indices = [trough["sample_index"] for trough in troughs]
        trough_original_prices = [trough["original_price"] for trough in troughs]

        ax.scatter(
            trough_indices,
            trough_original_prices,
            color=bootstrap_colors['success'],
            s=120,
            marker="v",
            label="Troughs ({})".format(len(troughs)),
            zorder=4,
            edgecolors=bootstrap_colors['dark'],
            linewidth=2,
            alpha=0.9
        )

        # Add trough annotations with bootstrap styling
        for i, (idx, price) in enumerate(zip(trough_indices, trough_original_prices)):
            ax.annotate(
                "T{}: ${:.4f}".format(i + 1, price),
                (idx, price),
                xytext=(8, -22),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
                color=bootstrap_colors['light'],
                bbox=dict(
                    boxstyle="round,pad=0.5", 
                    facecolor=bootstrap_colors['success'], 
                    alpha=0.9,
                    edgecolor=bootstrap_colors['dark'],
                    linewidth=1.5
                ),
                arrowprops=dict(
                    arrowstyle='->', 
                    color=bootstrap_colors['success'],
                    alpha=0.7
                )
            )

    # Professional bootstrap-style axis styling
    ax.set_ylabel("Price ($)", fontsize=14, fontweight="bold", color=bootstrap_colors['light'])
    ax.set_xlabel("Time (NYC/EDT)", fontsize=14, fontweight="bold", color=bootstrap_colors['light'])
    
    # Professional axis styling
    ax.tick_params(
        axis='both', 
        which='major', 
        labelsize=11, 
        colors=bootstrap_colors['light'],
        width=1.5,
        length=6
    )
    ax.tick_params(
        axis='both', 
        which='minor', 
        colors=bootstrap_colors['secondary'],
        width=1,
        length=4
    )

    # Create title with company name
    symbol = results["symbol"]
    company_name = results["company_name"]
    total_bars = results["total_bars"]
    window_len = results["filter_params"]["window_len"]
    lookahead = results["filter_params"]["lookahead"]

    # Get last sample date/time for title
    last_datetime = results["datetime_objects"][-1]
    last_time_str = last_datetime.strftime("%B-%d-%Y %H:%M")
    
    # Professional bootstrap-style title with gradient effect
    if company_name != symbol:
        title = (
            "{} ({}) - Professional Technical Analysis\n"
            "Bars: {} | Filter: Hanning(w={}) | Lookahead: {} | Peaks: {} | Troughs: {} | Last: {}"
        ).format(company_name, symbol, total_bars, window_len, lookahead, len(peaks), len(troughs), last_time_str)
    else:
        title = (
            "{} - Professional Technical Analysis\n"
            "Bars: {} | Filter: Hanning(w={}) | Lookahead: {} | Peaks: {} | Troughs: {} | Last: {}"
        ).format(symbol, total_bars, window_len, lookahead, len(peaks), len(troughs), last_time_str)

    ax.set_title(
        title, 
        fontsize=16, 
        fontweight="bold", 
        pad=25,
        color=bootstrap_colors['light'],
        bbox=dict(
            boxstyle="round,pad=0.8", 
            facecolor=bootstrap_colors['dark'], 
            alpha=0.8,
            edgecolor=bootstrap_colors['primary'],
            linewidth=2
        )
    )

    # Professional bootstrap-style grid
    ax.grid(
        True, 
        linestyle=":", 
        alpha=0.3, 
        color=bootstrap_colors['secondary'],
        linewidth=1
    )
    ax.set_axisbelow(True)  # Grid behind data
    
    # Add subtle border styling
    for spine in ax.spines.values():
        spine.set_edgecolor(bootstrap_colors['primary'])
        spine.set_linewidth(2)
        spine.set_alpha(0.8)

    # Calculate stats for text box
    price_min = float(original_prices.min())
    price_max = float(original_prices.max())
    noise_reduction = (
        (original_prices.std() - filtered_prices.std()) / original_prices.std() * 100
    )

    # Add date/time range to stats
    start_time = results["formatted_times"][0] if results["formatted_times"] else "Unknown"
    end_time = results["formatted_times"][-1] if results["formatted_times"] else "Unknown"

    # Professional bootstrap-style stats with symbols
    stats_text = (
        "Price Range: ${:.4f} - ${:.4f}\n"
        "Filter Smoothing: {:.1f}%\n"
        "Peak/Trough Ratio: {}/{}\n"
        "Time Range: {} to {}"
    ).format(price_min, price_max, noise_reduction, len(peaks), len(troughs), start_time, end_time)

    # Simple positioning: Stats in left corner, Legend uses matplotlib's automatic 'best' positioning
    def find_best_stats_position(original_prices, sample_indices):
        """Find the best left corner for stats box to avoid data overlap"""
        
        total_samples = len(sample_indices)
        y_min, y_max = original_prices.min(), original_prices.max()
        y_range = y_max - y_min
        
        # Only check left corners for stats box
        left_corners = {
            'upper_left': (0.0, 0.33, 0.66, 1.0),     # x: 0-33%, y: 66-100%
            'lower_left': (0.0, 0.33, 0.0, 0.33),     # x: 0-33%, y: 0-33%
        }
        
        # Calculate data density in each left corner
        left_scores = {}
        for region_name, (x_min, x_max, y_min_norm, y_max_norm) in left_corners.items():
            # Convert normalized coordinates to actual indices and prices
            x_start = int(x_min * total_samples)
            x_end = int(x_max * total_samples)
            y_start = y_min + y_min_norm * y_range
            y_end = y_min + y_max_norm * y_range
            
            # Count data points in this region
            data_in_region = 0
            if x_end > x_start:
                region_data = original_prices[x_start:x_end]
                data_in_region = np.sum((region_data >= y_start) & (region_data <= y_end))
            
            # Calculate density (points per unit area)
            area = (x_max - x_min) * (y_max_norm - y_min_norm)
            density = data_in_region / area if area > 0 else float('inf')
            
            left_scores[region_name] = density
        
        # Choose the left corner with lowest data density
        left_corners_sorted = sorted(left_scores.items(), key=lambda x: x[1])
        best_stats_corner = left_corners_sorted[0][0]
        
        logger.info(f"Stats placement: {best_stats_corner} (density score: {left_scores[best_stats_corner]:.1f})")
        logger.info(f"Legend placement: matplotlib 'best' automatic positioning")
        
        return best_stats_corner

    # Get optimal stats position (legend will use matplotlib's automatic positioning)
    stats_region = find_best_stats_position(original_prices, sample_indices)
    
    # Map regions to matplotlib positions with precise corner placement
    corner_positions = {
        'upper_left': {
            'legend_loc': 'upper left',
            'legend_bbox': (0.02, 0.98),
            'stats_bbox': (0.02, 0.98),  # Same corner as legend would be
            'stats_ha': 'left',
            'stats_va': 'top'
        },
        'upper_right': {
            'legend_loc': 'upper right', 
            'legend_bbox': (0.98, 0.98),
            'stats_bbox': (0.02, 0.98),  # Stats always go to upper left when legend is upper right
            'stats_ha': 'left',
            'stats_va': 'top'
        },
        'lower_left': {
            'legend_loc': 'lower left',
            'legend_bbox': (0.02, 0.02),
            'stats_bbox': (0.02, 0.02),  # Same corner as legend would be
            'stats_ha': 'left',
            'stats_va': 'bottom'
        },
        'lower_right': {
            'legend_loc': 'lower right',
            'legend_bbox': (0.98, 0.02),
            'stats_bbox': (0.02, 0.02),  # Stats always go to lower left when legend is lower right
            'stats_ha': 'left',
            'stats_va': 'bottom'
        }
    }
    
    # Alternative stats positions when legend is in a corner
    alternative_stats_positions = {
        'upper_center': (0.50, 0.98, 'center', 'top'),
        'middle_left': (0.02, 0.50, 'left', 'center'),
        'middle_center': (0.50, 0.50, 'center', 'center'),
        'middle_right': (0.98, 0.50, 'right', 'center'),
        'lower_center': (0.50, 0.02, 'center', 'bottom'),
    }
    
    # Professional positioning with proper spacing from borders
    legend_gap_x = 0.02  # Legend horizontal gap from border
    legend_gap_y = 0.02  # Legend vertical gap from border
    stats_gap_x = 0.02   # Stats box horizontal gap from border
    stats_gap_y = 0.04   # Stats box vertical gap from border (slightly more for better visibility)
    
    # Legend placement: Use matplotlib's automatic 'best' positioning to avoid data overlap
    legend = ax.legend(
        loc='best',  # Automatic positioning to minimize data overlap
        frameon=True, 
        fancybox=True, 
        shadow=True, 
        fontsize=12, 
        framealpha=0.95,
        facecolor=bootstrap_colors['dark'],
        edgecolor=bootstrap_colors['primary'],
        title="Technical Indicators",
        title_fontproperties={'weight': 'bold', 'size': 13}
    )
    legend.get_title().set_color(bootstrap_colors['light'])
    for text in legend.get_texts():
        text.set_color(bootstrap_colors['light'])
    
    # Stats box placement: LEFT corners only (upper_left or lower_left)
    if stats_region == 'upper_left':
        stats_bbox = (stats_gap_x, 1.0 - stats_gap_y)
        stats_va = 'top'
        stats_ha = 'left'
    else:  # stats_region == 'lower_left'
        stats_bbox = (stats_gap_x, stats_gap_y)
        stats_va = 'bottom'
        stats_ha = 'left'
    
    ax.text(
        stats_bbox[0], stats_bbox[1],
        stats_text,
        transform=ax.transAxes,
        fontsize=11,
        fontweight='bold',
        verticalalignment=stats_va,
        horizontalalignment=stats_ha,
        color=bootstrap_colors['light'],
        bbox=dict(
            boxstyle="round,pad=0.6", 
            facecolor=bootstrap_colors['dark'], 
            alpha=0.95,
            edgecolor=bootstrap_colors['info'],
            linewidth=2
        ),
    )

    # Set up custom x-axis with datetime labels at sample positions
    # Create a mapping from sample indices to formatted datetime strings
    num_labels = min(10, len(sample_indices) // 20)  # Reasonable number of labels
    if num_labels > 1:
        step = max(1, len(sample_indices) // num_labels)
        tick_positions = []
        tick_labels = []
        
        for i in range(0, len(sample_indices), step):
            if i < len(results["formatted_times"]):
                tick_positions.append(sample_indices[i])
                # Format: "June-06-2025 10:35" for cleaner display
                dt_obj = results["datetime_objects"][i]
                formatted_label = dt_obj.strftime("%B-%d-%Y %H:%M")
                tick_labels.append(formatted_label)
        
        # Don't add the last point to avoid crowding - it's now in the title
        
        # Set custom ticks
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha='right')
    else:
        # Fallback for very short datasets
        ax.set_xticks([sample_indices[0], sample_indices[-1]])
        start_label = results["datetime_objects"][0].strftime("%B-%d-%Y %H:%M")
        end_label = results["datetime_objects"][-1].strftime("%B-%d-%Y %H:%M")
        ax.set_xticklabels([start_label, end_label], rotation=45, ha='right')

    # Professional layout with padding
    plt.tight_layout(pad=3.0)
    
    # Add solid background - no transparency
    fig.patch.set_facecolor('#212529')
    fig.patch.set_alpha(1.0)

    # Show interactive plot with professional styling
    filepath = mcp_plot_manager.generate_filename(symbol)
    success = mcp_plot_manager.save_and_display(fig, filepath)
    
    if success:
        return filepath
    else:
        return None


def print_summary(results):
    """Print summary for a single symbol"""
    if not results:
        return

    symbol = results["symbol"]
    print("\n📊 RESULTS SUMMARY for {}:".format(symbol))
    print("   • Total bars processed: {}".format(results["total_bars"]))
    print(
        "   • Filter parameters: window_len={}, lookahead={}".format(
            results["filter_params"]["window_len"],
            results["filter_params"]["lookahead"],
        )
    )
    print(
        "   • Price range: ${:.4f} - ${:.4f}".format(
            float(results["original_prices"].min()), 
            float(results["original_prices"].max())
        )
    )
    print(
        "   • Peaks detected: {} (at original close prices)".format(
            len(results["peaks"])
        )
    )
    print(
        "   • Troughs detected: {} (at original close prices)".format(
            len(results["troughs"])
        )
    )

    if results["peaks"] or results["troughs"]:
        if results["peaks"]:
            print("   PEAKS (at original close prices):")
            for i, peak in enumerate(results["peaks"]):
                print(
                    "     P{}: Sample {}, ${:.4f} at {} (filtered: ${:.4f})".format(
                        i + 1,
                        peak["sample_index"],
                        peak["original_price"],
                        peak["formatted_time"],
                        peak["filtered_price"],
                    )
                )

        if results["troughs"]:
            print("   TROUGHS (at original close prices):")
            for i, trough in enumerate(results["troughs"]):
                print(
                    "     T{}: Sample {}, ${:.4f} at {} (filtered: ${:.4f})".format(
                        i + 1,
                        trough["sample_index"],
                        trough["original_price"],
                        trough["formatted_time"],
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
        "--no-plot",
        action="store_true",
        help="Skip plotting (useful for batch processing)",
    )


    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate HTML report for batch analysis results"
    )

    parser.add_argument(
        "--sort-by",
        type=str,
        default="signal_age",
        choices=["signal_age", "symbol", "signal_price", "current_price", "price_change", "price_change_pct"],
        help="Sort report by column (default: signal_age for freshest signals first)"
    )

    args = parser.parse_args()

    # Setup backend based on arguments
    setup_backend_for_args(no_plot=args.no_plot)

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments - timeframe-aware limits
    if args.timeframe == "1Day":
        max_days = 2520  # ~10 years for daily analysis
    elif args.timeframe in ["1Hour", "2Hour", "4Hour"]:
        max_days = 90    # 3 months for hourly
    else:  # Intraday timeframes (1Min, 5Min, etc.)
        max_days = 30    # Current limit for intraday
        
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
        logger.error(
            "APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables must be set"
        )
        sys.exit(1)

    # Extract and validate symbols
    if not args.symbols:
        logger.error("No symbols provided")
        sys.exit(1)

    # Parse comma-delimited symbols and convert to uppercase
    test_symbols = [
        symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()
    ]

    if not test_symbols:
        logger.error("No valid symbols found")
        sys.exit(1)

    # Remove limit for batch analysis - allow any number of symbols
    if len(test_symbols) > 100:
        logger.warning(f"Processing {len(test_symbols)} symbols - this may take several minutes")
        print(f"⚠️  Large batch: {len(test_symbols)} symbols - please wait...")

    days = args.days
    timeframe = args.timeframe
    feed = args.feed
    window_len = args.window
    lookahead = args.lookahead

    logger.info("Starting multi-symbol peak detection test...")
    logger.info("Symbols: %s", test_symbols)
    logger.info("Days: %d, Timeframe: %s, Feed: %s", days, timeframe, feed)
    logger.info("Filter params: window_len=%d, lookahead=%d", window_len, lookahead)

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

        # Get company names for all symbols
        logger.info("Fetching company names...")
        company_names = {}
        for symbol in test_symbols:
            company_names[symbol] = fetcher.get_asset_info(symbol)

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

            # Get company name
            company_name = company_names.get(symbol, symbol)

            # Process bars for peaks
            results = process_bars_for_peaks(symbol, bars, window_len, lookahead, company_name, timeframe)

            if results:
                all_results.append(results)
                print_summary(results)
            else:
                logger.error("Failed to process %s", symbol)

        if not all_results:
            logger.error("No symbols processed successfully")
            return

        # Print latest signals table
        print_latest_signals_table(all_results)

        # Generate plots if not disabled
        if not args.no_plot:
            logger.info("Creating interactive plots...")
            plot_files = []
            for results in all_results:
                filepath = plot_single_symbol(results)
                if filepath:
                    plot_files.append(filepath)
                    print(f"✅ Interactive plot displayed for {results['symbol']}")
                else:
                    print(f"❌ Failed to generate plot for {results['symbol']}")
            
            if plot_files:
                if INTERACTIVE_BACKEND:
                    print(f"\n📈 Generated {len(plot_files)} interactive plots")
                    print("💡 Close the plot windows when done viewing")
                    # Keep the script running until all plot windows are closed
                    try:
                        plt.show(block=True)  # Block until all plots are closed
                    except KeyboardInterrupt:
                        logger.info("Plot viewing interrupted by user")
                else:
                    print(f"\n📈 Generated {len(plot_files)} plots")
                    for plot_file in plot_files:
                        print(f"💾 Saved: {plot_file}")
        else:
            logger.info("Plotting skipped")

        # Print overall summary
        print("\n🎯 OVERALL SUMMARY:")
        print(
            "   • Symbols processed: {}/{}".format(len(all_results), len(test_symbols))
        )
        print(
            "   • Total peaks found: {}".format(
                sum(len(r["peaks"]) for r in all_results)
            )
        )
        print(
            "   • Total troughs found: {}".format(
                sum(len(r["troughs"]) for r in all_results)
            )
        )

        if all_results:
            avg_bars = np.mean([r["total_bars"] for r in all_results])
            print("   • Average bars per symbol: {:.0f}".format(avg_bars))

        # Generate HTML report if requested
        if args.report:
            analysis_params = {
                'days': days,
                'timeframe': timeframe,
                'feed': feed,
                'window_len': window_len,
                'lookahead': lookahead
            }
            report_file = generate_html_report(all_results, test_symbols, analysis_params, args.sort_by)

        logger.info("Multi-symbol peak detection test completed")

    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        mcp_plot_manager.force_cleanup()
    except Exception as e:
        logger.error("Test failed: %s", e)
        mcp_plot_manager.force_cleanup()
        raise


if __name__ == "__main__":
    main()