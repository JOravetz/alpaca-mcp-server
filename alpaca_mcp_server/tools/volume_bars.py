#!/usr/bin/env python3
"""
Volume Bars Implementation based on "Advances in Financial Machine Learning" by Marcos López de Prado

Volume bars sample data by volume rather than time, creating bars when a predefined volume threshold is reached.
This provides more informative sampling during high-activity periods and reduces noise during low-activity periods.

Key advantages:
1. Better statistical properties (closer to IID)
2. More responsive to market microstructure
3. Reduced serial correlation of returns
4. Better for ML models than time bars

Author: Implementation for Alpaca Trading System
Reference: Chapter 2, AFML - Marcos López de Prado
"""

import asyncio
import logging
import os
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Trade

logger = logging.getLogger(__name__)


@dataclass
class VolumeBar:
    """Represents a single volume bar with OHLCV and additional statistics"""

    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float  # Volume-weighted average price
    trade_count: int
    timestamp_open: datetime
    timestamp_close: datetime
    dollar_volume: float
    buy_volume: float  # Volume at upticks
    sell_volume: float  # Volume at downticks
    volume_imbalance: float  # (buy_volume - sell_volume) / total_volume
    tick_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for DataFrame creation"""
        return {
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "vwap": self.vwap,
            "trade_count": self.trade_count,
            "timestamp_open": self.timestamp_open,
            "timestamp_close": self.timestamp_close,
            "dollar_volume": self.dollar_volume,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "volume_imbalance": self.volume_imbalance,
            "tick_count": self.tick_count,
            "duration_seconds": (self.timestamp_close - self.timestamp_open).total_seconds(),
        }


class VolumeBarAggregator:
    """
    Aggregates trades OR bars into volume bars based on López de Prado's methodology

    Can work with either:
    1. Trade data - for finest granularity
    2. Bar data (1-min, 5-min, etc.) - uses pre-computed VWAP and trade counts

    Args:
        symbol: Stock symbol to track
        volume_threshold: Volume threshold to trigger new bar creation
        lookback_bars: Number of bars to keep in memory for analysis
        on_bar_complete: Callback function when a bar is completed
        use_bars: If True, expects Bar objects instead of Trade objects
    """

    def __init__(
        self,
        symbol: str,
        volume_threshold: float,
        lookback_bars: int = 100,
        on_bar_complete: Callable[[VolumeBar], None] | None = None,
        use_bars: bool = False,
    ):
        self.symbol = symbol
        self.volume_threshold = volume_threshold
        self.lookback_bars = lookback_bars
        self.on_bar_complete = on_bar_complete
        self.use_bars = use_bars

        # Current bar construction
        self.current_volume = 0.0
        self.current_trades: list[Trade] = []
        self.current_bars: list[Bar] = []  # For bar-based aggregation
        self.current_prices: list[float] = []
        self.current_volumes: list[float] = []
        self.current_vwaps: list[float] = []  # Store VWAPs from bars
        self.current_trade_counts: list[int] = []  # Store trade counts from bars
        self.previous_price: float | None = None

        # Historical bars
        self.completed_bars: deque = deque(maxlen=lookback_bars)

        # Statistics for dynamic threshold adjustment
        self.volume_history: deque = deque(maxlen=50)
        self.use_dynamic_threshold = False

    def process_trade(self, trade: Trade) -> VolumeBar | None:
        """
        Process a single trade and return completed bar if threshold is reached

        Args:
            trade: Alpaca Trade object

        Returns:
            Completed VolumeBar if threshold reached, None otherwise
        """
        if self.use_bars:
            raise ValueError(
                "Aggregator is configured for bars, not trades. Use process_bar() instead."
            )

        # Add trade to current bar
        self.current_trades.append(trade)
        self.current_prices.append(trade.price)
        self.current_volumes.append(trade.size)
        self.current_volume += trade.size

        # Check if we should complete the bar
        if self.current_volume >= self._get_volume_threshold():
            bar = self._create_bar()
            self._reset_current_bar()

            # Store completed bar
            self.completed_bars.append(bar)
            self.volume_history.append(bar.volume)

            # Trigger callback if provided
            if self.on_bar_complete:
                self.on_bar_complete(bar)

            return bar

        # Update previous price for tick direction
        self.previous_price = trade.price
        return None

    def process_bar(self, bar: Bar) -> VolumeBar | None:
        """
        Process a bar (e.g., 1-minute bar) and return completed volume bar if threshold is reached

        Uses the pre-computed VWAP and trade_count from Alpaca bars for efficiency.

        Args:
            bar: Alpaca Bar object with OHLCV, VWAP, and trade_count

        Returns:
            Completed VolumeBar if threshold reached, None otherwise
        """
        if not self.use_bars:
            raise ValueError(
                "Aggregator is configured for trades, not bars. Use process_trade() instead."
            )

        # Add bar to current accumulation
        self.current_bars.append(bar)
        self.current_volume += bar.volume

        # Store bar data for volume bar creation
        self.current_prices.extend([bar.open, bar.high, bar.low, bar.close])
        self.current_volumes.append(bar.volume)
        self.current_vwaps.append(bar.vwap if hasattr(bar, "vwap") else bar.close)  # type: ignore[arg-type]
        self.current_trade_counts.append(bar.trade_count if hasattr(bar, "trade_count") else 1)  # type: ignore[arg-type]

        # Check if we should complete the volume bar
        if self.current_volume >= self._get_volume_threshold():
            volume_bar = self._create_bar_from_bars()
            self._reset_current_bar()

            # Store completed bar
            self.completed_bars.append(volume_bar)
            self.volume_history.append(volume_bar.volume)

            # Trigger callback if provided
            if self.on_bar_complete:
                self.on_bar_complete(volume_bar)

            return volume_bar

        # Update previous price for tick direction
        self.previous_price = bar.close
        return None

    def _create_bar(self) -> VolumeBar:
        """Create a VolumeBar from accumulated trades"""
        if not self.current_trades:
            raise ValueError("Cannot create bar without trades")

        # Calculate OHLC
        prices = np.array(self.current_prices)
        volumes = np.array(self.current_volumes)

        open_price = self.current_prices[0]
        high_price = np.max(prices)
        low_price = np.min(prices)
        close_price = self.current_prices[-1]

        # Calculate VWAP
        vwap = np.sum(prices * volumes) / np.sum(volumes)

        # Calculate buy/sell volume (tick rule)
        buy_volume = 0.0
        sell_volume = 0.0

        for i, trade in enumerate(self.current_trades):
            if i == 0 and self.previous_price is not None:
                # Use previous bar's close for first trade
                if trade.price > self.previous_price:
                    buy_volume += trade.size
                elif trade.price < self.previous_price:
                    sell_volume += trade.size
                else:
                    # No change - split evenly
                    buy_volume += trade.size / 2
                    sell_volume += trade.size / 2
            elif i > 0:
                # Compare with previous trade
                if trade.price > self.current_trades[i - 1].price:
                    buy_volume += trade.size
                elif trade.price < self.current_trades[i - 1].price:
                    sell_volume += trade.size
                else:
                    # No change - use previous classification
                    if (
                        i > 0
                        and self.current_trades[i - 1].price
                        > self.current_trades[max(0, i - 2)].price
                    ):
                        buy_volume += trade.size
                    else:
                        sell_volume += trade.size

        # Calculate volume imbalance
        total_volume = buy_volume + sell_volume
        volume_imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0

        # Calculate dollar volume
        dollar_volume = np.sum(prices * volumes)

        return VolumeBar(
            symbol=self.symbol,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=self.current_volume,
            vwap=vwap,
            trade_count=len(self.current_trades),
            timestamp_open=self.current_trades[0].timestamp,
            timestamp_close=self.current_trades[-1].timestamp,
            dollar_volume=dollar_volume,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            volume_imbalance=volume_imbalance,
            tick_count=len(self.current_trades),
        )

    def _create_bar_from_bars(self) -> VolumeBar:
        """Create a VolumeBar from accumulated Bar objects, leveraging pre-computed VWAP"""
        if not self.current_bars:
            raise ValueError("Cannot create volume bar without bars")

        # Get first and last bars for timestamps
        first_bar = self.current_bars[0]
        last_bar = self.current_bars[-1]

        # Calculate OHLC across all accumulated bars
        open_price = first_bar.open
        close_price = last_bar.close
        high_price = max(bar.high for bar in self.current_bars)
        low_price = min(bar.low for bar in self.current_bars)

        # Calculate volume-weighted average price using pre-computed VWAPs
        # Each bar's VWAP is already volume-weighted, so we weight by volume again
        total_volume = sum(bar.volume for bar in self.current_bars)
        if total_volume > 0:
            weighted_vwap = (
                sum(
                    bar.vwap * bar.volume if hasattr(bar, "vwap") else bar.close * bar.volume  # type: ignore[misc,operator]
                    for bar in self.current_bars
                )
                / total_volume
            )
        else:
            weighted_vwap = close_price

        # Calculate buy/sell volume using price direction between bars
        buy_volume = 0.0
        sell_volume = 0.0

        for i, bar in enumerate(self.current_bars):
            # Determine direction based on close vs previous close
            if i == 0 and self.previous_price is not None:
                # First bar - compare with previous volume bar's close
                if bar.close > self.previous_price:
                    buy_volume += bar.volume
                elif bar.close < self.previous_price:
                    sell_volume += bar.volume
                else:
                    # Split evenly if no change
                    buy_volume += bar.volume / 2
                    sell_volume += bar.volume / 2
            elif i > 0:
                # Compare with previous bar's close
                prev_bar = self.current_bars[i - 1]
                if bar.close > prev_bar.close:
                    buy_volume += bar.volume
                elif bar.close < prev_bar.close:
                    sell_volume += bar.volume
                else:
                    # Use bar's internal price action (close vs open)
                    if bar.close > bar.open:
                        buy_volume += bar.volume
                    elif bar.close < bar.open:
                        sell_volume += bar.volume
                    else:
                        # Split evenly
                        buy_volume += bar.volume / 2
                        sell_volume += bar.volume / 2

        # Calculate volume imbalance
        volume_imbalance = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0

        # Calculate dollar volume
        dollar_volume = sum(
            bar.vwap * bar.volume if hasattr(bar, "vwap") else bar.close * bar.volume  # type: ignore[misc,operator]
            for bar in self.current_bars
        )

        # Sum trade counts
        total_trade_count = sum(
            bar.trade_count if hasattr(bar, "trade_count") else 1 for bar in self.current_bars  # type: ignore[misc]
        )

        return VolumeBar(
            symbol=self.symbol,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
            vwap=weighted_vwap,
            trade_count=total_trade_count,
            timestamp_open=first_bar.timestamp,
            timestamp_close=last_bar.timestamp,
            dollar_volume=dollar_volume,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            volume_imbalance=volume_imbalance,
            tick_count=len(self.current_bars),  # Number of bars aggregated
        )

    def _reset_current_bar(self):
        """Reset current bar accumulation"""
        self.current_volume = 0.0
        self.current_trades = []
        self.current_bars = []
        self.current_prices = []
        self.current_volumes = []
        self.current_vwaps = []
        self.current_trade_counts = []

    def _get_volume_threshold(self) -> float:
        """
        Get volume threshold (static or dynamic based on recent history)

        Dynamic threshold uses exponentially weighted average of recent bars
        """
        if not self.use_dynamic_threshold or len(self.volume_history) < 10:
            return self.volume_threshold

        # Use EWMA of recent volume bars
        weights = np.exp(np.linspace(-1, 0, len(self.volume_history)))
        weights /= weights.sum()
        dynamic_threshold = np.average(list(self.volume_history), weights=weights)

        # Bound between 0.5x and 2x original threshold
        return np.clip(dynamic_threshold, self.volume_threshold * 0.5, self.volume_threshold * 2.0)

    def get_bars_dataframe(self) -> pd.DataFrame:
        """Get completed bars as a pandas DataFrame"""
        if not self.completed_bars:
            return pd.DataFrame()

        bars_data = [bar.to_dict() for bar in self.completed_bars]
        df = pd.DataFrame(bars_data)
        df.set_index("timestamp_close", inplace=True)
        return df

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the volume bars"""
        if not self.completed_bars:
            return {}

        df = self.get_bars_dataframe()

        # Calculate returns
        df["returns"] = df["close"].pct_change()

        return {
            "total_bars": len(self.completed_bars),
            "avg_volume_per_bar": df["volume"].mean(),
            "avg_duration_seconds": df["duration_seconds"].mean(),
            "avg_trade_count": df["trade_count"].mean(),
            "avg_dollar_volume": df["dollar_volume"].mean(),
            "avg_volume_imbalance": df["volume_imbalance"].mean(),
            "returns_mean": df["returns"].mean(),
            "returns_std": df["returns"].std(),
            "returns_skew": df["returns"].skew(),
            "returns_kurtosis": df["returns"].kurtosis(),
            "autocorrelation_lag1": df["returns"].autocorr(lag=1) if len(df) > 1 else None,
        }


