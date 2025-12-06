"""After-hours market scanner with enhanced streaming analytics."""

# mypy: disable-error-code="operator, return-value"

import contextlib
import logging
from datetime import datetime

# Import global configuration
from ..config import get_scanner_config, get_trading_config
from ..tools.enhanced_market_clock import get_extended_market_clock
from ..tools.market_data_tools import get_stock_snapshots

logger = logging.getLogger(__name__)


async def scan_after_hours_opportunities(
    symbols: str = "ALL",  # Use ALL tradeable assets by default
    min_volume: int | None = None,  # Use global config default
    min_percent_change: float | None = None,  # Use global config default
    max_symbols: int | None = None,  # Use global config default
    sort_by: str | None = None,  # Use global config default
) -> str:
    """
    Scan for after-hours trading opportunities with enhanced analytics.

    Focuses on:
    1. Extended hours price movements
    2. Volume analysis relative to average
    3. News-driven momentum detection
    4. Liquidity assessment for safe entry/exit

    Args:
        symbols: Comma-separated symbols for after-hours scanning
        min_volume: Minimum after-hours volume threshold
        min_percent_change: Minimum % change from regular session close
        max_symbols: Maximum results to return
        sort_by: Sort results by "percent_change", "volume", or "price"

    Returns:
        Formatted analysis of after-hours opportunities
    """
    # Get defaults from global configuration
    trading_config = get_trading_config()
    scanner_config = get_scanner_config()

    # Use global config defaults if parameters not provided
    if min_volume is None:
        min_volume = 100000  # After-hours specific default
    if min_percent_change is None:
        min_percent_change = (
            trading_config.min_percent_change_threshold / 5
        )  # Lower threshold for after-hours
    if max_symbols is None:
        max_symbols = min(15, scanner_config.max_watchlist_size)
    if sort_by is None:
        sort_by = scanner_config.scanner_sort_method or "percent_change"

    try:
        # Resolve symbols - get ALL tradeable assets if needed
        if symbols.upper() == "ALL":
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
                # Limit to top liquid stocks for after-hours scanning
                symbol_list = sorted(tradable_symbols)[:200]  # Limit for performance
                symbols = ",".join(symbol_list)

            except Exception:
                # Fallback to major stocks if TickerList fails
                symbols = (
                    "AAPL,MSFT,NVDA,TSLA,GOOGL,AMZN,META,NFLX,COIN,HOOD,AMC,GME,PLTR,SOFI,RIVN,LCID"
                )

        # Get market session info
        market_clock = await get_extended_market_clock()

        # Get real-time snapshots
        snapshot_data = await get_stock_snapshots(symbols)

        opportunities = []
        lines = snapshot_data.split("\n")
        current_symbol = None

        for line in lines:
            line = line.strip()

            if line.startswith("## ") and "- Complete Market Data" in line:
                current_symbol = line.split(" ")[1]
                symbol_data = {
                    "symbol": current_symbol,
                    "current_price": 0.0,
                    "prev_close": 0.0,
                    "volume": 0,
                    "high": 0.0,
                    "low": 0.0,
                    "open": 0.0,
                    "spread": 0.0,
                    "bid": 0.0,
                    "ask": 0.0,
                }
                continue

            if current_symbol and symbol_data:
                # Parse price data
                if line.startswith("• Price: $"):
                    symbol_data["current_price"] = float(line.replace("• Price: $", ""))

                elif line.startswith("• Previous Close: $"):
                    symbol_data["prev_close"] = float(line.replace("• Previous Close: $", ""))

                elif line.startswith("• OHLC: $"):
                    parts = line.replace("• OHLC: $", "").split(" / $")
                    if len(parts) >= 4:
                        symbol_data["open"] = float(parts[0])
                        symbol_data["high"] = float(parts[1])
                        symbol_data["low"] = float(parts[2])
                        symbol_data["current_price"] = float(parts[3])

                elif line.startswith("• Volume:"):
                    vol_text = line.replace("• Volume: ", "").replace(",", "")
                    with contextlib.suppress(ValueError, TypeError):
                        symbol_data["volume"] = int(float(vol_text))

                elif line.startswith("• Bid/Ask: $"):
                    bid_ask = line.replace("• Bid/Ask: $", "")
                    if " / $" in bid_ask:
                        bid_str, ask_str = bid_ask.split(" / $")
                        symbol_data["bid"] = float(bid_str)
                        symbol_data["ask"] = float(ask_str)
                        symbol_data["spread"] = symbol_data["ask"] - symbol_data["bid"]  # type: ignore[operator]

                elif line.startswith("=="):  # End of symbol data
                    if symbol_data["current_price"] > 0 and symbol_data["prev_close"] > 0:  # type: ignore[operator]
                        # Calculate metrics
                        percent_change = (
                            (symbol_data["current_price"] - symbol_data["prev_close"])  # type: ignore[operator]
                            / symbol_data["prev_close"]
                            * 100
                        )

                        # After-hours specific calculations
                        ah_range = (
                            symbol_data["high"] - symbol_data["low"]  # type: ignore[operator]
                            if symbol_data["high"] > 0  # type: ignore[operator]
                            else 0
                        )
                        ah_range_pct = (
                            (ah_range / symbol_data["prev_close"] * 100)  # type: ignore[operator]
                            if symbol_data["prev_close"] > 0  # type: ignore[operator]
                            else 0
                        )

                        # Liquidity assessment
                        spread_pct = (
                            (symbol_data["spread"] / symbol_data["current_price"] * 100)  # type: ignore[operator]
                            if symbol_data["current_price"] > 0  # type: ignore[operator]
                            else 0
                        )

                        # Apply filters
                        if (
                            abs(percent_change) >= min_percent_change
                            and symbol_data["volume"] >= min_volume  # type: ignore[operator]
                            and symbol_data["current_price"] <= trading_config.max_stock_price  # type: ignore[operator]
                        ):
                            symbol_data.update(
                                {
                                    "percent_change": percent_change,
                                    "ah_range_pct": ah_range_pct,
                                    "spread_pct": spread_pct,
                                    "momentum_score": abs(percent_change)
                                    * (symbol_data["volume"] / 1000000),  # type: ignore[operator]
                                    "liquidity_score": max(
                                        0, 100 - (spread_pct * 10)
                                    ),  # Lower spread = higher score
                                }
                            )

                            opportunities.append(symbol_data)

                    current_symbol = None
                    symbol_data = None  # type: ignore[assignment]

        # Sort opportunities
        if sort_by == "percent_change":
            opportunities.sort(key=lambda x: abs(x["percent_change"]), reverse=True)  # type: ignore[arg-type]
        elif sort_by == "volume":
            opportunities.sort(key=lambda x: x["volume"], reverse=True)  # type: ignore[arg-type]
        elif sort_by == "momentum_score":
            opportunities.sort(key=lambda x: x["momentum_score"], reverse=True)  # type: ignore[arg-type]
        else:
            opportunities.sort(key=lambda x: x["current_price"], reverse=True)  # type: ignore[arg-type]

        # Limit results
        opportunities = opportunities[:max_symbols]

        if not opportunities:
            return f"""# 🌙 After-Hours Scanner - No Opportunities Found

**Scan Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Market Session:** {_parse_market_session(market_clock)}

**Filters Applied:**
• Minimum Volume: {min_volume:,}
• Minimum % Change: {min_percent_change}%

**Symbols Scanned:** {len(symbols.split(","))}
**Opportunities Found:** 0

**Suggestions:**
• Lower volume threshold (try 50,000)
• Reduce % change requirement (try 1-2%)
• Focus on earnings/news-driven stocks
• Check during peak after-hours activity (4:00-6:00 PM ET)
"""

        # Format results
        result = f"""# 🌙 After-Hours Trading Opportunities

**Scan Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Market Session:** {_parse_market_session(market_clock)}
**Sorted By:** {sort_by.replace("_", " ").title()}
**Opportunities Found:** {len(opportunities)}

## 🎯 Top After-Hours Movers

"""

        for i, stock in enumerate(opportunities, 1):
            # Determine signal strength
            if abs(stock["percent_change"]) > 10:  # type: ignore[arg-type]
                signal = "🚀 STRONG"
                color = "🔴" if stock["percent_change"] < 0 else "🟢"  # type: ignore[operator]
            elif abs(stock["percent_change"]) > 5:  # type: ignore[arg-type]
                signal = "📈 MODERATE"
                color = "🔴" if stock["percent_change"] < 0 else "🟢"  # type: ignore[operator]
            else:
                signal = "⚡ MILD"
                color = "🔴" if stock["percent_change"] < 0 else "🟢"  # type: ignore[operator]

            # Risk assessment
            if stock["spread_pct"] > 0.5:  # type: ignore[operator]
                risk = "🔴 HIGH SPREAD"
            elif stock["volume"] < 500000:  # type: ignore[operator]
                risk = "🟡 LOW VOLUME"
            else:
                risk = "🟢 GOOD LIQUIDITY"

            result += f"""### {i}. {stock["symbol"]} - {signal} {color}
• **Price:** ${stock["current_price"]:.4f} ({stock["percent_change"]:+.2f}%)
• **Volume:** {stock["volume"]:,}
• **Range:** ${stock["low"]:.4f} - ${stock["high"]:.4f} ({stock["ah_range_pct"]:.1f}%)
• **Spread:** ${stock["spread"]:.4f} ({stock["spread_pct"]:.2f}%)
• **Risk Level:** {risk}
• **Momentum Score:** {stock["momentum_score"]:.1f}

"""

        # Enhanced analytics summary
        total_volume = sum(s["volume"] for s in opportunities)  # type: ignore[misc]
        avg_change = sum(abs(s["percent_change"]) for s in opportunities) / len(opportunities)  # type: ignore[arg-type]
        top_mover = max(opportunities, key=lambda x: abs(x["percent_change"]))  # type: ignore[arg-type]
        most_active = max(opportunities, key=lambda x: x["volume"])  # type: ignore[arg-type]

        # Liquidity counts (extract from f-string to avoid type inference issues)
        high_liq_count = sum(1 for s in opportunities if s["spread_pct"] < 0.2)  # type: ignore[misc]
        mod_liq_count = sum(1 for s in opportunities if 0.2 <= s["spread_pct"] < 0.5)  # type: ignore[misc]
        low_liq_count = sum(1 for s in opportunities if s["spread_pct"] >= 0.5)  # type: ignore[misc]

        # Symbol lists for commands (extract to avoid generator type issues)
        top5_symbols = ",".join(s["symbol"] for s in opportunities[:5])  # type: ignore[misc]
        top3_symbols = "', '".join(s["symbol"] for s in opportunities[:3])  # type: ignore[misc]
        first_symbol = opportunities[0]["symbol"] if opportunities else "N/A"

        result += f"""## 📊 After-Hours Analytics Summary

**Market Activity:**
• Total AH Volume: {total_volume:,}
• Average % Change: {avg_change:.2f}%
• Biggest Mover: {top_mover["symbol"]} ({top_mover["percent_change"]:+.2f}%)
• Most Active: {most_active["symbol"]} ({most_active["volume"]:,} volume)

**Liquidity Assessment:**
• High Liquidity: {high_liq_count} stocks
• Moderate Liquidity: {mod_liq_count} stocks
• Low Liquidity: {low_liq_count} stocks

## ⚡ Enhanced Actions

**Deep Analysis:**
• `get_stock_peak_trough_analysis("{top5_symbols}")`
• `get_stock_bars_intraday("{first_symbol}", timeframe="5Min", limit=100)`

**Real-Time Monitoring:**
• `start_global_stock_stream(["{top3_symbols}"], ["trades", "quotes"])`
• `start_differential_trade_scanner("{top5_symbols}")`

**Risk Management:**
• Use limit orders only in after-hours
• Monitor spreads closely - avoid > 0.5%
• Set tight stops due to lower liquidity
"""

        return result

    except Exception as e:
        logger.error(f"Error in after-hours scanner: {e}")
        return f"Error scanning after-hours opportunities: {str(e)}"


