"""Market data tools for Alpaca MCP Server."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytz
from alpaca.common.enums import Sort, SupportedCurrencies
from alpaca.data.enums import Adjustment, DataFeed

# Alpaca imports for market data
from alpaca.data.models import BarSet
from alpaca.data.requests import (
    StockBarsRequest,
    StockLatestBarRequest,
    StockLatestQuoteRequest,
    StockLatestTradeRequest,
    StockTradesRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from ..config.settings import get_stock_historical_client
from ..utils.feed_select import feed_label, live_feed
from ..utils.timezone_utils import fmt_et, to_et
from ..utils.trading_calendar import latest_trading_day, trading_days_window_start


def _px(value: float) -> str:
    """Format a price: 2 decimals at $1 and up, 4 below.

    Sub-dollar names trade in hundredths of a cent; at 2 decimals a $0.1568
    print reads "$0.16" and a 3.8% spread reads as one cent.
    """
    v = float(value)
    return f"${v:.4f}" if abs(v) < 1 else f"${v:.2f}"


def _pxd(delta: float) -> str:
    """Format a signed price change with the same precision rule as _px."""
    d = float(delta)
    return ("-" if d < 0 else "+") + _px(abs(d))


def get_smart_date_range():
    """
    Get a smart date range for intraday data that considers market hours and days.

    Returns:
        tuple: (start_date, end_date, is_market_open) in YYYY-MM-DD format
    """
    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)

    # Check if today is a weekday (Monday=0, Sunday=6)
    is_weekday = now_et.weekday() < 5

    # Market hours: 9:30 AM - 4:00 PM ET (regular), 4:00 AM - 8:00 PM ET (extended)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    is_market_hours = market_open <= now_et <= market_close
    is_market_open = is_weekday and is_market_hours

    if is_weekday and now_et.hour >= 4:
        # Today, if it's a weekday and after 4 AM ET
        return now_et.strftime("%Y-%m-%d"), now_et.strftime("%Y-%m-%d"), is_market_open
    else:
        # Most recent trading day
        days_back = 1
        while days_back <= 7:  # Look back up to a week
            check_date = now_et - timedelta(days=days_back)
            if check_date.weekday() < 5:  # Found a weekday
                date_str = check_date.strftime("%Y-%m-%d")
                return date_str, date_str, False
            days_back += 1

        # Fallback: last Friday
        last_friday = now_et - timedelta(days=(now_et.weekday() + 3) % 7)
        date_str = last_friday.strftime("%Y-%m-%d")
        return date_str, date_str, False


async def get_stock_quote(symbol: str) -> str:
    """
    Get real-time bid/ask quote with spread analysis for immediate trading decisions.

    WHEN TO USE:
    - Checking current price before placing an order
    - Verifying spread before market/limit order decision
    - Confirming liquidity via bid/ask sizes
    - Real-time price monitoring during active trades

    HOW IT WORKS:
    1. Fetches latest quote from Alpaca market data API
    2. Returns bid price, ask price, spread, and sizes
    3. Includes timestamp for quote age verification

    WHY THIS TOOL:
    Use for IMMEDIATE price checks (last few seconds).
    For historical prices, use get_stock_bars() instead.
    For continuous monitoring, use start_global_stock_stream() instead.

    Examples:
        # Quick price check before order
        get_stock_quote("AAPL")

        # Verify spread before large order
        get_stock_quote("TSLA")  # Check if spread <0.5%

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT", "NVDA")

    Returns:
        Formatted quote with:
        - Ask Price: $X.XX (size)
        - Bid Price: $X.XX (size)
        - Spread (derived from ask - bid)
        - Timestamp in America/New_York timezone
    """
    try:
        client = get_stock_historical_client()
        feed = live_feed()  # BOATS overnight (20:00-04:00 ET), SIP otherwise
        request_params = StockLatestQuoteRequest(symbol_or_symbols=symbol, feed=feed)
        quotes = client.get_stock_latest_quote(request_params)

        if symbol in quotes:
            quote = quotes[symbol]
            # Convert timestamp to NYC/EDT
            eastern = pytz.timezone("America/New_York")
            timestamp_nyc = quote.timestamp.astimezone(eastern)

            return f"""Latest Quote for {symbol}:
