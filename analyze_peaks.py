#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Peak and Trough Analysis with Zero-Phase Filtering
Fetches historical data, applies Hanning filter, and detects peaks/troughs
"""

import argparse
from datetime import timedelta

import alpaca_trade_api as tradeapi
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytz
from alpaca_trade_api.rest import TimeFrame
from scipy import signal
from scipy.signal import filtfilt
from scipy.signal.windows import hann as hanning


def zero_phase_filter(data, window_len=11):
    """
    Apply zero-phase low-pass filter using Hanning window

    Parameters:
    -----------
    data : array_like
        Input signal
    window_len : int
        Length of the Hanning window (must be odd)

    Returns:
    --------
    filtered : array
        Zero-phase filtered signal
    """
    # Ensure window length is odd
    if window_len % 2 == 0:
        window_len += 1

    # Create Hanning window
    window = hanning(window_len)
    window = window / window.sum()  # Normalize

    # Apply zero-phase filtering using filtfilt
    # Pad the signal to handle edge effects
    pad_len = window_len // 2
    padded = np.pad(data, pad_len, mode="edge")

    # For zero-phase response, we use filtfilt
    # First, we need to ensure our filter has proper format
    filtered_padded = filtfilt(window, 1.0, padded)

    # Remove padding
    filtered = filtered_padded[pad_len:-pad_len]

    return filtered


def read_symbols_from_file(filename):
    """
    Read stock symbols from a file (one per line)

    Parameters:
    -----------
    filename : str
        Path to the file containing stock symbols

    Returns:
    --------
    list : List of uppercase stock symbols
    """
    symbols = []
    try:
        with open(filename, "r") as f:
            for line in f:
                symbol = line.strip().upper()
                if symbol and not symbol.startswith(
                    "#"
                ):  # Skip empty lines and comments
                    symbols.append(symbol)
    except FileNotFoundError:
        raise FileNotFoundError(f"Stock file '{filename}' not found")
    return symbols


def fetch_bars(api, symbol, num_days, timeframe_str, feed):
    """
    Fetch historical bar data from Alpaca for a single symbol
    """
    # Map timeframe string to TimeFrame object
    from alpaca_trade_api.rest import TimeFrameUnit

    timeframe_map = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "30Min": TimeFrame(30, TimeFrameUnit.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }

    timeframe = timeframe_map.get(timeframe_str, TimeFrame.Minute)

    # Get trading calendar
    calendar = api.get_calendar()
    trading_days = []
    current_date = pd.Timestamp.now().date()

    for day in reversed(calendar):
        if pd.Timestamp(day.date).date() <= current_date:
            trading_days.append(day)
            if len(trading_days) >= num_days:
                break

    if not trading_days:
        raise ValueError("No trading days found")

    # Get start and end times
    start_date = trading_days[-1].date
    end_date = trading_days[0].date

    # Fetch bars
    bars = api.get_bars(
        symbol,
        timeframe,
        start=start_date.strftime("%Y-%m-%d"),
        end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
        feed=feed,
        adjustment="split",
        asof=None,
    )

    return list(bars)


def fetch_bars_multiple(api, symbols, num_days, timeframe_str, feed):
    """
    Fetch historical bar data from Alpaca for multiple symbols in a single API call

    Parameters:
    -----------
    api : alpaca_trade_api.REST
        Alpaca API instance
    symbols : list
        List of stock symbols
    num_days : int
        Number of trading days to fetch
    timeframe_str : str
        Timeframe string (e.g., '1Min', '5Min')
    feed : str
        Data feed to use

    Returns:
    --------
    dict : Dictionary mapping symbol to list of bars
    """
    # Map timeframe string to TimeFrame object
    from alpaca_trade_api.rest import TimeFrameUnit

    timeframe_map = {
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "30Min": TimeFrame(30, TimeFrameUnit.Minute),
        "1Hour": TimeFrame.Hour,
        "1Day": TimeFrame.Day,
    }

    timeframe = timeframe_map.get(timeframe_str, TimeFrame.Minute)

    # Get trading calendar
    calendar = api.get_calendar()
    trading_days = []
    current_date = pd.Timestamp.now().date()

    for day in reversed(calendar):
        if pd.Timestamp(day.date).date() <= current_date:
            trading_days.append(day)
            if len(trading_days) >= num_days:
                break

    if not trading_days:
        raise ValueError("No trading days found")

    # Get start and end times
    start_date = trading_days[-1].date
    end_date = trading_days[0].date

    # Fetch bars for all symbols
    bars_dict = {}
    for symbol in symbols:
        try:
            bars = api.get_bars(
                symbol,
                timeframe,
                start=start_date.strftime("%Y-%m-%d"),
                end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"),
                feed=feed,
                adjustment="split",
                asof=None,
            )
            bars_dict[symbol] = list(bars)
        except Exception as e:
            print(f"Warning: Failed to fetch data for {symbol}: {e}")
            bars_dict[symbol] = []

    return bars_dict


def analyze_peaks_and_troughs(
    bars, window_len=11, lookahead=1, symbol="Unknown", timeframe="1Min"
):
    """
    Analyze peaks and troughs in the close price data

    Parameters:
    -----------
    bars : list
        List of bar data
    window_len : int
        Hanning filter window length
    lookahead : int
        Lookahead parameter for peak detection
    symbol : str
        Stock symbol

    Returns:
    --------
    dict : Analysis results
    """
    # Extract close prices and timestamps
    close_prices = np.array([bar.c for bar in bars])
    timestamps = np.array([bar.t for bar in bars])
    volumes = np.array([bar.v for bar in bars])
    vwap = np.array([bar.vw for bar in bars])
    trade_counts = np.array([bar.n for bar in bars])

    # Convert timestamps to NYC/EDT timezone
    ny_tz = pytz.timezone("America/New_York")
    timestamps_ny = np.array([ts.astimezone(ny_tz) for ts in timestamps])

    # Apply zero-phase Hanning filter
    filtered_prices = zero_phase_filter(close_prices, window_len)

    # Create time axis (minutes from start)
    start_time = timestamps[0]
    time_minutes = np.array([(t - start_time).total_seconds() / 60 for t in timestamps])

    # Detect peaks and troughs using Savitzky-Golay first derivative
    first_derivative = signal.savgol_filter(
        filtered_prices, delta=1, window_length=3, polyorder=2, deriv=1
    )

    # Find zero crossings (where derivative changes sign)
    zero_crossings = np.where(np.diff(np.sign(first_derivative)))[0]

    max_peak_indices = []
    min_peak_indices = []

    for i in zero_crossings:
        # Peak: derivative goes from positive to negative
        if first_derivative[i] > 0 and first_derivative[i + 1] < 0:
            start = max(0, i - lookahead)
            end = min(len(filtered_prices), i + 1 + lookahead)
            local_max_idx = start + np.argmax(filtered_prices[start:end])
            if local_max_idx not in max_peak_indices:
                max_peak_indices.append(local_max_idx)

        # Trough: derivative goes from negative to positive
        elif first_derivative[i] < 0 and first_derivative[i + 1] > 0:
            start = max(0, i - lookahead)
            end = min(len(filtered_prices), i + 1 + lookahead)
            local_min_idx = start + np.argmin(filtered_prices[start:end])
            if local_min_idx not in min_peak_indices:
                min_peak_indices.append(local_min_idx)

    max_peaks = [
        (time_minutes[i], filtered_prices[i]) for i in sorted(max_peak_indices)
    ]
    min_peaks = [
        (time_minutes[i], filtered_prices[i]) for i in sorted(min_peak_indices)
    ]

    # Convert peak times back to timestamps
    def minutes_to_timestamp(minutes):
        return start_time + timedelta(minutes=minutes)

    # Process peaks
    peaks_data = []
    for peak_time, peak_value in max_peaks:
        idx = np.argmin(np.abs(time_minutes - peak_time))
        peaks_data.append(
            {
                "time": timestamps[idx],
                "filtered_price": peak_value,
                "original_price": close_prices[idx],
                "volume": volumes[idx],
                "index": idx,
            }
        )

    # Process troughs
    troughs_data = []
    for trough_time, trough_value in min_peaks:
        idx = np.argmin(np.abs(time_minutes - trough_time))
        troughs_data.append(
            {
                "time": timestamps[idx],
                "filtered_price": trough_value,
                "original_price": close_prices[idx],
                "volume": volumes[idx],
                "index": idx,
            }
        )

    # Calculate statistics
    results = {
        "symbol": symbol,
        "timeframe": timeframe,
        "num_bars": len(bars),
        "time_range": {
            "start": timestamps[0].isoformat(),
            "end": timestamps[-1].isoformat(),
        },
        "price_range": {
            "min": float(np.min(close_prices)),
            "max": float(np.max(close_prices)),
            "mean": float(np.mean(close_prices)),
            "std": float(np.std(close_prices)),
        },
        "filter_params": {
            "window_type": "hanning",
            "window_length": window_len,
            "lookahead": lookahead,
        },
        "peaks": {"count": len(peaks_data), "data": peaks_data},
        "troughs": {"count": len(troughs_data), "data": troughs_data},
        "filtering_effect": {
            "max_deviation": float(np.max(np.abs(close_prices - filtered_prices))),
            "mean_deviation": float(np.mean(np.abs(close_prices - filtered_prices))),
            "smoothing_ratio": float(np.std(filtered_prices) / np.std(close_prices)),
        },
    }

    # Add cycle analysis if we have both peaks and troughs
    if peaks_data and troughs_data:
        # Calculate average cycle periods
        peak_times = [p["time"] for p in peaks_data]
        trough_times = [t["time"] for t in troughs_data]

        # Initialize cycle_analysis dict
        results["cycle_analysis"] = {}

        if len(peak_times) > 1:
            peak_periods = [
                (peak_times[i + 1] - peak_times[i]).total_seconds() / 60
                for i in range(len(peak_times) - 1)
            ]
            results["cycle_analysis"]["avg_peak_to_peak_minutes"] = float(
                np.mean(peak_periods)
            )
            results["cycle_analysis"]["std_peak_to_peak_minutes"] = float(
                np.std(peak_periods)
            )

        # Calculate average amplitude
        amplitudes = []
        for peak in peaks_data:
            # Find nearest trough
            nearest_troughs = sorted(
                troughs_data,
                key=lambda t: abs((t["time"] - peak["time"]).total_seconds()),
            )
            if nearest_troughs:
                amplitude = (
                    peak["filtered_price"] - nearest_troughs[0]["filtered_price"]
                )
                amplitudes.append(amplitude)

        if amplitudes:
            results["cycle_analysis"]["avg_amplitude"] = float(np.mean(amplitudes))
            results["cycle_analysis"]["avg_amplitude_pct"] = float(
                np.mean(amplitudes) / np.mean(close_prices) * 100
            )

    # Add support/resistance level analysis
    def analyze_support_resistance():
        """
        Analyze support and resistance levels based on peaks and troughs
        Returns most recent levels and distances from current price
        """
        current_price = close_prices[-1]
        current_index = len(close_prices) - 1

        # Sort peaks and troughs by time (most recent first)
        sorted_peaks = sorted(peaks_data, key=lambda x: x["time"], reverse=True)
        sorted_troughs = sorted(troughs_data, key=lambda x: x["time"], reverse=True)

        # Find most recent resistance (peak above current price)
        resistance_level = None
        for peak in sorted_peaks:
            if peak["original_price"] > current_price:
                samples_ago = current_index - peak["index"]
                resistance_level = {
                    "price": peak["original_price"],
                    "time": peak["time"],
                    "samples_ago": samples_ago,
                    "index": peak["index"],
                    "distance_pct": (
                        (peak["original_price"] - current_price) / current_price
                    )
                    * 100,
                }
                break

        # Find most recent support (trough below current price)
        support_level = None
        for trough in sorted_troughs:
            if trough["original_price"] < current_price:
                samples_ago = current_index - trough["index"]
                support_level = {
                    "price": trough["original_price"],
                    "time": trough["time"],
                    "samples_ago": samples_ago,
                    "index": trough["index"],
                    "distance_pct": (
                        (current_price - trough["original_price"]) / current_price
                    )
                    * 100,
                }
                break

        # Find all significant levels within reasonable distance
        significant_resistance = []
        significant_support = []

        # Look for resistance levels within 10% above current price
        for peak in sorted_peaks:
            if peak["original_price"] > current_price:
                distance_pct = (
                    (peak["original_price"] - current_price) / current_price
                ) * 100
                if distance_pct <= 10:  # Within 10% above
                    samples_ago = current_index - peak["index"]
                    significant_resistance.append(
                        {
                            "price": peak["original_price"],
                            "time": peak["time"],
                            "samples_ago": samples_ago,
                            "index": peak["index"],
                            "distance_pct": distance_pct,
                        }
                    )

        # Look for support levels within 10% below current price
        for trough in sorted_troughs:
            if trough["original_price"] < current_price:
                distance_pct = (
                    (current_price - trough["original_price"]) / current_price
                ) * 100
                if distance_pct <= 10:  # Within 10% below
                    samples_ago = current_index - trough["index"]
                    significant_support.append(
                        {
                            "price": trough["original_price"],
                            "time": trough["time"],
                            "samples_ago": samples_ago,
                            "index": trough["index"],
                            "distance_pct": distance_pct,
                        }
                    )

        # Sort by proximity to current price
        significant_resistance.sort(key=lambda x: x["distance_pct"])
        significant_support.sort(key=lambda x: x["distance_pct"])

        return {
            "current_price": current_price,
            "current_index": current_index,
            "nearest_resistance": resistance_level,
            "nearest_support": support_level,
            "significant_resistance": significant_resistance[:3],  # Top 3 closest
            "significant_support": significant_support[:3],  # Top 3 closest
        }

    # Store this function in results for later use
    results["analyze_support_resistance"] = analyze_support_resistance

    # Add buy/sell pairs analysis with cash management
    def calculate_trading_pairs(initial_cash):
        buy_sell_pairs = []
        current_cash = initial_cash
        trading_stopped = False

        if troughs_data and peaks_data:
            # Sort by time to ensure proper ordering
            sorted_troughs = sorted(troughs_data, key=lambda x: x["time"])
            sorted_peaks = sorted(peaks_data, key=lambda x: x["time"])

            for trough in sorted_troughs:
                if trading_stopped:
                    break

                # Find the next peak after this trough
                next_peaks = [p for p in sorted_peaks if p["time"] > trough["time"]]
                if next_peaks:
                    peak = next_peaks[0]

                    # Calculate shares we can buy (integer shares only)
                    shares = int(current_cash / trough["original_price"])
                    if shares == 0:
                        continue  # Not enough cash for even 1 share

                    # Calculate actual cash used and remaining
                    cash_used = shares * trough["original_price"]
                    remaining_cash = current_cash - cash_used

                    # Calculate proceeds from sale
                    sale_proceeds = shares * peak["original_price"]

                    # Calculate profit/loss
                    profit = sale_proceeds - cash_used
                    percent_profit = (profit / cash_used) * 100

                    # Update cash for next trade
                    new_cash = remaining_cash + sale_proceeds

                    buy_sell_pairs.append(
                        {
                            "buy_time": trough["time"],
                            "buy_price": trough["original_price"],
                            "buy_index": trough["index"],
                            "sell_time": peak["time"],
                            "sell_price": peak["original_price"],
                            "sell_index": peak["index"],
                            "shares": shares,
                            "cash_used": cash_used,
                            "remaining_cash": remaining_cash,
                            "sale_proceeds": sale_proceeds,
                            "profit": profit,
                            "percent_profit": percent_profit,
                            "new_cash": new_cash,
                            "hold_time_minutes": (
                                peak["time"] - trough["time"]
                            ).total_seconds()
                            / 60,
                        }
                    )

                    # Stop trading if this was a losing trade (wash sale protection)
                    if profit < 0:
                        trading_stopped = True
                    else:
                        current_cash = new_cash

        return buy_sell_pairs, current_cash, trading_stopped

    # Store this function in results for later use
    results["calculate_trading_pairs"] = calculate_trading_pairs

    # Store raw data for plotting
    results["raw_data"] = {
        "timestamps": timestamps,
        "timestamps_ny": timestamps_ny,
        "close_prices": close_prices,
        "filtered_prices": filtered_prices,
        "volumes": volumes,
        "vwap": vwap,
        "trade_counts": trade_counts,
    }

    return results


def generate_report(results, initial_cash=1000.0):
    """
    Generate a report from the analysis results
    """
    symbol = results["symbol"]

    # Calculate trading pairs with the provided initial cash
    if "calculate_trading_pairs" in results:
        trades, final_cash, trading_stopped = results["calculate_trading_pairs"](
            initial_cash
        )

        # Calculate trading statistics
        winning_trades = sum(1 for trade in trades if trade["profit"] >= 0)
        losing_trades = sum(1 for trade in trades if trade["profit"] < 0)
        total_profit = final_cash - initial_cash
        cumulative_percent_change = (total_profit / initial_cash) * 100

        # Store trading analysis in results
        results["trading_analysis"] = {
            "initial_cash": initial_cash,
            "final_cash": final_cash,
            "total_profit": total_profit,
            "cumulative_percent_change": cumulative_percent_change,
            "trades": trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "trading_stopped": trading_stopped,
        }

        # Add support/resistance analysis
        if "analyze_support_resistance" in results:
            sr_analysis = results["analyze_support_resistance"]()
            results["support_resistance"] = sr_analysis
        report = []
        report.append("=" * 80)
        report.append(f"PEAK AND TROUGH ANALYSIS REPORT - {symbol}")
        report.append("=" * 80)
        report.append(
            f"\nAnalysis Period: {results['time_range']['start']} to {results['time_range']['end']}"
        )
        report.append(f"Total Bars Analyzed: {results['num_bars']}")

        report.append("\nPrice Statistics:")
        report.append(
            f"  Range: ${results['price_range']['min']:.2f} - ${results['price_range']['max']:.2f}"
        )
        report.append(f"  Mean: ${results['price_range']['mean']:.2f}")
        report.append(f"  Std Dev: ${results['price_range']['std']:.2f}")

        report.append("\nFilter Parameters:")
        report.append(f"  Type: Zero-phase {results['filter_params']['window_type']}")
        report.append(f"  Window Length: {results['filter_params']['window_length']}")
        report.append(f"  Lookahead: {results['filter_params']['lookahead']}")

        report.append("\nFiltering Effect:")
        report.append(
            f"  Max Deviation: ${results['filtering_effect']['max_deviation']:.4f}"
        )
        report.append(
            f"  Mean Deviation: ${results['filtering_effect']['mean_deviation']:.4f}"
        )
        report.append(
            f"  Smoothing Ratio: {results['filtering_effect']['smoothing_ratio']:.2%}"
        )

        report.append("\nPeak Detection Results:")
        report.append(f"  Peaks Found: {results['peaks']['count']}")
        report.append(f"  Troughs Found: {results['troughs']['count']}")

        if "cycle_analysis" in results:
            report.append("\nCycle Analysis:")
            if "avg_peak_to_peak_minutes" in results["cycle_analysis"]:
                report.append(
                    f"  Avg Peak-to-Peak: {results['cycle_analysis']['avg_peak_to_peak_minutes']:.1f} minutes"
                )
                report.append(
                    f"  Std Peak-to-Peak: {results['cycle_analysis']['std_peak_to_peak_minutes']:.1f} minutes"
                )
            report.append(
                f"  Avg Amplitude: ${results['cycle_analysis']['avg_amplitude']:.2f} ({results['cycle_analysis']['avg_amplitude_pct']:.2f}%)"
            )

        # Add support/resistance analysis section
        if "support_resistance" in results:
            sr = results["support_resistance"]
            report.append("\nSupport and Resistance Analysis:")
            report.append(f"  Current Price: ${sr['current_price']:.2f}")

            if sr["nearest_resistance"]:
                res = sr["nearest_resistance"]
                report.append(
                    f"  Nearest Resistance: ${res['price']:.2f} ({res['samples_ago']} samples ago, +{res['distance_pct']:.2f}%)"
                )
                report.append(f"    Time: {res['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                report.append("  Nearest Resistance: None found above current price")

            if sr["nearest_support"]:
                sup = sr["nearest_support"]
                report.append(
                    f"  Nearest Support: ${sup['price']:.2f} ({sup['samples_ago']} samples ago, -{sup['distance_pct']:.2f}%)"
                )
                report.append(f"    Time: {sup['time'].strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                report.append("  Nearest Support: None found below current price")

            # Show significant levels
            if sr["significant_resistance"]:
                report.append("  Key Resistance Levels:")
                for i, res in enumerate(sr["significant_resistance"]):
                    report.append(
                        f"    R{i + 1}: ${res['price']:.2f} ({res['samples_ago']} samples ago, +{res['distance_pct']:.2f}%)"
                    )

            if sr["significant_support"]:
                report.append("  Key Support Levels:")
                for i, sup in enumerate(sr["significant_support"]):
                    report.append(
                        f"    S{i + 1}: ${sup['price']:.2f} ({sup['samples_ago']} samples ago, -{sup['distance_pct']:.2f}%)"
                    )

        # Add trading analysis section
        if "trading_analysis" in results:
            ta = results["trading_analysis"]
            report.append(
                f"\nTrading Analysis (Initial Capital: ${ta['initial_cash']:.2f}):"
            )
            report.append(f"  Total Trades Executed: {len(ta['trades'])}")
            report.append(f"  Winning Trades: {ta['winning_trades']}")
            report.append(f"  Losing Trades: {ta['losing_trades']}")
            report.append(
                f"  Trading Stopped: {'Yes (Wash Sale Protection)' if ta['trading_stopped'] else 'No'}"
            )
            report.append(f"  Beginning Capital: ${ta['initial_cash']:.2f}")
            report.append(f"  Ending Capital: ${ta['final_cash']:.2f}")
            report.append(f"  Total Profit/Loss: ${ta['total_profit']:.2f}")
            report.append(
                f"  Cumulative Percent Change: {ta['cumulative_percent_change']:.2f}%"
            )

            if ta["trades"]:
                avg_hold_time = sum(
                    trade["hold_time_minutes"] for trade in ta["trades"]
                ) / len(ta["trades"])
                report.append(f"  Average Hold Time: {avg_hold_time:.1f} minutes")

            report.append("\nIndividual Trades:")
            for i, trade in enumerate(ta["trades"]):
                status = "WIN" if trade["profit"] >= 0 else "LOSS"
                report.append(f"  Trade {i + 1} ({status}):")
                report.append(
                    f"    Buy:  {trade['buy_time'].strftime('%Y-%m-%d %H:%M:%S')} @ ${trade['buy_price']:.2f}"
                )
                report.append(
                    f"    Shares: {trade['shares']:,} | Cash Used: ${trade['cash_used']:.2f}"
                )
                report.append(
                    f"    Sell: {trade['sell_time'].strftime('%Y-%m-%d %H:%M:%S')} @ ${trade['sell_price']:.2f}"
                )
                report.append(
                    f"    Proceeds: ${trade['sale_proceeds']:.2f} | Profit: ${trade['profit']:.2f} ({trade['percent_profit']:.2f}%)"
                )
                report.append(f"    New Cash Balance: ${trade['new_cash']:.2f}")
                report.append(
                    f"    Hold Time: {trade['hold_time_minutes']:.1f} minutes"
                )

        # List peaks
        report.append("\nDetected Peaks:")
        for i, peak in enumerate(results["peaks"]["data"]):
            report.append(
                f"  Peak {i + 1}: {peak['time'].strftime('%Y-%m-%d %H:%M:%S')} - "
                f"Price: ${peak['original_price']:.2f} (filtered: ${peak['filtered_price']:.2f}) - "
                f"Volume: {peak['volume']:,}"
            )

        # List troughs
        report.append("\nDetected Troughs:")
        for i, trough in enumerate(results["troughs"]["data"]):
            report.append(
                f"  Trough {i + 1}: {trough['time'].strftime('%Y-%m-%d %H:%M:%S')} - "
                f"Price: ${trough['original_price']:.2f} (filtered: ${trough['filtered_price']:.2f}) - "
                f"Volume: {trough['volume']:,}"
            )

        return "\n".join(report)

    return "\n".join(report)


def process_multiple_stocks(
    symbols, api, num_days, timeframe_str, feed, window_len, lookahead, initial_cash
):
    """
    Process multiple stocks and return summary results for tabular report

    Parameters:
    -----------
    symbols : list
        List of stock symbols to analyze
    api : alpaca_trade_api.REST
        Alpaca API instance
    num_days : int
        Number of trading days to fetch
    timeframe_str : str
        Timeframe string
    feed : str
        Data feed to use
    window_len : int
        Hanning filter window length
    lookahead : int
        Peak detection lookahead
    initial_cash : float
        Initial cash for trading simulation

    Returns:
    --------
    list : List of result dictionaries for each symbol
    """
    print(f"Fetching data for {len(symbols)} symbols...")
    bars_dict = fetch_bars_multiple(api, symbols, num_days, timeframe_str, feed)

    results = []
    for symbol in symbols:
        bars = bars_dict.get(symbol, [])
        if not bars:
            print(f"No data available for {symbol}")
            continue

        print(f"Processing {symbol}... ({len(bars)} bars)")

        try:
            # Analyze peaks and troughs
            analysis = analyze_peaks_and_troughs(
                bars, window_len, lookahead, symbol, timeframe_str
            )

            # Calculate trading results
            if "calculate_trading_pairs" in analysis:
                trades, final_cash, trading_stopped = analysis[
                    "calculate_trading_pairs"
                ](initial_cash)

                # Calculate summary statistics
                total_profit = final_cash - initial_cash
                percent_return = (total_profit / initial_cash) * 100
                winning_trades = sum(1 for trade in trades if trade["profit"] >= 0)
                losing_trades = sum(1 for trade in trades if trade["profit"] < 0)

                avg_hold_time = 0
                if trades:
                    avg_hold_time = sum(
                        trade["hold_time_minutes"] for trade in trades
                    ) / len(trades)

                # Calculate support/resistance info
                sr_info = {}
                if "analyze_support_resistance" in analysis:
                    sr_data = analysis["analyze_support_resistance"]()
                    sr_info = {
                        "current_price": sr_data["current_price"],
                        "nearest_resistance_price": (
                            sr_data["nearest_resistance"]["price"]
                            if sr_data["nearest_resistance"]
                            else None
                        ),
                        "nearest_resistance_samples": (
                            sr_data["nearest_resistance"]["samples_ago"]
                            if sr_data["nearest_resistance"]
                            else None
                        ),
                        "nearest_support_price": (
                            sr_data["nearest_support"]["price"]
                            if sr_data["nearest_support"]
                            else None
                        ),
                        "nearest_support_samples": (
                            sr_data["nearest_support"]["samples_ago"]
                            if sr_data["nearest_support"]
                            else None
                        ),
                        "resistance_distance_pct": (
                            sr_data["nearest_resistance"]["distance_pct"]
                            if sr_data["nearest_resistance"]
                            else None
                        ),
                        "support_distance_pct": (
                            sr_data["nearest_support"]["distance_pct"]
                            if sr_data["nearest_support"]
                            else None
                        ),
                    }

                # Store summary results
                results.append(
                    {
                        "symbol": symbol,
                        "bars": len(bars),
                        "peaks": analysis["peaks"]["count"],
                        "troughs": analysis["troughs"]["count"],
                        "trades": len(trades),
                        "winners": winning_trades,
                        "losers": losing_trades,
                        "initial_cash": initial_cash,
                        "final_cash": final_cash,
                        "profit": total_profit,
                        "percent_return": percent_return,
                        "avg_hold_time": avg_hold_time,
                        "trading_stopped": trading_stopped,
                        "smoothing_ratio": analysis["filtering_effect"][
                            "smoothing_ratio"
                        ],
                        **sr_info,  # Add support/resistance info
                    }
                )

        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            continue

    return results


def generate_tabular_report(results, timeframe_str, num_days, window_len, lookahead):
    """
    Generate a professional tabular report from multiple stock analysis results

    Parameters:
    -----------
    results : list
        List of result dictionaries from process_multiple_stocks
    timeframe_str : str
        Timeframe used for analysis
    num_days : int
        Number of days analyzed
    window_len : int
        Filter window length
    lookahead : int
        Peak detection lookahead

    Returns:
    --------
    str : Formatted tabular report
    """
    if not results:
        return "No valid results to display"

    # Sort results by return percentage (descending) for better presentation
    sorted_results = sorted(results, key=lambda x: x["percent_return"], reverse=True)

    # Header with professional styling
    report = []
    report.append("┏" + "━" * 180 + "┓")
    report.append(
        "┃"
        + " " * 65
        + "📊 PEAK/TROUGH TRADING ANALYSIS WITH SUPPORT/RESISTANCE 📊"
        + " " * 52
        + "┃"
    )
    report.append("┗" + "━" * 180 + "┛")
    report.append("")
    report.append(
        f"📈 Analysis Period: {num_days} day(s) | Timeframe: {timeframe_str} | Filter Window: {window_len} | Lookahead: {lookahead}"
    )
    report.append("")

    # Professional table with precise column widths
    # Columns: Symbol(8) Current$(9) Resist$(9) R-Samp(7) Supp$(9) S-Samp(7) Peaks(6) Troughs(8) Trades(7) W/L(6) Profit(11) Return%(9)
    header_line = (
        "┌"
        + "─" * 8
        + "┬"
        + "─" * 9
        + "┬"
        + "─" * 9
        + "┬"
        + "─" * 7
        + "┬"
        + "─" * 9
        + "┬"
        + "─" * 7
        + "┬"
        + "─" * 6
        + "┬"
        + "─" * 8
        + "┬"
        + "─" * 7
        + "┬"
        + "─" * 6
        + "┬"
        + "─" * 11
        + "┬"
        + "─" * 9
        + "┐"
    )
    report.append(header_line)

    header = f"│{'Symbol':^8}│{'Current$':^9}│{'Resist$':^9}│{'R-Samp':^7}│{'Supp$':^9}│{'S-Samp':^7}│{'Peaks':^6}│{'Troughs':^8}│{'Trades':^7}│{'W/L':^6}│{'Profit':^11}│{'Return%':^9}│"
    report.append(header)

    separator_line = (
        "├"
        + "─" * 8
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 6
        + "┼"
        + "─" * 8
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 6
        + "┼"
        + "─" * 11
        + "┼"
        + "─" * 9
        + "┤"
    )
    report.append(separator_line)

    # Table rows with performance-based coloring indicators
    total_initial = 0
    total_final = 0
    total_trades = 0
    total_winners = 0
    total_losers = 0

    for result in sorted_results:
        symbol = result["symbol"]
        peaks = result["peaks"]
        troughs = result["troughs"]
        trades = result["trades"]
        winners = result["winners"]
        losers = result["losers"]
        profit = result["profit"]
        percent_return = result["percent_return"]

        # Support/Resistance data
        current_price = result.get("current_price", 0)
        resistance_price = result.get("nearest_resistance_price")
        resistance_samples = result.get("nearest_resistance_samples")
        support_price = result.get("nearest_support_price")
        support_samples = result.get("nearest_support_samples")

        # Performance indicator
        if percent_return >= 10:
            perf_indicator = "🟢"  # Excellent
        elif percent_return >= 5:
            perf_indicator = "🔵"  # Good
        elif percent_return >= 2:
            perf_indicator = "🟡"  # Fair
        elif percent_return > 0:
            perf_indicator = "🟠"  # Poor
        else:
            perf_indicator = "🔴"  # Loss

        # Format row with professional styling
        symbol_display = f"{perf_indicator}{symbol}"
        current_display = f"${current_price:.2f}" if current_price > 0 else "─"
        resistance_display = f"${resistance_price:.2f}" if resistance_price else "─"
        resist_samples_display = f"{resistance_samples}" if resistance_samples else "─"
        support_display = f"${support_price:.2f}" if support_price else "─"
        support_samples_display = f"{support_samples}" if support_samples else "─"
        wl_display = f"{winners}/{losers}"
        profit_display = f"${profit:+.2f}"
        return_display = f"{percent_return:+.2f}%"

        row = f"│{symbol_display:<8}│{current_display:>9}│{resistance_display:>9}│{resist_samples_display:>7}│{support_display:>9}│{support_samples_display:>7}│{peaks:>6}│{troughs:>8}│{trades:>7}│{wl_display:>6}│{profit_display:>11}│{return_display:>9}│"
        report.append(row)

        # Accumulate totals
        total_initial += result["initial_cash"]
        total_final += result["final_cash"]
        total_trades += trades
        total_winners += winners
        total_losers += losers

    # Summary section
    total_profit = total_final - total_initial
    total_return = (total_profit / total_initial) * 100 if total_initial > 0 else 0

    summary_line = (
        "├"
        + "─" * 8
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 6
        + "┼"
        + "─" * 8
        + "┼"
        + "─" * 7
        + "┼"
        + "─" * 6
        + "┼"
        + "─" * 11
        + "┼"
        + "─" * 9
        + "┤"
    )
    report.append(summary_line)

    total_wl = f"{total_winners}/{total_losers}"
    total_profit_display = f"${total_profit:+.2f}"
    total_return_display = f"{total_return:+.2f}%"

    summary_row = f"│{'📊TOTAL':<8}│{'─':>9}│{'─':>9}│{'─':>7}│{'─':>9}│{'─':>7}│{'─':>6}│{'─':>8}│{total_trades:>7}│{total_wl:>6}│{total_profit_display:>11}│{total_return_display:>9}│"
    report.append(summary_row)

    bottom_line = (
        "└"
        + "─" * 8
        + "┴"
        + "─" * 9
        + "┴"
        + "─" * 9
        + "┴"
        + "─" * 7
        + "┴"
        + "─" * 9
        + "┴"
        + "─" * 7
        + "┴"
        + "─" * 6
        + "┴"
        + "─" * 8
        + "┴"
        + "─" * 7
        + "┴"
        + "─" * 6
        + "┴"
        + "─" * 11
        + "┴"
        + "─" * 9
        + "┘"
    )
    report.append(bottom_line)

    # Professional statistics section
    report.append("")
    report.append("┏" + "━" * 60 + "┓")
    report.append("┃" + " " * 20 + "📋 PORTFOLIO SUMMARY" + " " * 19 + "┃")
    report.append("┗" + "━" * 60 + "┛")

    win_rate = (total_winners / total_trades * 100) if total_trades > 0 else 0

    report.append(f"📊 Symbols Analyzed     : {len(results):>8}")
    report.append(f"⚡ Total Trades        : {total_trades:>8}")
    report.append(f"🎯 Win Rate           : {win_rate:>7.1f}%")
    report.append(f"💰 Portfolio Return   : {total_return:>+7.2f}%")
    report.append(f"💵 Total P&L          : ${total_profit:>+.2f}")

    # Performance rankings
    if results:
        best_performer = max(sorted_results, key=lambda x: x["percent_return"])
        worst_performer = min(sorted_results, key=lambda x: x["percent_return"])
        most_active = max(sorted_results, key=lambda x: x["trades"])

        report.append("")
        report.append("🏆 Top Performers:")
        report.append(
            f"   Best Return     : {best_performer['symbol']} ({best_performer['percent_return']:+.2f}%)"
        )
        report.append(
            f"   Most Active     : {most_active['symbol']} ({most_active['trades']} trades)"
        )
        report.append(
            f"   Worst Performer : {worst_performer['symbol']} ({worst_performer['percent_return']:+.2f}%)"
        )

    # Performance distribution
    excellent = sum(1 for r in results if r["percent_return"] >= 10)
    good = sum(1 for r in results if 5 <= r["percent_return"] < 10)
    fair = sum(1 for r in results if 2 <= r["percent_return"] < 5)
    poor = sum(1 for r in results if 0 < r["percent_return"] < 2)
    losses = sum(1 for r in results if r["percent_return"] <= 0)

    report.append("")
    report.append("📈 Performance Distribution:")
    report.append(f"   🟢 Excellent (≥10%) : {excellent:>3} stocks")
    report.append(f"   🔵 Good (5-10%)     : {good:>3} stocks")
    report.append(f"   🟡 Fair (2-5%)      : {fair:>3} stocks")
    report.append(f"   🟠 Poor (0-2%)      : {poor:>3} stocks")
    report.append(f"   🔴 Losses (≤0%)     : {losses:>3} stocks")

    # Support/Resistance Summary
    stocks_with_resistance = sum(
        1 for r in results if r.get("nearest_resistance_price")
    )
    stocks_with_support = sum(1 for r in results if r.get("nearest_support_price"))

    if stocks_with_resistance > 0 or stocks_with_support > 0:
        report.append("")
        report.append("🎯 Support/Resistance Summary:")
        report.append(f"   📊 Stocks with Resistance: {stocks_with_resistance:>3}")
        report.append(f"   📊 Stocks with Support   : {stocks_with_support:>3}")

        # Find stocks with closest resistance/support
        resistance_stocks = [
            (r["symbol"], r["nearest_resistance_samples"])
            for r in results
            if r.get("nearest_resistance_samples")
        ]
        support_stocks = [
            (r["symbol"], r["nearest_support_samples"])
            for r in results
            if r.get("nearest_support_samples")
        ]

        if resistance_stocks:
            closest_resistance = min(resistance_stocks, key=lambda x: x[1])
            report.append(
                f"   🔴 Closest Resistance    : {closest_resistance[0]} ({closest_resistance[1]} samples)"
            )

        if support_stocks:
            closest_support = min(support_stocks, key=lambda x: x[1])
            report.append(
                f"   🟢 Closest Support      : {closest_support[0]} ({closest_support[1]} samples)"
            )

    # Column explanations
    report.append("")
    report.append("📋 Column Explanations:")
    report.append("   Current$ : Current close price")
    report.append("   Resist$  : Nearest resistance level (peak above current)")
    report.append("   R-Samp   : Samples ago when resistance was formed")
    report.append("   Supp$    : Nearest support level (trough below current)")
    report.append("   S-Samp   : Samples ago when support was formed")
    report.append("   Profit   : Trading simulation profit/loss")
    report.append("   Return%  : Percentage return on investment")

    return "\n".join(report)


def get_price_format(price):
    """
    Determine the appropriate decimal places based on price level

    Parameters:
    -----------
    price : float
        The price value

    Returns:
    --------
    str : Format string for the price
    """
    if price < 1:
        return ".4f"  # 4 decimal places for prices under $1
    elif price < 10:
        return ".3f"  # 3 decimal places for prices under $10
    else:
        return ".2f"  # 2 decimal places for prices $10 and above


def plot_results(results, save_path=None):
    """
    Create a visualization of the analysis
    
    Parameters:
    -----------
    results : dict
        Analysis results from analyze_peaks_and_troughs
    save_path : str, optional
        Path to save the PNG file. If None, displays the plot
    
    Returns:
    --------
    str : Path to saved PNG file if save_path is provided, None otherwise
    """
    import os
    from datetime import datetime
    
    # If save_path is True (from command line), generate a path in /tmp
    if save_path is True:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol = results.get('symbol', 'UNKNOWN')
        timeframe = results.get('timeframe', '1Min')
        save_path = f"/tmp/{symbol}_{timeframe}_{timestamp}.png"
    
    # Set backend for headless operation if saving
    if save_path:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
    
    # Set dark theme style
    plt.style.use("dark_background")

    # Create figure with dark background - WIDER aspect ratio for modal display
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 8), height_ratios=[3, 1])
    fig.patch.set_facecolor("#0f0f0f")
    ax1.set_facecolor("#1a1a1a")
    ax2.set_facecolor("#1a1a1a")

    # Extract data
    timestamps = results["raw_data"]["timestamps"]
    timestamps_ny = results["raw_data"]["timestamps_ny"]
    close_prices = results["raw_data"]["close_prices"]
    filtered_prices = results["raw_data"]["filtered_prices"]
    volumes = results["raw_data"]["volumes"]
    vwap = results["raw_data"]["vwap"]
    trade_counts = results["raw_data"]["trade_counts"]

    # Create sample indices
    samples = np.arange(len(close_prices))

    # Create sample to time mapping for annotations
    # For 1Day timeframe, show date with year; for minute timeframes, show date and time
    if results.get("timeframe") == "1Day":
        time_map = {i: ts.strftime("%m-%d-%y") for i, ts in enumerate(timestamps_ny)}
    else:
        # For minute-level timeframes, include date and time
        time_map = {i: ts.strftime("%m-%d %H:%M") for i, ts in enumerate(timestamps_ny)}

    # Plot prices and VWAP using sample indices with vibrant colors
    ax1.plot(
        samples,
        close_prices,
        color="#00D9FF",
        alpha=0.9,
        label="Close Price",
        linewidth=2,
        zorder=3,
    )
    ax1.plot(
        samples,
        filtered_prices,
        color="#FF006E",
        label="Filtered (Hanning)",
        linewidth=2.5,
        zorder=4,
    )
    ax1.plot(
        samples,
        vwap,
        color="#FFBE0B",
        alpha=0.9,
        label="VWAP",
        linewidth=2,
        linestyle="--",
        zorder=2,
    )

    # Mark peaks with glowing effect and smart positioning
    for i, peak in enumerate(results["peaks"]["data"]):
        # Outer glow
        ax1.scatter(
            peak["index"],
            peak["original_price"],
            s=300,
            color="#00FF41",
            alpha=0.3,
            zorder=5,
        )
        # Inner marker
        ax1.scatter(
            peak["index"],
            peak["original_price"],
            s=150,
            color="#00FF41",
            marker="^",
            edgecolors="white",
            linewidth=2,
            label="Peak" if i == 0 else "",
            zorder=6,
        )

        # Smart annotation positioning to avoid overlap
        # Alternate between different positions for closely spaced peaks
        y_offset = 25 + (i % 3) * 10  # Vary vertical offset
        x_offset = (i % 2) * 15 - 7.5  # Slight horizontal offset alternation

        # Stylish annotation with improved spacing
        price_fmt = get_price_format(peak["original_price"])
        ax1.annotate(
            f"${peak['original_price']:{price_fmt}}\n{time_map[peak['index']]}",
            (peak["index"], peak["original_price"]),
            textcoords="offset points",
            xytext=(x_offset, y_offset),
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="white",
            bbox=dict(
                boxstyle="round,pad=0.7",
                facecolor="#00FF41",
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            ),
            arrowprops=dict(arrowstyle="-", color="#00FF41", alpha=0.6, linewidth=1),
        )

    # Mark troughs with glowing effect and smart positioning
    for i, trough in enumerate(results["troughs"]["data"]):
        # Outer glow
        ax1.scatter(
            trough["index"],
            trough["original_price"],
            s=300,
            color="#FF006E",
            alpha=0.3,
            zorder=5,
        )
        # Inner marker
        ax1.scatter(
            trough["index"],
            trough["original_price"],
            s=150,
            color="#FF006E",
            marker="v",
            edgecolors="white",
            linewidth=2,
            label="Trough" if i == 0 else "",
            zorder=6,
        )

        # Smart annotation positioning to avoid overlap
        # Alternate between different positions for closely spaced troughs
        y_offset = -35 - (i % 3) * 10  # Vary vertical offset (negative for below)
        x_offset = (i % 2) * 15 - 7.5  # Slight horizontal offset alternation

        # Stylish annotation with improved spacing
        price_fmt = get_price_format(trough["original_price"])
        ax1.annotate(
            f"${trough['original_price']:{price_fmt}}\n{time_map[trough['index']]}",
            (trough["index"], trough["original_price"]),
            textcoords="offset points",
            xytext=(x_offset, y_offset),
            ha="center",
            fontsize=8,
            fontweight="bold",
            color="white",
            bbox=dict(
                boxstyle="round,pad=0.7",
                facecolor="#FF006E",
                alpha=0.8,
                edgecolor="white",
                linewidth=1.5,
            ),
            arrowprops=dict(arrowstyle="-", color="#FF006E", alpha=0.6, linewidth=1),
        )

    # Format first subplot with style
    current_price = close_prices[-1]
    current_price_fmt = get_price_format(current_price)
    title_text = f"{results['symbol']} - Peak and Trough Analysis with VWAP"
    subtitle_text = f"Current: ${current_price:{current_price_fmt}} | Window={results['filter_params']['window_length']} | {timestamps_ny[0].strftime('%Y-%m-%d %H:%M')} to {timestamps_ny[-1].strftime('%Y-%m-%d %H:%M')} EDT"

    ax1.text(
        0.5,
        1.06,
        title_text,
        transform=ax1.transAxes,
        fontsize=14,
        fontweight="bold",
        ha="center",
        color="white",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#1a1a1a",
            edgecolor="#00D9FF",
            linewidth=1.5,
        ),
    )
    ax1.text(
        0.5,
        1.01,
        subtitle_text,
        transform=ax1.transAxes,
        fontsize=10,
        ha="center",
        color="#888888",
    )

    ax1.set_ylabel("Price ($)", fontsize=14, fontweight="bold", color="white")
    ax1.set_xlabel("Sample Index", fontsize=14, fontweight="bold", color="white")

    # Style the legend
    legend = ax1.legend(
        loc="upper left", fontsize=11, frameon=True, fancybox=True, shadow=True
    )
    legend.get_frame().set_facecolor("#1a1a1a")
    legend.get_frame().set_edgecolor("#444444")
    legend.get_frame().set_linewidth(1.5)

    # Enhanced grid styling for better visibility
    ax1.grid(True, alpha=0.4, linestyle="--", color="#555555", linewidth=0.8)
    ax1.grid(True, alpha=0.3, linestyle=":", which="minor", color="#444444")

    # Add subtle background gradient effect
    ax1.axhspan(
        ax1.get_ylim()[0], ax1.get_ylim()[1], alpha=0.02, color="#00D9FF", zorder=0
    )

    # Spine styling
    for spine in ax1.spines.values():
        spine.set_edgecolor("#444444")
        spine.set_linewidth(1.5)

    # Tick styling
    ax1.tick_params(colors="#CCCCCC", which="both")

    # Calculate sigma values for volume and trade count
    volume_mean = np.mean(volumes)
    volume_std = np.std(volumes)
    volume_sigma = (volumes - volume_mean) / volume_std

    trade_mean = np.mean(trade_counts)
    trade_std = np.std(trade_counts)
    trade_sigma = (trade_counts - trade_mean) / trade_std

    # Plot volume and trade count with gradient effect
    ax2_twin = ax2.twinx()

    # Create gradient effect for volume bars with better visibility
    colors = [
        "#FF00FF" if v > 2 else "#00BFFF" if v > 0 else "#00CED1" for v in volume_sigma
    ]
    bars = ax2.bar(
        samples,
        volume_sigma,
        width=0.8,
        alpha=0.9,
        edgecolor="#FFFFFF",
        linewidth=0.3,
        label="Volume (σ)",
    )

    # Set individual bar colors
    for bar, color, v in zip(bars, colors, volume_sigma):
        bar.set_facecolor(color)
        if v > 2:  # Add glow effect for high volume
            bar.set_linewidth(1.5)
            bar.set_alpha(1.0)

    # Trade count line with enhanced glow effect
    ax2_twin.plot(
        samples,
        trade_sigma,
        color="#FFA500",
        linewidth=3,
        alpha=1.0,
        label="Trade Count (σ)",
        zorder=10,
    )
    ax2_twin.plot(
        samples, trade_sigma, color="#FFFF00", linewidth=6, alpha=0.4, zorder=9
    )  # Glow effect

    # Format second subplot with style
    ax2.text(
        0.5,
        1.05,
        "Normalized Volume and Trade Count (Standard Deviations)",
        transform=ax2.transAxes,
        fontsize=14,
        fontweight="bold",
        ha="center",
        color="white",
    )

    ax2.set_ylabel("Volume (σ)", fontsize=12, fontweight="bold", color="#00BFFF")
    ax2_twin.set_ylabel(
        "Trade Count (σ)", fontsize=12, fontweight="bold", color="#FFA500"
    )
    ax2.set_xlabel("Sample Index", fontsize=14, fontweight="bold", color="white")

    # Tick styling
    ax2.tick_params(axis="y", labelcolor="#00BFFF", labelsize=10)
    ax2_twin.tick_params(axis="y", labelcolor="#FFA500", labelsize=10)
    ax2.tick_params(axis="x", labelcolor="#CCCCCC", labelsize=10)

    # Add horizontal reference lines with better visibility
    ax2.axhline(y=0, color="#888888", linestyle="-", alpha=1.0, linewidth=1.5, zorder=5)
    ax2.axhline(
        y=2, color="#00FF41", linestyle="--", alpha=0.8, linewidth=1.5, zorder=5
    )
    ax2.axhline(
        y=-2, color="#FF006E", linestyle="--", alpha=0.8, linewidth=1.5, zorder=5
    )

    # Add sigma level annotations
    ax2.text(
        len(samples) - 5,
        2.1,
        "+2σ",
        ha="right",
        va="bottom",
        color="#00FF41",
        fontsize=9,
        fontweight="bold",
    )
    ax2.text(
        len(samples) - 5,
        -1.9,
        "-2σ",
        ha="right",
        va="top",
        color="#FF006E",
        fontsize=9,
        fontweight="bold",
    )

    # Enhanced grid styling for volume subplot
    ax2.grid(True, alpha=0.4, linestyle="--", color="#555555", linewidth=0.8)
    ax2.set_axisbelow(True)  # Put grid behind bars

    # Spine styling
    for spine in ax2.spines.values():
        spine.set_edgecolor("#444444")
        spine.set_linewidth(1.5)
    for spine in ax2_twin.spines.values():
        spine.set_edgecolor("#444444")
        spine.set_linewidth(1.5)

    # Combined legend with style
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    legend2 = ax2.legend(
        lines1 + lines2,
        labels1 + labels2,
        loc="upper left",
        fontsize=10,
        frameon=True,
        fancybox=True,
        shadow=True,
    )
    legend2.get_frame().set_facecolor("#1a1a1a")
    legend2.get_frame().set_edgecolor("#444444")
    legend2.get_frame().set_linewidth(1.5)

    # Add sample-to-time reference with style
    sample_refs = np.linspace(0, len(samples) - 1, min(8, len(samples)), dtype=int)
    ref_text = " | ".join([f"{s}: {time_map[s]}" for s in sample_refs])
    fig.text(
        0.5,
        0.02,
        ref_text,
        ha="center",
        fontsize=10,
        color="#666666",
        style="italic",
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="#0a0a0a",
            edgecolor="#333333",
            linewidth=1,
        ),
    )

    # Add watermark/brand
    fig.text(
        0.98,
        0.02,
        "▲ Peak Analysis System ▼",
        ha="right",
        fontsize=9,
        color="#444444",
        style="italic",
        alpha=0.7,
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.06, top=0.92, hspace=0.25)
    
    # Save or show the plot
    if save_path:
        plt.savefig(save_path, dpi=100, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()  # Close to free memory
        print(f"Chart saved to: {save_path}")
        return save_path
    else:
        plt.show()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Analyze peaks and troughs in stock data with zero-phase filtering"
    )

    # Arguments from get_bars.py
    parser.add_argument(
        "-n", type=int, default=1, help="Number of trading days to fetch (default: 1)"
    )
    parser.add_argument(
        "-t",
        type=str,
        default="1Min",
        choices=["1Min", "5Min", "15Min", "30Min", "1Hour", "1Day"],
        help="Timeframe for bars (default: 1Min)",
    )
    parser.add_argument(
        "-s",
        type=str,
        help="Stock symbol(s) to analyze - single symbol or comma-separated list (required if not using -f)",
    )
    parser.add_argument(
        "-f", "--file", type=str, help="File containing stock symbols (one per line)"
    )
    parser.add_argument(
        "-o",
        type=str,
        choices=["json", "bars", "full"],
        help="Output format (default: full analysis)",
    )
    parser.add_argument(
        "--feed",
        type=str,
        default="sip",
        choices=["sip", "iex", "otc"],
        help="Data feed to use (default: sip)",
    )

    # New arguments for peak analysis
    parser.add_argument(
        "-w",
        "--window",
        type=int,
        default=11,
        help="Hanning filter window length (must be odd, default: 11)",
    )
    parser.add_argument(
        "-l",
        "--lookahead",
        type=int,
        default=1,
        help="Lookahead parameter for peak detection (default: 1)",
    )
    parser.add_argument(
        "--plot", action="store_true", help="Generate and display interactive plot"
    )
    parser.add_argument(
        "--save-plot", 
        nargs='?', 
        const=True,
        help="Save plot to file. If no path provided, saves to /tmp with auto-generated name"
    )
    parser.add_argument(
        "--cash",
        type=float,
        default=1000.0,
        help="Initial cash amount for trading (default: $1000)",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.s and not args.file:
        parser.error(
            "Either -s (single symbol) or -f (file with symbols) must be provided"
        )

    if args.s and args.file:
        parser.error("Cannot use both -s and -f options. Choose one.")

    # Ensure window length is odd
    if args.window % 2 == 0:
        args.window += 1
        print(f"Window length adjusted to {args.window} (must be odd)")

    # Initialize API
    api = tradeapi.REST()

    try:
        if args.file:
            # Multi-stock analysis mode from file
            print(f"Reading symbols from file: {args.file}")
            symbols = read_symbols_from_file(args.file)
            print(f"Found {len(symbols)} symbols: {', '.join(symbols)}")

            # Process multiple stocks
            results = process_multiple_stocks(
                symbols,
                api,
                args.n,
                args.t,
                args.feed,
                args.window,
                args.lookahead,
                args.cash,
            )

            # Generate tabular report
            report = generate_tabular_report(
                results, args.t, args.n, args.window, args.lookahead
            )
            print("\n" + report)

        else:
            # Parse symbols from -s argument (single or comma-separated)
            symbols_input = args.s.upper().replace(" ", "")  # Remove spaces
            symbols = [
                symbol.strip() for symbol in symbols_input.split(",") if symbol.strip()
            ]

            if len(symbols) == 1:
                # Single stock analysis mode with detailed report
                symbol = symbols[0]

                # Fetch bars
                print(f"Fetching {args.n} day(s) of {args.t} data for {symbol}...")
                bars = fetch_bars(api, symbol, args.n, args.t, args.feed)
                print(f"Fetched {len(bars)} bars")

                # Analyze peaks and troughs
                print(f"Applying zero-phase Hanning filter (window={args.window})...")
                print(f"Detecting peaks and troughs (lookahead={args.lookahead})...")
                results = analyze_peaks_and_troughs(
                    bars, args.window, args.lookahead, symbol, args.t
                )

                # Generate detailed report
                report = generate_report(results, args.cash)
                print("\n" + report)

                # Generate plot if requested
                if args.plot:
                    plot_results(results)
                elif args.save_plot:
                    saved_path = plot_results(results, args.save_plot)
                    if saved_path:
                        print(f"\n✅ Chart successfully saved to: {saved_path}")
            else:
                # Multi-stock analysis mode from comma-separated symbols
                print(f"Found {len(symbols)} symbols: {', '.join(symbols)}")

                # Process multiple stocks
                results = process_multiple_stocks(
                    symbols,
                    api,
                    args.n,
                    args.t,
                    args.feed,
                    args.window,
                    args.lookahead,
                    args.cash,
                )

                # Generate tabular report
                report = generate_tabular_report(
                    results, args.t, args.n, args.window, args.lookahead
                )
                print("\n" + report)

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
