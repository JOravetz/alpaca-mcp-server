#!/usr/bin/env python3
"""
Enhanced Volume Bars Implementation with Multiple Bar Types
Based on "Advances in Financial Machine Learning" by Marcos López de Prado

This module implements all information-driven bar types from Chapter 2:
1. Tick Bars - Sample by number of trades
2. Volume Bars - Sample by volume traded
3. Dollar Bars - Sample by dollar value traded
4. Tick Imbalance Bars (TIBs) - Sample by tick imbalance
5. Volume Imbalance Bars (VIBs) - Sample by volume imbalance
6. Dollar Imbalance Bars (DIBs) - Sample by dollar imbalance

Key advantages over time bars:
- Better statistical properties (closer to IID)
- Reduced serial correlation
- More responsive to market microstructure
- Better suited for machine learning models
"""

# mypy: disable-error-code="operator, misc"

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from alpaca.data.models import Bar, Trade

logger = logging.getLogger(__name__)


class BarType(Enum):
    """Types of information-driven bars"""

    TICK = "tick"
    VOLUME = "volume"
    DOLLAR = "dollar"
    TICK_IMBALANCE = "tick_imbalance"
    VOLUME_IMBALANCE = "volume_imbalance"
    DOLLAR_IMBALANCE = "dollar_imbalance"