------------------------
Feed: {feed_label(feed)}
Ask Price: {_px(quote.ask_price)}
Bid Price: {_px(quote.bid_price)}
Ask Size: {quote.ask_size:,.0f}
Bid Size: {quote.bid_size:,.0f}
Timestamp: {timestamp_nyc.strftime("%Y-%m-%d %H:%M:%S %Z")}"""
        else:
            return f"No quote data found for {symbol}."

    except Exception as e:
        return f"Error fetching quote for {symbol}: {str(e)}"


async def get_stock_bars(symbol: str, days: int = 5) -> str:
    """
    Fetch daily OHLCV price bars for technical analysis and charting.

    WHEN TO USE:
    - Need historical price data for charting patterns
    - Calculating technical indicators (moving averages, RSI, etc.)
    - Reviewing recent price trends and volatility
    - Backtesting strategies on daily timeframes

    HOW IT WORKS:
    1. Fetches {days} trading days of daily bar data
    2. Returns OHLCV (Open, High, Low, Close, Volume)
    3. Sorted chronologically (oldest → newest)
    4. Reports TWO distinct percentages per bar, because they differ:
       - "Daily Change (close-to-close)": this close vs the PREVIOUS close.
         This is the day's move, the number almost every caller means.
       - "Open-to-Close": the intraday move within the session.
    5. Prices are SPLIT AND DIVIDEND ADJUSTED (Adjustment.ALL) on the SIP feed.
       Without adjustment a split in the window silently breaks multi-day
       returns, so adjustment is not optional here.

    WHY THIS TOOL:
    Use for DAILY bars only (one bar per trading day).
    For intraday (1min, 5min, 15min), use get_stock_bars_intraday() instead.
    For real-time data, use get_stock_quote() or start_global_stock_stream() instead.

    Examples:
        # Get last 5 trading days (default)
        get_stock_bars("AAPL")

        # Get 20 days for longer-term analysis
        get_stock_bars("TSLA", days=20)

        # Get full month of data
        get_stock_bars("NVDA", days=30)

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT", "NVDA")
        days: Number of trading days to fetch (default: 5, max: 1000)

    Returns:
        Formatted table with:
        Date | Open | High | Low | Close | Volume
             | Daily Change (close-to-close) | Open-to-Close
        Sorted oldest to newest for easy trend analysis.
        The first row shows "n/a" for the daily change only when no earlier
        bar exists in the window to measure it against.
    """
    try:
        client = get_stock_historical_client()

        # Start bound covers exactly the last `days` NYSE *trading* days (holiday-aware),
        # so results always run through the latest trading day (not sequential calendar days).
        # Aware UTC: alpaca-py sends a naive datetime as UTC, so a naive local now()
        # on this America/Chicago host would cut the window 5-6 hours short.
        end_date = datetime.now(UTC)
        # One EXTRA trading day: the earliest bar is held back purely as the previous
        # close for the first displayed day, so every displayed row carries a real
        # close-to-close change instead of an open-to-close one.
        start_date = trading_days_window_start(days + 1)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date,
            limit=days + 1,
            # newest-first so `limit` keeps the MOST RECENT `days` bars, not the oldest.
            # (Default ASC + limit returned the oldest N in the window -> stale by ~1-2 days.)
            sort=Sort.DESC,
            # Corporate actions MUST be applied. The SDK default is `raw`, under which a
            # split anywhere in the window silently corrupts every multi-day return:
            # SOXX split 3-for-1 on 2026-11-05, and its true -12.15% day reads as
            # -70.7% off raw closes (450.41 -> 131.90 instead of 150.14 -> 131.90).
            adjustment=Adjustment.ALL,
            # Consolidated tape, stated explicitly rather than left to the default.
            feed=DataFeed.SIP,
        )

        bars_data = client.get_stock_bars(request_params)

        # BarSet stores data in .data attribute, not directly accessible via 'in'
        bars_dict = bars_data.data if hasattr(bars_data, "data") else bars_data
        if symbol in bars_dict and bars_dict[symbol]:
            # sort=DESC returns newest->oldest; restore chronological oldest->newest for display.
            bars = list(reversed(bars_dict[symbol]))
            # Hold back the extra leading bar as the baseline close. It is NOT displayed;
            # it only supplies the previous close for the first displayed row.
            baseline = None
            if len(bars) > days:
                baseline, bars = bars[0], bars[1:]

            result = (
                f"Historical Price Bars for {symbol} "
                f"(Last {len(bars)} trading days, split/dividend adjusted, SIP):\n"
            )
            result += "=" * 60 + "\n"

            prev_close = float(baseline.close) if baseline is not None else None
            for bar in bars:
                bar_open, bar_close = float(bar.open), float(bar.close)

                # "Daily change" means CLOSE-TO-CLOSE. The open-to-close move is a
                # different number and is reported separately rather than under the
                # wrong name: on 2026-11-05 SOXX was -7.81% open-to-close but -12.15%
                # on the day, and only the second is the day's move.
                if prev_close is None:
                    change_line = "Daily Change: n/a (no prior close in window)"
                else:
                    daily_change = ((bar_close - prev_close) / prev_close) * 100
                    indicator = "📈" if daily_change > 0 else "📉" if daily_change < 0 else "➡️"
                    change_line = f"Daily Change (close-to-close): {indicator} {daily_change:+.2f}%"
                prev_close = bar_close

                intraday_change = ((bar_close - bar_open) / bar_open) * 100

                result += f"""Date: {bar.timestamp.strftime("%Y-%m-%d")}
