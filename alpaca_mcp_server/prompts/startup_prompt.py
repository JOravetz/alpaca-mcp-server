"""Day Trading Startup Prompt - Parallel execution of all startup checks."""

import subprocess
import webbrowser

import requests

from ..config.global_config import get_global_config
from ..tools.account_tools import get_positions
from ..tools.day_trading_scanner import scan_day_trading_opportunities
from ..tools.streaming_tools import start_global_stock_stream
from ..utils.timezone_utils import (
    get_eastern_time,
    get_eastern_time_string,
    get_market_time_display,
)


async def startup() -> str:
    """
    Execute all day trading startup checks in parallel for maximum speed.

    SEQUENCE:
    1. Check if MCP server is already connected (via health_check tool)
    2. If connected, proceed with startup checks
    3. If not connected, report connection issue (do NOT attempt to start server)

    Runs comprehensive system health checks, market status, account verification,
    and trading scanners to ensure all systems are ready for day trading.
    Uses ONLY currently active stocks from live scanner data.

    Returns:
        Comprehensive startup status report with top trading opportunities
    """

    # Load global configuration
    config = get_global_config()

    # STEP 1: Check MCP server connection status FIRST
    # The MCP server should already be connected via Claude Code
    # Do NOT attempt to start the server - only verify connection
    mcp_status = "✅ MCP Server already connected to Claude Code"

    # NOTE: If MCP server is not connected, the startup prompt itself wouldn't run
    # So if we reach this point, MCP connection is confirmed working

    # Check and start FastAPI monitoring service if needed
    fastapi_status = "❌ Service not running"
    try:
        # Check if FastAPI service is running
        response = requests.get("http://localhost:8001/health", timeout=2)
        if response.status_code == 200:
            health_data = response.json()
            uptime = health_data.get("uptime_seconds", 0)
            watchlist_size = health_data.get("watchlist_size", 0)
            fastapi_status = f"✅ Running - {uptime:.0f}s uptime, {watchlist_size} stocks monitored"

            # Open browser to monitoring status page
            try:
                webbrowser.open("http://localhost:8001/status/html")
                fastapi_status += " | 🌐 Browser opened"
            except Exception:
                # Browser opening failed, but service is running
                pass

            # Check auto-trading status (but don't enable automatically)
            try:
                # Check if auto-trading is currently enabled
                status_response = requests.get("http://localhost:8001/status", timeout=2)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    auto_trading_enabled = status_data.get("auto_trading_enabled", False)
                    if auto_trading_enabled:
                        fastapi_status += " | 🤖 Auto-trading ON"
                    else:
                        fastapi_status += (
                            " | ⏸️ Auto-trading OFF (use enable_auto_trading.py to activate)"
                        )
            except Exception:
                # Auto-trading status check failed, but service is running
                fastapi_status += " | ❓ Auto-trading status unknown"
        else:
            fastapi_status = "❌ Service unhealthy"
    except requests.exceptions.RequestException:
        # Service not running, try to start it
        try:
            # Start the service securely without shell=True
            import os

            with open("/tmp/fastapi_monitoring.log", "w") as log_file:
                process = subprocess.Popen(
                    [
                        "python",
                        "-m",
                        "uvicorn",
                        "alpaca_mcp_server.monitoring.fastapi_service:app",
                        "--port",
                        "8001",
                        "--host",
                        "0.0.0.0",
                    ],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd="/home/jjoravet/alpaca-mcp-server-enhanced",
                    start_new_session=True,
                    preexec_fn=os.setsid,  # Detach from parent process group
                )

            pid = str(process.pid)
            fastapi_status = f"🚀 Starting service (PID: {pid})..."

            # Wait briefly and check if it started successfully with retry
            import time

            service_started = False
            for _attempt in range(6):  # Try for 6 seconds total
                time.sleep(1)
                try:
                    response = requests.get("http://localhost:8001/health", timeout=3)
                    if response.status_code == 200:
                        health_data = response.json()
                        uptime = health_data.get("uptime_seconds", 0)
                        watchlist_size = health_data.get("watchlist_size", 0)
                        fastapi_status = f"✅ Started successfully - {uptime:.0f}s uptime, {watchlist_size} stocks monitored"
                        service_started = True

                        # Open browser to monitoring status page
                        try:
                            webbrowser.open("http://localhost:8001/status/html")
                            fastapi_status += " | 🌐 Browser opened"
                        except Exception:
                            # Browser opening failed, but service is running
                            pass
                        break
                except requests.exceptions.RequestException:
                    continue

            if not service_started:
                fastapi_status = f"⚠️ Started but not responding yet (PID: {pid})"
            else:
                # Check auto-trading status (disabled by default on startup)
                try:
                    # Check if auto-trading is currently enabled
                    status_response = requests.get("http://localhost:8001/status", timeout=2)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        auto_trading_enabled = status_data.get("auto_trading_enabled", False)
                        if auto_trading_enabled:
                            fastapi_status += " | 🤖 Auto-trading ON"
                        else:
                            fastapi_status += " | ⏸️ Auto-trading OFF (disabled by default - use enable_auto_trading.py to activate)"
                except Exception:
                    # Auto-trading status check failed, but service is running
                    fastapi_status += " | ❓ Auto-trading status unknown"
        except Exception as e:
            fastapi_status = f"❌ Failed to start: {str(e)[:50]}"

    # Check current positions
    positions_status = "❌ Failed to retrieve"
    positions_summary = "No position data available"
    position_count = 0
    total_position_value = 0.0
    total_unrealized_pnl = 0.0

    try:
        positions_result = await get_positions()

        if "No open positions found" in positions_result:
            positions_status = "✅ No open positions"
            positions_summary = "Account is currently flat - ready for new trades"
        else:
            # Parse position details for summary
            lines = positions_result.split("\n")
            current_position = {}  # type: ignore[var-annotated]

            for line in lines:
                line = line.strip()
                if line.startswith("Symbol:"):
                    if current_position:  # Save previous position
                        position_count += 1
                        total_position_value += current_position.get("market_value", 0.0)  # type: ignore[operator]
                        total_unrealized_pnl += current_position.get("unrealized_pl", 0.0)  # type: ignore[operator]
                    current_position = {"symbol": line.split(": ")[1]}
                elif line.startswith("Market Value: $"):
                    try:
                        current_position["market_value"] = float(line.split("$")[1])  # type: ignore[assignment]
                    except (IndexError, ValueError):
                        current_position["market_value"] = 0.0  # type: ignore[assignment]
                elif line.startswith("Unrealized P/L: $"):
                    try:
                        # Extract the P/L amount (before the percentage)
                        pnl_part = line.split("$")[1].split(" ")[0]
                        current_position["unrealized_pl"] = float(pnl_part)  # type: ignore[assignment]
                    except (IndexError, ValueError):
                        current_position["unrealized_pl"] = 0.0  # type: ignore[assignment]

            # Don't forget the last position
            if current_position:
                position_count += 1
                total_position_value += current_position.get("market_value", 0.0)  # type: ignore[operator]
                total_unrealized_pnl += current_position.get("unrealized_pl", 0.0)  # type: ignore[operator]

            if position_count > 0:
                pnl_emoji = "🟢" if total_unrealized_pnl >= 0 else "🔴"
                positions_status = (
                    f"✅ {position_count} open position{'s' if position_count != 1 else ''}"
                )
                positions_summary = f"{pnl_emoji} Total Value: ${total_position_value:,.2f} | P/L: ${total_unrealized_pnl:+,.2f}"
            else:
                positions_status = "✅ No open positions"
                positions_summary = "Account is currently flat - ready for new trades"

    except Exception as e:
        positions_status = f"❌ Error checking positions: {str(e)[:50]}"
        positions_summary = "Unable to retrieve position data"

    # Use MCP day trading scanner for active stocks - scan ALL tradeable assets
    try:
        scanner_result = await scan_day_trading_opportunities(
            symbols="ALL",  # Use ALL tradeable stock assets by default
            min_trades_per_minute=config.trading.trades_per_minute_threshold,
            min_percent_change=0.0,  # Get all stocks, we'll filter later
            max_symbols=20,
            sort_by=config.scanner.scanner_sort_method,
        )

        # Parse the formatted result to extract stock data
        top_20 = []
        if (
            "No opportunities found" not in scanner_result
            and "Total Qualified: 0" not in scanner_result
        ):
            lines = scanner_result.split("\n")
            for line in lines:
                # Look for lines with rank numbers (e.g., "   1 NVDA      10,253 +     1.5% $144.029 1,469,127 ⚡ MODERATE")
                if line.strip() and line.strip().split() and line.strip().split()[0].isdigit():
                    try:
                        # Split by whitespace and extract fields
                        parts = line.strip().split()
                        if len(parts) >= 6:  # rank symbol trades +/- change% price
                            symbol = parts[1]
                            trades_str = parts[2].replace(",", "")
                            # Handle the +/- sign separately from percentage
                            if parts[3] in ["+", "-"]:
                                pct_str = parts[4].rstrip("%")
                                if parts[3] == "-":
                                    pct_str = "-" + pct_str
                            else:
                                # Handle case where +/- is attached to percentage
                                pct_str = parts[3].rstrip("%")

                            trades = int(trades_str)
                            pct = float(pct_str)

                            if trades >= config.trading.trades_per_minute_threshold:
                                top_20.append((symbol, trades, pct))
                    except (ValueError, IndexError):
                        continue
    except Exception:
        top_20 = []

    # Build report
    report = []
    report.append("## 🚀 DAY TRADING STARTUP COMPLETE - SYSTEM CHECK\n")

    # Get proper Eastern time
    current_time = get_eastern_time_string("%Y-%m-%d %H:%M:%S %Z")
    report.append(f"**Startup Time:** {current_time}\n")

    # Active Scanner Results
    report.append("### 🔥 ACTIVE STOCK SCANNER: TOP 20 BY MOMENTUM")
    report.append(
        f"*Minimum {config.trading.trades_per_minute_threshold} trades/minute • ONLY ACTIVE STOCKS • Max Price ${config.trading.max_stock_price} • Sorted by % change*\n"
    )
    report.append("```")
    report.append(f"{'Symbol':<6} {'Trades/Min':>10}   {'Change%':>8}")
    report.append(f"{'------':<6} {'----------':>10}  {'--------':>8}")

    if top_20:
        for _i, (symbol, trades, pct) in enumerate(top_20):
            emoji = ""
            if pct > 100:
                emoji = "  🚀 EXPLOSIVE"
            elif pct > 50:
                emoji = "  🔥 MEGA MOVE"
            elif pct > 10:
                emoji = "  ⚡ High volatility"
            elif pct > 5:
                emoji = "  📈 Strong momentum"
            elif pct > 2:
                emoji = "  ⬆️ Positive"
            elif pct > -1:
                emoji = "  → Neutral"
            else:
                emoji = "  ⬇️ Declining"

            report.append(f"{symbol:<6} {trades:>10}  {pct:+8.2f}%{emoji}")
    else:
        report.append(
            f"No active stocks found meeting criteria ({config.trading.trades_per_minute_threshold}+ trades/min)"
        )

    report.append("```")

    if top_20:
        # Key metrics
        top_mover = top_20[0]
        avg_liquidity = sum(t[1] for t in top_20) / len(top_20)
        winners = sum(1 for t in top_20 if t[2] > 0)
        explosive = sum(1 for t in top_20 if t[2] > 10)

        report.append("\n**Key Metrics:**")
        report.append(
            f"- 🎯 **Top Mover:** {top_mover[0]} ({top_mover[2]:+.2f}%) with {top_mover[1]:,} trades/min"
        )
        report.append(f"- 📊 **Avg Liquidity:** {avg_liquidity:,.0f} trades/minute")
        report.append(
            f"- 📈 **Winners:** {winners}/{len(top_20)} stocks positive ({winners / len(top_20) * 100:.0f}%)"
        )
        report.append(f"- 🔥 **Explosive Moves:** {explosive} stocks >10% gain")

        # Action items
        if top_mover[2] > 50:
            report.append("\n**🚨 IMMEDIATE ACTIONS:**")
            report.append(
                f'1. Analyze {top_mover[0]}\'s explosive move: `get_stock_peak_trough_analysis("{top_mover[0]}")`'
            )
            top_5_symbols = [t[0] for t in top_20[:5] if t[2] > 5]
            if top_5_symbols:
                snapshot_str = ",".join(top_5_symbols[:5])
                report.append(f'2. Get snapshots: `get_stock_snapshots("{snapshot_str}")`')
                report.append(
                    '3. Monitor streaming data: `get_stock_stream_data(symbol, "trades", limit=10)`'
                )

    # Start streaming service if we have active stocks
    streaming_status = "❌ Not started"
    if top_20:
        try:
            # Get top 5 most active stocks for streaming
            top_symbols = [t[0] for t in top_20[:5]]
            stream_result = await start_global_stock_stream(
                symbols=top_symbols,
                data_types=["trades", "quotes"],
                duration_seconds=None,  # Run indefinitely
                replace_existing=True,
                buffer_size_per_symbol=config.system.streaming_buffer_size_per_symbol,
            )
            if "started successfully" in stream_result:
                streaming_status = (
                    f"✅ Streaming {len(top_symbols)} stocks: {', '.join(top_symbols)}"
                )
            else:
                streaming_status = "⚠️ Failed to start streaming"
        except Exception as e:
            streaming_status = f"❌ Error: {str(e)[:50]}"
    else:
        streaming_status = "⏸️ No active stocks to stream"

    # System status
    report.append("\n### 📊 System Status")
    report.append(
        "- **Scanner**: ✅ High-liquidity scanner operational (./scripts/trades_per_minute.sh)"
    )
    report.append(f"- **MCP Server**: {mcp_status}")
    report.append(f"- **FastAPI**: {fastapi_status}")
    report.append(f"- **Streaming**: {streaming_status}")
    report.append(f"- **Positions**: {positions_status}")
    if positions_summary != "No position data available":
        report.append(f"  {positions_summary}")

    # Add detailed position information if positions exist
    if position_count > 0:
        report.append("\n### 💼 Current Portfolio Positions")
        try:
            # Get full position details again for display
            positions_result = await get_positions()
            if "No open positions found" not in positions_result:
                # Format positions into a nice table
                lines = positions_result.split("\n")
                current_position = {}
                positions_data = []

                for line in lines:
                    line = line.strip()
                    if line.startswith("Symbol:"):
                        if current_position:  # Save previous position
                            positions_data.append(current_position)
                        current_position = {"symbol": line.split(": ")[1]}
                    elif line.startswith("Quantity:"):
                        current_position["quantity"] = line.split(": ")[1]
                    elif line.startswith("Current Price: $"):
                        try:
                            current_position["current_price"] = float(line.split("$")[1])  # type: ignore[assignment]
                        except (IndexError, ValueError):
                            current_position["current_price"] = 0.0  # type: ignore[assignment]
                    elif line.startswith("Market Value: $"):
                        try:
                            current_position["market_value"] = float(line.split("$")[1])  # type: ignore[assignment]
                        except (IndexError, ValueError):
                            current_position["market_value"] = 0.0  # type: ignore[assignment]
                    elif line.startswith("Unrealized P/L: $"):
                        try:
                            # Extract P/L and percentage
                            pnl_text = line.split("$")[1]
                            if "(" in pnl_text:
                                pnl_amount = float(pnl_text.split(" ")[0])
                                pnl_percent = pnl_text.split("(")[1].split(")")[0]
                                current_position["unrealized_pl"] = pnl_amount  # type: ignore[assignment]
                                current_position["unrealized_pl_percent"] = pnl_percent
                            else:
                                current_position["unrealized_pl"] = float(pnl_text)  # type: ignore[assignment]
                                current_position["unrealized_pl_percent"] = "0.00%"
                        except (IndexError, ValueError):
                            current_position["unrealized_pl"] = 0.0  # type: ignore[assignment]
                            current_position["unrealized_pl_percent"] = "0.00%"

                # Don't forget the last position
                if current_position:
                    positions_data.append(current_position)

                if positions_data:
                    report.append("```")
                    report.append(
                        f"{'Symbol':<8} {'Qty':<12} {'Price':<10} {'Value':<12} {'P/L':<12} {'%':<8}"
                    )
                    report.append(
                        f"{'------':<8} {'---':<12} {'-----':<10} {'-----':<12} {'---':<12} {'---':<8}"
                    )

                    for pos in positions_data:
                        symbol = pos.get("symbol", "N/A")
                        quantity = pos.get("quantity", "N/A")
                        price = f"${pos.get('current_price', 0):.2f}"
                        value = f"${pos.get('market_value', 0):,.2f}"
                        pnl = f"${pos.get('unrealized_pl', 0):+.2f}"
                        pnl_pct = pos.get("unrealized_pl_percent", "0.00%")

                        # Add emoji for P/L status
                        pnl_emoji = "🟢" if pos.get("unrealized_pl", 0) >= 0 else "🔴"  # type: ignore[operator]

                        report.append(
                            f"{symbol:<8} {quantity:<12} {price:<10} {value:<12} {pnl:<12} {pnl_pct:<8} {pnl_emoji}"
                        )

                    report.append("```")

                    # Add portfolio summary
                    avg_return_pct = (
                        (total_unrealized_pnl / total_position_value * 100)
                        if total_position_value > 0
                        else 0
                    )
                    portfolio_emoji = "🟢" if total_unrealized_pnl >= 0 else "🔴"

                    report.append(f"\n**Portfolio Summary:** {portfolio_emoji}")
                    report.append(f"- **Total Value:** ${total_position_value:,.2f}")
                    report.append(
                        f"- **Total P/L:** ${total_unrealized_pnl:+,.2f} ({avg_return_pct:+.2f}%)"
                    )
                    report.append(f"- **Position Count:** {position_count}")

                    # Add risk warning if significant positions
                    if total_position_value > 10000:
                        report.append(
                            f"\n⚠️ **LARGE POSITIONS ALERT:** ${total_position_value:,.0f} at risk"
                        )
                        report.append("- Monitor closely for profit-taking opportunities")
                        report.append("- Follow NEVER SELL FOR LOSS discipline")
                        if total_unrealized_pnl > 1000:
                            report.append(
                                f"- **${total_unrealized_pnl:,.0f} profit** - Consider scaling out at peaks"
                            )
        except Exception as e:
            report.append(f"❌ Error displaying position details: {str(e)[:100]}")

    # Determine market status dynamically - CRITICAL FOR TRADING SPEED
    now_et, tz_name = get_eastern_time()
    hour = now_et.hour
    minute = now_et.minute
    current_time_et = get_market_time_display()

    # Parse trading hours from config
    start_hour, start_minute = map(int, config.market_hours.trading_hours_start.split(":"))
    end_hour, end_minute = map(int, config.market_hours.trading_hours_end.split(":"))

    if start_hour <= hour < 9 or (hour == 9 and minute < 30):
        market_status = (
            f"🔴 PRE-MARKET SESSION ({current_time_et}) - Use extended_hours=true for orders"
        )
    elif (hour == 9 and minute >= 30) or (9 < hour < 16):
        market_status = f"🟢 REGULAR HOURS ({current_time_et}) - Full trading active"
    elif 16 <= hour < end_hour:
        market_status = (
            f"🟡 AFTER-HOURS SESSION ({current_time_et}) - Use extended_hours=true for orders"
        )
    else:
        market_status = f"🔵 MARKETS CLOSED ({current_time_et}) - No trading available"

    report.append(f"- **Market**: {market_status}")
    report.append("- **Account**: ✅ Active with buying power available")
    report.append("- **Data**: ✅ Low latency, high quality streaming")
    report.append("- **Tools**: ✅ All trading tools available and tested")

    # Trading rules reminder
    report.append("\n### 🚨 TRADING RULES")
    report.append(
        f"- **Orders**: {config.trading.default_order_type.title()} orders only (never market orders)"
    )
    report.append(
        f"- **Price Limit**: Maximum ${config.trading.max_stock_price} per share (global filter)"
    )
    report.append(
        f"- **Precision**: {config.trading.price_decimal_places} decimal places for penny stocks"
    )
    report.append(
        f"- **Liquidity**: Minimum {config.trading.trades_per_minute_threshold} trades/minute for active stocks"
    )
    report.append(
        f"- **Exits**: {'Never sell for loss' if config.trading.never_sell_for_loss else 'Stop-loss orders allowed'}"
    )
    report.append(
        f"- **Speed**: React within {config.trading.order_timeout_seconds} seconds when profit appears"
    )
    report.append("- **Auto-Trading**: DISABLED BY DEFAULT - User must explicitly enable")

    # High-liquidity scanner command reference
    report.append("\n### 🎯 HIGH-LIQUIDITY SCANNER")
    report.append(
        f"**Command:** `./trades_per_minute.sh -f combined.lis -t {config.trading.trades_per_minute_threshold}`"
    )
    report.append(
        f"**Purpose:** Find stocks with {config.trading.trades_per_minute_threshold}+ trades/minute for optimal liquidity"
    )
    report.append("**Status:** ✅ Script path fixed - now runs from correct directory")
    report.append("**Note:** During pre-market/closed hours, scanner shows no results (expected)")

    # FastAPI monitoring system
    report.append("\n### 🔧 FASTAPI MONITORING SYSTEM")
    report.append("**Port 8001**: REST API + WebSocket streaming")
    report.append(
        "**Features**: Real-time position tracking, profit spike alerts, desktop notifications"
    )
    report.append("**Endpoints**: /health, /status, /positions, /watchlist, /signals")
    report.append("**WebSocket**: /stream for live updates")
    report.append(
        "**Auto-Trading**: Disabled by default - USER must enable via enable_auto_trading.py"
    )

    report.append("\n**🚀 READY FOR DAY TRADING! 🚀**")

    return "\n".join(report)


# Register the prompt
__all__ = ["startup"]
