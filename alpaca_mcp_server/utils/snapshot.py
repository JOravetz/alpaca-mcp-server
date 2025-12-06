import argparse
import asyncio
import os
from datetime import datetime, timedelta

import aiohttp
import numpy as np
import pandas as pd
import pandas_market_calendars as mcal  # type: ignore[import-untyped]
import requests

# Load Alpaca API credentials from the environment variables
API_KEY_ID = os.environ.get("APCA_API_KEY_ID")
SECRET_KEY_ID = os.environ.get("APCA_API_SECRET_KEY")
BASE_URL = "https://data.alpaca.markets"


class DictWrapper:
    def __init__(self, data):
        self.data = data or {}

    def __getattr__(self, name):
        mapping = {
            "price": "p",
            "close": "c",
            "high": "h",
            "low": "l",
            "open": "o",
            "volume": "v",
            "trades": "n",
            "vwap": "vw",
            "timestamp": "t",
            "exchange": "x",
            "conditions": "c",
            "size": "s",
            "ask_price": "ap",
            "ask_size": "as",
            "ask_exchange": "ax",
            "bid_price": "bp",
            "bid_size": "bs",
            "bid_exchange": "bx",
        }
        key = mapping.get(name, name)
        value = self.data.get(key)
        if isinstance(value, list) and len(value) == 1:
            return value[0]
        return value


class SnapshotAccessor:
    def __init__(self, data):
        self.data = data or {}

    def __getattr__(self, name):
        mapping = {
            "latest_trade": "latestTrade",
            "latest_quote": "latestQuote",
            "minute_bar": "minuteBar",
            "daily_bar": "dailyBar",
            "prev_daily_bar": "prevDailyBar",
        }
        key = mapping.get(name, name)
        value = self.data.get(key)
        if isinstance(value, dict):
            return DictWrapper(value)
        return value


def wrap_snapshot(snapshot):
    if isinstance(snapshot, dict):
        return SnapshotAccessor(snapshot)
    return snapshot


class PatternAnalyzer:
    def __init__(self) -> None:
        pass

    def detect_consolidation(self, high, low, volume, avg_volume):
        range_percent = (high - low) / low if low > 0 else 0
        return range_percent < 0.02 and volume < avg_volume * 0.8

    def detect_breakout_pattern(self, price, resistance, support, volume, avg_volume):
        if price > resistance and volume > avg_volume * 1.5:
            return "BREAKOUT_UP"
        elif price < support and volume > avg_volume * 1.5:
            return "BREAKOUT_DOWN"
        return None


