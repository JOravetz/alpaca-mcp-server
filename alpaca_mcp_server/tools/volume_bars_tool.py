#!/usr/bin/env python3
"""
Volume Bars MCP Tool - Integration with Alpaca MCP Server

Provides MCP tool interface for Volume Bars implementation based on 
"Advances in Financial Machine Learning" by Marcos López de Prado

This tool integrates with the existing streaming infrastructure to provide
volume-based sampling as an alternative to time-based bars.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from alpaca.data.models import Bar, Trade
from alpaca.data.requests import StockBarsRequest, StockTradesRequest
from alpaca.data.timeframe import TimeFrame

from ..config.settings import get_stock_historical_client
from .volume_bars import MultiSymbolVolumeBarAggregator, VolumeBar, VolumeBarAggregator


# Simple formatting functions
def format_currency(value: float) -> str:
    """Format a number as currency"""
    return f"${value:,.2f}"

def format_number(value: float) -> str:
    """Format a number with thousands separator"""
    return f"{value:,.0f}"

def format_percentage(value: float) -> str:
    """Format a number as percentage"""
    return f"{value:.2%}"

logger = logging.getLogger(__name__)

# Global storage for volume bar aggregators
_volume_bar_aggregators: Dict[str, VolumeBarAggregator] = {}
_completed_volume_bars: Dict[str, List[VolumeBar]] = {}


async def get_volume_bars_from_history(
    symbol: str,
    volume_threshold: float = None,
    days: int = 1,
    auto_calculate_threshold: bool = True,
    target_bars_per_day: int = 50,
    use_bars: bool = True,
    bar_timeframe: str = "1Min"
) -> str:
    """
    Generate volume bars from historical data
    
    This method can use either:
    1. Bar data (default) - More efficient, uses pre-computed VWAP and trade counts
    2. Trade data - Finer granularity but more data intensive
    
    Args:
        symbol: Stock symbol
        volume_threshold: Volume per bar (if None, auto-calculates)
        days: Number of days of history to process
        auto_calculate_threshold: Whether to auto-calculate optimal threshold
        target_bars_per_day: Target number of bars per day for auto-calculation
        use_bars: If True, uses bar data; if False, uses trade data
        bar_timeframe: Timeframe for bars ("1Min", "5Min", etc.) when use_bars=True
        
    Returns:
        Formatted volume bars analysis
    """
    market_data_client = get_stock_historical_client()

    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # First, get daily bars to estimate volume if needed
        if volume_threshold is None and auto_calculate_threshold:
            bars_request = StockBarsRequest(
                symbol_or_symbols=symbol,
                start=start_date,
                end=end_date,
                timeframe=TimeFrame.Day
            )
            daily_bars = market_data_client.get_stock_bars(bars_request)

            if symbol in daily_bars:
                bars_df = daily_bars[symbol]
                if not bars_df.empty:
                    avg_daily_volume = bars_df['volume'].mean()
                    volume_threshold = avg_daily_volume / target_bars_per_day
                    logger.info(f"Auto-calculated volume threshold: {volume_threshold:,.0f} shares/bar")
                else:
                    volume_threshold = 10000  # Default fallback
            else:
                volume_threshold = 10000  # Default fallback

        # Create volume bar aggregator
        aggregator = VolumeBarAggregator(
            symbol=symbol,
            volume_threshold=volume_threshold,
            lookback_bars=1000,
            use_bars=use_bars
        )

        bars_created = 0
        total_data_points = 0

        if use_bars:
            # Use bar data (more efficient, includes pre-computed VWAP)
            # Parse timeframe
            timeframe_map = {
                "1Min": TimeFrame.Minute,
                "5Min": TimeFrame(5, "Min"),
                "15Min": TimeFrame(15, "Min"),
                "30Min": TimeFrame(30, "Min"),
                "1Hour": TimeFrame.Hour,
                "Day": TimeFrame.Day
            }

            timeframe = timeframe_map.get(bar_timeframe, TimeFrame.Minute)

            bars_request = StockBarsRequest(
                symbol_or_symbols=symbol,
                start=start_date,
                end=end_date,
                timeframe=timeframe
            )

            bars_response = market_data_client.get_stock_bars(bars_request)

            if symbol not in bars_response:
                return f"No bar data available for {symbol}"

            bars_df = bars_response[symbol]

            if bars_df.empty:
                return f"No {bar_timeframe} bars found for {symbol} in the last {days} days"

            # Process all bars
            for timestamp, bar_row in bars_df.iterrows():
                # Create Bar-like object with all necessary fields
                bar = type('Bar', (), {
                    'symbol': symbol,
                    'open': bar_row['open'],
                    'high': bar_row['high'],
                    'low': bar_row['low'],
                    'close': bar_row['close'],
                    'volume': bar_row['volume'],
                    'vwap': bar_row['vwap'] if 'vwap' in bar_row else bar_row['close'],
                    'trade_count': bar_row['trade_count'] if 'trade_count' in bar_row else 1,
                    'timestamp': timestamp
                })()

                volume_bar = aggregator.process_bar(bar)
                if volume_bar:
                    bars_created += 1
                total_data_points += 1

        else:
            # Use trade data (finer granularity)
            trades_request = StockTradesRequest(
                symbol_or_symbols=symbol,
                start=start_date,
                end=end_date,
                limit=10000  # Adjust based on needs
            )

            trades_response = market_data_client.get_stock_trades(trades_request)

            if symbol not in trades_response:
                return f"No trade data available for {symbol}"

            trades = trades_response[symbol]

            if trades.empty:
                return f"No trades found for {symbol} in the last {days} days"

            # Process all trades
            for _, trade_row in trades.iterrows():
                # Convert DataFrame row to Trade-like object
                trade = type('Trade', (), {
                    'symbol': symbol,
                    'price': trade_row['price'],
                    'size': trade_row['size'],
                    'timestamp': trade_row.name  # Index is timestamp
                })()

                volume_bar = aggregator.process_trade(trade)
                if volume_bar:
                    bars_created += 1
                total_data_points += 1

        # Get statistics
        stats = aggregator.get_statistics()
        df = aggregator.get_bars_dataframe()

        # Format output
        output = []
        output.append(f"📊 VOLUME BARS ANALYSIS FOR {symbol}")
        output.append("=" * 60)
        output.append(f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        output.append(f"Data Source: {'Bar Data (' + bar_timeframe + ')' if use_bars else 'Trade Data'}")
        if use_bars:
            output.append(f"  ✅ Using pre-computed VWAP and trade counts from Alpaca bars")
        output.append(f"Volume Threshold: {format_number(volume_threshold)} shares/bar")
        output.append(f"Total {'Bars' if use_bars else 'Trades'} Processed: {format_number(total_data_points)}")
        output.append(f"Volume Bars Created: {bars_created}")
        output.append("")

        if stats:
            output.append("📈 STATISTICAL PROPERTIES:")
            output.append(f"  • Avg Volume/Bar: {format_number(stats.get('avg_volume_per_bar', 0))}")
            output.append(f"  • Avg Duration: {stats.get('avg_duration_seconds', 0):.1f} seconds")
            output.append(f"  • Avg Trades/Bar: {stats.get('avg_trade_count', 0):.1f}")
            output.append(f"  • Avg Dollar Volume: {format_currency(stats.get('avg_dollar_volume', 0))}")
            output.append(f"  • Avg Volume Imbalance: {format_percentage(stats.get('avg_volume_imbalance', 0))}")
            output.append("")
            output.append("📊 RETURNS ANALYSIS:")
            output.append(f"  • Mean Return: {format_percentage(stats.get('returns_mean', 0))}")
            output.append(f"  • Std Deviation: {format_percentage(stats.get('returns_std', 0))}")
            output.append(f"  • Skewness: {stats.get('returns_skew', 0):.3f}")
            output.append(f"  • Kurtosis: {stats.get('returns_kurtosis', 0):.3f}")

            autocorr = stats.get('autocorrelation_lag1')
            if autocorr is not None:
                output.append(f"  • Autocorrelation (lag-1): {autocorr:.3f}")
                if abs(autocorr) < 0.1:
                    output.append("    ✅ Low autocorrelation - good for ML")
                else:
                    output.append("    ⚠️ High autocorrelation detected")

        if not df.empty:
            output.append("")
            output.append("🕐 LAST 5 VOLUME BARS:")
            output.append("-" * 60)

            for _, bar_row in df.tail(5).iterrows():
                output.append(f"  {bar_row.name.strftime('%H:%M:%S')}: "
                            f"OHLC=[{bar_row['open']:.2f}, {bar_row['high']:.2f}, "
                            f"{bar_row['low']:.2f}, {bar_row['close']:.2f}]")
                output.append(f"    Volume: {format_number(bar_row['volume'])} | "
                            f"VWAP: ${bar_row['vwap']:.2f} | "
                            f"Imbalance: {format_percentage(bar_row['volume_imbalance'])}")

        # Store aggregator for potential reuse
        _volume_bar_aggregators[symbol] = aggregator

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error generating volume bars for {symbol}: {e}")
        return f"Error generating volume bars: {str(e)}"


async def start_volume_bar_streaming(
    symbols: str,
    volume_thresholds: str = None,
    auto_calculate: bool = True,
    target_bars_per_day: int = 50
) -> str:
    """
    Start real-time volume bar aggregation using existing stream
    
    Integrates with the global stock stream to aggregate trades into volume bars.
    
    Args:
        symbols: Comma-separated symbols to track
        volume_thresholds: Comma-separated thresholds or single value for all
        auto_calculate: Auto-calculate thresholds based on ADV
        target_bars_per_day: Target bars per day for auto-calculation
        
    Returns:
        Status message
    """
    from ..utils.alpaca_stream import _stock_stream_active, _stock_stream_buffers

    symbol_list = [s.strip().upper() for s in symbols.split(',')]

    # Parse volume thresholds
    threshold_dict = {}
    if volume_thresholds:
        thresholds = [float(t.strip()) for t in volume_thresholds.split(',')]
        if len(thresholds) == 1:
            # Use same threshold for all symbols
            for symbol in symbol_list:
                threshold_dict[symbol] = thresholds[0]
        else:
            # Map thresholds to symbols
            for i, symbol in enumerate(symbol_list):
                if i < len(thresholds):
                    threshold_dict[symbol] = thresholds[i]
                else:
                    threshold_dict[symbol] = thresholds[-1]  # Use last threshold for remaining

    # Auto-calculate if needed
    if auto_calculate:
        market_data_client = get_stock_historical_client()
        for symbol in symbol_list:
            if symbol not in threshold_dict:
                # Fetch recent daily volume
                end_date = datetime.now()
                start_date = end_date - timedelta(days=20)

                bars_request = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    start=start_date,
                    end=end_date,
                    timeframe=TimeFrame.Day
                )

                try:
                    daily_bars = market_data_client.get_stock_bars(bars_request)
                    if symbol in daily_bars:
                        bars_df = daily_bars[symbol]
                        if not bars_df.empty:
                            avg_daily_volume = bars_df['volume'].mean()
                            threshold_dict[symbol] = avg_daily_volume / target_bars_per_day
                            logger.info(f"Auto-calculated threshold for {symbol}: {threshold_dict[symbol]:,.0f}")
                except Exception as e:
                    logger.error(f"Error calculating threshold for {symbol}: {e}")
                    threshold_dict[symbol] = 100000  # Default

    # Ensure all symbols have thresholds
    for symbol in symbol_list:
        if symbol not in threshold_dict:
            threshold_dict[symbol] = 100000  # Default 100k shares

    # Create aggregator
    def on_bar_complete(bar: VolumeBar):
        """Store completed bars"""
        if bar.symbol not in _completed_volume_bars:
            _completed_volume_bars[bar.symbol] = []
        _completed_volume_bars[bar.symbol].append(bar)

        # Keep only last 100 bars per symbol
        if len(_completed_volume_bars[bar.symbol]) > 100:
            _completed_volume_bars[bar.symbol] = _completed_volume_bars[bar.symbol][-100:]

        logger.info(f"Volume bar completed for {bar.symbol}: "
                   f"Close=${bar.close:.2f}, Volume={bar.volume:,.0f}, "
                   f"Imbalance={bar.volume_imbalance:.2%}")

    aggregator = MultiSymbolVolumeBarAggregator(
        symbol_thresholds=threshold_dict,
        lookback_bars=100,
        on_bar_complete=on_bar_complete
    )

    # Store globally for access
    for symbol in symbol_list:
        _volume_bar_aggregators[symbol] = aggregator.aggregators[symbol]

    # Check if stream is active
    if not _stock_stream_active:
        return ("⚠️ Stock stream is not active. Please start it first with:\n"
                "start_global_stock_stream(symbols='" + ",".join(symbol_list) + "', data_types=['trades'])")

    # Format output
    output = []
    output.append("✅ VOLUME BAR AGGREGATION STARTED")
    output.append("=" * 60)
    output.append(f"Symbols: {', '.join(symbol_list)}")
    output.append("Thresholds:")
    for symbol, threshold in threshold_dict.items():
        output.append(f"  • {symbol}: {format_number(threshold)} shares/bar")
    output.append("")
    output.append("📊 Volume bars will be created when thresholds are reached.")
    output.append("Use get_volume_bar_stats() to check progress.")

    return "\n".join(output)


async def get_volume_bar_stats(symbol: str = None) -> str:
    """
    Get current volume bar statistics and recent bars
    
    Args:
        symbol: Specific symbol or None for all
        
    Returns:
        Formatted statistics and recent bars
    """
    output = []
    output.append("📊 VOLUME BAR STATISTICS")
    output.append("=" * 60)

    if symbol:
        symbols = [symbol]
    else:
        symbols = list(_volume_bar_aggregators.keys())

    if not symbols:
        return "No volume bar aggregators active. Use start_volume_bar_streaming() first."

    for sym in symbols:
        if sym not in _volume_bar_aggregators:
            continue

        aggregator = _volume_bar_aggregators[sym]
        stats = aggregator.get_statistics()

        output.append(f"\n{sym}:")
        output.append("-" * 40)

        if stats:
            output.append(f"  Total Bars: {stats.get('total_bars', 0)}")
            output.append(f"  Avg Volume: {format_number(stats.get('avg_volume_per_bar', 0))}")
            output.append(f"  Avg Duration: {stats.get('avg_duration_seconds', 0):.1f}s")
            output.append(f"  Avg Imbalance: {format_percentage(stats.get('avg_volume_imbalance', 0))}")
            output.append(f"  Return Volatility: {format_percentage(stats.get('returns_std', 0))}")

            autocorr = stats.get('autocorrelation_lag1')
            if autocorr is not None:
                output.append(f"  Autocorrelation: {autocorr:.3f}")
        else:
            output.append("  No completed bars yet")

        # Show current bar progress
        if aggregator.current_volume > 0:
            progress = (aggregator.current_volume / aggregator.volume_threshold) * 100
            output.append(f"  Current Bar Progress: {progress:.1f}% "
                         f"({format_number(aggregator.current_volume)}/{format_number(aggregator.volume_threshold)})")

        # Show recent bars if available
        if sym in _completed_volume_bars and _completed_volume_bars[sym]:
            recent_bars = _completed_volume_bars[sym][-3:]  # Last 3 bars
            if recent_bars:
                output.append("  Recent Bars:")
                for bar in recent_bars:
                    output.append(f"    {bar.timestamp_close.strftime('%H:%M:%S')}: "
                                f"${bar.close:.2f} | Vol: {format_number(bar.volume)} | "
                                f"Imb: {format_percentage(bar.volume_imbalance)}")

    return "\n".join(output)


async def compare_bar_types(
    symbol: str,
    days: int = 1,
    time_bars_minutes: int = 5,
    volume_threshold: float = None
) -> str:
    """
    Compare statistical properties of time bars vs volume bars
    
    This comparison helps understand the benefits of volume bars over
    traditional time-based sampling as described in López de Prado's book.
    
    Args:
        symbol: Stock symbol to analyze
        days: Number of days to analyze
        time_bars_minutes: Minute interval for time bars
        volume_threshold: Volume threshold for volume bars
        
    Returns:
        Comparative analysis of both bar types
    """
    market_data_client = get_stock_historical_client()

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get time bars
        timeframe_map = {
            1: TimeFrame.Minute,
            5: TimeFrame(5, "Min"),
            15: TimeFrame(15, "Min"),
            30: TimeFrame(30, "Min"),
            60: TimeFrame.Hour
        }

        timeframe = timeframe_map.get(time_bars_minutes, TimeFrame(time_bars_minutes, "Min"))

        bars_request = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start_date,
            end=end_date,
            timeframe=timeframe
        )

        time_bars_response = market_data_client.get_stock_bars(bars_request)

        if symbol not in time_bars_response:
            return f"No data available for {symbol}"

        time_bars_df = time_bars_response[symbol]

        # Calculate time bar statistics
        time_bars_df['returns'] = time_bars_df['close'].pct_change()

        time_stats = {
            'count': len(time_bars_df),
            'returns_mean': time_bars_df['returns'].mean(),
            'returns_std': time_bars_df['returns'].std(),
            'returns_skew': time_bars_df['returns'].skew(),
            'returns_kurtosis': time_bars_df['returns'].kurtosis(),
            'autocorr_lag1': time_bars_df['returns'].autocorr(lag=1) if len(time_bars_df) > 1 else None,
            'avg_volume': time_bars_df['volume'].mean()
        }

        # Generate volume bars for comparison
        volume_result = await get_volume_bars_from_history(
            symbol=symbol,
            volume_threshold=volume_threshold,
            days=days,
            auto_calculate_threshold=(volume_threshold is None)
        )

        # Get volume bar stats from aggregator
        if symbol in _volume_bar_aggregators:
            volume_stats = _volume_bar_aggregators[symbol].get_statistics()
        else:
            volume_stats = {}

        # Format comparison
        output = []
        output.append(f"📊 BAR TYPE COMPARISON FOR {symbol}")
        output.append("=" * 60)
        output.append(f"Period: {days} day(s)")
        output.append("")

        output.append(f"TIME BARS ({time_bars_minutes}-minute):")
        output.append(f"  • Bar Count: {time_stats['count']}")
        output.append(f"  • Avg Volume/Bar: {format_number(time_stats['avg_volume'])}")
        output.append(f"  • Return Volatility: {format_percentage(time_stats['returns_std'])}")
        output.append(f"  • Return Skewness: {time_stats['returns_skew']:.3f}")
        output.append(f"  • Return Kurtosis: {time_stats['returns_kurtosis']:.3f}")

        if time_stats['autocorr_lag1'] is not None:
            output.append(f"  • Autocorrelation: {time_stats['autocorr_lag1']:.3f}")
            if abs(time_stats['autocorr_lag1']) > 0.1:
                output.append("    ⚠️ High autocorrelation (bad for ML)")

        output.append("")
        output.append("VOLUME BARS:")
        if volume_stats:
            output.append(f"  • Bar Count: {volume_stats.get('total_bars', 0)}")
            output.append(f"  • Avg Volume/Bar: {format_number(volume_stats.get('avg_volume_per_bar', 0))}")
            output.append(f"  • Return Volatility: {format_percentage(volume_stats.get('returns_std', 0))}")
            output.append(f"  • Return Skewness: {volume_stats.get('returns_skew', 0):.3f}")
            output.append(f"  • Return Kurtosis: {volume_stats.get('returns_kurtosis', 0):.3f}")

            if volume_stats.get('autocorrelation_lag1') is not None:
                output.append(f"  • Autocorrelation: {volume_stats['autocorrelation_lag1']:.3f}")
                if abs(volume_stats['autocorrelation_lag1']) < abs(time_stats.get('autocorr_lag1', 1)):
                    output.append("    ✅ Lower autocorrelation than time bars (better for ML)")
        else:
            output.append("  No volume bars generated")

        output.append("")
        output.append("💡 KEY INSIGHTS:")

        if volume_stats and time_stats:
            # Compare autocorrelation
            vol_autocorr = abs(volume_stats.get('autocorrelation_lag1', 1))
            time_autocorr = abs(time_stats.get('autocorr_lag1', 1))

            if vol_autocorr < time_autocorr:
                output.append("  ✅ Volume bars show lower autocorrelation (better statistical properties)")

            # Compare kurtosis (closer to 3 is more normal)
            vol_kurt = abs(volume_stats.get('returns_kurtosis', 0) - 3)
            time_kurt = abs(time_stats.get('returns_kurtosis', 0) - 3)

            if vol_kurt < time_kurt:
                output.append("  ✅ Volume bars have returns closer to normal distribution")

            # Information content
            if volume_stats.get('total_bars', 0) < time_stats['count']:
                output.append("  ✅ Volume bars provide more information per sample")

            output.append("  📚 Volume bars better capture market microstructure (López de Prado)")

        return "\n".join(output)

    except Exception as e:
        logger.error(f"Error comparing bar types: {e}")
        return f"Error comparing bar types: {str(e)}"


# Export functions for MCP tool registration
__all__ = [
    'get_volume_bars_from_history',
    'start_volume_bar_streaming',
    'get_volume_bar_stats',
    'compare_bar_types'
]