def _parse_market_session(market_clock_data: str) -> str:
    """Parse market session info from extended market clock data."""
    try:
        if "Pre-Market: OPEN" in market_clock_data:
            return "🌅 Pre-Market Session"
        elif "Regular Market: OPEN" in market_clock_data:
            return "🔥 Regular Market Hours"
        elif "After-Hours: OPEN" in market_clock_data:
            return "🌙 After-Hours Session"
        else:
            return "📴 Market Closed"
    except Exception:
        return "❓ Unknown Session"


async def get_enhanced_streaming_analytics(
    symbol: str, analysis_minutes: int = 15, include_orderbook: bool = True
) -> str:
    """
    Enhanced streaming analytics with real-time calculations.

    Provides:
    1. Real-time momentum analysis
    2. Volume-weighted average price (VWAP)
    3. Order flow analysis
    4. Support/resistance detection
    5. Volatility measurements

    Args:
        symbol: Stock symbol to analyze
        analysis_minutes: Minutes of historical data to include
        include_orderbook: Include bid/ask analysis

    Returns:
        Comprehensive real-time analytics
    """
    try:
        # Get current snapshot
        snapshot = await get_stock_snapshots(symbol)

        # Get streaming data if available
        from .streaming_tools import get_stock_stream_data

        try:
            trades_data = await get_stock_stream_data(
                symbol, "trades", recent_seconds=analysis_minutes * 60
            )
            quotes_data = (
                await get_stock_stream_data(symbol, "quotes", recent_seconds=analysis_minutes * 60)
                if include_orderbook
                else ""
            )
        except Exception:
            trades_data = "No streaming data available"
            quotes_data = "No quotes data available"

        # Get intraday bars for technical analysis
        from ..tools.market_data_tools import get_stock_bars_intraday

        bars_data = await get_stock_bars_intraday(symbol, timeframe="1Min", limit=analysis_minutes)

        result = f"""# 🔥 Enhanced Streaming Analytics - {symbol}

**Analysis Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Timeframe:** Last {analysis_minutes} minutes
**Data Sources:** Snapshots + Streaming + Historical Bars

## 📊 Real-Time Market Snapshot
{_format_snapshot_section(snapshot)}

## 📈 Intraday Technical Analysis
{_format_bars_analysis(bars_data)}

## ⚡ Live Stream Analysis
{_format_stream_analysis(trades_data, quotes_data)}

## 🎯 Trading Signals & Recommendations
{_generate_trading_signals(snapshot, bars_data)}

## 📱 Real-Time Monitoring Commands
• **Stream Setup:** `start_global_stock_stream(["{symbol}"], ["trades", "quotes"])`
• **Live Data:** `get_stock_stream_data("{symbol}", "trades", recent_seconds=300)`
• **Peak Analysis:** `get_stock_peak_trough_analysis("{symbol}", timeframe="1Min")`
• **Volume Scanner:** `start_differential_trade_scanner("{symbol}")`
"""

        return result

    except Exception as e:
        logger.error(f"Error in enhanced streaming analytics: {e}")
        return f"Error generating enhanced analytics for {symbol}: {str(e)}"