@dataclass
class InformationBar:
    """Universal bar structure for all information-driven bar types"""

    symbol: str
    bar_type: BarType
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: float
    dollar_volume: float
    trade_count: int
    timestamp_open: datetime
    timestamp_close: datetime

    # Microstructure metrics
    buy_volume: float
    sell_volume: float
    volume_imbalance: float  # (buy_volume - sell_volume) / total_volume
    tick_imbalance: float  # (buy_ticks - sell_ticks) / total_ticks
    dollar_imbalance: float  # (buy_dollars - sell_dollars) / total_dollars

    # Statistical properties
    returns: float | None = None
    log_returns: float | None = None
    realized_volatility: float | None = None

    # Sampling information
    threshold_value: float = 0.0  # The threshold that triggered this bar
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for DataFrame creation"""
        return {
            "symbol": self.symbol,
            "bar_type": self.bar_type.value,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "vwap": self.vwap,
            "dollar_volume": self.dollar_volume,
            "trade_count": self.trade_count,
            "timestamp_open": self.timestamp_open,
            "timestamp_close": self.timestamp_close,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "volume_imbalance": self.volume_imbalance,
            "tick_imbalance": self.tick_imbalance,
            "dollar_imbalance": self.dollar_imbalance,
            "returns": self.returns,
            "log_returns": self.log_returns,
            "realized_volatility": self.realized_volatility,
            "threshold_value": self.threshold_value,
            "duration_seconds": self.duration_seconds,
        }


class UniversalBarAggregator:
    """
    Universal aggregator for all types of information-driven bars

    Implements the generalized algorithm from López de Prado's AFML book
    for creating tick, volume, dollar, and imbalance bars.
    """

    def __init__(
        self,
        symbol: str,
        bar_type: BarType,
        threshold: float,
        lookback_bars: int = 100,
        on_bar_complete: Callable[[InformationBar], None] | None = None,
        use_dynamic_threshold: bool = False,
        use_bars: bool = False,
    ):
        self.symbol = symbol
        self.bar_type = bar_type
        self.base_threshold = threshold
        self.current_threshold = threshold
        self.lookback_bars = lookback_bars
        self.on_bar_complete = on_bar_complete
        self.use_dynamic_threshold = use_dynamic_threshold
        self.use_bars = use_bars

        # Current bar construction
        self.reset_current_bar()

        # Historical bars
        self.completed_bars: deque = deque(maxlen=lookback_bars)

        # For dynamic threshold adjustment
        self.threshold_history: deque = deque(maxlen=50)

        # For imbalance bars
        self.expected_imbalance = 0.0
        self.imbalance_window: deque = deque(maxlen=20)

    def reset_current_bar(self):
        """Reset current bar accumulation"""
        self.current_value = 0.0  # Current accumulated value (ticks/volume/dollars)
        self.current_trades: list[Trade] = []
        self.current_bars: list[Bar] = []
        self.current_prices: list[float] = []
        self.current_volumes: list[float] = []
        self.current_dollars: list[float] = []
        self.buy_ticks = 0
        self.sell_ticks = 0
        self.buy_volume = 0.0
        self.sell_volume = 0.0
        self.buy_dollars = 0.0
        self.sell_dollars = 0.0
        self.previous_price: float | None = None

    def process_trade(self, trade: Trade) -> InformationBar | None:
        """Process a single trade and return completed bar if threshold is reached"""
        if self.use_bars:
            raise ValueError(
                "Aggregator is configured for bars, not trades. Use process_bar() instead."
            )

        # Classify trade direction (tick rule)
        direction = self._classify_trade_direction(trade.price)

        # Update accumulation based on bar type
        self._update_accumulation_trade(trade, direction)

        # Store trade data
        self.current_trades.append(trade)
        self.current_prices.append(trade.price)
        self.current_volumes.append(trade.size)
        self.current_dollars.append(trade.price * trade.size)

        # Check if we should complete the bar
        if self._should_complete_bar():
            bar = self._create_bar()
            self.reset_current_bar()

            # Store completed bar
            self.completed_bars.append(bar)
            self.threshold_history.append(bar.threshold_value)

            # Update dynamic threshold if enabled
            if self.use_dynamic_threshold:
                self._update_dynamic_threshold()

            # Update expected imbalance for imbalance bars
            if self.bar_type in [
                BarType.TICK_IMBALANCE,
                BarType.VOLUME_IMBALANCE,
                BarType.DOLLAR_IMBALANCE,
            ]:
                self._update_expected_imbalance(bar)

            # Calculate returns if we have history
            if len(self.completed_bars) > 1:
                prev_bar = self.completed_bars[-2]
                bar.returns = (bar.close - prev_bar.close) / prev_bar.close
                bar.log_returns = np.log(bar.close / prev_bar.close)

            # Trigger callback
            if self.on_bar_complete:
                self.on_bar_complete(bar)

            return bar

        # Update previous price
        self.previous_price = trade.price
        return None

    def process_bar(self, bar: Bar) -> InformationBar | None:
        """Process a bar (e.g., 1-minute bar) and return completed information bar if threshold is reached"""
        if not self.use_bars:
            raise ValueError(
                "Aggregator is configured for trades, not bars. Use process_trade() instead."
            )

        # Estimate trade direction from bar
        direction = self._classify_bar_direction(bar)

        # Update accumulation based on bar type
        self._update_accumulation_bar(bar, direction)

        # Store bar data
        self.current_bars.append(bar)
        self.current_prices.extend([bar.open, bar.high, bar.low, bar.close])
        self.current_volumes.append(bar.volume)
        self.current_dollars.append(
            bar.vwap * bar.volume if hasattr(bar, "vwap") else bar.close * bar.volume  # type: ignore[operator]
        )

        # Check if we should complete the bar
        if self._should_complete_bar():
            info_bar = self._create_bar_from_bars()
            self.reset_current_bar()

            # Store completed bar
            self.completed_bars.append(info_bar)
            self.threshold_history.append(info_bar.threshold_value)

            # Update dynamic threshold if enabled
            if self.use_dynamic_threshold:
                self._update_dynamic_threshold()

            # Update expected imbalance for imbalance bars
            if self.bar_type in [
                BarType.TICK_IMBALANCE,
                BarType.VOLUME_IMBALANCE,
                BarType.DOLLAR_IMBALANCE,
            ]:
                self._update_expected_imbalance(info_bar)

            # Calculate returns if we have history
            if len(self.completed_bars) > 1:
                prev_bar = self.completed_bars[-2]
                info_bar.returns = (info_bar.close - prev_bar.close) / prev_bar.close
                info_bar.log_returns = np.log(info_bar.close / prev_bar.close)

            # Trigger callback
            if self.on_bar_complete:
                self.on_bar_complete(info_bar)

            return info_bar

        # Update previous price
        self.previous_price = bar.close
        return None

    def _classify_trade_direction(self, price: float) -> int:
        """Classify trade direction using tick rule (-1, 0, 1)"""
        if self.previous_price is None:
            return 0
        elif price > self.previous_price:
            return 1
        elif price < self.previous_price:
            return -1
        else:
            return 0

    def _classify_bar_direction(self, bar: Bar) -> float:
        """Estimate net direction from a bar"""
        # Use close vs open as primary indicator
        if bar.close > bar.open:
            return 0.7  # 70% buy direction
        elif bar.close < bar.open:
            return -0.7  # 70% sell direction
        else:
            # Use comparison with previous close
            if self.previous_price and bar.close > self.previous_price:
                return 0.5
            elif self.previous_price and bar.close < self.previous_price:
                return -0.5
            else:
                return 0

    def _update_accumulation_trade(self, trade: Trade, direction: int) -> None:
        """Update accumulation based on bar type and trade"""
        trade_value = trade.price * trade.size

        # Update directional metrics
        if direction > 0:
            self.buy_ticks += 1
            self.buy_volume += trade.size
            self.buy_dollars += trade_value
        elif direction < 0:
            self.sell_ticks += 1
            self.sell_volume += trade.size
            self.sell_dollars += trade_value
        else:
            # Split evenly for neutral trades
            self.buy_ticks += 0.5  # type: ignore[assignment]
            self.sell_ticks += 0.5  # type: ignore[assignment]
            self.buy_volume += trade.size / 2
            self.sell_volume += trade.size / 2
            self.buy_dollars += trade_value / 2
            self.sell_dollars += trade_value / 2

        # Update current value based on bar type
        if self.bar_type == BarType.TICK:
            self.current_value += 1
        elif self.bar_type == BarType.VOLUME:
            self.current_value += trade.size
        elif self.bar_type == BarType.DOLLAR:
            self.current_value += trade_value
        elif self.bar_type == BarType.TICK_IMBALANCE:
            # Accumulate signed ticks
            self.current_value += abs(direction * self._get_expected_imbalance())
        elif self.bar_type == BarType.VOLUME_IMBALANCE:
            # Accumulate signed volume
            self.current_value += abs(direction * trade.size * self._get_expected_imbalance())
        elif self.bar_type == BarType.DOLLAR_IMBALANCE:
            # Accumulate signed dollars
            self.current_value += abs(direction * trade_value * self._get_expected_imbalance())

    def _update_accumulation_bar(self, bar: Bar, direction: float) -> None:
        """Update accumulation based on bar type and bar data"""
        bar_value = bar.vwap * bar.volume if hasattr(bar, "vwap") else bar.close * bar.volume  # type: ignore[operator]
        trade_count = bar.trade_count if hasattr(bar, "trade_count") else 1

        # Estimate directional metrics from bar
        buy_ratio = (1 + direction) / 2  # Convert [-1, 1] to [0, 1]
        sell_ratio = 1 - buy_ratio

        self.buy_ticks += trade_count * buy_ratio  # type: ignore[assignment]
        self.sell_ticks += trade_count * sell_ratio  # type: ignore[assignment]
        self.buy_volume += bar.volume * buy_ratio
        self.sell_volume += bar.volume * sell_ratio
        self.buy_dollars += bar_value * buy_ratio
        self.sell_dollars += bar_value * sell_ratio

        # Update current value based on bar type
        if self.bar_type == BarType.TICK:
            self.current_value += trade_count  # type: ignore[operator]
        elif self.bar_type == BarType.VOLUME:
            self.current_value += bar.volume
        elif self.bar_type == BarType.DOLLAR:
            self.current_value += bar_value
        elif self.bar_type == BarType.TICK_IMBALANCE:
            self.current_value += abs(direction * trade_count * self._get_expected_imbalance())  # type: ignore[operator]
        elif self.bar_type == BarType.VOLUME_IMBALANCE:
            self.current_value += abs(direction * bar.volume * self._get_expected_imbalance())
        elif self.bar_type == BarType.DOLLAR_IMBALANCE:
            self.current_value += abs(direction * bar_value * self._get_expected_imbalance())

    def _should_complete_bar(self) -> bool:
        """Check if current accumulation has reached threshold"""
        return self.current_value >= self.current_threshold

    def _get_expected_imbalance(self) -> float:
        """Get expected imbalance for imbalance bars"""
        if not self.imbalance_window:
            return 0.0
        # Use exponentially weighted average of recent imbalances
        weights = np.exp(np.linspace(-1, 0, len(self.imbalance_window)))
        weights /= weights.sum()
        return np.average(list(self.imbalance_window), weights=weights)

    def _update_expected_imbalance(self, bar: InformationBar) -> None:
        """Update expected imbalance based on completed bar"""
        if self.bar_type == BarType.TICK_IMBALANCE:
            self.imbalance_window.append(bar.tick_imbalance)
        elif self.bar_type == BarType.VOLUME_IMBALANCE:
            self.imbalance_window.append(bar.volume_imbalance)
        elif self.bar_type == BarType.DOLLAR_IMBALANCE:
            self.imbalance_window.append(bar.dollar_imbalance)

    def _update_dynamic_threshold(self):
        """Update dynamic threshold based on recent history"""
        if len(self.threshold_history) < 10:
            return

        # Use EWMA of recent thresholds
        weights = np.exp(np.linspace(-1, 0, len(self.threshold_history)))
        weights /= weights.sum()
        dynamic_threshold = np.average(list(self.threshold_history), weights=weights)

        # Bound between 0.5x and 2x original threshold
        self.current_threshold = np.clip(
            dynamic_threshold, self.base_threshold * 0.5, self.base_threshold * 2.0
        )

    def _create_bar(self) -> InformationBar:
        """Create an information bar from accumulated trades"""
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
        total_volume = np.sum(volumes)
        vwap = np.sum(prices * volumes) / total_volume if total_volume > 0 else close_price

        # Calculate dollar volume
        dollar_volume = np.sum(self.current_dollars)

        # Calculate imbalances
        total_ticks = self.buy_ticks + self.sell_ticks
        tick_imbalance = (self.buy_ticks - self.sell_ticks) / total_ticks if total_ticks > 0 else 0

        volume_imbalance = (
            (self.buy_volume - self.sell_volume) / total_volume if total_volume > 0 else 0
        )

        total_dollars = self.buy_dollars + self.sell_dollars
        dollar_imbalance = (
            (self.buy_dollars - self.sell_dollars) / total_dollars if total_dollars > 0 else 0
        )

        # Calculate duration
        duration = (
            self.current_trades[-1].timestamp - self.current_trades[0].timestamp
        ).total_seconds()

        return InformationBar(
            symbol=self.symbol,
            bar_type=self.bar_type,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
            vwap=vwap,
            dollar_volume=dollar_volume,
            trade_count=len(self.current_trades),
            timestamp_open=self.current_trades[0].timestamp,
            timestamp_close=self.current_trades[-1].timestamp,
            buy_volume=self.buy_volume,
            sell_volume=self.sell_volume,
            volume_imbalance=volume_imbalance,
            tick_imbalance=tick_imbalance,
            dollar_imbalance=dollar_imbalance,
            threshold_value=self.current_value,
            duration_seconds=duration,
        )

    def _create_bar_from_bars(self) -> InformationBar:
        """Create an information bar from accumulated Bar objects"""
        if not self.current_bars:
            raise ValueError("Cannot create bar without bars")

        # Get first and last bars for timestamps
        first_bar = self.current_bars[0]
        last_bar = self.current_bars[-1]

        # Calculate OHLC across all accumulated bars
        open_price = first_bar.open
        close_price = last_bar.close
        high_price = max(bar.high for bar in self.current_bars)
        low_price = min(bar.low for bar in self.current_bars)

        # Calculate volume-weighted average price using pre-computed VWAPs
        total_volume = sum(bar.volume for bar in self.current_bars)
        if total_volume > 0:
            vwap = (
                sum(
                    bar.vwap * bar.volume if hasattr(bar, "vwap") else bar.close * bar.volume  # type: ignore[operator]
                    for bar in self.current_bars
                )
                / total_volume
            )
        else:
            vwap = close_price

        # Calculate dollar volume
        dollar_volume = sum(self.current_dollars)

        # Calculate imbalances
        total_ticks = self.buy_ticks + self.sell_ticks
        tick_imbalance = (self.buy_ticks - self.sell_ticks) / total_ticks if total_ticks > 0 else 0

        volume_imbalance = (
            (self.buy_volume - self.sell_volume) / total_volume if total_volume > 0 else 0
        )

        total_dollars = self.buy_dollars + self.sell_dollars
        dollar_imbalance = (
            (self.buy_dollars - self.sell_dollars) / total_dollars if total_dollars > 0 else 0
        )

        # Sum trade counts
        total_trade_count = sum(
            bar.trade_count if hasattr(bar, "trade_count") else 1 for bar in self.current_bars  # type: ignore[misc]
        )

        # Calculate duration
        duration = (last_bar.timestamp - first_bar.timestamp).total_seconds()

        return InformationBar(
            symbol=self.symbol,
            bar_type=self.bar_type,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=total_volume,
            vwap=vwap,
            dollar_volume=dollar_volume,
            trade_count=total_trade_count,
            timestamp_open=first_bar.timestamp,
            timestamp_close=last_bar.timestamp,
            buy_volume=self.buy_volume,
            sell_volume=self.sell_volume,
            volume_imbalance=volume_imbalance,
            tick_imbalance=tick_imbalance,
            dollar_imbalance=dollar_imbalance,
            threshold_value=self.current_value,
            duration_seconds=duration,
        )

    def get_bars_dataframe(self) -> pd.DataFrame:
        """Get completed bars as a pandas DataFrame"""
        if not self.completed_bars:
            return pd.DataFrame()

        bars_data = [bar.to_dict() for bar in self.completed_bars]
        df = pd.DataFrame(bars_data)
        df.set_index("timestamp_close", inplace=True)
        return df

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about the information bars"""
        if not self.completed_bars:
            return {}

        df = self.get_bars_dataframe()

        # Calculate returns if not already present
        if "returns" not in df.columns or df["returns"].isna().all():
            df["returns"] = df["close"].pct_change()
            df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Calculate realized volatility
        df["realized_vol"] = df["log_returns"].rolling(window=20).std() * np.sqrt(252)

        stats = {
            "bar_type": self.bar_type.value,
            "total_bars": len(self.completed_bars),
            "current_threshold": self.current_threshold,
            "avg_threshold_value": (
                df["threshold_value"].mean() if "threshold_value" in df.columns else None
            ),
            "avg_duration_seconds": df["duration_seconds"].mean(),
            "avg_volume": df["volume"].mean(),
            "avg_dollar_volume": df["dollar_volume"].mean(),
            "avg_trade_count": df["trade_count"].mean(),
            # Microstructure metrics
            "avg_volume_imbalance": df["volume_imbalance"].mean(),
            "avg_tick_imbalance": df["tick_imbalance"].mean(),
            "avg_dollar_imbalance": df["dollar_imbalance"].mean(),
            "imbalance_autocorr": df["volume_imbalance"].autocorr(lag=1) if len(df) > 1 else None,
            # Returns analysis
            "returns_mean": df["returns"].mean(),
            "returns_std": df["returns"].std(),
            "returns_skew": df["returns"].skew(),
            "returns_kurtosis": df["returns"].kurtosis(),
            "sharpe_ratio": (
                df["returns"].mean() / df["returns"].std() * np.sqrt(252)
                if df["returns"].std() > 0
                else None
            ),
            # Autocorrelation at different lags
            "autocorr_lag1": df["returns"].autocorr(lag=1) if len(df) > 1 else None,
            "autocorr_lag5": df["returns"].autocorr(lag=5) if len(df) > 5 else None,
            "autocorr_lag10": df["returns"].autocorr(lag=10) if len(df) > 10 else None,
            # Jarque-Bera test for normality
            "jarque_bera": self._jarque_bera_test(df["returns"].dropna()),
            # Efficiency metrics
            "bars_per_hour": (
                len(df) / (df["duration_seconds"].sum() / 3600)
                if df["duration_seconds"].sum() > 0
                else None
            ),
        }

        return stats

    def _jarque_bera_test(self, returns: pd.Series) -> dict[str, float]:
        """Perform Jarque-Bera test for normality"""
        if len(returns) < 3:
            return {"statistic": None, "p_value": None}  # type: ignore[dict-item]

        from scipy import stats  # type: ignore[import-untyped]

        jb_stat, jb_pvalue = stats.jarque_bera(returns)
        return {"statistic": jb_stat, "p_value": jb_pvalue}

    def get_trading_signals(self) -> dict[str, Any]:
        """Generate trading signals based on bar patterns"""
        if len(self.completed_bars) < 3:
            return {"signal": "NEUTRAL", "confidence": 0.0}

        df = self.get_bars_dataframe()
        latest_bar = self.completed_bars[-1]

        signals = []
        confidence_scores = []

        # Signal 1: Volume imbalance
        if abs(latest_bar.volume_imbalance) > 0.6:
            if latest_bar.volume_imbalance > 0:
                signals.append("BUY")
                confidence_scores.append(min(latest_bar.volume_imbalance, 1.0))
            else:
                signals.append("SELL")
                confidence_scores.append(min(abs(latest_bar.volume_imbalance), 1.0))

        # Signal 2: Price vs VWAP
        vwap_deviation = (latest_bar.close - latest_bar.vwap) / latest_bar.vwap
        if abs(vwap_deviation) > 0.002:  # 0.2% threshold
            if vwap_deviation < 0 and latest_bar.volume_imbalance > 0:
                signals.append("BUY")
                confidence_scores.append(0.7)
            elif vwap_deviation > 0 and latest_bar.volume_imbalance < 0:
                signals.append("SELL")
                confidence_scores.append(0.7)

        # Signal 3: Microstructure pattern (sequential imbalances)
        if len(df) >= 3:
            recent_imbalances = df["volume_imbalance"].tail(3).values
            if all(imb > 0.3 for imb in recent_imbalances):
                signals.append("BUY")
                confidence_scores.append(0.8)
            elif all(imb < -0.3 for imb in recent_imbalances):
                signals.append("SELL")
                confidence_scores.append(0.8)

        # Aggregate signals
        if not signals:
            return {"signal": "NEUTRAL", "confidence": 0.0, "reasons": []}

        buy_signals = signals.count("BUY")
        sell_signals = signals.count("SELL")

        if buy_signals > sell_signals:
            signal = "BUY"
            confidence = np.mean(
                [c for s, c in zip(signals, confidence_scores, strict=False) if s == "BUY"]
            )
        elif sell_signals > buy_signals:
            signal = "SELL"
            confidence = np.mean(
                [c for s, c in zip(signals, confidence_scores, strict=False) if s == "SELL"]
            )
        else:
            signal = "NEUTRAL"
            confidence = 0.0

        return {
            "signal": signal,
            "confidence": confidence,
            "volume_imbalance": latest_bar.volume_imbalance,
            "tick_imbalance": latest_bar.tick_imbalance,
            "vwap_deviation": vwap_deviation,
            "recent_bars": len(self.completed_bars),
            "reasons": signals,
        }