Open: {_px(bar_open)}
High: {_px(float(bar.high))}
Low: {_px(float(bar.low))}
Close: {_px(bar_close)}
Volume: {bar.volume:,.0f}
{change_line}
Open-to-Close: {intraday_change:+.2f}%
------------------------------
"""
            return result
        else:
            return f"No bar data found for {symbol}."

    except Exception as e:
        return f"Error fetching bars for {symbol}: {str(e)}"


async def get_stock_bars_intraday(
    symbol: str,
    timeframe: str = "1Min",
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 10000,
    adjustment: str = "raw",
    feed: str = "auto",
    currency: str = "USD",
    sort: str = "asc",
) -> str:
    """
    Retrieves comprehensive intraday historical bars with professional analysis.

    Args:
        symbol (str): Stock ticker symbol(s) - can be comma-separated (e.g., AAPL, MSFT or AAPL,MSFT,GOOGL)
        timeframe (str): Timeframe for bars (1Min, 5Min, 15Min, 30Min, 1Hour)
        start_date (Optional[str]): Start date in YYYY-MM-DD format (default: today)
        end_date (Optional[str]): End date in YYYY-MM-DD format (default: now)
        limit (int): Maximum number of bars to return per symbol (default: 10000)
        adjustment (str): Price adjustment type (raw, split, dividend, all)
        feed (str): Data feed: "auto" (default: BOATS during the 20:00-04:00 ET
            overnight session, SIP otherwise), or sip, boats, overnight, otc
        currency (str): Currency for international symbols
        sort (str): Sort order (asc, desc)

    Returns:
        str: Comprehensive formatted analysis with professional insights
    """
    try:
        client = get_stock_historical_client()

        # Parse symbols - handle comma-separated list
        if "," in symbol:
            symbol_list = [s.strip().upper() for s in symbol.split(",")]
        else:
            symbol_list = [symbol.strip().upper()]

        # Parse timeframe
        timeframe_map = {
            "1Min": TimeFrame.Minute,
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "30Min": TimeFrame(30, TimeFrameUnit.Minute),
            "1Hour": TimeFrame.Hour,
            "1Day": TimeFrame.Day,
        }

        if timeframe not in timeframe_map:
            return f"Invalid timeframe: {timeframe}. Valid options: {list(timeframe_map.keys())}"

        tf = timeframe_map[timeframe]

        # Parse dates - the SDK requires timezone-aware datetime objects
        eastern = pytz.timezone("America/New_York")

        if start_date and end_date:
            # User provided both dates
            # Handle both YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS formats
            try:
                if "T" in str(start_date):
                    start = eastern.localize(
                        datetime.strptime(str(start_date), "%Y-%m-%dT%H:%M:%S")
                    )
                else:
                    start = eastern.localize(
                        datetime.strptime(str(start_date), "%Y-%m-%d").replace(hour=4, minute=0)
                    )
            except ValueError:
                # Try alternative format with just date part
                start = eastern.localize(
                    datetime.strptime(str(start_date).split("T")[0], "%Y-%m-%d").replace(
                        hour=4, minute=0
                    )
                )

            try:
                if "T" in str(end_date):
                    end = eastern.localize(datetime.strptime(str(end_date), "%Y-%m-%dT%H:%M:%S"))
                else:
                    end = eastern.localize(
                        datetime.strptime(str(end_date), "%Y-%m-%d").replace(hour=20, minute=0)
                    )
            except ValueError:
                # Try alternative format with just date part
                end = eastern.localize(
                    datetime.strptime(str(end_date).split("T")[0], "%Y-%m-%d").replace(
                        hour=20, minute=0
                    )
                )
        elif start_date:
            # User provided start date only
            try:
                if "T" in str(start_date):
                    start = eastern.localize(
                        datetime.strptime(str(start_date), "%Y-%m-%dT%H:%M:%S")
                    )
                else:
                    start = eastern.localize(
                        datetime.strptime(str(start_date), "%Y-%m-%d").replace(hour=4, minute=0)
                    )
            except ValueError:
                start = eastern.localize(
                    datetime.strptime(str(start_date).split("T")[0], "%Y-%m-%d").replace(
                        hour=4, minute=0
                    )
                )
            end = datetime.now(eastern)
        elif end_date:
            # User provided end date only
            try:
                if "T" in str(end_date):
                    end = eastern.localize(datetime.strptime(str(end_date), "%Y-%m-%dT%H:%M:%S"))
                else:
                    end = eastern.localize(
                        datetime.strptime(str(end_date), "%Y-%m-%d").replace(hour=20, minute=0)
                    )
            except ValueError:
                end = eastern.localize(
                    datetime.strptime(str(end_date).split("T")[0], "%Y-%m-%d").replace(
                        hour=20, minute=0
                    )
                )
            # Default to same day
            start = eastern.localize(
                datetime.strptime(str(end_date).split("T")[0], "%Y-%m-%d").replace(hour=4, minute=0)
            )
        else:
            # No dates provided - use smart defaults
            smart_start, smart_end, is_market_open = get_smart_date_range()
            start = eastern.localize(
                datetime.strptime(smart_start, "%Y-%m-%d").replace(hour=4, minute=0)
            )
            if is_market_open:
                # Market is open, use current time
                end = datetime.now(eastern)
            else:
                # Market closed, use end of trading day
                end = eastern.localize(
                    datetime.strptime(smart_end, "%Y-%m-%d").replace(hour=20, minute=0)
                )

        # Parse enums
        adjustment_enum = getattr(Adjustment, adjustment.upper(), Adjustment.RAW)
        if feed.lower() == "auto":
            feed_enum = live_feed()
        else:
            feed_enum = getattr(DataFeed, feed.upper(), DataFeed.SIP)
        feed = feed_enum.value
        currency_enum = getattr(SupportedCurrencies, currency.upper(), SupportedCurrencies.USD)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbol_list,
            timeframe=tf,
            start=start,
            end=end,
            limit=limit,
            adjustment=adjustment_enum,
            feed=feed_enum,
            currency=currency_enum,
            # newest-first so a small `limit` keeps the MOST RECENT bars (default ASC + limit
            # returned the oldest N -> stale). Materialized back to chronological below.
            sort=Sort.DESC,
        )

        bars_data = client.get_stock_bars(request_params)

        # Type narrowing: ensure we have a BarSet object
        if not isinstance(bars_data, BarSet):
            return f"Error: Unexpected response type from get_stock_bars: {type(bars_data)}"

        # Check if we have any data at all
        if not bars_data.data:
            return f"""No intraday data found for symbols {", ".join(symbol_list)} in timeframe {timeframe}.