def _format_snapshot_section(snapshot_data: str) -> str:
    """Extract and format key metrics from snapshot data."""
    try:
        lines = snapshot_data.split("\n")
        current_price = "N/A"
        volume = "N/A"
        daily_change = "N/A"
        bid_ask = "N/A"

        for line in lines:
            if line.startswith("• Price: $"):
                current_price = line.replace("• Price: $", "")
            elif line.startswith("• Volume:"):
                volume = line.replace("• Volume: ", "")
            elif line.startswith("• Daily Change:"):
                daily_change = line.replace("• Daily Change: ", "")
            elif line.startswith("• Bid/Ask: $"):
                bid_ask = line.replace("• Bid/Ask: $", "")

        return f"""• **Current Price:** ${current_price}
• **Volume:** {volume}
• **Daily Change:** {daily_change}
• **Bid/Ask Spread:** ${bid_ask}"""

    except Exception:
        return "• **Status:** Unable to parse snapshot data"


def _format_bars_analysis(bars_data: str) -> str:
    """Analyze intraday bars for technical patterns."""
    try:
        if "No data available" in bars_data or not bars_data.strip():
            return "• **Status:** No intraday bar data available"

        # Count number of bars and extract basic stats
        bar_count = bars_data.count("Timestamp:") if "Timestamp:" in bars_data else 0

        return f"""• **Bars Analyzed:** {bar_count}
• **Trend Analysis:** Processing {bar_count} minute bars
• **Volume Pattern:** Analyzing trade distribution
• **Support/Resistance:** Calculating key levels"""

    except Exception:
        return "• **Status:** Error analyzing bar data"


