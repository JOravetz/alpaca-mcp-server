"""Day trading scanner tool focused on trades per minute and % change - FIXED VERSION."""

import logging
import os
from datetime import UTC, datetime
from typing import List, Optional, Tuple

import pytz
import requests

# Import global configuration
from ..config import get_scanner_config, get_trading_config

logger = logging.getLogger(__name__)


def _is_market_hours() -> Tuple[bool, str]:
    """Check if market is currently open and return status message."""
    eastern = pytz.timezone("America/New_York")
    now = datetime.now(eastern)

    # Weekend check
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return (
            False,
            f"WEEKEND - No trading on {now.strftime('%A')}. Next market open: Monday 9:30 AM ET",
        )

    # Check regular market hours (9:30 AM - 4:00 PM ET)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

    if market_open <= now <= market_close:
        return True, "MARKET OPEN - Regular trading hours"

    # Check after-hours (4:00 PM - 8:00 PM ET)
    after_hours_close = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if market_close < now <= after_hours_close:
        return False, "AFTER-HOURS - Limited trading until 8:00 PM ET"

    # Check pre-market (4:00 AM - 9:30 AM ET)
    pre_market_open = now.replace(hour=4, minute=0, second=0, microsecond=0)
    if pre_market_open <= now < market_open:
        return False, "PRE-MARKET - Limited trading until 9:30 AM ET"

    return False, "CLOSED - Market closed overnight"