Possible reasons:
• Market is closed or symbols traded on non-trading day (weekends/holidays)
• Invalid symbol(s) - check ticker spelling
• {feed.upper()} feed may have limited data for these symbols
• Time range may be outside available data period

Suggestions:
• Try a recent trading day (Monday-Friday)
• Use SIP feed for most comprehensive data
• Verify symbols are valid and actively traded
• Check if market was open during specified time range"""

        # For single symbol, provide detailed analysis
        if len(symbol_list) == 1:
            symbol = symbol_list[0]
            if symbol not in bars_data.data or not bars_data.data[symbol]:
                return f"""No intraday data found for {symbol} in timeframe {timeframe}.

Possible reasons:
• Market is closed or {symbol} traded on non-trading day (weekends/holidays)
• Invalid symbol - check ticker spelling for {symbol}
• {feed.upper()} feed may have limited data for {symbol}
• Time range may be outside available data period

Suggestions:
• Try a recent trading day (Monday-Friday)
• Use SIP feed for most comprehensive data
• Verify {symbol} is valid and actively traded
• Check if market was open during specified time range"""

            # sort=DESC fetch returns newest-first; restore chronological order for analysis.
            bars = sorted(bars_data.data[symbol], key=lambda b: b.timestamp)

            # Professional analysis starts here
            result = f"""# Professional Intraday Analysis: {symbol}

## Market Data Summary
Symbol: {symbol}
Timeframe: {timeframe}
Period: {start.strftime("%Y-%m-%d %H:%M")} to {end.strftime("%Y-%m-%d %H:%M")} ET
Total Bars: {len(bars)}
Data Feed: {feed.upper()}
Adjustment: {adjustment.title()}

"""

            if len(bars) < 2:
                return result + "Insufficient data for analysis."

            # Calculate key metrics
            first_bar = bars[0]
            last_bar = bars[-1]
            open_price = float(first_bar.open)
            close_price = float(last_bar.close)

            # Find high and low
            high_price = max(float(bar.high) for bar in bars)
            low_price = min(float(bar.low) for bar in bars)

            # Calculate returns
            total_return = ((close_price - open_price) / open_price) * 100

            # Volume analysis
            total_volume = sum(bar.volume for bar in bars)
            avg_volume = total_volume / len(bars)

            # Recent bars for momentum
            recent_bars = bars[-min(10, len(bars)) :]
            recent_prices = [float(bar.close) for bar in recent_bars]

            # Simple momentum calculation
            if len(recent_prices) >= 3:
                early_avg = sum(recent_prices[: len(recent_prices) // 2]) / (
                    len(recent_prices) // 2
                )
                late_avg = sum(recent_prices[len(recent_prices) // 2 :]) / (
                    len(recent_prices) - len(recent_prices) // 2
                )
                momentum = "BULLISH" if late_avg > early_avg else "BEARISH"
            else:
                momentum = "NEUTRAL"

            result += f"""## Key Metrics
Period Return: {total_return:+.2f}%
Opening Price: {_px(open_price)}
Closing Price: {_px(close_price)}
Session High: {_px(high_price)}
Session Low: {_px(low_price)}
Range: {_px(high_price - low_price)} ({((high_price - low_price) / open_price) * 100:.2f}%)

## Volume Analysis
Total Volume: {total_volume:,} shares
Average Volume per Bar: {avg_volume:,.0f} shares
Volume Trend: {"Heavy" if total_volume > avg_volume * len(bars) * 1.5 else "Normal" if total_volume > avg_volume * len(bars) * 0.8 else "Light"}

## Technical Analysis
Short-term Momentum: {momentum}
Volatility: {"High" if (high_price - low_price) / open_price > 0.03 else "Moderate" if (high_price - low_price) / open_price > 0.015 else "Low"}
Price Action: {"Trending Up" if close_price > open_price else "Trending Down" if close_price < open_price else "Sideways"}