class StockAnalyzer:
    def __init__(self) -> None:
        self.pattern_analyzer = PatternAnalyzer()

    def calculate_zscore(self, value, values):
        if not values or len(values) == 0:
            return 0
        mean = np.mean(values)
        std = np.std(values)
        if std == 0:
            return 0
        return (value - mean) / std

    def calculate_volatility(self, snapshot):
        try:
            daily_high = float(snapshot.daily_bar.high or 0)
            daily_low = float(snapshot.daily_bar.low or 0)
            daily_open = float(snapshot.daily_bar.open or 0)
            daily_close = float(snapshot.daily_bar.close or 0)

            prev_close = float(snapshot.prev_daily_bar.close or 0)

            true_range = max(
                daily_high - daily_low,
                abs(daily_high - prev_close),
                abs(daily_low - prev_close),
            )

            volatility = true_range / max(prev_close, 0.01) * 100
            intraday_volatility = (daily_high - daily_low) / max(daily_open, 0.01) * 100
            price_velocity = abs(daily_close - daily_open) / max(daily_high - daily_low, 0.01)

            return {
                "volatility": volatility,
                "intraday_volatility": intraday_volatility,
                "price_velocity": price_velocity,
            }
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return {"volatility": 0, "intraday_volatility": 0, "price_velocity": 0}

    def analyze_volume_pattern(self, snapshot, historical_volumes, historical_trades):
        try:
            # Get raw values
            minute_vol = float(snapshot.minute_bar.volume or 0)
            daily_vol = float(snapshot.daily_bar.volume or 0)
            trades = int(snapshot.daily_bar.trades or 0)

            # Filter out zero volumes from historical data
            historical_volumes = [v for v in historical_volumes if v > 0]
            if not historical_volumes:
                historical_volumes = [daily_vol]

            # Calculate metrics
            avg_minute_vol = max(daily_vol / 390, 1)  # Prevent division by zero
            vol_acceleration = minute_vol / avg_minute_vol

            # Calculate z-scores
            trades_zscore = self.calculate_zscore(trades, historical_trades)
            avg_historical_volume = np.mean(historical_volumes)
            if avg_historical_volume < 1:
                avg_historical_volume = 1  # Prevent division by zero or very small numbers
            vol_ratio = daily_vol / avg_historical_volume
            vol_zscore = self.calculate_zscore(daily_vol, historical_volumes)

            return {
                "vol_acceleration": vol_acceleration,
                "vol_ratio": vol_ratio,
                "trades": trades,
                "trades_zscore": trades_zscore,
                "volume_zscore": vol_zscore,
            }
        except Exception:
            return {
                "vol_acceleration": 0,
                "vol_ratio": 0,
                "trades": 0,
                "trades_zscore": 0,
                "volume_zscore": 0,
            }

    def analyze_price_velocity(self, snapshot):
        try:
            current_price = float(snapshot.latest_trade.price or 0)
            minute_vwap = float(snapshot.minute_bar.vwap or 0)
            daily_vwap = float(snapshot.daily_bar.vwap or 0)
            prev_vwap = float(snapshot.prev_daily_bar.vwap or 0)

            minute_velocity = (current_price - minute_vwap) / max(minute_vwap, 0.01)
            daily_velocity = (current_price - daily_vwap) / max(daily_vwap, 0.01)
            multi_day_velocity = (current_price - prev_vwap) / max(prev_vwap, 0.01)

            return {
                "minute_velocity": minute_velocity,
                "daily_velocity": daily_velocity,
                "multi_day_velocity": multi_day_velocity,
            }
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return {"minute_velocity": 0, "daily_velocity": 0, "multi_day_velocity": 0}

    def analyze_breakout_potential(self, snapshot):
        try:
            price = float(snapshot.latest_trade.price or 0)
            daily_high = float(snapshot.daily_bar.high or 0)
            daily_low = float(snapshot.daily_bar.low or 0)
            prev_high = float(snapshot.prev_daily_bar.high or 0)
            prev_low = float(snapshot.prev_daily_bar.low or 0)

            resistance = max(daily_high, prev_high)
            support = min(daily_low, prev_low)
            range_size = resistance - support

            dist_to_resistance = (resistance - price) / max(price, 0.01)
            dist_to_support = (price - support) / max(price, 0.01)

            minute_trades = int(snapshot.minute_bar.trades or 0)
            daily_trades = int(snapshot.daily_bar.trades or 0)

            trade_acceleration = minute_trades / (max(daily_trades / 390, 1)) if daily_trades else 0

            return {
                "range_size": range_size,
                "dist_to_resistance": dist_to_resistance,
                "dist_to_support": dist_to_support,
                "trade_acceleration": trade_acceleration,
            }
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return {
                "range_size": 0,
                "dist_to_resistance": 0,
                "dist_to_support": 0,
                "trade_acceleration": 0,
            }

    def analyze_momentum_exhaustion(self, snapshot):
        try:
            price = float(snapshot.latest_trade.price or 0)
            minute_vwap = float(snapshot.minute_bar.vwap or 0)
            daily_vwap = float(snapshot.daily_bar.vwap or 0)
            daily_high = float(snapshot.daily_bar.high or 0)
            daily_low = float(snapshot.daily_bar.low or 0)

            price_position = (
                (price - daily_low) / (daily_high - daily_low)
                if (daily_high - daily_low) > 0
                else 0.5
            )
            minute_vwap_divergence = (price - minute_vwap) / max(minute_vwap, 0.01)
            daily_vwap_divergence = (price - daily_vwap) / max(daily_vwap, 0.01)

            minute_vol = float(snapshot.minute_bar.volume or 0)
            daily_vol = float(snapshot.daily_bar.volume or 0)
            volume_exhaustion = minute_vol / (max(daily_vol / 390, 1)) if daily_vol else 0

            return {
                "price_position": price_position,
                "minute_vwap_divergence": minute_vwap_divergence,
                "daily_vwap_divergence": daily_vwap_divergence,
                "volume_exhaustion": volume_exhaustion,
            }
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return {
                "price_position": 0,
                "minute_vwap_divergence": 0,
                "daily_vwap_divergence": 0,
                "volume_exhaustion": 0,
            }

    def generate_signals(
        self,
        snapshot,
        breakout_data,
        momentum_data,
        volume_data,
        velocity_data,
        volatility_data,
    ):
        signals = []
        signal_strength = 0

        try:
            # Price position signals
            if momentum_data:
                if momentum_data["price_position"] > 0.9:
                    signals.append("NEAR_DAY_HIGH")
                elif momentum_data["price_position"] < 0.1:
                    signals.append("NEAR_DAY_LOW")

            # Momentum signals
            if velocity_data and volume_data:
                if velocity_data["minute_velocity"] > 0.01 and volume_data["vol_ratio"] > 1.5:
                    signals.append("STRONG_UPWARD_MOMENTUM")
                    signal_strength += 2
                elif velocity_data["minute_velocity"] < -0.01 and volume_data["vol_ratio"] > 1.5:
                    signals.append("STRONG_DOWNWARD_MOMENTUM")
                    signal_strength -= 2

            # Volatility signals
            if (
                volatility_data
                and volatility_data["volatility"] > 3.0
                and volume_data
                and volume_data["trades_zscore"] > 2.0
            ):
                signals.append("HIGH_VOLATILITY_WITH_VOLUME")
                signal_strength += abs(velocity_data["minute_velocity"] * 2) if velocity_data else 1

            # Pattern signals
            price = float(snapshot.latest_trade.price or 0)
            daily_high = float(snapshot.daily_bar.high or 0)
            daily_low = float(snapshot.daily_bar.low or 0)
            avg_volume = (
                np.mean(volume_data["vol_ratio"])
                if isinstance(volume_data["vol_ratio"], list)
                else volume_data["vol_ratio"]
            )

            if self.pattern_analyzer.detect_consolidation(
                daily_high, daily_low, float(snapshot.daily_bar.volume or 0), avg_volume
            ):
                signals.append("CONSOLIDATION")

            pattern = self.pattern_analyzer.detect_breakout_pattern(
                price,
                daily_high,
                daily_low,
                float(snapshot.daily_bar.volume or 0),
                avg_volume,
            )
            if pattern:
                signals.append(pattern)
                signal_strength += 2 if pattern == "BREAKOUT_UP" else -2

            return signals, signal_strength

        except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError):
            return [], 0


