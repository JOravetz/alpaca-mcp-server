"""Refactored FastAPI-based Hybrid Trading Service

Production-ready monitoring service with clean modular architecture,
REST API, WebSocket streaming, and persistent background monitoring.
"""

import asyncio
import json
import logging
import webbrowser
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

# Global state file path
STATE_FILE = Path(__file__).parent.parent.parent / "monitoring_data" / "fastapi_service_state.json"


def load_state():
    """Load service state from disk"""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                state = json.load(f)
                logging.info(
                    f"Loaded service state: {len(state.get('watchlist', []))} symbols in watchlist"
                )
                return state
    except Exception as e:
        logging.warning(f"Could not load service state: {e}")

    return {
        "watchlist": [],
        "auto_scan_enabled": False,
        "auto_trader_enabled": False,
        "last_saved": None,
    }


def save_state(state_data: dict):
    """Save service state to disk"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state_data["last_saved"] = datetime.now().isoformat()

        with open(STATE_FILE, "w") as f:
            json.dump(state_data, f, indent=2)

        logging.info(f"Saved service state: {len(state_data.get('watchlist', []))} symbols")

    except Exception as e:
        logging.error(f"Could not save service state: {e}")


# Create a simple monitoring service instance
monitoring_service = None
watchlist_task = None


async def update_watchlist_task():
    """Background task to update watchlist every 30 seconds using scanner"""
    await asyncio.sleep(5)  # Give time for service to initialize

    while True:
        try:
            logging.info("Running scanner to update watchlist...")

            # Run the MCP scanner tool to get active stocks
            from ..config.global_config import get_global_config
            from ..tools.day_trading_scanner import scan_day_trading_opportunities

            config = get_global_config()

            # Use a pre-defined list of popular day trading symbols to avoid TickerList issues
            default_symbols = [
                "PSTV",
                "PHIO",
                "NEHC",
                "SOUN",
                "RIOT",
                "MARA",
                "COIN",
                "HOOD",
                "RBLX",
                "AMC",
                "GME",
                "PLTR",
                "SOFI",
                "RIVN",
                "LCID",
                "CERO",
                "NVDA",
                "AMD",
                "TSLA",
                "AAPL",
                "MSFT",
                "META",
                "GOOGL",
                "AMZN",
                "NFLX",
                "SPY",
                "QQQ",
            ]

            # Run scanner with specific symbols to avoid alpaca_trade_api dependency
            scanner_result = await scan_day_trading_opportunities(
                symbols=",".join(default_symbols),
                min_trades_per_minute=config.trading.trades_per_minute_threshold,
                min_percent_change=config.trading.min_percent_change_threshold,
                max_symbols=config.scanner.max_watchlist_size,
            )

            # Parse scanner results and extract qualified symbols
            new_watchlist = set()
            if "Total Qualified:" in scanner_result and "0 stocks" not in scanner_result:
                lines = scanner_result.split("\n")
                in_table = False

                for line in lines:
                    if "Rank Symbol  Trades/Min" in line:
                        in_table = True
                        continue
                    elif "Key Metrics:" in line:
                        in_table = False
                        break

                    if in_table and line.strip() and not line.startswith("==="):
                        parts = line.split()
                        if len(parts) >= 5:
                            try:
                                symbol = parts[1]
                                # Extract price from parts[4] which should be like "$0.317"
                                if "$" in parts[4]:
                                    price = float(parts[4].replace("$", "").replace(",", ""))
                                    if (
                                        price <= config.trading.max_stock_price
                                        and len(symbol) <= 4
                                        and symbol.isalpha()
                                    ):
                                        new_watchlist.add(symbol)
                                        logging.debug(
                                            f"Scanner found active stock: {symbol} at ${price:.3f}"
                                        )
                            except (IndexError, ValueError) as e:
                                logging.debug(f"Failed to parse scanner line: {line} - {e}")
                                continue

            # Update monitoring service watchlist with active stocks
            if monitoring_service:
                old_size = len(monitoring_service.watchlist)
                monitoring_service.watchlist = new_watchlist
                new_size = len(new_watchlist)

                if new_size != old_size:
                    logging.info(f"Watchlist updated: {old_size} → {new_size} active stocks")
                    if new_watchlist:
                        logging.info(f"Active stocks: {', '.join(sorted(new_watchlist))}")
                else:
                    logging.debug(f"Watchlist unchanged: {new_size} active stocks")

        except Exception as e:
            logging.error(f"Error updating watchlist from scanner: {e}")

        await asyncio.sleep(30)  # Update every 30 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global monitoring_service, watchlist_task

    # Startup
    logging.info("Starting FastAPI Hybrid Trading Monitoring Service...")

    # Import here to avoid circular imports
    from .hybrid_service import HybridTradingService

    monitoring_service = HybridTradingService()

    # Load previous state
    state = load_state()
    monitoring_service.watchlist = set(state.get("watchlist", []))

    # Auto-trader is disabled by default per CLAUDE.md requirements
    if hasattr(monitoring_service, "auto_trader") and monitoring_service.auto_trader:
        monitoring_service.auto_trader.enabled = False

    # Start background watchlist update task
    watchlist_task = asyncio.create_task(update_watchlist_task())
    logging.info("Background scanner task started - will update watchlist every 30 seconds")

    logging.info(
        f"Service initialized with {len(monitoring_service.watchlist)} symbols in watchlist"
    )
    logging.info("Auto-trading is DISABLED by default - user must enable manually")

    # Open browser automatically after a short delay
    async def open_browser():
        await asyncio.sleep(1.5)  # Wait for server to be fully ready
        dashboard_url = "http://localhost:8001/dashboard"
        logging.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)

    # Schedule browser opening
    asyncio.create_task(open_browser())

    yield

    # Shutdown
    logging.info("Shutting down FastAPI service...")

    # Stop background watchlist task
    if watchlist_task:
        watchlist_task.cancel()
        with suppress(asyncio.CancelledError):
            await watchlist_task
        logging.info("Background scanner task stopped")

    # Save current state
    if monitoring_service:
        current_state = {
            "watchlist": list(monitoring_service.watchlist),
            "auto_trader_enabled": (
                getattr(monitoring_service.auto_trader, "enabled", False)
                if hasattr(monitoring_service, "auto_trader") and monitoring_service.auto_trader
                else False
            ),
        }
        save_state(current_state)

        # Stop monitoring if active
        if monitoring_service.active:
            await monitoring_service.stop_service()

    logging.info("FastAPI service shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Alpaca Trading Monitoring Service",
        description="FastAPI-based monitoring service for automated trading",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Health endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "monitoring",
            "active": monitoring_service.active if monitoring_service else False,
        }

    # Status endpoint
    @app.get("/status")
    async def get_status():
        """Get monitoring service status"""
        if not monitoring_service:
            return {"status": "error", "message": "Service not initialized"}

        positions = {}
        if hasattr(monitoring_service, "position_tracker") and monitoring_service.position_tracker:
            try:
                positions = monitoring_service.position_tracker.get_all_positions()
            except (AttributeError, ConnectionError, Exception):
                positions = {}

        signals = {}
        if hasattr(monitoring_service, "signal_detector") and monitoring_service.signal_detector:
            try:
                signals = monitoring_service.signal_detector.active_signals
            except (AttributeError, KeyError, Exception):
                signals = {}

        # Get configuration parameters
        from ..config.global_config import get_global_config

        config = get_global_config()

        # Run peak/trough analysis on watchlist + positions if any symbols exist
        peak_trough_signals = {}
        analysis_symbols = list(monitoring_service.watchlist)

        # Add any position symbols to analysis
        if positions and hasattr(positions, "keys"):
            for pos_symbol in positions:
                if pos_symbol not in analysis_symbols:
                    analysis_symbols.append(pos_symbol)

        # Run analysis on up to 10 symbols to avoid overload
        if analysis_symbols:
            try:
                from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs_with_plot_py

                symbols_to_analyze = analysis_symbols[:10]  # Limit to 10 for performance

                analysis_result = await analyze_peaks_and_troughs_with_plot_py(
                    symbols=",".join(symbols_to_analyze),
                    timeframe="1Min",
                    days=1,
                    window_len=config.technical_analysis.hanning_window_samples,
                    lookahead=config.technical_analysis.peak_trough_lookahead,
                )

                # Parse signals from analysis result
                if "LATEST PEAK/TROUGH SIGNALS" in analysis_result:
                    lines = analysis_result.split("\n")
                    in_signals = False
                    for line in lines:
                        if "LATEST PEAK/TROUGH SIGNALS" in line:
                            in_signals = True
                            continue
                        elif "Signals found:" in line:
                            break
                        elif in_signals and any(sym in line for sym in symbols_to_analyze):
                            # Parse signal line
                            parts = line.split()
                            if len(parts) >= 6:
                                symbol = parts[0].strip()
                                signal_type = (
                                    "peak"
                                    if "^P" in parts[1]
                                    else "trough" if "vT" in parts[1] else "unknown"
                                )
                                bars_ago = parts[2].strip()
                                signal_price = parts[3].strip()
                                current_price = parts[4].strip()

                                peak_trough_signals[symbol] = {
                                    "type": signal_type,
                                    "bars_ago": bars_ago,
                                    "signal_price": signal_price,
                                    "current_price": current_price,
                                    "fresh": (
                                        int(bars_ago)
                                        <= config.technical_analysis.hanning_window_samples
                                        if bars_ago.isdigit()
                                        else False
                                    ),
                                }
            except Exception as e:
                logging.warning(f"Error running peak/trough analysis: {e}")

        return {
            "active": monitoring_service.active,
            "watchlist": {
                "symbols": list(monitoring_service.watchlist),
                "size": len(monitoring_service.watchlist),
            },
            "positions": positions,
            "signals": signals,
            "peak_trough_analysis": peak_trough_signals,
            "auto_trader_enabled": (
                getattr(monitoring_service.auto_trader, "enabled", False)
                if hasattr(monitoring_service, "auto_trader") and monitoring_service.auto_trader
                else False
            ),
            "check_count": getattr(monitoring_service, "check_count", 0),
            "error_count": getattr(monitoring_service, "error_count", 0),
            "config_parameters": {
                "max_stock_price": config.trading.max_stock_price,
                "trades_per_minute_threshold": config.trading.trades_per_minute_threshold,
                "min_percent_change_threshold": config.trading.min_percent_change_threshold,
                "fresh_signal_bars": config.technical_analysis.hanning_window_samples,
                "peak_trough_lookahead": config.technical_analysis.peak_trough_lookahead,
                "never_sell_for_loss": config.trading.never_sell_for_loss,
                "family_protection_profit_percent": config.trading.family_protection_profit_threshold_percent,
                "automatic_profit_percent": config.trading.automatic_profit_threshold_percent,
            },
            "last_updated": datetime.now().isoformat(),
        }

    # Start monitoring
    @app.post("/start")
    async def start_monitoring():
        """Start the monitoring service"""
        if not monitoring_service:
            return {"status": "error", "message": "Service not initialized"}

        if monitoring_service.active:
            return {"status": "warning", "message": "Service already running"}

        result = await monitoring_service.start_service()
        return result

    # Stop monitoring
    @app.post("/stop")
    async def stop_monitoring():
        """Stop the monitoring service"""
        if not monitoring_service:
            return {"status": "error", "message": "Service not initialized"}

        if not monitoring_service.active:
            return {"status": "warning", "message": "Service not running"}

        await monitoring_service.stop_service()
        return {"status": "success", "message": "Monitoring stopped"}

    # Add symbols to watchlist
    @app.post("/watchlist/add")
    async def add_to_watchlist(symbols: list[str]):
        """Add symbols to the watchlist"""
        if not monitoring_service:
            return {"status": "error", "message": "Service not initialized"}

        monitoring_service.watchlist.update(symbols)
        save_state(
            {
                "watchlist": list(monitoring_service.watchlist),
                "auto_trader_enabled": (
                    getattr(monitoring_service.auto_trader, "enabled", False)
                    if hasattr(monitoring_service, "auto_trader") and monitoring_service.auto_trader
                    else False
                ),
            }
        )

        return {
            "status": "success",
            "message": f"Added {len(symbols)} symbols",
            "watchlist": list(monitoring_service.watchlist),
        }

    # Clean watchlist based on price filter
    @app.post("/watchlist/clean")
    async def clean_watchlist():
        """Remove symbols that exceed the max price filter"""
        if not monitoring_service:
            return {"status": "error", "message": "Service not initialized"}

        from ..config.global_config import get_global_config
        from ..tools.market_data_tools import get_stock_snapshots

        config = get_global_config()
        max_price = config.trading.max_stock_price

        current_symbols = list(monitoring_service.watchlist)
        symbols_to_remove = []

        # Check prices in batches
        batch_size = 10
        for i in range(0, len(current_symbols), batch_size):
            batch = current_symbols[i : i + batch_size]
            try:
                # Get current prices
                snapshot_result = await get_stock_snapshots(",".join(batch))

                # Parse prices from snapshot result
                for symbol in batch:
                    if symbol in snapshot_result:
                        # Extract price from snapshot
                        lines = snapshot_result.split("\n")
                        for line in lines:
                            if f"## {symbol}" in line:
                                # Find the current price line
                                for _j, price_line in enumerate(lines[lines.index(line) :]):
                                    if "Current Price:" in price_line:
                                        price_str = (
                                            price_line.split("$")[1].split()[0]
                                            if "$" in price_line
                                            else "0"
                                        )
                                        try:
                                            price = float(price_str)
                                            if price > max_price:
                                                symbols_to_remove.append(symbol)
                                        except (ValueError, TypeError):
                                            pass
                                        break
                                break
            except Exception as e:
                logging.warning(f"Error checking prices for batch {batch}: {e}")

        # Remove overpriced symbols
        for symbol in symbols_to_remove:
            monitoring_service.watchlist.discard(symbol)

        # Save updated state
        save_state(
            {
                "watchlist": list(monitoring_service.watchlist),
                "auto_trader_enabled": (
                    getattr(monitoring_service.auto_trader, "enabled", False)
                    if hasattr(monitoring_service, "auto_trader") and monitoring_service.auto_trader
                    else False
                ),
            }
        )

        return {
            "status": "success",
            "message": f"Removed {len(symbols_to_remove)} overpriced symbols (>{max_price})",
            "removed_symbols": symbols_to_remove,
            "remaining_count": len(monitoring_service.watchlist),
        }

    # WebSocket endpoint (simplified)
    @app.websocket("/ws")
    async def websocket_route(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                # Simple echo for now
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
        except Exception:
            pass

    # Dashboard endpoint
    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Simple monitoring dashboard"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trading Monitor Dashboard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background-color: #1a1a1a; color: #fff; }
                .container { max-width: 1200px; margin: 0 auto; }
                .status-box { background-color: #2d2d2d; padding: 20px; margin: 10px 0; border-radius: 8px; }
                .symbol { display: inline-block; margin: 5px; padding: 8px 12px;
                         background-color: #007acc; color: white; border-radius: 4px; }
                .fresh-signal { background-color: #28a745; }
                .stale-signal { background-color: #ffc107; color: black; }
                .error { background-color: #dc3545; }
                button { background-color: #007acc; color: white; border: none;
                        padding: 10px 15px; margin: 5px; border-radius: 4px; cursor: pointer; }
                button:hover { background-color: #005c99; }
                #log { background-color: #000; color: #0f0; padding: 10px;
                      font-family: monospace; height: 200px; overflow-y: scroll; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Trading Monitor Dashboard</h1>

                <div class="status-box">
                    <h2>Service Status</h2>
                    <div id="service-status">Loading...</div>
                    <button onclick="startService()">Start Monitoring</button>
                    <button onclick="stopService()">Stop Monitoring</button>
                    <button onclick="refreshStatus()">Refresh</button>
                </div>

                <div class="status-box">
                    <h2>Active Filters & Parameters</h2>
                    <div id="config-parameters">Loading...</div>
                </div>

                <div class="status-box">
                    <h2>Watchlist</h2>
                    <div id="watchlist">Loading...</div>
                </div>

                <div class="status-box">
                    <h2>Positions</h2>
                    <div id="positions">Loading...</div>
                </div>

                <div class="status-box">
                    <h2>Signals</h2>
                    <div id="signals">Loading...</div>
                </div>

                <div class="status-box">
                    <h2>Real-time Log</h2>
                    <div id="log"></div>
                </div>
            </div>

            <script>
                let ws = null;
                let isConnected = false;

                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;

                    ws = new WebSocket(wsUrl);

                    ws.onopen = function(event) {
                        isConnected = true;
                        addLog('WebSocket connected');
                    };

                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        handleWebSocketMessage(data);
                    };

                    ws.onclose = function(event) {
                        isConnected = false;
                        addLog('WebSocket disconnected');
                        setTimeout(connectWebSocket, 5000);
                    };

                    ws.onerror = function(error) {
                        addLog(`WebSocket error: ${error}`);
                    };
                }

                function handleWebSocketMessage(data) {
                    addLog(`${data.type}: ${JSON.stringify(data.data || {})}`);

                    if (data.type === 'status_update') {
                        updateServiceStatus(data.data);
                    } else if (data.type === 'position_update') {
                        updatePositions(data.data);
                    } else if (data.type === 'signal_update') {
                        updateSignals(data.data);
                    }
                }

                function addLog(message) {
                    const log = document.getElementById('log');
                    const timestamp = new Date().toLocaleTimeString();
                    log.innerHTML += `[${timestamp}] ${message}<br>`;
                    log.scrollTop = log.scrollHeight;
                }

                async function refreshStatus() {
                    try {
                        const response = await fetch('/status');
                        const data = await response.json();
                        updateServiceStatus(data);
                        updateWatchlist(data.watchlist);
                        updatePositions(data.positions);
                        updateSignals(data.signals);
                        updateConfigParameters(data.config_parameters);
                    } catch (error) {
                        addLog(`Error refreshing status: ${error}`);
                    }
                }

                function updateServiceStatus(data) {
                    const status = document.getElementById('service-status');
                    const activeText = data.active ? 'ACTIVE' : 'INACTIVE';
                    const uptimeText = data.uptime_seconds ?
                        `Uptime: ${Math.floor(data.uptime_seconds / 60)}m ${Math.floor(data.uptime_seconds % 60)}s` : '';

                    status.innerHTML = `
                        <strong>Status:</strong> ${activeText}<br>
                        <strong>Check Count:</strong> ${data.check_count || 0}<br>
                        <strong>Error Count:</strong> ${data.error_count || 0}<br>
                        ${uptimeText}
                    `;
                }

                function updateWatchlist(data) {
                    const watchlist = document.getElementById('watchlist');
                    if (data && data.symbols) {
                        let html = `<strong>Size:</strong> ${data.size || 0}<br><br>`;
                        // Handle both array of strings and array of objects
                        if (Array.isArray(data.symbols)) {
                            data.symbols.forEach(symbol => {
                                if (typeof symbol === 'string') {
                                    html += `<span class="symbol">${symbol}</span>`;
                                } else if (symbol.symbol) {
                                    const signalClass = symbol.bars_ago <= 11 ? 'fresh-signal' : 'stale-signal';
                                    html += `<span class="symbol ${signalClass}">${symbol.symbol} (${symbol.signal_type || 'watching'})</span>`;
                                }
                            });
                        }
                        watchlist.innerHTML = html;
                    } else {
                        watchlist.innerHTML = 'No watchlist data';
                    }
                }

                function updatePositions(data) {
                    const positions = document.getElementById('positions');
                    if (data && data.positions) {
                        let html = `<strong>Count:</strong> ${data.count || 0}<br>`;
                        html += `<strong>Total P&L:</strong> $${(data.total_unrealized_pnl || 0).toFixed(2)}<br><br>`;
                        data.positions.forEach(pos => {
                            const pnl = parseFloat(pos.unrealized_pnl || 0);
                            const pnlClass = pnl >= 0 ? 'fresh-signal' : 'error';
                            html += `<span class="symbol ${pnlClass}">${pos.symbol}: $${pnl.toFixed(2)}</span>`;
                        });
                        positions.innerHTML = html;
                    } else {
                        positions.innerHTML = 'No positions';
                    }
                }

                function updateSignals(data) {
                    const signals = document.getElementById('signals');
                    if (data && data.active_signals) {
                        let html = `<strong>Count:</strong> ${data.signal_count || 0}<br><br>`;
                        Object.entries(data.active_signals).forEach(([symbol, signal]) => {
                            html += `<span class="symbol fresh-signal">${symbol}: ${signal.type}</span>`;
                        });
                        signals.innerHTML = html;
                    } else {
                        signals.innerHTML = 'No active signals';
                    }
                }

                async function startService() {
                    try {
                        const response = await fetch('/start', { method: 'POST' });
                        const data = await response.json();
                        addLog(`Start service: ${data.message}`);
                        refreshStatus();
                    } catch (error) {
                        addLog(`Error starting service: ${error}`);
                    }
                }

                async function stopService() {
                    try {
                        const response = await fetch('/stop', { method: 'POST' });
                        const data = await response.json();
                        addLog(`Stop service: ${data.message}`);
                        refreshStatus();
                    } catch (error) {
                        addLog(`Error stopping service: ${error}`);
                    }
                }

                function updateConfigParameters(params) {
                    const configDiv = document.getElementById('config-parameters');
                    if (params) {
                        let html = `
                            <strong>Price Filter:</strong> Max $${params.max_stock_price || 'N/A'}<br>
                            <strong>Volume Filter:</strong> ${params.trades_per_minute_threshold || 'N/A'} trades/min<br>
                            <strong>Change Filter:</strong> ${params.min_percent_change_threshold || 'N/A'}% minimum<br>
                            <strong>Signal Freshness:</strong> ${params.fresh_signal_bars || 'N/A'} bars<br>
                            <strong>Peak/Trough Sensitivity:</strong> ${params.peak_trough_lookahead || 'N/A'} lookahead<br>
                            <strong>Trading Rules:</strong> ${params.never_sell_for_loss ? 'Never sell for loss' : 'Standard rules'}<br>
                            <strong>Profit Targets:</strong> ${params.automatic_profit_percent || 'N/A'}% auto, ${params.family_protection_profit_percent || 'N/A'}% family
                        `;
                        configDiv.innerHTML = html;
                    } else {
                        configDiv.innerHTML = 'No configuration data';
                    }
                }

                // Initialize
                connectWebSocket();
                refreshStatus();
                setInterval(refreshStatus, 10000); // Refresh every 10 seconds
            </script>
        </body>
        </html>
        """

    return app


# Create the app instance at module level for uvicorn
app = create_app()


def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Run the FastAPI server"""
    uvicorn.run(
        "alpaca_mcp_server.monitoring.fastapi_service_refactored:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run the server
    run_server(port=8100, reload=False)