"""

            # Recent bars detail
            result += f"## Recent Price Action (Last {min(5, len(bars))} bars):\n"
            for bar in bars[-5:]:
                bar_change = ((float(bar.close) - float(bar.open)) / float(bar.open)) * 100
                trend_arrow = "🟢" if bar_change > 0.5 else "🔴" if bar_change < -0.5 else "🟡"

                result += f"""{trend_arrow} {to_et(bar.timestamp).strftime("%H:%M")} | O:{_px(float(bar.open))} H:{_px(float(bar.high))} L:{_px(float(bar.low))} C:{_px(float(bar.close))} | Vol:{bar.volume:,.0f} | {bar_change:+.2f}%
"""

            # Trading insights
            result += f"""
## Trading Insights

Support/Resistance Levels:
• Resistance: {_px(high_price)} (session high)
• Support: {_px(low_price)} (session low)

Volume Analysis:
• {"Strong institutional interest" if total_volume > avg_volume * len(bars) * 2 else "Normal trading activity" if total_volume > avg_volume * len(bars) else "Below average volume - limited interest"}

Momentum Signals:
• {momentum} momentum detected in recent bars
• {"Consider long positions on pullbacks" if momentum == "BULLISH" and total_return > 1 else "Monitor for reversal signals" if momentum == "BEARISH" and total_return < -1 else "Wait for clearer directional signals"}

Risk Considerations:
• Intraday volatility: {((high_price - low_price) / open_price) * 100:.2f}%
• {"High risk - tight stops recommended" if (high_price - low_price) / open_price > 0.03 else "Moderate risk - normal position sizing" if (high_price - low_price) / open_price > 0.015 else "Lower risk - suitable for larger positions"}

Analysis Time: {fmt_et()}
"""

            return result

        else:
            # Multiple symbols - provide summary analysis
            result = f"""# Intraday Analysis: Multiple Symbols

## Summary
Symbols: {", ".join(symbol_list)}
Timeframe: {timeframe}
Period: {start.strftime("%Y-%m-%d %H:%M")} to {end.strftime("%Y-%m-%d %H:%M")} ET
Data Feed: {feed.upper()}

"""

            # Analyze each symbol
            for symbol in symbol_list:
                if symbol not in bars_data.data or not bars_data.data[symbol]:
                    result += f"\n## {symbol} - No Data Available\n"
                    continue

                bars = sorted(bars_data.data[symbol], key=lambda b: b.timestamp)
                if len(bars) < 2:
                    result += f"\n## {symbol} - Insufficient Data\n"
                    continue

                # Calculate key metrics for each symbol
                first_bar = bars[0]
                last_bar = bars[-1]
                open_price = float(first_bar.open)
                close_price = float(last_bar.close)

                # Find high and low
                high_price = max(float(bar.high) for bar in bars)
                low_price = min(float(bar.low) for bar in bars)

                # Calculate returns
                total_return = ((close_price - open_price) / open_price) * 100

                # Volume analysis
                total_volume = sum(bar.volume for bar in bars)
                avg_volume_per_bar = total_volume / len(bars)

                # Recent momentum
                recent_bars = bars[-min(5, len(bars)) :]
                recent_change = (
                    (float(recent_bars[-1].close) - float(recent_bars[0].open))
                    / float(recent_bars[0].open)
                ) * 100

                result += f"""## {symbol}

### Performance
• Period Return: {total_return:+.2f}%
• Open: {_px(open_price)} → Close: {_px(close_price)}
• High: {_px(high_price)} | Low: {_px(low_price)}
• Range: {_px(high_price - low_price)} ({((high_price - low_price) / open_price) * 100:.2f}%)

### Volume
• Total: {total_volume:,} shares
• Avg/Bar: {avg_volume_per_bar:,.0f} shares
• Bars: {len(bars)}

### Recent Action (Last {len(recent_bars)} bars)
• Momentum: {recent_change:+.2f}%
• Last Price: {_px(float(last_bar.close))}
• Last Volume: {last_bar.volume:,.0f}