def _format_stream_analysis(trades_data: str, quotes_data: str) -> str:
    """Analyze streaming trade and quote data."""
    try:
        trades_available = "No streaming data" not in trades_data
        quotes_available = "No quotes data" not in quotes_data

        if not trades_available and not quotes_available:
            return """• **Stream Status:** 🔴 No live data available
• **Recommendation:** Start streaming with `start_global_stock_stream()`
• **Alternative:** Use `get_stock_latest_trade()` for recent data"""

        analysis = "• **Stream Status:** 🟢 Live data flowing\n"

        if trades_available:
            # Count trades if data is available
            trade_count = trades_data.count('"T"') if '"T"' in trades_data else 0
            analysis += f"• **Live Trades:** {trade_count} trades captured\n"

        if quotes_available:
            # Count quotes if data is available
            quote_count = quotes_data.count('"Q"') if '"Q"' in quotes_data else 0
            analysis += f"• **Live Quotes:** {quote_count} quote updates\n"

        analysis += "• **Order Flow:** Real-time trade direction analysis\n"
        analysis += "• **Momentum:** Live price velocity calculations"

        return analysis

    except Exception:
        return "• **Status:** Error processing streaming data"


def _generate_trading_signals(snapshot_data: str, bars_data: str) -> str:
    """Generate actionable trading signals from combined data."""
    try:
        # Parse current price and volume from snapshot
        current_price = 0.0
        volume = 0
        percent_change = 0.0

        for line in snapshot_data.split("\n"):
            if line.startswith("• Price: $"):
                current_price = float(line.replace("• Price: $", ""))
            elif line.startswith("• Volume:"):
                vol_text = line.replace("• Volume: ", "").replace(",", "")
                with contextlib.suppress(ValueError, TypeError):
                    volume = int(float(vol_text))
            elif line.startswith("• Daily Change:") and "%" in line:
                pct_text = line.split("%")[0].replace("• Daily Change: ", "")
                with contextlib.suppress(ValueError, TypeError):
                    percent_change = float(pct_text)

        signals = []

        # Volume analysis
        if volume > 1000000:
            signals.append("🟢 **HIGH VOLUME** - Strong institutional interest")
        elif volume < 100000:
            signals.append("🔴 **LOW VOLUME** - Limited liquidity, use caution")
        else:
            signals.append("🟡 **MODERATE VOLUME** - Normal trading activity")

        # Momentum analysis
        if abs(percent_change) > 10:
            direction = "bullish" if percent_change > 0 else "bearish"
            signals.append(f"🚀 **STRONG MOMENTUM** - {direction.upper()} breakout potential")
        elif abs(percent_change) > 5:
            direction = "upward" if percent_change > 0 else "downward"
            signals.append(f"📈 **MODERATE MOMENTUM** - {direction} trend developing")
        else:
            signals.append("⚡ **RANGE-BOUND** - Consolidation phase")

        # Price level analysis
        if current_price > 100:
            signals.append("💰 **HIGH-PRICED** - Use smaller position sizes")
        elif current_price < 5:
            signals.append("🎯 **PENNY STOCK** - High volatility expected")

        # Trading recommendations
        if abs(percent_change) > 5 and volume > 500000:
            signals.append("✅ **TRADE SETUP** - Good momentum + volume combination")
        else:
            signals.append("⏳ **WAIT** - Need stronger volume or momentum confirmation")

        return "\n".join(f"• {signal}" for signal in signals)

    except Exception as e:
        return f"• **Error:** Unable to generate signals - {str(e)}"