async def fetch_historical_data(symbols, timeframe="1Day", trading_days=15):
    """Fetch historical data for symbols asynchronously."""
    try:
        config = {
            "APCA_API_KEY_ID": API_KEY_ID,
            "APCA_API_SECRET_KEY": SECRET_KEY_ID,
        }

        base_url = f"{BASE_URL}/v2/stocks/bars"
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": config["APCA_API_KEY_ID"],
            "APCA-API-SECRET-KEY": config["APCA_API_SECRET_KEY"],
        }

        nyse = mcal.get_calendar("NYSE")
        today = pd.Timestamp(datetime.now().date())
        schedule = nyse.valid_days(start_date=today - timedelta(days=5000), end_date=today)
        end_date = schedule[-1] if today in schedule else schedule[-1]
        start_date = schedule[-trading_days]

        params = {
            "timeframe": timeframe,
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "limit": 10000,
            "adjustment": "split",
            "feed": "sip",
            "sort": "asc",
        }

        chunk_size = max(1, 200 // trading_days)
        symbol_chunks = [symbols[i : i + chunk_size] for i in range(0, len(symbols), chunk_size)]

        async with aiohttp.ClientSession() as session:
            tasks = []
            for chunk in symbol_chunks:
                params["symbols"] = ",".join(chunk)
                tasks.append(fetch_symbol_data(session, base_url, params.copy(), headers))

            results = await asyncio.gather(*tasks)

        all_data = {}
        for result in results:
            all_data.update(result)

        return all_data

    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return {}


async def fetch_symbol_data(session, url, params, headers):
    """Fetch historical data for a group of symbols."""
    all_data = {}  # type: ignore[var-annotated]
    try:
        while True:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    for symbol, bars in data.get("bars", {}).items():
                        if symbol not in all_data:
                            all_data[symbol] = []
                        all_data[symbol].extend(bars)

                    next_page_token = data.get("next_page_token")
                    if next_page_token:
                        params["page_token"] = next_page_token
                    else:
                        break
                else:
                    error_text = await response.text()
                    print(f"Error fetching data: {error_text}")
                    break

        return all_data

    except Exception as e:
        print(f"Error in fetch_symbol_data: {e}")
        return {}


def run(args):
    symbol_list = str(args.list)
    min_price = float(args.min_price) if args.min_price else 0.0
    min_volume = int(args.min_volume) if args.min_volume else 0
    sort_column = args.sort if args.sort else "percent_change"
    timeframe = args.timeframe
    trading_days = int(args.trading_days)

    print("\nInitializing analysis...")

    if symbol_list:
        try:
            with open(symbol_list) as file:
                universe = [row.strip().split()[0].upper() for row in file if row.strip() != ""]
            print(f"Read {len(universe)} symbols from {symbol_list}")
        except Exception as e:
            print(f"Error reading {symbol_list}: {e}")
            universe = []
            print("No symbols to process.")
            return
    else:
        print("No symbol list provided.")
        return

    print("Fetching market data...")
    try:
        symbols = ",".join(universe)
        url = f"{BASE_URL}/v2/stocks/snapshots?symbols={symbols}&feed=sip"
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": API_KEY_ID,
            "APCA-API-SECRET-KEY": SECRET_KEY_ID,
        }
        response = requests.get(url, headers=headers)  # type: ignore[arg-type]
        snapshots = response.json()
        print(f"Retrieved data for {len(snapshots)} symbols")
    except Exception as e:
        print(f"Error fetching snapshots: {e}")
        return

    # Fetch historical data for Z-Score calculation
    print("Fetching historical data for Z-Score calculation...")
    historical_data = asyncio.run(
        fetch_historical_data(universe, timeframe=timeframe, trading_days=trading_days)
    )

    analyzer = StockAnalyzer()
    filtered_count = 0
    price_filtered = 0
    volume_filtered = 0
    error_count = 0

    analysis_results = []

    print(f"\nApplying filters (min_price: ${min_price}, min_volume: {min_volume:,})")

    for symbol in universe:
        try:
            raw_snapshot = snapshots.get(symbol)
            if not raw_snapshot:
                filtered_count += 1
                continue

            snapshot = wrap_snapshot(raw_snapshot)
            if not snapshot or not snapshot.latest_trade:
                filtered_count += 1
                continue

            price = float(snapshot.latest_trade.price or 0)
            if price < min_price:
                price_filtered += 1
                continue

            daily_vol = float(snapshot.daily_bar.volume or 0)
            if daily_vol < min_volume:
                volume_filtered += 1
                continue

            # Get historical volumes and trades for Z-Score calculation
            symbol_bars = historical_data.get(symbol, [])
            historical_volumes = [bar["v"] for bar in symbol_bars if "v" in bar]
            historical_trades = [bar.get("n", 0) for bar in symbol_bars]

            # Ensure we have enough data
            if len(historical_volumes) < 2:
                historical_volumes.append(daily_vol)
            if len(historical_trades) < 2:
                historical_trades.append(int(snapshot.daily_bar.trades or 0))

            # Calculate all metrics
            breakout_data = analyzer.analyze_breakout_potential(snapshot)
            momentum_data = analyzer.analyze_momentum_exhaustion(snapshot)
            volume_data = analyzer.analyze_volume_pattern(
                snapshot, historical_volumes, historical_trades
            )
            velocity_data = analyzer.analyze_price_velocity(snapshot)
            volatility_data = analyzer.calculate_volatility(snapshot)

            signals, signal_strength = analyzer.generate_signals(
                snapshot,
                breakout_data,
                momentum_data,
                volume_data,
                velocity_data,
                volatility_data,
            )

            # Calculate percent change
            prev_close = float(snapshot.prev_daily_bar.close or 0)
            percent_change = ((price - prev_close) / max(prev_close, 0.01)) * 100

            # Store results
            result = {
                "symbol": symbol,
                "price": price,
                "percent_change": percent_change,
                "signal_strength": signal_strength,
                "volume_ratio": volume_data.get("vol_ratio", 0),
                "volume_acceleration": volume_data.get("vol_acceleration", 0),
                "volatility": volatility_data.get("volatility", 0),
                "vwap_divergence": momentum_data.get("daily_vwap_divergence", 0),
                "trades": volume_data.get("trades", 0),
                "trades_zscore": volume_data.get("trades_zscore", 0),
                "volume_zscore": volume_data.get("volume_zscore", 0),
                "signals": signals,
            }

            analysis_results.append(result)

        except Exception:
            error_count += 1
            continue

    print("\nFiltering results:")
    print(f"No data: {filtered_count}")
    print(f"Price < ${min_price}: {price_filtered}")
    print(f"Volume < {min_volume:,}: {volume_filtered}")
    print(f"Errors: {error_count}")
    print(f"Passing symbols: {len(analysis_results)}")

    # Sort results in ascending order
    analysis_results.sort(key=lambda x: x.get(sort_column, 0), reverse=False)

    # Print results
    print("\nAdvanced Market Analysis Report")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        "\nSymbol  Price     %Chg    Vol.Rat  Vol.Acc  Volat.  VWAP.Div  Trades  Z-Score  Vol-Z  Str  Signals"
    )
    print("-" * 140)

    for result in analysis_results:
        signal_str = ", ".join(result["signals"]) if result["signals"] else ""
        print(
            f"{result['symbol']:<6} {result['price']:8.3f} {result['percent_change']:8.2f} "
            f"{result['volume_ratio']:8.2f} {result['volume_acceleration']:8.2f} "
            f"{result['volatility']:8.2f} {result['vwap_divergence']:9.2f} "
            f"{int(result['trades']):7d} {result['trades_zscore']:8.2f} {result['volume_zscore']:6.2f} "
            f"{int(result['signal_strength']):4d}  {signal_str}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Advanced stock market analysis tool")
    parser.add_argument(
        "--list",
        type=str,
        default="combined.lis",
        help="Symbol list (default: combined.lis)",
    )
    parser.add_argument(
        "--min-price",
        type=float,
        default=0.0,
        help="Minimum price filter (default=0.0)",
    )
    parser.add_argument(
        "--min-volume", type=int, default=0, help="Minimum volume filter (default=0)"
    )
    parser.add_argument(
        "--sort",
        type=str,
        default="percent_change",
        help="Sort column (percent_change, signal_strength, volume_ratio, etc.)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1Day",
        help="Timeframe for historical data (default: 1Day)",
    )
    parser.add_argument(
        "--trading-days",
        type=int,
        default=15,
        help="Number of trading days for baseline computations (default: 15)",
    )
    arguments = parser.parse_args()
    run(arguments)