---
"""

            # Add summary rankings
            result += "\n## Summary Rankings\n\n"

            # Collect metrics for ranking
            symbol_metrics: list[dict[str, Any]] = []
            for symbol in symbol_list:
                if symbol in bars_data.data and bars_data.data[symbol]:
                    bars = sorted(bars_data.data[symbol], key=lambda b: b.timestamp)
                    if len(bars) >= 2:
                        first_bar = bars[0]
                        last_bar = bars[-1]
                        total_return = (
                            (float(last_bar.close) - float(first_bar.open)) / float(first_bar.open)
                        ) * 100
                        total_volume = sum(bar.volume for bar in bars)
                        volatility = (
                            (
                                max(float(bar.high) for bar in bars)
                                - min(float(bar.low) for bar in bars)
                            )
                            / float(first_bar.open)
                            * 100
                        )

                        symbol_metrics.append(
                            {
                                "symbol": symbol,
                                "return": total_return,
                                "volume": total_volume,
                                "volatility": volatility,
                                "last_price": float(last_bar.close),
                            }
                        )

            # Sort by return (cast to float for type safety)
            symbol_metrics.sort(key=lambda x: cast(float, x["return"]), reverse=True)

            result += "### By Performance\n"
            for i, m in enumerate(symbol_metrics[:10], 1):
                result += f"{i}. {m['symbol']}: {m['return']:+.2f}% ({_px(m['last_price'])})\n"

            # Sort by volume (cast to int for type safety)
            symbol_metrics.sort(key=lambda x: cast(int, x["volume"]), reverse=True)

            result += "\n### By Volume\n"
            for i, m in enumerate(symbol_metrics[:10], 1):
                result += f"{i}. {m['symbol']}: {m['volume']:,} shares\n"

            # Sort by volatility (cast to float for type safety)
            symbol_metrics.sort(key=lambda x: cast(float, x["volatility"]), reverse=True)

            result += "\n### By Volatility\n"
            for i, m in enumerate(symbol_metrics[:10], 1):
                result += f"{i}. {m['symbol']}: {m['volatility']:.2f}% range\n"

            return result

    except Exception as e:
        return f"Error fetching intraday data: {str(e)}"


async def get_stock_snapshots(symbols: str | list[str]) -> str:
    """
    Get comprehensive market snapshots for one or more stocks.

    Args:
        symbols: Single symbol string or list of symbols

    Returns:
        str: Comprehensive market data with analysis
    """
    try:
        client = get_stock_historical_client()

        # Handle single symbol or list
        if isinstance(symbols, str):
            if "," in symbols:
                symbol_list = [s.strip().upper() for s in symbols.split(",")]
            else:
                symbol_list = [symbols.upper()]
        else:
            symbol_list = [s.upper() for s in symbols]

        # Get snapshot data using correct method
        from alpaca.data.requests import StockSnapshotRequest

        request_params = StockSnapshotRequest(symbol_or_symbols=symbol_list, feed=DataFeed.SIP)
        snapshots = client.get_stock_snapshot(request_params)

        # Overnight the SIP tape is silent: take the live prints (trade, quote,
        # minute bar) from BOATS. Daily and previous-day bars stay SIP, because a
        # BOATS daily bar covers only the overnight session.
        feed = live_feed()
        live_snapshots = snapshots
        if feed == DataFeed.BOATS:
            live_snapshots = client.get_stock_snapshot(
                StockSnapshotRequest(symbol_or_symbols=symbol_list, feed=feed)
            )

        if not snapshots:
            return f"No snapshot data found for symbols: {', '.join(symbol_list)}"

        result = "# Market Snapshots\n"
        result += f"Symbols: {', '.join(symbol_list)}\n"
        # Display current timestamp in NYC/EDT
        eastern = pytz.timezone("America/New_York")
        current_time_nyc = datetime.now(eastern)
        result += f"Timestamp: {current_time_nyc.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        result += f"Live prints: {feed_label(feed)} | Daily bars: SIP\n\n"

        for symbol in symbol_list:
            if symbol in snapshots:
                snapshot = snapshots[symbol]
                live = live_snapshots.get(symbol) if live_snapshots is not snapshots else None
                live = live or snapshot  # no BOATS print: fall back to SIP

                # Extract data safely with correct attribute names
                latest_trade = getattr(live, "latest_trade", None)
                latest_quote = getattr(live, "latest_quote", None)
                minute_bar = getattr(live, "minute_bar", None)
                daily_bar = getattr(snapshot, "daily_bar", None)
                previous_daily_bar = getattr(
                    snapshot, "previous_daily_bar", None
                )  # Correct attribute name

                result += f"""## {symbol} - Complete Market Data

### Latest Trade
"""
                if latest_trade:
                    # Convert timestamp to NYC/EDT
                    eastern = pytz.timezone("America/New_York")
                    trade_time_nyc = latest_trade.timestamp.astimezone(eastern)

                    result += f"""• Price: {_px(float(latest_trade.price))}
• Size: {latest_trade.size:,.0f} shares
• Time: {trade_time_nyc.strftime("%H:%M:%S %Z")}
• Exchange: {getattr(latest_trade, "exchange", "N/A")}
"""
                else:
                    result += "• No recent trade data available\n"

                result += "\n### Latest Quote\n"
                if latest_quote:
                    spread = float(latest_quote.ask_price) - float(latest_quote.bid_price)
                    ask = float(latest_quote.ask_price)
                    spread_pct = (spread / ask) * 100 if ask else 0.0

                    # Convert timestamp to NYC/EDT
                    eastern = pytz.timezone("America/New_York")
                    quote_time_nyc = latest_quote.timestamp.astimezone(eastern)

                    result += f"""• Bid: {_px(float(latest_quote.bid_price))} (Size: {latest_quote.bid_size:,.0f})
