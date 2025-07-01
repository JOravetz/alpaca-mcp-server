"""Market momentum resource with real SPY data analysis."""

from datetime import datetime

import pytz
from alpaca.data.enums import DataFeed
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from ..config.settings import get_stock_historical_client
from ..tools.market_data_tools import get_stock_bars_intraday


async def get_market_momentum(
    symbol: str = "SPY",
    timeframe_minutes: int = 1,
    analysis_hours: int = 2,
    sma_short: int = 5,
    sma_long: int = 20,
) -> dict:
    """Calculate real market momentum using configurable parameters.

    Args:
        symbol: Stock symbol to analyze (default: SPY)
        timeframe_minutes: Bar timeframe in minutes (default: 1)
        analysis_hours: Hours of data to analyze (default: 2)
        sma_short: Short moving average period (default: 5)
        sma_long: Long moving average period (default: 20)
    """
    try:
        # Use the working intraday data tool instead of direct API calls
        # This tool handles timezone, data feed, and paper trading limitations properly

        # Map timeframe to string format expected by the tool
        timeframe_map = {
            1: "1Min",
            5: "5Min",
            15: "15Min",
            30: "30Min",
            60: "1Hour",
        }

        timeframe_str = timeframe_map.get(timeframe_minutes, "1Min")

        # Calculate required bars based on SMAs and add buffer
        required_bars = max(sma_short, sma_long) * 2  # Double for safety

        # Use the working intraday tool to get data
        _ = await get_stock_bars_intraday(
            symbol=symbol,
            timeframe=timeframe_str,
            limit=required_bars,
        )

        # Parse the result to extract actual bar data
        # The tool returns formatted text, but we need to call the API directly with the same parameters

        # Fall back to direct API call using the same logic as the working tool
        data_client = get_stock_historical_client()
        eastern = pytz.timezone("America/New_York")

        # Use smart date range (copied from working tool)
        now_et = datetime.now(eastern)

        # Default to today's extended hours data (4 AM - 8 PM ET)
        start = eastern.localize(
            datetime.strptime(now_et.strftime("%Y-%m-%d"), "%Y-%m-%d").replace(hour=4, minute=0)
        )

        is_weekday = now_et.weekday() < 5

        if is_weekday and (4 <= now_et.hour <= 20):
            # Market is open or in extended hours, use current time
            end = now_et
        else:
            # Market closed, use end of extended hours
            end = eastern.localize(
                datetime.strptime(now_et.strftime("%Y-%m-%d"), "%Y-%m-%d").replace(
                    hour=20, minute=0
                )
            )

        # Map timeframe
        if timeframe_minutes == 1:
            timeframe = TimeFrame.Minute
        elif timeframe_minutes == 5:
            timeframe = TimeFrame(5, TimeFrameUnit.Minute)
        elif timeframe_minutes == 15:
            timeframe = TimeFrame(15, TimeFrameUnit.Minute)
        elif timeframe_minutes == 30:
            timeframe = TimeFrame(30, TimeFrameUnit.Minute)
        elif timeframe_minutes == 60:
            timeframe = TimeFrame.Hour
        else:
            timeframe = TimeFrame.Minute

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=required_bars,
            feed=DataFeed.SIP,
        )

        bars_data = data_client.get_stock_bars(request)
        symbol_bars = (
            list(bars_data.data[symbol]) if bars_data.data and symbol in bars_data.data else []
        )

        if len(symbol_bars) < max(sma_short, sma_long):
            return {
                "error": f"Insufficient {symbol} data for momentum calculation",
                "bars_received": len(symbol_bars),
                "required_bars": max(sma_short, sma_long),
                "symbol": symbol,
                "start_time_et": start.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "end_time_et": end.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "market_status": "weekday" if now_et.weekday() < 5 else "weekend",
                "hour_et": now_et.hour,
                "timeframe": str(timeframe),
                "last_updated": datetime.now().isoformat(),
            }

        # Calculate momentum metrics using configurable parameters
        prices = [float(bar.close) for bar in symbol_bars]
        current_price = prices[-1]

        # Dynamic SMA calculations based on user parameters
        sma_short_value = (
            sum(prices[-sma_short:]) / sma_short if len(prices) >= sma_short else current_price
        )
        sma_long_value = (
            sum(prices[-sma_long:]) / sma_long if len(prices) >= sma_long else current_price
        )

        # Trend direction calculation using dynamic SMAs
        if current_price > sma_short_value > sma_long_value:
            direction = "bullish"
        elif current_price < sma_short_value < sma_long_value:
            direction = "bearish"
        else:
            direction = "neutral"

        # Momentum strength calculation (0-10 scale)
        price_change_pct = ((current_price - prices[0]) / prices[0]) * 100
        momentum_strength = min(10, abs(price_change_pct) * 2)

        # Volume analysis for confirmation
        volume_analysis_bars = min(10, len(symbol_bars))
        volumes = [bar.volume for bar in symbol_bars[-volume_analysis_bars:]]
        avg_volume = sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Price volatility (standard deviation using configurable period)
        volatility_period = min(sma_long, len(prices))
        volatility_prices = prices[-volatility_period:]
        avg_price = sum(volatility_prices) / len(volatility_prices)
        variance = sum((p - avg_price) ** 2 for p in volatility_prices) / len(volatility_prices)
        volatility = variance**0.5
        volatility_pct = (volatility / avg_price) * 100

        # Recent price action (configurable short-term momentum)
        short_term_period = min(sma_short, len(prices) // 2)
        if len(prices) >= short_term_period * 2:
            recent_prices = prices[-short_term_period:]
            previous_prices = prices[-short_term_period * 2 : -short_term_period]

            recent_avg = sum(recent_prices) / len(recent_prices)
            previous_avg = sum(previous_prices) / len(previous_prices)

            short_term_momentum = (
                ((recent_avg - previous_avg) / previous_avg) * 100 if previous_avg > 0 else 0
            )
        else:
            short_term_momentum = 0

        return {
            "symbol": symbol,
            "direction": direction,
            "momentum_strength": round(momentum_strength, 1),
            "price_change_pct": round(price_change_pct, 2),
            "short_term_momentum_pct": round(short_term_momentum, 2),
            "current_price": round(current_price, 2),
            f"sma_{sma_short}": round(sma_short_value, 2),
            f"sma_{sma_long}": round(sma_long_value, 2),
            "volume_ratio": round(volume_ratio, 2),
            "volatility_pct": round(volatility_pct, 2),
            "bars_analyzed": len(symbol_bars),
            "timeframe_minutes": timeframe_minutes,
            "analysis_period_hours": analysis_hours,
            "last_bar_time": symbol_bars[-1].timestamp.isoformat(),
            "start_time_et": start.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "end_time_et": end.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "parameters": {
                "symbol": symbol,
                "timeframe_minutes": timeframe_minutes,
                "analysis_hours": analysis_hours,
                "sma_short": sma_short,
                "sma_long": sma_long,
            },
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "symbol": symbol,
            "direction": "unknown",
            "momentum_strength": 0,
            "parameters": {
                "symbol": symbol,
                "timeframe_minutes": timeframe_minutes,
                "analysis_hours": analysis_hours,
                "sma_short": sma_short,
                "sma_long": sma_long,
            },
            "last_updated": datetime.now().isoformat(),
        }