def calculate_optimal_thresholds(
    symbol: str, historical_data: pd.DataFrame, target_bars_per_day: int = 50
) -> dict[str, float]:
    """
    Calculate optimal thresholds for different bar types based on historical data

    Args:
        symbol: Stock symbol
        historical_data: DataFrame with trade or bar data
        target_bars_per_day: Desired number of bars per trading day

    Returns:
        Dictionary with optimal thresholds for each bar type
    """
    # Calculate daily averages
    daily_ticks = len(historical_data) / historical_data.index.normalize().nunique()  # type: ignore[attr-defined]
    daily_volume = historical_data["volume"].sum() / historical_data.index.normalize().nunique()  # type: ignore[attr-defined]
    daily_dollars = (
        historical_data["volume"] * historical_data["close"]
    ).sum() / historical_data.index.normalize().nunique()  # type: ignore[attr-defined]

    return {
        "tick_threshold": daily_ticks / target_bars_per_day,
        "volume_threshold": daily_volume / target_bars_per_day,
        "dollar_threshold": daily_dollars / target_bars_per_day,
        "tick_imbalance_threshold": daily_ticks
        / (target_bars_per_day * 2),  # Imbalance bars need lower threshold
        "volume_imbalance_threshold": daily_volume / (target_bars_per_day * 2),
        "dollar_imbalance_threshold": daily_dollars / (target_bars_per_day * 2),
    }


if __name__ == "__main__":
    # Example usage
    print("Enhanced Volume Bars Implementation")
    print("=" * 60)
    print("Bar Types Available:")
    for bar_type in BarType:
        print(f"  • {bar_type.value.upper()} BARS")
    print("\nRefer to López de Prado's AFML Chapter 2 for theoretical background")