• Ask: {_px(float(latest_quote.ask_price))} (Size: {latest_quote.ask_size:,.0f})
• Spread: {_px(spread)} ({spread_pct:.2f}%)
• Time: {quote_time_nyc.strftime("%H:%M:%S %Z")}
"""
                else:
                    result += "• No current quote data available\n"

                result += "\n### Current Minute Bar\n"
                if minute_bar:
                    try:
                        m_open = float(minute_bar.open)
                        minute_change = (
                            (float(minute_bar.close) - m_open) / m_open * 100 if m_open else 0.0
                        )

                        # Convert timestamp to NYC/EDT
                        eastern = pytz.timezone("America/New_York")
                        minute_time_nyc = minute_bar.timestamp.astimezone(eastern)

                        # Get trade count (if available)
                        trades = (
                            int(float(minute_bar.trade_count))
                            if hasattr(minute_bar, "trade_count")
                            and minute_bar.trade_count is not None
                            else 0
                        )

                        result += f"• OHLC: {_px(float(minute_bar.open))} / {_px(float(minute_bar.high))} / {_px(float(minute_bar.low))} / {_px(float(minute_bar.close))}\n"
                        result += f"• Volume: {minute_bar.volume:,.0f}\n"
                        result += f"• Trades: {trades:,} trades/min\n"
                        result += f"• Change: {minute_change:+.2f}%\n"
                        result += f"• Time: {minute_time_nyc.strftime('%H:%M %Z')}\n"
                    except Exception as e:
                        result += f"• Error processing minute bar: {str(e)}\n"
                else:
                    result += "• No current minute bar data\n"

                result += "\n### Daily Performance\n"
                # Reset per symbol: the indicator below must never reuse the
                # previous symbol's change (it used to test `in locals()`).
                daily_change: float | None = None
                if daily_bar:
                    day_open = float(daily_bar.open)
                    daily_range = float(daily_bar.high) - float(daily_bar.low)
                    daily_range_pct = (daily_range / day_open) * 100 if day_open else 0.0

                    # Check if daily bar is stale (current price way outside daily range)
                    is_stale_daily = False
                    if latest_trade:
                        current_price = float(latest_trade.price)
                        daily_high = float(daily_bar.high)

                        if current_price > daily_high * 1.5 or (
                            daily_high < 2.0 and current_price > daily_high + 0.5
                        ):
                            is_stale_daily = True
                            result += "⚠️ **STALE DATA WARNING**: Daily bar appears to be from previous day\n"
                            result += f"   Current price {_px(current_price)} is way above daily high {_px(daily_high)}\n"

                    result += f"""• {'Yesterday' if is_stale_daily else 'Session'} OHLC ({daily_bar.timestamp.astimezone(eastern).strftime('%Y-%m-%d')}): {_px(day_open)} / {_px(float(daily_bar.high))} / {_px(float(daily_bar.low))} / {_px(float(daily_bar.close))}
• Volume: {daily_bar.volume:,.0f}
• Range: {_px(daily_range)} ({daily_range_pct:.2f}%)
"""

                    # Session close-to-close: the day's move, the number most callers mean.
                    prev_close = float(previous_daily_bar.close) if previous_daily_bar else 0.0
                    if prev_close:
                        session_change = (float(daily_bar.close) - prev_close) / prev_close * 100
                        result += (
                            f"• Session Change (close-to-close): {session_change:+.2f}% "
                            f"({_pxd(float(daily_bar.close) - prev_close)}) vs prior close {_px(prev_close)}\n"
                        )

                    # Pre-market only on a trading day: on a weekend or holiday morning
                    # the daily bar is the last session, and the reference stays its prior close.
                    current_time_et = datetime.now(eastern)
                    market_open = current_time_et.replace(hour=9, minute=30, second=0, microsecond=0)
                    is_pre_market = (
                        current_time_et.hour >= 4
                        and current_time_et < market_open
                        and latest_trading_day() == current_time_et.date()
                    )

                    if latest_trade:
                        current_price = float(latest_trade.price)
                        if is_pre_market:
                            reference_price = float(daily_bar.close)
                            ref_note = " (yesterday's daily bar close)"
                            result += f"• Market Status: PRE-MARKET ({current_time_et.strftime('%H:%M %Z')})\n"
                        else:
                            reference_price = prev_close or float(daily_bar.close)
                            ref_note = ""
                        if reference_price:
                            daily_change = (current_price - reference_price) / reference_price * 100
                            result += f"""• Daily Change: {daily_change:+.2f}% ({_pxd(current_price - reference_price)}) — last trade vs reference close, incl. extended hours
• Reference Close: {_px(reference_price)}{ref_note}
• Current Price: {_px(current_price)}
"""
                    elif prev_close:
                        daily_change = (float(daily_bar.close) - prev_close) / prev_close * 100
                        result += f"""• Daily Change: {daily_change:+.2f}% ({_pxd(float(daily_bar.close) - prev_close)})