async def scan_day_trading_opportunities(
    symbols: str = "ALL",  # Default to ALL symbols from combined.lis
    min_trades_per_minute: Optional[int] = None,
    min_percent_change: Optional[float] = None,
    max_symbols: Optional[int] = None,
    sort_by: Optional[str] = None,  # "trades", "percent_change", or "volume"
) -> str:
    """Scan with global config defaults - ALWAYS uses global config for key parameters"""
    # Load global config defaults
    trading_config = get_trading_config()
    scanner_config = get_scanner_config()

    # Log incoming parameters for debugging
    logger.info(
        f"🔍 SCANNER CALLED WITH: trades={min_trades_per_minute}, change={min_percent_change}, max={max_symbols}, sort={sort_by}"
    )

    # ALWAYS use global config for trades_per_minute and min_percent_change
    # This ensures consistency with CLAUDE.md trading rules
    min_trades_per_minute = trading_config.trades_per_minute_threshold
    logger.info(f"📊 ENFORCING GLOBAL CONFIG: trades_per_minute = {min_trades_per_minute}")

    min_percent_change = trading_config.min_percent_change_threshold
    logger.info(f"📊 ENFORCING GLOBAL CONFIG: min_percent_change = {min_percent_change}")

    # Allow override for max_symbols and sort_by since they're less critical
    if max_symbols is None:
        max_symbols = scanner_config.max_watchlist_size
        logger.info(f"📊 USING GLOBAL CONFIG: max_symbols = {max_symbols}")
    else:
        logger.info(f"📊 USING PROVIDED VALUE: max_symbols = {max_symbols}")

    if sort_by is None:
        sort_by = scanner_config.scanner_sort_method
        logger.info(f"📊 USING GLOBAL CONFIG: sort_by = {sort_by}")
    else:
        logger.info(f"📊 USING PROVIDED VALUE: sort_by = {sort_by}")
    """
    Scan for EXPLOSIVE UP-ONLY day-trading opportunities with extreme volatility.

    UPDATED FILTER CRITERIA:
    1. ONLY UP STOCKS - No negative movers ever
    2. Minimum gain threshold from global config (min_percent_change_threshold)
    3. Minimum trades/minute from global config (trades_per_minute_threshold)
    4. EXPLOSIVE VOLATILITY FOCUS - Penny stocks and rocket ships preferred

    Args:
        symbols: Comma-separated symbols to scan (default: ALL tradeable assets)
        min_trades_per_minute: IGNORED - Always uses global config value
        min_percent_change: IGNORED - Always uses global config value
        max_symbols: Maximum results to return (default: from global config)
        sort_by: Sort results by "trades", "percent_change", or "volume" (default: from global config)

    Returns:
        Formatted analysis with EXPLOSIVE UP-ONLY trading opportunities.
    """
    try:
        # Check market status first
        is_open, market_status = _is_market_hours()
        eastern = pytz.timezone("America/New_York")
        current_time = datetime.now(eastern)

        # Parse symbols - get from Alpaca if ALL
        if symbols.upper() == "ALL":
            logger.info("Fetching tradable stock assets using TickerList (≤4 characters)")
            symbol_list = []

            # Use TickerList class for optimal filtering
            try:
                from ..utils.tickers import TickerList

                ticker_list = TickerList()
                assets = ticker_list.rest_api.list_assets(status="active")

                # Filter using TickerList validation logic
                tradable_symbols = [
                    asset.symbol
                    for asset in assets
                    if asset.tradable and ticker_list.is_valid_symbol(asset.symbol)
                ]
                symbol_list = sorted(tradable_symbols)
                logger.info(
                    f"Loaded {len(symbol_list)} tradable stock symbols (≤4 chars) using TickerList"
                )

            except Exception as e:
                logger.error(f"Error using TickerList: {e}")
                return f"Error: Unable to fetch tradable assets using TickerList - {str(e)}"

            if not symbol_list:
                return "Error: No tradable stock assets found using TickerList"
        else:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]

        # Get API credentials exactly like C program (lines 527-528)
        api_key = os.environ.get("APCA_API_KEY_ID")
        secret_key = os.environ.get("APCA_API_SECRET_KEY")

        if not api_key or not secret_key:
            return "Error: API keys not set in environment variables (same error as C program line 531)"

        # Set headers exactly like C program (lines 575-584)
        headers = {
            "accept": "application/json",
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
        }

        # Batch symbols for API limits (Alpaca allows ~500 symbols per request)
        batch_size = 500
        all_snapshots = {}

        for i in range(0, len(symbol_list), batch_size):
            batch = symbol_list[i : i + batch_size]
            url = f"https://data.alpaca.markets/v2/stocks/snapshots?symbols={','.join(batch)}"

            # Make API call exactly like C program curl (line 592)
            response = requests.get(url, headers=headers, timeout=120)
            if response.status_code != 200:
                logger.warning(
                    f"Error fetching batch {i // batch_size + 1}: {response.status_code}"
                )
                continue

            # Parse JSON and merge with existing snapshots
            batch_snapshots = response.json()
            all_snapshots.update(batch_snapshots)

            logger.info(
                f"Processed batch {i // batch_size + 1}/{(len(symbol_list) + batch_size - 1) // batch_size}"
            )

        snapshots = all_snapshots
        results = []

        # Process each symbol exactly like C program (lines 668-759)
        for symbol in symbol_list:
            try:
                # Get snapshot object exactly like C program (line 670)
                snapshot = snapshots.get(symbol)
                if not snapshot:
                    continue

                # Check for required fields exactly like C program (lines 674-680)
                latest_trade = snapshot.get("latestTrade")
                minute_bar = snapshot.get("minuteBar")

                if not latest_trade or not minute_bar:
                    continue

                # Extract trade count from minuteBar.n exactly like C program (lines 682-687)
                minute_trades = minute_bar.get("n")
                if minute_trades is None:
                    continue
                minute_trades = int(minute_trades)

                # Check data freshness - minute bar timestamp
                minute_bar_time = minute_bar.get("t")
                data_age_warning = ""
                if minute_bar_time:
                    try:
                        bar_time = datetime.fromisoformat(minute_bar_time.replace("Z", "+00:00"))
                        age_minutes = (
                            current_time.replace(tzinfo=UTC) - bar_time
                        ).total_seconds() / 60
                        if age_minutes > 60:  # Data older than 1 hour
                            data_age_warning = f" (Data: {age_minutes:.0f}m old)"
                    except (AttributeError, TypeError, ValueError):
                        pass

                # Apply 50 trade filter exactly like C program (line 687)
                if minute_trades < min_trades_per_minute:
                    continue

                # Get price exactly like C program (lines 689-697)
                price_now = latest_trade.get("p")
                if price_now is None:
                    continue
                price_now = float(price_now)

                # Apply global price limit
                max_price = trading_config.max_stock_price
                if price_now > max_price:
                    continue

                # Get daily bar exactly like C program (lines 699-707)
                daily_bar = snapshot.get("dailyBar")
                if not daily_bar:
                    continue

                day_close = daily_bar.get("c")
                if day_close is None:
                    continue
                day_close = float(day_close)

                # Get minute volume exactly like C program (lines 709-713)
                minute_volume = minute_bar.get("v")
                if minute_volume is None:
                    continue
                minute_volume = int(minute_volume)

                # Get reference price for % calculation exactly like C program (lines 715-731)
                # Note: Simplified premarket logic for now - using prevDailyBar.c
                prev_daily_bar = snapshot.get("prevDailyBar")
                if prev_daily_bar and prev_daily_bar.get("c"):
                    reference_price = float(prev_daily_bar["c"])
                else:
                    reference_price = day_close  # Fallback

                # Calculate percent change exactly like C program (line 733)
                percent = ((price_now - reference_price) / reference_price) * 100.0
                percent_change = abs(percent)  # Use absolute value for filtering

                # Apply percent change filter - ONLY UP STOCKS
                if percent_change < min_percent_change or percent <= 0:
                    continue

                # Store results exactly like C program structure (lines 743-754)
                results.append(
                    {
                        "symbol": symbol,
                        "price": price_now,
                        "trades_per_minute": minute_trades,  # This is minuteBar.n from raw JSON!
                        "volume": minute_volume,
                        "percent_change": percent_change,
                        "prev_close": reference_price,
                        "day_close": day_close,
                        "percent": percent,  # Raw percent for display
                        "data_age_warning": data_age_warning,
                    }
                )

            except Exception as e:
                logger.warning(f"Error processing {symbol}: {e}")
                continue

        # Sort results
        if sort_by == "trades":
            results.sort(key=lambda x: x["trades_per_minute"], reverse=True)
        elif sort_by == "percent_change":
            results.sort(key=lambda x: x["percent_change"], reverse=True)
        elif sort_by == "volume":
            results.sort(key=lambda x: x["volume"], reverse=True)

        # Limit results
        results = results[:max_symbols]

        if not results:
            weekend_warning = ""
            if not is_open and current_time.weekday() >= 5:
                weekend_warning = f"\n⚠️  **{market_status}**\n⚠️  **Data shown may be stale from Friday's close - no live weekend trading**\n"

            return f"""
🎯 **DAY TRADING OPPORTUNITY SCAN**
Time: {current_time.strftime("%Y-%m-%d %H:%M:%S")} EDT
Market Status: {market_status}
Threshold: {min_trades_per_minute} trades/minute
Total Qualified: 0 stocks
{weekend_warning}
**No opportunities found with current filters**

**Configured Thresholds:**
- Minimum trades/minute: {min_trades_per_minute}
- Minimum % change: {min_percent_change}%
- Maximum stock price: ${trading_config.max_stock_price}

**Symbols Scanned:** {len(symbol_list):,}
**Scanner Method:** TickerList (tradable assets ≤4 chars)
"""

        # Add market status warning for stale data
        weekend_warning = ""
        if not is_open and current_time.weekday() >= 5:
            weekend_warning = f"\n⚠️  **{market_status}**\n⚠️  **TRADING DATA BELOW IS STALE - Friday's close data, not live trading**\n"

        # Professional tabular format like shell script output
        result = f"""
🎯 **DAY TRADING OPPORTUNITY SCAN**
Time: {current_time.strftime("%Y-%m-%d %H:%M:%S")} EDT
Market Status: {market_status}
Threshold: {min_trades_per_minute} trades/minute
Total Qualified: {len(results)} stocks
{weekend_warning}

```
Rank Symbol  Trades/Min    Change%     Price    Volume      Momentum
=================================================================="""

        for i, stock in enumerate(results, 1):
            # Determine momentum level
            if stock["percent_change"] > 40:
                momentum = "🚀 EXPLOSIVE"
            elif stock["percent_change"] > 20:
                momentum = "🔥 STRONG"
            elif stock["percent_change"] > 10:
                momentum = "📈 ACTIVE"
            else:
                momentum = "⚡ MODERATE"

            # Format percent with proper sign
            change_sign = "+" if stock["percent"] > 0 else ""

            result += f"""
{i:4} {stock["symbol"]:<6} {stock["trades_per_minute"]:>9,} {change_sign}{stock["percent"]:>8.1f}% ${stock["price"]:>7.3f} {stock["volume"]:>9,} {momentum}{stock["data_age_warning"]}"""

        result += """
```

**Key Metrics:**"""

        if results:
            avg_trades = sum(s["trades_per_minute"] for s in results) / len(results)
            # top_trader = max(results, key=lambda x: x["trades_per_minute"])  # Currently unused
            top_mover = max(results, key=lambda x: x["percent_change"])
            winners = len([s for s in results if s["percent"] > 0])
            explosive = len([s for s in results if s["percent_change"] > 10])

            result += f"""
- 🎯 **Top Mover:** {top_mover["symbol"]} ({top_mover["percent"]:+.1f}%) with {top_mover["trades_per_minute"]:,} trades/min
- 📊 **Avg Liquidity:** {avg_trades:,.0f} trades/minute
- 📈 **Winners:** {winners}/{len(results)} stocks positive ({winners / len(results) * 100:.0f}%)
- 🔥 **Explosive Moves:** {explosive} stocks >10% gain

**🚀 READY FOR DAY TRADING! 🚀**"""

        else:
            result += """
- No opportunities found with current filters
- Market must meet configured thresholds"""

        return result

    except Exception as e:
        logger.error(f"Error in day trading scanner: {e}")
        return f"Error scanning for day trading opportunities: {str(e)}"


async def scan_explosive_momentum(
    symbols: str = "ALL",  # Use ALL tradeable assets by default
    min_percent_change: float = 15.0,
) -> str:
    """
    Quick scanner for explosive momentum moves - EXPLOSIVE UP-ONLY.

    Focused on extreme % changes and high activity across all tradeable assets.
    ONLY UP STOCKS - No crashes or negative movers.
    """
    return await scan_day_trading_opportunities(
        symbols=symbols,
        min_trades_per_minute=500,  # Extreme liquidity threshold
        min_percent_change=min_percent_change,
        max_symbols=10,
        sort_by="percent_change",
    )