class MultiSymbolVolumeBarAggregator:
    """
    Manages volume bar aggregation for multiple symbols simultaneously

    Can work with either Trade or Bar data sources.

    Args:
        symbol_thresholds: Dictionary mapping symbols to their volume thresholds
        lookback_bars: Number of bars to keep per symbol
        on_bar_complete: Callback for completed bars
        use_bars: If True, expects Bar objects instead of Trade objects
    """

    def __init__(
        self,
        symbol_thresholds: dict[str, float],
        lookback_bars: int = 100,
        on_bar_complete: Callable[[VolumeBar], None] | None = None,
        use_bars: bool = False,
    ):
        self.aggregators: dict[str, VolumeBarAggregator] = {}
        self.use_bars = use_bars

        # Create aggregator for each symbol
        for symbol, threshold in symbol_thresholds.items():
            self.aggregators[symbol] = VolumeBarAggregator(
                symbol=symbol,
                volume_threshold=threshold,
                lookback_bars=lookback_bars,
                on_bar_complete=on_bar_complete,
                use_bars=use_bars,
            )

    def process_trade(self, trade: Trade) -> VolumeBar | None:
        """Process trade for the appropriate symbol"""
        if trade.symbol in self.aggregators:
            return self.aggregators[trade.symbol].process_trade(trade)
        return None

    def process_bar(self, bar: Bar) -> VolumeBar | None:
        """Process bar for the appropriate symbol"""
        if bar.symbol in self.aggregators:
            return self.aggregators[bar.symbol].process_bar(bar)
        return None

    def get_all_statistics(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all symbols"""
        return {symbol: agg.get_statistics() for symbol, agg in self.aggregators.items()}

    def get_all_dataframes(self) -> dict[str, pd.DataFrame]:
        """Get DataFrames for all symbols"""
        return {symbol: agg.get_bars_dataframe() for symbol, agg in self.aggregators.items()}


async def stream_volume_bars(
    symbols: list[str],
    volume_thresholds: dict[str, float],
    data_feed: str = "sip",
    on_bar_complete: Callable[[VolumeBar], None] | None = None,
) -> None:
    """
    Stream trades and aggregate into volume bars in real-time

    Args:
        symbols: List of symbols to track
        volume_thresholds: Volume thresholds per symbol
        data_feed: Data feed to use (sip, iex, etc.)
        on_bar_complete: Callback when bars complete
    """
    # Create multi-symbol aggregator
    aggregator = MultiSymbolVolumeBarAggregator(
        symbol_thresholds=volume_thresholds, on_bar_complete=on_bar_complete
    )

    # Set up stream
    stream = StockDataStream(
        api_key=os.environ.get("APCA_API_KEY_ID"),  # type: ignore[arg-type]
        secret_key=os.environ.get("APCA_API_SECRET_KEY"),  # type: ignore[arg-type]
        feed=data_feed,  # type: ignore[arg-type]
    )

    # Trade handler
    async def handle_trade(trade: Trade) -> None:
        """Process incoming trades"""
        bar = aggregator.process_trade(trade)
        if bar:
            logger.info(
                f"Volume bar completed for {bar.symbol}: "
                f"OHLC=[{bar.open:.2f}, {bar.high:.2f}, {bar.low:.2f}, {bar.close:.2f}], "
                f"Volume={bar.volume:.0f}, VWAP={bar.vwap:.2f}, "
                f"Imbalance={bar.volume_imbalance:.2%}"
            )

    # Subscribe to trades
    for symbol in symbols:
        stream.subscribe_trades(handle_trade, symbol)  # type: ignore[arg-type]

    # Run stream
    logger.info(f"Starting volume bar stream for {symbols}")
    await stream.run()  # type: ignore[func-returns-value]


def calculate_optimal_threshold(
    symbol: str, lookback_days: int = 20, target_bars_per_day: int = 50
) -> float:
    """
    Calculate optimal volume threshold based on historical data

    Uses average daily volume to target a specific number of bars per day

    Args:
        symbol: Stock symbol
        lookback_days: Days of history to analyze
        target_bars_per_day: Desired number of bars per trading day

    Returns:
        Suggested volume threshold
    """
    # This would need to fetch historical data from Alpaca
    # For now, return a placeholder
    # In practice, you'd use: get_stock_bars() to fetch historical data

    logger.info(f"Calculating optimal threshold for {symbol}")
    # Placeholder - in practice, calculate from historical ADV
    return 10000.0  # Default 10k shares per bar


if __name__ == "__main__":
    # Example usage
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Example symbols and thresholds
    symbols = ["AAPL", "MSFT", "TSLA"]
    thresholds = {
        "AAPL": 100000,  # 100k shares per bar
        "MSFT": 50000,  # 50k shares per bar
        "TSLA": 75000,  # 75k shares per bar
    }

    # Bar completion callback
    def on_bar(bar: VolumeBar) -> None:
        print(f"\n{'='*60}")
        print(f"Volume Bar Completed: {bar.symbol}")
        print(f"OHLC: [{bar.open:.2f}, {bar.high:.2f}, {bar.low:.2f}, {bar.close:.2f}]")
        print(f"Volume: {bar.volume:,.0f} | VWAP: {bar.vwap:.2f}")
        print(f"Buy/Sell: {bar.buy_volume:,.0f}/{bar.sell_volume:,.0f}")
        print(f"Imbalance: {bar.volume_imbalance:.2%}")
        print(f"Duration: {(bar.timestamp_close - bar.timestamp_open).total_seconds():.1f}s")
        print(f"{'='*60}")

    # Run streaming
    try:
        asyncio.run(
            stream_volume_bars(
                symbols=symbols, volume_thresholds=thresholds, on_bar_complete=on_bar  # type: ignore[arg-type]
            )
        )
    except KeyboardInterrupt:
        logger.info("Volume bar streaming stopped by user")
        sys.exit(0)