• Reference Close: {_px(prev_close)}
"""

                    if daily_change is not None:
                        result += "\n### Performance Indicators\n"
                        if daily_change > 3:
                            result += "• Strong Upward Movement - Consider momentum plays\n"
                        elif daily_change > 1:
                            result += "• Positive Momentum - Watch for continuation\n"
                        elif daily_change < -3:
                            result += "• Significant Decline - Risk management critical\n"
                        elif daily_change < -1:
                            result += "• Negative Pressure - Monitor for reversal\n"
                        else:
                            result += "• Consolidating - Await directional break\n"
                    else:
                        result += "• Change data not available\n"

                else:
                    result += "• Daily bar data not available\n"

                result += "\n" + "=" * 50 + "\n"

            else:
                result += f"## {symbol} - No Data Available\n"
                result += "• Symbol may be invalid or data unavailable\n\n"

        return result

    except Exception as e:
        return f"Error fetching snapshots: {str(e)}"


async def get_stock_trades(symbol: str, days: int = 5, limit: int | None = None) -> str:
    """
    Retrieves historical trades for a stock.

    Args:
        symbol (str): Stock ticker symbol
        days (int): Number of days to look back (default: 5)
        limit (Optional[int]): Maximum number of trades to return

    Returns:
        str: Formatted string containing recent trades
    """
    try:
        client = get_stock_historical_client()

        # Trading-day lookback so `days` means trading days; sort=DESC + limit returns the
        # MOST RECENT trades (default ASC + limit returned the oldest N -> stale by ~`days`).
        # Aware UTC: alpaca-py sends a naive datetime as UTC, so a naive local now()
        # on this America/Chicago host would cut the window 5-6 hours short.
        end_date = datetime.now(UTC)
        start_date = trading_days_window_start(days)

        feed = live_feed()  # BOATS overnight (20:00-04:00 ET), SIP otherwise
        request_params = StockTradesRequest(
            symbol_or_symbols=symbol,
            start=start_date,
            end=end_date,
            limit=limit or 100,
            feed=feed,
            sort=Sort.DESC,
        )

        trades_data = client.get_stock_trades(request_params)

        # Alpaca SDK returns a TradeSet wrapper; unwrap via .data dict
        trades_dict = trades_data.data if hasattr(trades_data, "data") else trades_data

        if symbol in trades_dict and trades_dict[symbol]:
            # sort=DESC returns newest-first; reverse to chronological for display.
            trades = list(reversed(trades_dict[symbol]))

            result = f"Recent Trades for {symbol} (Last {len(trades)} trades, {feed_label(feed)}):\n"
            result += "=" * 50 + "\n"

            eastern = pytz.timezone("America/New_York")
            for trade in trades[-10:]:  # Show last 10 trades
                trade_time = trade.timestamp.astimezone(eastern)
                result += f"""Time: {trade_time.strftime("%Y-%m-%d %H:%M:%S %Z")}
Price: {_px(float(trade.price))}
Size: {trade.size:,.0f} shares
Exchange: {getattr(trade, "exchange", "N/A")}
------------------------------
"""
            return result
        else:
            return f"No trade data found for {symbol}."

    except Exception as e:
        return f"Error fetching trades for {symbol}: {str(e)}"


async def get_stock_latest_trade(symbol: str) -> str:
    """
    Gets the latest trade for a stock.

    Args:
        symbol (str): Stock ticker symbol

    Returns:
        str: Formatted string containing the latest trade information with NYC/EDT timestamp
    """
    try:
        client = get_stock_historical_client()
        feed = live_feed()  # BOATS overnight (20:00-04:00 ET), SIP otherwise
        request_params = StockLatestTradeRequest(symbol_or_symbols=symbol, feed=feed)
        trades = client.get_stock_latest_trade(request_params)

        if symbol in trades:
            trade = trades[symbol]
            # Convert timestamp to NYC/EDT
            eastern = pytz.timezone("America/New_York")
            timestamp_nyc = trade.timestamp.astimezone(eastern)

            return f"""Latest Trade for {symbol}:
-----------------------
Feed: {feed_label(feed)}
Price: {_px(float(trade.price))}
Size: {trade.size:,.0f} shares
Time: {timestamp_nyc.strftime("%Y-%m-%d %H:%M:%S %Z")}
Exchange: {getattr(trade, "exchange", "N/A")}"""
        else:
            return f"No recent trade data found for {symbol}."

    except Exception as e:
        return f"Error fetching latest trade for {symbol}: {str(e)}"


async def get_stock_latest_bar(symbol: str) -> str:
    """
    Gets the latest minute bar for a stock.

    Args:
        symbol (str): Stock ticker symbol

    Returns:
        str: Formatted string containing the latest bar information with NYC/EDT timestamp
    """
    try:
        client = get_stock_historical_client()
        feed = live_feed()  # BOATS overnight (20:00-04:00 ET), SIP otherwise
        request_params = StockLatestBarRequest(symbol_or_symbols=symbol, feed=feed)
        bars = client.get_stock_latest_bar(request_params)

        if symbol in bars:
            bar = bars[symbol]
            bar_open = float(bar.open)
            bar_change = ((float(bar.close) - bar_open) / bar_open) * 100 if bar_open else 0.0

            # Convert timestamp to NYC/EDT
            eastern = pytz.timezone("America/New_York")
            timestamp_nyc = bar.timestamp.astimezone(eastern)

            return f"""Latest Minute Bar for {symbol}:
-----------------------------
Feed: {feed_label(feed)}
Time: {timestamp_nyc.strftime("%Y-%m-%d %H:%M %Z")}
Open: {_px(float(bar.open))}
High: {_px(float(bar.high))}
Low: {_px(float(bar.low))}
Close: {_px(float(bar.close))}
Volume: {bar.volume:,.0f}
Change: {bar_change:+.2f}%"""
        else:
            return f"No recent bar data found for {symbol}."

    except Exception as e:
        return f"Error fetching latest bar for {symbol}: {str(e)}"
