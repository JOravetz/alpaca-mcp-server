from alpaca.trading.models import Position
"""FastAPI-based Hybrid Trading Service

Production-ready monitoring service with REST API, WebSocket streaming,
and persistent background monitoring for automated trading signals.
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from ..config import get_scanner_config, get_system_config, get_trading_config
from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs
from ..utils.timezone_utils import get_eastern_time_string
from .alert_system import AlertSystem
from .auto_trader import AutoTrader
from .desktop_notifications import DesktopNotificationService
from .hybrid_service import ServiceConfig, ServiceStatus
from .position_tracker import PositionTracker
from .signal_detector import SignalDetector
from .streaming_integration import AlpacaStreamingService
from .trade_confirmation import TradeConfirmationService

# Module-level logger for standalone functions
logger = logging.getLogger(__name__)


class AddSymbolsRequest(BaseModel):
    symbols: list[str] = Field(..., description="List of stock symbols to add")


class RemoveSymbolsRequest(BaseModel):
    symbols: list[str] = Field(..., description="List of stock symbols to remove")


class OrderCheckRequest(BaseModel):
    order_info: dict[str, Any] | None = Field(None, description="Order information for tracking")


class ScanSyncRequest(BaseModel):
    min_trades_per_minute: int = Field(
        500, description="Minimum trades per minute for active stocks"
    )
    min_percent_change: float = Field(5.0, description="Minimum percentage change")
    max_symbols: int = Field(20, description="Maximum symbols to monitor")
    force_update: bool = Field(False, description="Force update even if symbols are the same")


class TechnicalAnalysisUpdateRequest(BaseModel):
    hanning_window_samples: int | None = Field(
        None, ge=3, le=101, description="Hanning window size (odd numbers only)"
    )
    peak_trough_lookahead: int | None = Field(
        None, ge=1, le=50, description="Peak/trough detection sensitivity"
    )
    peak_trough_min_distance: int | None = Field(
        None, ge=1, le=20, description="Minimum distance between peaks"
    )


class TradingConfigUpdateRequest(BaseModel):
    trades_per_minute_threshold: int | None = Field(
        None, ge=1, le=10000, description="Minimum trades per minute"
    )
    min_percent_change_threshold: float | None = Field(
        None, ge=0.1, le=100.0, description="Minimum % change"
    )
    max_stock_price: float | None = Field(
        None, ge=0.01, le=1000.0, description="Maximum stock price"
    )
    family_protection_profit_threshold_percent: float | None = Field(
        None, ge=1.0, le=50.0, description="Family protection profit threshold %"
    )
    automatic_profit_threshold_percent: float | None = Field(
        None, ge=0.1, le=20.0, description="Automatic profit threshold %"
    )
    default_position_size_usd: int | None = Field(
        None, ge=1000, le=500000, description="Default position size in USD"
    )
    max_concurrent_positions: int | None = Field(
        None, ge=1, le=20, description="Maximum concurrent positions"
    )


class AutoScanConfigRequest(BaseModel):
    enabled: bool = Field(..., description="Enable/disable automatic scanning")
    interval_seconds: int = Field(60, description="Scan interval in seconds (minimum 30)")
    min_trades_per_minute: int = Field(500, description="Minimum trades per minute threshold")
    min_percent_change: float = Field(5.0, description="Minimum percentage change threshold")
    max_symbols: int = Field(20, description="Maximum symbols to monitor")


class TradeConfirmationRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    expected_price: float = Field(..., description="Expected execution price")


class ConfirmExecutionRequest(BaseModel):
    trade_id: str = Field(..., description="Trade confirmation ID")
    actual_price: float = Field(..., description="Actual execution price")
    fill_timestamp: str = Field(..., description="Execution timestamp")
    screenshot_path: str | None = Field(None, description="Path to screenshot proof")


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="buy or sell")
    quantity: int = Field(..., description="Number of shares")
    order_type: str = Field("limit", description="Order type")
    limit_price: float | None = Field(None, description="Limit price for limit orders")
    time_in_force: str = Field("day", description="Time in force")


def get_signal_color(signal_type: str, bars_ago: int) -> str:
    """Get color for signal based on type and staleness

    Returns:
        - Green (#0f0): Fresh trough signals (≤11 bars ago) - BUY
        - Red (#f44): Fresh peak signals (≤11 bars ago) - SELL
        - Orange (#ff8c00): Stale signals (>11 bars ago) - WARNING/OLD
    """
    # Check if signal is stale (older than 11 bars ago)
    if bars_ago > 11:
        return "#ff8c00"  # Orange for stale signals

    # Fresh signals: red for peaks (sell), green for troughs (buy)
    if "peak" in signal_type.lower():
        return "#f44"  # Red for fresh peak/sell signals
    else:
        return "#0f0"  # Green for fresh trough/buy signals


class MonitoringServiceAPI:
    """Core monitoring service with FastAPI integration"""

    def __init__(self):
        self.config = ServiceConfig()
        self.logger = self._setup_logging()

        # Service state
        self.active = False
        self.start_time: datetime | None = None
        self.last_check: datetime | None = None
        self.check_count = 0
        self.error_count = 0

        # Initialize core components immediately for API availability
        try:
            self.position_tracker = PositionTracker()
            self.signal_detector = SignalDetector()
            self.alert_system = AlertSystem(self.config.alert_channels)
            self.desktop_notifications = DesktopNotificationService()
            self.trade_confirmation = TradeConfirmationService(self.desktop_notifications)
            self.streaming_service = AlpacaStreamingService()
            self.auto_trader = AutoTrader()
            self.logger.info("All services initialized successfully")
        except Exception as e:
            self.logger.warning(f"Some services failed to initialize: {e}")
            # Initialize with minimal fallback services to ensure API responses work
            self.position_tracker = (
                PositionTracker()
                if not isinstance(self, Position)
                else self.position_tracker
            )
            self.signal_detector = (
                SignalDetector() if not isinstance(self, Position) else self.signal_detector
            )
            self.alert_system = (
                AlertSystem([]) if not isinstance(self, Position) else self.alert_system
            )
            self.desktop_notifications = (
                DesktopNotificationService()
                if not isinstance(self, Position)
                else self.desktop_notifications
            )
            self.trade_confirmation = (
                TradeConfirmationService(self.desktop_notifications)
                if not isinstance(self, Position)
                else self.trade_confirmation
            )
            self.streaming_service = (
                AlpacaStreamingService()
                if not isinstance(self, Position)
                else self.streaming_service
            )

        # Monitoring state
        self.watchlist: set[str] = set()
        self.current_signals: list[dict] = []
        self.signal_history: list[dict] = []
        self.monitoring_task: asyncio.Task | None = None

        # Auto-scanning configuration from global config
        scanner_config = get_scanner_config()
        trading_config = get_trading_config()
        self.auto_scan_enabled = True
        self.scan_interval_seconds = scanner_config.active_scan_interval_seconds
        self.scan_params = {
            "min_trades_per_minute": trading_config.trades_per_minute_threshold,  # 500 by default
            "min_percent_change": trading_config.min_percent_change_threshold,  # 10.0% by default
            "max_symbols": scanner_config.max_watchlist_size,  # 50 by default
        }

        # Auto-trading configuration
        self.auto_trading_enabled = False  # Disabled by default - requires explicit enable
        self.trading_config = trading_config
        self.position_size_usd = trading_config.default_position_size_usd
        self.max_positions = trading_config.max_concurrent_positions
        self.never_sell_for_loss = trading_config.never_sell_for_loss
        self.order_timeout = trading_config.order_timeout_seconds

        # Active trading state
        self.active_orders: dict[str, dict] = {}
        self.active_positions: dict[str, dict] = {}
        self.processed_signals: set[str] = set()
        self.last_scan_time: datetime | None = None

        # Wash sale tracking for recently sold positions
        self.recently_sold_symbols: dict[str, datetime] = {}
        self.wash_sale_cooldown_minutes = 30  # Don't re-add symbols sold within 30 minutes

        # Hibernation mode for resource optimization from global config
        system_config = get_system_config()
        self.hibernation_enabled = system_config.hibernation_enabled
        self.is_hibernating = False
        self.hibernation_reason: str | None = None

        # WebSocket connections for real-time updates
        self.websocket_connections: set[WebSocket] = set()

        # Communication files
        self.state_dir = Path("monitoring_data")
        self.state_dir.mkdir(exist_ok=True)

        self.logger.info("MonitoringServiceAPI initialized")

    def _setup_logging(self) -> logging.Logger:
        """Set up structured logging for audit trail"""
        logger = logging.getLogger("fastapi_monitoring_service")
        logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler for permanent audit trail
        log_path = Path("fastapi_monitoring.log")
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.INFO)

        # Console handler for real-time monitoring
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Structured formatter for audit compliance
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    async def startup(self):
        """Initialize service components on startup"""
        try:
            self.logger.info("🚀 Starting FastAPI Monitoring Service")

            # Initialize components
            self.position_tracker = PositionTracker()
            self.signal_detector = SignalDetector()
            self.alert_system = AlertSystem(self.config.alert_channels)
            self.streaming_service = AlpacaStreamingService()
            self.desktop_notifications = DesktopNotificationService()
            self.trade_confirmation = TradeConfirmationService(self.desktop_notifications)

            # Load previous state if exists
            await self._load_state()

            # Mark service as active
            self.active = True
            self.start_time = datetime.now(UTC)
            self.last_check = None
            self.check_count = 0
            self.error_count = 0

            # Check positions immediately on startup
            if self.position_tracker:
                await self.position_tracker.update_positions()
                initial_position_count = len(self.position_tracker.positions)
                self._last_position_count = initial_position_count

                if initial_position_count > 0:
                    position_symbols = list(self.position_tracker.positions.keys())
                    self.logger.warning(
                        f"🔔 STARTUP: Found {initial_position_count} existing positions: {position_symbols}"
                    )

                    # Alert about existing positions
                    await self.alert_system.send_alert(
                        "📊 Existing Positions Detected at Startup",
                        f"Found {initial_position_count} open positions: {', '.join(position_symbols)}",
                        priority="high",
                    )
                else:
                    self.logger.info("✅ STARTUP: No existing positions found")

            # Setup streaming callbacks and start
            if self.streaming_service:
                self.streaming_service.set_callbacks(
                    on_trade_update=self._handle_trade_update,
                    on_profit_spike=self._handle_profit_spike,
                )
                await self.streaming_service.start()
                if self.watchlist:
                    await self.streaming_service.subscribe_market_data(list(self.watchlist))

            # Start background monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

            # Send startup alert
            await self.alert_system.send_alert(
                "🚀 FastAPI Monitoring Service STARTED",
                f"Service running with {len(self.watchlist)} symbols in watchlist",
                priority="info",
            )

            # Save initial state
            await self._save_state()

            self.logger.info("✅ FastAPI Monitoring Service started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            self.active = False
            raise

    async def shutdown(self):
        """Clean shutdown of service components"""
        try:
            self.logger.info("🛑 Stopping FastAPI Monitoring Service")

            # Mark as inactive
            self.active = False

            # Cancel monitoring task
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self.monitoring_task

            # Close WebSocket connections
            for websocket in self.websocket_connections.copy():
                with suppress(Exception):
                    await websocket.close()
            self.websocket_connections.clear()

            # Clean shutdown of components
            if self.streaming_service:
                await self.streaming_service.stop()

            if self.position_tracker:
                await self.position_tracker.stop()

            # Save final state
            await self._save_state()

            # Send shutdown alert
            if self.alert_system:
                uptime = time.time() - self.start_time.timestamp() if self.start_time else 0
                await self.alert_system.send_alert(
                    "🛑 FastAPI Monitoring Service STOPPED",
                    f"Service stopped after {uptime:.0f} seconds uptime. "
                    f"Completed {self.check_count} monitoring cycles.",
                    priority="warning",
                )

            self.logger.info("✅ FastAPI Monitoring Service stopped gracefully")

        except Exception as e:
            self.logger.error(f"Error during service shutdown: {e}")

    async def get_health(self) -> dict:
        """Health check endpoint"""
        uptime = 0
        if self.start_time:
            uptime = time.time() - self.start_time.timestamp()  # type: ignore[assignment]

        return {
            "status": "healthy" if self.active else "inactive",
            "uptime_seconds": uptime,
            "check_count": self.check_count,
            "error_count": self.error_count,
            "watchlist_size": len(self.watchlist),
            "active_positions": (
                len(self.position_tracker.positions) if self.position_tracker else 0
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_status(self) -> ServiceStatus:
        """Get detailed service status"""
        uptime = 0
        if self.start_time:
            uptime = time.time() - self.start_time.timestamp()  # type: ignore[assignment]

        return ServiceStatus(
            active=self.active,
            start_time=self.start_time,
            last_check=self.last_check,
            watchlist_size=len(self.watchlist),
            active_positions=len(self.position_tracker.positions) if self.position_tracker else 0,
            signals_detected_today=len(
                [
                    s
                    for s in self.signal_history
                    if s.get("timestamp", "").startswith(get_eastern_time_string("%Y-%m-%d"))
                ]
            ),
            uptime_seconds=uptime,
            check_count=self.check_count,
            error_count=self.error_count,
        )

    async def get_watchlist(self) -> dict:
        """Get current watchlist with peak/trough analysis"""
        from ..config.global_config import get_technical_config
        from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs_with_plot_py

        watchlist_analysis = []
        tech_config = get_technical_config()

        # Get scanner results to match against
        try:
            from ..tools.day_trading_scanner import scan_day_trading_opportunities

            await scan_day_trading_opportunities()
            # Extract symbols from scanner result (would need to parse the formatted string)
            # For now, we'll implement without scanner rank
        except (ConnectionError, TimeoutError, Exception) as e:
            self.logger.debug(f"Error running day trading scanner: {e}")

        for symbol in sorted(self.watchlist):
            try:
                # Get peak/trough analysis for each symbol
                analysis_result = await analyze_peaks_and_troughs_with_plot_py(
                    symbols=symbol,
                    timeframe="1Min",
                    days=1,
                    window_len=tech_config.hanning_window_samples,
                    lookahead=tech_config.peak_trough_lookahead,
                )

                # Parse the analysis to extract key info
                symbol_data = self._extract_watchlist_analysis(symbol, analysis_result)
                watchlist_analysis.append(symbol_data)

            except Exception as e:
                self.logger.error(f"Error analyzing {symbol}: {e}")
                # Fallback data
                watchlist_analysis.append(
                    {
                        "symbol": symbol,
                        "latest_signal": "Error",
                        "signal_type": "unknown",
                        "bars_ago": 999,
                        "signal_price": 0.0,
                        "current_price": 0.0,
                        "analysis_status": "❌ Error",
                        "scanner_rank": "Not in scan",
                    }
                )

        # For now, use basic symbols if analysis failed
        if not watchlist_analysis:
            for symbol in sorted(self.watchlist):
                watchlist_analysis.append(
                    {
                        "symbol": symbol,
                        "latest_signal": "N/A",
                        "signal_type": "none",
                        "bars_ago": "N/A",
                        "signal_price": 0.0,
                        "current_price": 0.0,
                        "analysis_status": "No Analysis",
                        "scanner_rank": "N/A",
                    }
                )

        return {
            "watchlist": sorted(self.watchlist),
            "size": len(self.watchlist),
            "limit": self.config.watchlist_size_limit,
            "last_updated": self.last_check.isoformat() if self.last_check else None,
            "analysis": watchlist_analysis,
            "symbols": watchlist_analysis,  # Add this for status endpoint compatibility
        }

    def _extract_watchlist_analysis(self, symbol: str, analysis: str) -> dict:
        """Extract key analysis data for watchlist display from plot.py output"""
        try:
            import re

            # Default values
            latest_signal = "No Signal"
            signal_type = "none"
            bars_ago = 999
            signal_price = 0.0
            current_price = 0.0

            lines = analysis.split("\n")

            # Look for current price in various formats
            for line in lines:
                # Try different price formats from plot.py output
                if "Current price:" in line or "Latest price:" in line:
                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        current_price = float(price_match.group(1))
                        break
                # Also check for price in signal lines
                elif symbol in line and "CURRENT" in line.upper():
                    price_match = re.search(r"(\d+\.\d+)", line)
                    if price_match:
                        current_price = float(price_match.group(1))
                        break

            # If no current price found in analysis, try to get it from Alpaca API
            if current_price == 0.0:
                try:
                    import os

                    import requests

                    api_key = os.getenv("APCA_API_KEY_ID")
                    secret_key = os.getenv("APCA_API_SECRET_KEY")

                    if api_key and secret_key:
                        headers = {
                            "accept": "application/json",
                            "APCA-API-KEY-ID": api_key,
                            "APCA-API-SECRET-KEY": secret_key,
                        }

                        quote_url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
                        response = requests.get(quote_url, headers=headers, timeout=3)

                        if response.status_code == 200:
                            quote_data = response.json()
                            quote = quote_data.get("quote", {})
                            bid_price = float(quote.get("bp", 0))
                            ask_price = float(quote.get("ap", 0))
                            if bid_price and ask_price:
                                current_price = (bid_price + ask_price) / 2
                except Exception:
                    pass  # Keep current_price as 0.0

            # Look for signals in the LATEST PEAK/TROUGH SIGNALS table
            in_signals_section = False
            for line in lines:
                # Check if we're in the signals table section
                if "LATEST PEAK/TROUGH SIGNALS" in line:
                    in_signals_section = True
                    continue
                elif "Signals found:" in line and in_signals_section:
                    break  # End of signals section
                elif not in_signals_section:
                    continue

                # Skip header and separator lines
                if (
                    "Symbol" in line and "Signal" in line and "Ago" in line
                ) or line.strip().startswith("--"):
                    continue

                # Parse signal line format: "AAPL       ^P      4       201.1500       200.9837      -0.1663     -0.08%       24/06/2025 10:34"
                if symbol in line and ("^P" in line or "vT" in line):
                    parts = line.split()
                    if len(parts) >= 4:
                        signal_symbol = parts[0].strip()
                        if signal_symbol == symbol:
                            signal_indicator = parts[1].strip()  # ^P for peak, vT for trough
                            bars_ago = int(parts[2].strip())
                            signal_price = float(parts[3].strip())

                            # Set signal type and display
                            if signal_indicator == "^P":
                                latest_signal = "^P Peak"
                                signal_type = "peak"
                            elif signal_indicator == "vT":
                                latest_signal = "vT Trough"
                                signal_type = "trough"

                            # Update current price if we have it from the signal line
                            if len(parts) >= 5:
                                with suppress(Exception):
                                    current_price = float(parts[4].strip())
                            break

            # If no signals found in table, look for summary info
            if latest_signal == "No Signal":
                for line in lines:
                    if "Last signal:" in line:
                        if "PEAK" in line.upper():
                            latest_signal = "Peak"
                            signal_type = "peak"
                        elif "TROUGH" in line.upper():
                            latest_signal = "Trough"
                            signal_type = "trough"

                        # Extract price from summary line
                        price_match = re.search(r"\$(\d+\.?\d*)", line)
                        if price_match:
                            signal_price = float(price_match.group(1))
                        break

                # Look for bars ago in nearby lines
                for line in lines:
                    if "bars ago" in line and symbol.lower() in line.lower():
                        bars_match = re.search(r"(\d+)\s+bars?\s+ago", line)
                        if bars_match:
                            bars_ago = int(bars_match.group(1))
                            break

            # Determine status based on freshness
            from ..config.global_config import get_technical_config

            tech_config = get_technical_config()
            fresh_threshold = tech_config.hanning_window_samples

            if latest_signal == "No Signal" or signal_type == "none":
                status = "⚪ Monitoring"
            elif bars_ago <= fresh_threshold:
                if signal_type == "trough":
                    status = "✅ Fresh Buy"
                elif signal_type == "peak":
                    status = "✅ Fresh Sell"
                else:
                    status = "✅ Fresh"
            elif bars_ago <= fresh_threshold * 2:
                status = "⚠️ Stale"
            else:
                status = "❌ Very Stale"

            return {
                "symbol": symbol,
                "latest_signal": latest_signal,
                "signal_type": signal_type,
                "bars_ago": bars_ago,
                "signal_price": signal_price,
                "current_price": current_price,
                "analysis_status": status,
                "scanner_rank": "Not in scan",  # TODO: Add scanner integration
            }

        except Exception as e:
            self.logger.error(f"Error extracting watchlist analysis for {symbol}: {e}")
            return {
                "symbol": symbol,
                "latest_signal": "Error",
                "signal_type": "unknown",
                "bars_ago": 999,
                "signal_price": 0.0,
                "current_price": current_price if "current_price" in locals() else 0.0,
                "analysis_status": "❌ Error",
                "scanner_rank": "Not in scan",
            }

    async def add_symbols(self, symbols: list[str]) -> dict:
        """Add symbols to watchlist"""
        added = []
        errors = []

        # Get trading config for trades/minute threshold
        from ..config import get_trading_config

        trading_config = get_trading_config()
        min_trades_threshold = trading_config.trades_per_minute_threshold

        for symbol in symbols:
            symbol = symbol.upper().strip()
            if len(self.watchlist) >= self.config.watchlist_size_limit:
                errors.append(f"Watchlist limit reached ({self.config.watchlist_size_limit})")
                break
            if symbol not in self.watchlist:
                # Validate symbol meets trades/minute threshold before adding
                try:
                    # Get snapshot to check trades/minute
                    from ..tools.market_data_tools import get_stock_snapshots

                    snapshot_result = await get_stock_snapshots(symbol)

                    # Parse trades/minute from formatted string response
                    trades_per_minute = 0
                    if isinstance(snapshot_result, str):
                        # Look for "Trades: X trades/min" pattern in the string
                        import re

                        trades_match = re.search(r"Trades:\s*(\d+)\s*trades/min", snapshot_result)
                        if trades_match:
                            trades_per_minute = int(trades_match.group(1))
                        else:
                            # Market might be closed or no data
                            self.logger.warning(
                                f"Could not find trades/minute data for {symbol} in snapshot"
                            )
                    elif isinstance(snapshot_result, dict) and symbol in snapshot_result:
                        # Handle dictionary response (direct API call)
                        minute_bar = snapshot_result[symbol].get("minuteBar", {})
                        trades_per_minute = minute_bar.get("n", 0) if minute_bar else 0

                    # Validate against threshold
                    if trades_per_minute > 0 and trades_per_minute < min_trades_threshold:
                        errors.append(
                            f"{symbol}: {trades_per_minute} trades/min < {min_trades_threshold} required"
                        )
                        self.logger.warning(
                            f"Rejected {symbol}: only {trades_per_minute} trades/min, need {min_trades_threshold}"
                        )
                        continue
                    elif trades_per_minute == 0:
                        # No data available (market closed) - allow add but log warning
                        self.logger.warning(
                            f"No trades/minute data for {symbol} - allowing add (market may be closed)"
                        )

                except Exception as e:
                    self.logger.warning(f"Error validating {symbol}: {e} - allowing add")

                # Symbol passed validation or couldn't be validated (market closed)
                self.watchlist.add(symbol)
                added.append(symbol)

        if added:
            await self._save_state()
            self.logger.info(f"Added to watchlist: {added}")

            # Update streaming subscriptions for new symbols
            if self.streaming_service and self.streaming_service.is_running:
                try:
                    await self.streaming_service.subscribe_market_data(added)
                    self.logger.info(f"Added streaming subscriptions for: {added}")
                except Exception as e:
                    self.logger.error(f"Failed to subscribe to streaming for {added}: {e}")

            # Send WebSocket update
            await self._broadcast_update(
                {
                    "type": "watchlist_update",
                    "action": "added",
                    "symbols": added,
                    "watchlist_size": len(self.watchlist),
                }
            )

            if self.alert_system:
                await self.alert_system.send_alert(
                    "📊 Watchlist Updated",
                    f"Added symbols: {', '.join(added)}. Total watchlist: {len(self.watchlist)}",
                    priority="info",
                )

            # Check hibernation conditions after adding symbols
            if self.hibernation_enabled:
                try:
                    await self.check_hibernation_conditions()
                except Exception as e:
                    self.logger.error(f"❌ Hibernation check failed after adding symbols: {e}")

        return {
            "status": "success",
            "added": added,
            "errors": errors,
            "watchlist_size": len(self.watchlist),
            "current_watchlist": sorted(self.watchlist),
        }

    async def remove_symbols(self, symbols: list[str]) -> dict:
        """Remove symbols from watchlist"""
        removed = []

        for symbol in symbols:
            symbol = symbol.upper().strip()
            if symbol in self.watchlist:
                self.watchlist.remove(symbol)
                removed.append(symbol)

        if removed:
            await self._save_state()
            self.logger.info(f"Removed from watchlist: {removed}")

            # Update streaming subscriptions for removed symbols
            if self.streaming_service and self.streaming_service.is_running:
                try:
                    await self.streaming_service.unsubscribe_market_data(removed)
                    self.logger.info(f"Removed streaming subscriptions for: {removed}")
                except Exception as e:
                    self.logger.error(f"Failed to unsubscribe from streaming for {removed}: {e}")

            # Send WebSocket update
            await self._broadcast_update(
                {
                    "type": "watchlist_update",
                    "action": "removed",
                    "symbols": removed,
                    "watchlist_size": len(self.watchlist),
                }
            )

            if self.alert_system:
                await self.alert_system.send_alert(
                    "📊 Watchlist Updated",
                    f"Removed symbols: {', '.join(removed)}. Total watchlist: {len(self.watchlist)}",
                    priority="info",
                )

            # Check hibernation conditions after removing symbols
            if self.hibernation_enabled:
                try:
                    await self.check_hibernation_conditions()
                except Exception as e:
                    self.logger.error(f"❌ Hibernation check failed after removing symbols: {e}")

        return {
            "status": "success",
            "removed": removed,
            "watchlist_size": len(self.watchlist),
            "current_watchlist": sorted(self.watchlist),
        }

    async def _embedded_scanner(
        self, min_trades_per_minute: int, min_percent_change: float, max_symbols: int
    ) -> set[str]:
        """Embedded scanner - uses C analyzer for real active stocks from combined.lis"""
        import json
        import subprocess
        from datetime import datetime

        import requests

        # First try to use the C analyzer for active stocks
        try:
            # Run the C analyzer on combined.lis
            result = subprocess.run(
                ["./stock_analyzer_json", "combined.lis"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/home/jjoravet/alpaca-mcp-server-enhanced",
            )

            if result.returncode == 0:
                # Parse JSON output (ignore stderr messages)
                json_output = result.stdout
                if json_output:
                    data = json.loads(json_output)
                    active_stocks = set()

                    # Get max price from global config
                    from alpaca_mcp_server.config.global_config import get_trading_config

                    max_price = get_trading_config().max_stock_price

                    # Extract symbols that meet ALL criteria
                    for stock in data.get("stocks", []):
                        symbol = stock.get("symbol")
                        trades = stock.get("trades", 0)
                        percent_change = stock.get("percent_change", 0)
                        price = stock.get("price", 0)

                        # Debug log for all stocks from C analyzer (no hard-coding)
                        self.logger.debug(
                            f"🔍 C ANALYZER: {symbol} trades={trades}, change={percent_change:.2f}%, price=${price:.2f}, thresholds=(trades>={min_trades_per_minute}, change>={min_percent_change}%, price<=${max_price})"
                        )

                        # Apply ALL filters: trades/minute, % change, AND price
                        if (
                            trades >= min_trades_per_minute
                            and percent_change >= min_percent_change
                            and price <= max_price
                            and price > 0
                        ):
                            active_stocks.add(symbol)
                            self.logger.info(
                                f"✅ C ANALYZER FOUND: {symbol} with {trades} trades, {percent_change:.2f}% change, ${price:.2f} price"
                            )

                    if active_stocks:
                        self.logger.info(
                            f"🔍 C ANALYZER: Found {len(active_stocks)} active stocks: {active_stocks}"
                        )
                        return active_stocks
                    else:
                        self.logger.info(
                            "🔍 C ANALYZER: No stocks meet criteria, falling back to API scanner"
                        )

        except Exception as e:
            self.logger.warning(f"C analyzer failed: {e}, falling back to API scanner")

        # Fallback to original API scanner
        try:
            # Get API credentials
            api_key = os.environ.get("APCA_API_KEY_ID")
            secret_key = os.environ.get("APCA_API_SECRET_KEY")

            if not api_key or not secret_key:
                self.logger.error("API keys not set in environment variables")
                return set()

            # Set headers
            headers = {
                "accept": "application/json",
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key,
            }

            # Get tradable symbols (use direct API call instead of TickerList to avoid import issues)
            try:
                # Direct API call to get assets
                assets_url = "https://paper-api.alpaca.markets/v2/assets"
                assets_response = requests.get(assets_url, headers=headers, timeout=30)

                if assets_response.status_code != 200:
                    self.logger.error(f"Failed to fetch assets: {assets_response.status_code}")
                    return set()

                assets_data = assets_response.json()

                # Filter for tradable US equity stocks under max price
                symbol_list = []

                for asset in assets_data:
                    if (
                        asset.get("tradable", False)
                        and asset.get("status") == "active"
                        and asset.get("class") == "us_equity"
                        and len(asset.get("symbol", "")) <= 5
                        and not any(char in asset.get("symbol", "") for char in [".", "/", "-"])
                    ):
                        symbol_list.append(asset["symbol"])

                self.logger.info(f"Loaded {len(symbol_list)} tradable symbols")
            except Exception as e:
                self.logger.error(f"Error getting symbol list: {e}")
                return set()

            # Batch API calls (500 symbols per request)
            batch_size = 500
            all_snapshots = {}

            for i in range(0, len(symbol_list), batch_size):
                batch = symbol_list[i : i + batch_size]
                url = f"https://data.alpaca.markets/v2/stocks/snapshots?symbols={','.join(batch)}"

                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        batch_snapshots = response.json()
                        all_snapshots.update(batch_snapshots)
                    else:
                        self.logger.warning(
                            f"API error for batch {i//batch_size + 1}: {response.status_code}"
                        )
                except Exception as e:
                    self.logger.warning(f"Request error for batch {i//batch_size + 1}: {e}")
                    continue

            # Process snapshots to find active stocks
            results = []
            datetime.now(UTC)

            for symbol in symbol_list:
                try:
                    snapshot = all_snapshots.get(symbol)
                    if not snapshot:
                        continue

                    # Extract required data
                    latest_trade = snapshot.get("latestTrade")
                    minute_bar = snapshot.get("minuteBar")
                    daily_bar = snapshot.get("dailyBar")
                    prev_daily_bar = snapshot.get("prevDailyBar")

                    if not all([latest_trade, minute_bar, daily_bar]):
                        continue

                    # Get minute trades count
                    minute_trades = minute_bar.get("n")

                    # No hard-coded symbols - scanner uses combined.lis via C analyzer

                    if not minute_trades or minute_trades < min_trades_per_minute:
                        continue

                    # Get prices
                    price_now = float(latest_trade.get("p", 0))
                    if price_now <= 0:
                        continue

                    # Apply global price limit
                    from ..config import get_trading_config

                    max_price = get_trading_config().max_stock_price
                    if price_now > max_price:
                        continue

                    # Calculate percent change
                    if prev_daily_bar and prev_daily_bar.get("c"):
                        reference_price = float(prev_daily_bar["c"])
                    else:
                        reference_price = float(daily_bar.get("c", price_now))

                    if reference_price <= 0:
                        continue

                    percent = ((price_now - reference_price) / reference_price) * 100.0

                    # Filter: only UP stocks with minimum change
                    if percent <= 0 or abs(percent) < min_percent_change:
                        continue

                    # Get volume
                    minute_volume = minute_bar.get("v", 0)

                    results.append(
                        {
                            "symbol": symbol,
                            "trades_per_minute": minute_trades,
                            "percent_change": abs(percent),
                            "price": price_now,
                            "volume": minute_volume,
                            "percent": percent,
                        }
                    )

                except Exception:
                    continue  # Skip problematic symbols

            # Sort by trades per minute and limit results
            results.sort(key=lambda x: x["trades_per_minute"], reverse=True)
            results = results[:max_symbols]

            active_symbols = {r["symbol"] for r in results}
            self.logger.info(
                f"🔍 EMBEDDED SCANNER: Found {len(active_symbols)} active stocks: {active_symbols}"
            )

            return active_symbols

        except Exception as e:
            self.logger.error(f"Embedded scanner error: {e}")
            return set()

    async def _validate_watchlist_activity(self, symbols: list[str]) -> set[str]:
        """Validate individual symbols for current activity using same criteria as scanner"""
        import requests

        try:
            # Get trading config for thresholds
            trading_config = get_trading_config()
            min_trades_per_minute = trading_config.trades_per_minute_threshold
            min_percent_change = trading_config.min_percent_change_threshold
            max_price = trading_config.max_stock_price

            # Get API credentials
            api_key = os.environ.get("APCA_API_KEY_ID")
            secret_key = os.environ.get("APCA_API_SECRET_KEY")

            if not api_key or not secret_key:
                self.logger.error("API keys not set for watchlist validation")
                return set(symbols)  # Return all symbols if can't validate

            headers = {
                "accept": "application/json",
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key,
            }

            # Get snapshots for watchlist symbols
            if not symbols:
                return set()

            url = f"https://data.alpaca.markets/v2/stocks/snapshots?symbols={','.join(symbols)}"
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                self.logger.warning(
                    f"Failed to validate watchlist activity: {response.status_code}"
                )
                return set(symbols)  # Return all symbols if validation fails

            snapshots = response.json()
            active_symbols = set()

            for symbol in symbols:
                try:
                    snapshot = snapshots.get(symbol)
                    if not snapshot:
                        self.logger.warning(f"No snapshot data for {symbol} - marking as inactive")
                        continue

                    # Extract required data
                    latest_trade = snapshot.get("latestTrade")
                    minute_bar = snapshot.get("minuteBar")
                    daily_bar = snapshot.get("dailyBar")
                    prev_daily_bar = snapshot.get("prevDailyBar")

                    if not all([latest_trade, minute_bar, daily_bar]):
                        self.logger.warning(f"Incomplete data for {symbol} - marking as inactive")
                        continue

                    # Check minute trades count (primary activity indicator)
                    minute_trades = minute_bar.get("n", 0)

                    if minute_trades < min_trades_per_minute:
                        self.logger.warning(
                            f"❌ {symbol}: {minute_trades} trades/min < {min_trades_per_minute} required - INACTIVE"
                        )
                        continue

                    # Check price limits
                    price_now = float(latest_trade.get("p", 0))
                    if price_now <= 0 or price_now > max_price:
                        self.logger.warning(
                            f"❌ {symbol}: price ${price_now} outside limits - INACTIVE"
                        )
                        continue

                    # Check percent change (only up stocks)
                    if prev_daily_bar and prev_daily_bar.get("c"):
                        reference_price = float(prev_daily_bar["c"])
                    else:
                        reference_price = float(daily_bar.get("c", price_now))

                    if reference_price <= 0:
                        continue

                    percent = ((price_now - reference_price) / reference_price) * 100.0

                    if percent <= 0 or abs(percent) < min_percent_change:
                        self.logger.warning(
                            f"❌ {symbol}: {percent:.2f}% change < {min_percent_change}% required - INACTIVE"
                        )
                        continue

                    # Symbol passed all activity checks
                    active_symbols.add(symbol)
                    self.logger.info(
                        f"✅ {symbol}: {minute_trades} trades/min, {percent:.2f}% change - ACTIVE"
                    )

                except Exception as e:
                    self.logger.warning(f"Error validating {symbol}: {e} - marking as inactive")
                    continue

            self.logger.info(
                f"Watchlist validation: {len(active_symbols)}/{len(symbols)} symbols still active"
            )
            return active_symbols

        except Exception as e:
            self.logger.error(f"Error in watchlist validation: {e}")
            return set(symbols)  # Return all symbols if validation fails completely

    async def sync_with_scanner_results(self, scan_params: dict) -> dict:
        """Sync watchlist with active scanner results using embedded scanner"""
        try:
            # Use exact configuration from global config or provided parameters
            trading_config = get_trading_config()
            scanner_config = get_scanner_config()

            min_trades = scan_params.get(
                "min_trades_per_minute", trading_config.trades_per_minute_threshold
            )
            min_change = scan_params.get(
                "min_percent_change", trading_config.min_percent_change_threshold
            )
            max_symbols = scan_params.get("max_symbols", scanner_config.max_watchlist_size)

            self.logger.info(
                f"🔍 EMBEDDED SCAN: {min_trades} trades/min, {min_change}% change, max {max_symbols} symbols"
            )

            # Use embedded scanner instead of MCP tool
            active_symbols = await self._embedded_scanner(min_trades, min_change, max_symbols)

            # Get active positions to protect from removal
            protected_symbols = set()
            if self.position_tracker:
                await self.position_tracker.update_positions()
                protected_symbols = set(self.position_tracker.positions.keys())

            # Clean up old wash sale entries (older than cooldown period)
            now = datetime.now(UTC)
            cutoff_time = now - timedelta(minutes=self.wash_sale_cooldown_minutes)
            self.recently_sold_symbols = {
                symbol: sold_time
                for symbol, sold_time in self.recently_sold_symbols.items()
                if sold_time > cutoff_time
            }

            # Filter out recently sold symbols to prevent wash sales
            wash_sale_filtered = active_symbols - set(self.recently_sold_symbols.keys())
            if len(active_symbols) > len(wash_sale_filtered):
                filtered_out = active_symbols - wash_sale_filtered
                self.logger.info(
                    f"⚠️ Filtered out {len(filtered_out)} recently sold symbols to prevent wash sales: {filtered_out}"
                )

            # Compare with current watchlist
            current_watchlist = set(self.watchlist)
            to_add = wash_sale_filtered - current_watchlist

            # CRITICAL: Never remove symbols with active positions
            potential_removals = current_watchlist - wash_sale_filtered
            to_remove = potential_removals - protected_symbols
            protected_from_removal = potential_removals & protected_symbols

            # IMPROVED: When scanner returns no results, validate existing watchlist individually
            if len(active_symbols) == 0 and len(current_watchlist) > 0:
                self.logger.info(
                    "Scanner returned no active results - validating existing watchlist individually"
                )

                # Validate each symbol in current watchlist for activity
                validated_symbols = await self._validate_watchlist_activity(list(current_watchlist))
                inactive_symbols = current_watchlist - validated_symbols - protected_symbols

                if inactive_symbols:
                    # Remove inactive symbols even when scanner returns no new results
                    await self.remove_symbols(list(inactive_symbols))
                    self.logger.warning(
                        f"🔻 REMOVED INACTIVE SYMBOLS: {', '.join(sorted(inactive_symbols))}"
                    )

                    return {
                        "status": "cleanup_completed",
                        "message": f"Removed {len(inactive_symbols)} inactive symbols from watchlist",
                        "removed": sorted(inactive_symbols),
                        "remaining_watchlist": sorted(self.watchlist),
                        "watchlist_size": len(self.watchlist),
                    }
                else:
                    return {
                        "status": "no_active_stocks",
                        "message": "No new active stocks found, current watchlist validated and active",
                        "watchlist_size": len(self.watchlist),
                        "current_watchlist": sorted(self.watchlist),
                    }

            if protected_from_removal:
                self.logger.warning(
                    f"Protected symbols with active positions from removal: {protected_from_removal}"
                )
                # Keep protected symbols in active list for continued monitoring
                active_symbols.update(protected_from_removal)

            # Only proceed if there are changes or force_update is True
            if not to_add and not to_remove and not scan_params.get("force_update", False):
                message = "Watchlist already synced with active stocks"
                if protected_from_removal:
                    message += (
                        f". Protected {len(protected_from_removal)} position stocks from removal."
                    )

                return {
                    "status": "no_changes",
                    "message": message,
                    "protected": sorted(protected_from_removal) if protected_from_removal else [],
                    "active_symbols": sorted(active_symbols),
                    "watchlist_size": len(self.watchlist),
                }

            sync_results = []

            # Remove inactive symbols
            if to_remove:
                await self.remove_symbols(list(to_remove))
                sync_results.append(f"Removed {len(to_remove)} inactive symbols")

            # Add new active symbols
            if to_add:
                await self.add_symbols(list(to_add))
                sync_results.append(f"Added {len(to_add)} new active symbols")

            self.logger.info(f"Watchlist synced with scanner: +{len(to_add)}, -{len(to_remove)}")

            sync_message = f"Watchlist synced with active stocks. {'; '.join(sync_results)}"
            if protected_from_removal:
                sync_message += (
                    f" Protected {len(protected_from_removal)} position stocks from removal."
                )
            if self.recently_sold_symbols:
                sync_message += f" Wash sale protection active for {len(self.recently_sold_symbols)} recently sold symbols."

            return {
                "status": "success",
                "message": sync_message,
                "added": sorted(to_add),
                "removed": sorted(to_remove),
                "protected": sorted(protected_from_removal) if protected_from_removal else [],
                "wash_sale_filtered": (
                    sorted(self.recently_sold_symbols.keys()) if self.recently_sold_symbols else []
                ),
                "active_symbols": sorted(wash_sale_filtered),
                "watchlist_size": len(self.watchlist),
                "scan_parameters": {
                    "min_trades_per_minute": min_trades,
                    "min_percent_change": min_change,
                    "max_symbols": max_symbols,
                    "wash_sale_cooldown_minutes": self.wash_sale_cooldown_minutes,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to sync with scanner results: {e}")
            return {
                "status": "error",
                "message": f"Sync failed: {str(e)}",
                "watchlist_size": len(self.watchlist),
            }

    async def configure_auto_scan(self, config: dict) -> dict:
        """Configure automatic scanning parameters"""
        try:
            # Validate interval (minimum 30 seconds)
            interval = max(30, config.get("interval_seconds", 60))

            # Update configuration
            old_enabled = self.auto_scan_enabled
            self.auto_scan_enabled = config.get("enabled", True)
            self.scan_interval_seconds = interval
            self.scan_params = {
                "min_trades_per_minute": config.get("min_trades_per_minute", 500),
                "min_percent_change": config.get("min_percent_change", 5.0),
                "max_symbols": config.get("max_symbols", 20),
            }

            # Reset scan timer if enabled/disabled changed
            if old_enabled != self.auto_scan_enabled:
                self.last_scan_time = None

            await self._save_state()

            status_msg = "enabled" if self.auto_scan_enabled else "disabled"
            self.logger.info(
                f"📊 Auto-scanning {status_msg}: {interval}s interval, {self.scan_params}"
            )

            return {
                "status": "success",
                "message": f"Auto-scanning {status_msg}",
                "config": {
                    "enabled": self.auto_scan_enabled,
                    "interval_seconds": self.scan_interval_seconds,
                    **self.scan_params,
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to configure auto-scan: {e}")
            return {"status": "error", "message": f"Configuration failed: {str(e)}"}

    async def get_auto_scan_status(self) -> dict:
        """Get current auto-scanning configuration and status"""
        next_scan = None
        if self.auto_scan_enabled and self.last_scan_time:
            next_scan_time = self.last_scan_time.timestamp() + self.scan_interval_seconds
            next_scan = datetime.fromtimestamp(next_scan_time, UTC).isoformat()

        # Clean up old wash sale entries for status display
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(minutes=self.wash_sale_cooldown_minutes)
        active_wash_sales = {
            symbol: sold_time
            for symbol, sold_time in self.recently_sold_symbols.items()
            if sold_time > cutoff_time
        }

        return {
            "enabled": self.auto_scan_enabled,
            "interval_seconds": self.scan_interval_seconds,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "next_scan": next_scan,
            "scan_parameters": self.scan_params,
            "wash_sale_tracking": {
                "cooldown_minutes": self.wash_sale_cooldown_minutes,
                "recently_sold_count": len(active_wash_sales),
                "recently_sold_symbols": sorted(active_wash_sales.keys()),
            },
        }

    async def check_hibernation_conditions(self) -> bool:
        """Check if system should enter hibernation mode"""
        if not self.hibernation_enabled:
            return False

        # Get current positions
        position_count = 0
        if self.position_tracker:
            await self.position_tracker.update_positions()
            position_count = len(self.position_tracker.positions)

        # Check conditions for hibernation
        no_watchlist = len(self.watchlist) == 0
        no_positions = position_count == 0

        should_hibernate = no_watchlist and no_positions

        if should_hibernate and not self.is_hibernating:
            await self._enter_hibernation()
        elif not should_hibernate and self.is_hibernating:
            await self._exit_hibernation()

        return self.is_hibernating

    async def _enter_hibernation(self):
        """Enter hibernation mode - stop streaming to save resources"""
        if self.is_hibernating:
            return

        self.logger.info("💤 Entering hibernation mode: No active stocks or positions to monitor")

        # Stop streaming service
        if self.streaming_service and self.streaming_service.is_running:
            try:
                await self.streaming_service.stop()
                self.logger.info("🛑 Streaming service stopped for hibernation")
            except Exception as e:
                self.logger.error(f"Error stopping streaming for hibernation: {e}")

        self.is_hibernating = True
        self.hibernation_reason = f"No watchlist ({len(self.watchlist)}) and no positions"

        # Broadcast hibernation status
        await self._broadcast_update(
            {
                "type": "hibernation_started",
                "reason": self.hibernation_reason,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def _exit_hibernation(self):
        """Exit hibernation mode - restart streaming"""
        if not self.is_hibernating:
            return

        self.logger.info("🔥 Exiting hibernation mode: Active stocks or positions detected")

        # Restart streaming service if there are symbols to monitor
        if len(self.watchlist) > 0 and self.streaming_service:
            try:
                await self.streaming_service.start()
                await self.streaming_service.subscribe_market_data(list(self.watchlist))
                self.logger.info(
                    f"🚀 Streaming service restarted for {len(self.watchlist)} symbols"
                )
            except Exception as e:
                self.logger.error(f"Error restarting streaming after hibernation: {e}")

        self.is_hibernating = False
        old_reason = self.hibernation_reason
        self.hibernation_reason = None

        # Broadcast wake status
        await self._broadcast_update(
            {
                "type": "hibernation_ended",
                "previous_reason": old_reason,
                "watchlist_size": len(self.watchlist),
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    async def get_hibernation_status(self) -> dict:
        """Get current hibernation status with fresh data"""
        # Get fresh position count
        position_count = 0
        if self.position_tracker:
            await self.position_tracker.update_positions()
            position_count = len(self.position_tracker.positions)

        return {
            "hibernation_enabled": self.hibernation_enabled,
            "is_hibernating": self.is_hibernating,
            "hibernation_reason": self.hibernation_reason,
            "watchlist_size": len(self.watchlist),
            "active_positions": position_count,
            "streaming_active": (
                self.streaming_service.is_running if self.streaming_service else False
            ),
        }

    async def get_positions(self) -> dict:
        """Get current positions"""
        if not self.position_tracker:
            return {"positions": [], "count": 0}

        await self.position_tracker.update_positions()
        positions = []

        for symbol, position in self.position_tracker.positions.items():
            positions.append(
                {
                    "symbol": symbol,
                    "quantity": float(position.qty),  # type: ignore[attr-defined]
                    "market_value": float(position.market_value),
                    "unrealized_pl": float(position.unrealized_pl),  # type: ignore[attr-defined]
                    "unrealized_plpc": float(position.unrealized_plpc),  # type: ignore[attr-defined]
                    "avg_entry_price": float(position.avg_entry_price),  # type: ignore[attr-defined]
                    "current_price": (
                        float(position.current_price) if position.current_price else None
                    ),
                }
            )

        return {
            "positions": positions,
            "count": len(positions),
            "total_market_value": sum(
                float(p.market_value) for p in self.position_tracker.positions.values()
            ),
            "total_unrealized_pl": sum(
                float(p.unrealized_pl) for p in self.position_tracker.positions.values()  # type: ignore[attr-defined,misc]
            ),
        }

    async def get_signals(self) -> dict:
        """Get FRESH trading signals directly from peak/trough analysis using plot.py"""
        from ..config import get_trading_config
        from ..config.global_config import get_technical_config
        from ..tools.market_data_tools import get_stock_snapshots
        from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs_with_plot_py

        tech_config = get_technical_config()
        trading_config = get_trading_config()
        min_trades_threshold = trading_config.trades_per_minute_threshold
        fresh_signals = []

        try:
            # Process only first 3 symbols to avoid timeouts
            watchlist_subset = (
                list(self.watchlist)[:3] if len(self.watchlist) > 3 else list(self.watchlist)
            )

            # Validate symbols meet trades/minute threshold before analysis
            valid_symbols = []
            for symbol in watchlist_subset:
                try:
                    # Get snapshot to check trades/minute
                    snapshot_result = await asyncio.to_thread(get_stock_snapshots, symbol)

                    # Parse trades/minute from response
                    trades_per_minute = 0
                    if isinstance(snapshot_result, str):
                        # Look for "Trades: X trades/min" pattern in the string
                        import re

                        trades_match = re.search(r"Trades:\s*(\d+)\s*trades/min", snapshot_result)
                        if trades_match:
                            trades_per_minute = int(trades_match.group(1))
                    elif isinstance(snapshot_result, dict) and symbol in snapshot_result:
                        minute_bar = snapshot_result[symbol].get("minuteBar", {})
                        trades_per_minute = minute_bar.get("n", 0) if minute_bar else 0

                    # Validate against threshold
                    if trades_per_minute > 0 and trades_per_minute >= min_trades_threshold:
                        valid_symbols.append(symbol)
                    elif trades_per_minute > 0:
                        self.logger.debug(
                            f"Skipping {symbol} for signals: {trades_per_minute} trades/min < {min_trades_threshold}"
                        )
                    else:
                        # No data (market closed), include symbol anyway
                        valid_symbols.append(symbol)
                except Exception as e:
                    self.logger.debug(f"Could not validate {symbol}: {e}")
                    # Include symbol if validation fails (market closed)
                    valid_symbols.append(symbol)

            # Generate fresh signals for each validated symbol
            for symbol in valid_symbols:
                try:
                    # Call peak/trough tool directly for fresh analysis using plot.py
                    analysis_result = await analyze_peaks_and_troughs_with_plot_py(
                        symbols=symbol,
                        timeframe="1Min",
                        days=1,
                        window_len=tech_config.hanning_window_samples,  # Use global config (11)
                        lookahead=tech_config.peak_trough_lookahead,  # Use global config (1)
                    )

                    # Parse for fresh signals
                    symbol_signals = self._parse_fresh_analysis(symbol, analysis_result)
                    fresh_signals.extend(symbol_signals)

                except Exception as e:
                    self.logger.error(f"Error getting fresh signals for {symbol}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error generating fresh signals: {e}")

        return {
            "current_signals": fresh_signals,
            "signal_count": len(fresh_signals),
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _parse_fresh_analysis(self, symbol: str, analysis: str) -> list[dict]:
        """Parse fresh peak/trough analysis for trading signals from plot.py output"""
        signals = []

        try:
            # Look for the "LATEST PEAK/TROUGH SIGNALS" section in plot.py output
            lines = analysis.split("\n")

            in_signals_section = False

            for line in lines:
                # Check if we're in the signals table section
                if "LATEST PEAK/TROUGH SIGNALS" in line:
                    in_signals_section = True
                    continue
                elif "Signals found:" in line and in_signals_section:
                    break  # End of signals section
                elif not in_signals_section:
                    continue

                # Skip header and separator lines
                if (
                    "Symbol" in line and "Signal" in line and "Ago" in line
                ) or line.strip().startswith("--"):
                    continue

                # Parse signal line format: "RUN       ^P      3         6.8650         6.8550      -0.0100     -0.15%       24/06/2025 10:40"
                if symbol in line and ("^P" in line or "vT" in line):
                    signal = self._extract_signal_from_plot_line(symbol, line)
                    if signal:
                        signals.append(signal)

        except Exception as e:
            self.logger.error(f"Error parsing plot.py analysis for {symbol}: {e}")

        return signals

    def _extract_signal_from_plot_line(self, symbol: str, line: str) -> dict | None:
        """Extract signal from plot.py output line format"""
        try:
            import pytz

            # Parse line format: "RUN       ^P      3         6.8650         6.8550      -0.0100     -0.15%       24/06/2025 10:40"
            parts = line.split()
            if len(parts) < 8:
                return None

            signal_symbol = parts[0].strip()
            if signal_symbol != symbol:
                return None

            signal_indicator = parts[1].strip()  # ^P for peak, vT for trough
            bars_ago = int(parts[2].strip())
            signal_price = float(parts[3].strip())
            current_price = float(parts[4].strip())

            # Determine signal type
            if signal_indicator == "^P":
                signal_type = "fresh_peak"
                action = "sell_candidate"
            elif signal_indicator == "vT":
                signal_type = "fresh_trough"
                action = "buy_candidate"
            else:
                return None

            # Check if signal is fresh enough
            from ..config.global_config import get_global_config

            config = get_global_config()
            fresh_threshold = config.technical_analysis.hanning_window_samples

            if bars_ago > fresh_threshold:
                self.logger.debug(
                    f"Rejecting {symbol} {signal_type}: {bars_ago} bars ago > {fresh_threshold}"
                )
                return None

            # Convert to NYC/EDT timezone
            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": signal_type,
                "price": signal_price,
                "current_price": current_price,
                "bars_ago": bars_ago,
                "action": action,
                "detected_at": nyc_time.isoformat(),
                "source": "plot_py_analysis",
                "timestamp": nyc_time.isoformat(),
                "id": f"{symbol}_{int(nyc_time.timestamp())}",
            }

            self.logger.info(
                f"✅ FRESH SIGNAL: {symbol} {signal_type} at ${signal_price} ({bars_ago} bars ago)"
            )
            return signal

        except Exception as e:
            self.logger.error(f"Error extracting signal from plot line for {symbol}: {e}")
            return None

    def _extract_signal_from_line(self, symbol: str, line: str, signal_type: str) -> dict | None:
        """Extract signal from latest peak/trough line"""
        try:
            import re

            import pytz

            # Parse line like: "Latest trough: Sample 369, $11.3816 (14 bars ago)"
            # Extract price
            price_match = re.search(r"\$(\d+\.?\d*)", line)
            price = float(price_match.group(1)) if price_match else None

            # Extract bars ago
            bars_match = re.search(r"\((\d+)\s+bars?\s+ago\)", line)
            bars_ago = int(bars_match.group(1)) if bars_match else 999

            # Only accept fresh signals (≤hanning_window_samples bars ago)
            from ..config.global_config import get_global_config

            config = get_global_config()
            fresh_threshold = config.technical_analysis.hanning_window_samples

            if bars_ago > fresh_threshold:
                self.logger.debug(
                    f"Rejecting {symbol} {signal_type}: {bars_ago} bars ago > {fresh_threshold}"
                )
                return None

            if not price:
                return None

            action = "buy_candidate" if signal_type == "fresh_trough" else "sell_candidate"

            # Convert to NYC/EDT timezone
            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": signal_type,
                "price": price,
                "bars_ago": bars_ago,
                "action": action,
                "detected_at": nyc_time.isoformat(),
                "source": "fresh_peak_trough_analysis",
                "timestamp": nyc_time.isoformat(),
                "id": f"{symbol}_{int(nyc_time.timestamp())}",
            }

            self.logger.info(
                f"✅ FRESH SIGNAL: {symbol} {signal_type} at ${price} ({bars_ago} bars ago)"
            )
            return signal

        except Exception as e:
            self.logger.error(f"Error extracting signal from line for {symbol}: {e}")
            return None

    # ========== AUTOMATED TRADING METHODS ==========

    async def enable_auto_trading(self) -> dict:
        """Enable automated trading with BULLETPROOF ONE-BUY-THEN-SELL-FOR-PROFIT logic"""
        if self.auto_trading_enabled:
            return {"status": "already_enabled", "message": "Auto trading already active"}

        # CRITICAL: Clear any existing state to start fresh
        self.active_orders.clear()
        self.active_positions.clear()
        self.processed_signals.clear()

        # Enable the AutoTrader which has comprehensive state management
        if isinstance(self, Position) and self.auto_trader:
            auto_trader_result = await self.auto_trader.enable_trading()
            self.auto_trading_enabled = True

            # Start aggressive position monitoring for profit-taking
            asyncio.create_task(self._aggressive_profit_monitoring())

            self.logger.warning(
                "🚀 BULLETPROOF AUTO-TRADING ENABLED - ONE BUY → MUST SELL FOR PROFIT"
            )

            return {
                "status": "enabled",
                "message": "BULLETPROOF auto-trading: ONE BUY then MUST SELL FOR PROFIT",
                "auto_trader_status": auto_trader_result.get("status"),
                "config": auto_trader_result.get("config", {}),
                "rules": [
                    "✅ Only ONE buy per symbol",
                    "✅ MUST sell for profit before buying again",
                    "✅ Aggressive profit monitoring every 0.5 seconds",
                    "✅ Family protection at 10%+ profit",
                    "✅ Quick profit at 3%+ gain",
                ],
            }
        else:
            # Fallback if AutoTrader not available
            await self._sync_positions_with_alpaca()
            self.auto_trading_enabled = True
            self.logger.warning("🚀 BASIC AUTO-TRADING ENABLED - AutoTrader not available")

            return {
                "status": "enabled",
                "message": "Basic auto-trading activated",
                "config": {
                    "position_size_usd": self.position_size_usd,
                    "max_positions": self.max_positions,
                    "never_sell_for_loss": self.never_sell_for_loss,
                    "order_timeout": self.order_timeout,
                },
            }

    async def disable_auto_trading(self) -> dict:
        """Disable automated trading"""
        if not self.auto_trading_enabled:
            return {"status": "already_disabled", "message": "Auto trading already inactive"}

        # Disable AutoTrader if available
        if isinstance(self, Position) and self.auto_trader:
            auto_trader_result = await self.auto_trader.disable_trading()
            self.auto_trading_enabled = False
            self.logger.warning("🛑 AUTOMATED TRADING DISABLED - AutoTrader deactivated")

            return {
                "status": "disabled",
                "message": "Automated trading deactivated with state preserved",
                "auto_trader_status": auto_trader_result.get("status"),
                "stats": auto_trader_result.get("stats", {}),
            }
        else:
            # Fallback disable
            self.auto_trading_enabled = False
            self.logger.warning("🛑 AUTOMATED TRADING DISABLED")

            return {
                "status": "disabled",
                "message": "Automated trading deactivated",
                "active_orders": len(self.active_orders),
                "active_positions": len(self.active_positions),
            }

    async def process_fresh_signal_for_trading(self, signal: dict) -> dict:
        """Process fresh signal with BULLETPROOF state management - ONE BUY THEN MUST SELL FOR PROFIT"""
        if not self.auto_trading_enabled:
            return {"status": "disabled", "message": "Auto trading not enabled"}

        symbol = signal.get("symbol")
        if not symbol:
            return {"status": "error", "message": "No symbol in signal"}

        # BULLETPROOF CHECK 1: Only process fresh trough signals for buying
        if signal.get("signal_type") != "fresh_trough":
            return {"status": "ignored", "message": "Only fresh trough signals trigger buys"}

        # BULLETPROOF CHECK 2: Check if we already have ANY position in this symbol
        try:
            from ..tools.account_tools import get_positions

            positions_result = await get_positions()

            # Parse positions to check if symbol exists
            if (
                positions_result
                and isinstance(positions_result, str)
                and f"Symbol: {symbol}" in positions_result
            ):
                # Extract quantity to verify it's not zero
                lines = positions_result.split("\n")
                for i, line in enumerate(lines):
                    if f"Symbol: {symbol}" in line:
                        # Look for quantity in the next few lines
                        for j in range(i + 1, min(i + 10, len(lines))):
                            if "Quantity:" in lines[j]:
                                qty_str = lines[j].split("Quantity:")[1].strip()
                                qty = (
                                    float(qty_str)
                                    if qty_str.replace(".", "").replace("-", "").isdigit()
                                    else 0
                                )
                                if abs(qty) > 0:
                                    self.logger.warning(
                                        f"🚫 POSITION EXISTS: {symbol} has {qty} shares - CANNOT BUY AGAIN"
                                    )
                                    return {
                                        "status": "position_exists",
                                        "message": f"Already have position in {symbol}: {qty} shares",
                                    }
                                break
        except Exception as e:
            self.logger.error(f"Error checking positions for {symbol}: {e}")
            return {"status": "error", "message": f"Could not verify positions: {e}"}

        # BULLETPROOF CHECK 3: Check active orders to prevent duplicate orders
        try:
            from ..tools.order_tools import get_orders

            orders_result = await get_orders(status="open", limit=50)

            if orders_result and symbol in orders_result:
                self.logger.warning(f"🚫 OPEN ORDER EXISTS: {symbol} already has pending order")
                return {
                    "status": "order_exists",
                    "message": f"Already have open order for {symbol}",
                }
        except Exception as e:
            self.logger.error(f"Error checking orders for {symbol}: {e}")

        # BULLETPROOF CHECK 4: Use AutoTrader for comprehensive state management if available
        if isinstance(self, Position) and self.auto_trader:
            try:
                # Let AutoTrader handle the execution with its profit-first logic
                result = await self.auto_trader.process_fresh_signal(signal)

                # Log the result
                if result.get("status") == "success":
                    self.logger.warning(
                        f"🚀 AutoTrader executed buy for {symbol}: {result.get('message')}"
                    )
                elif result.get("status") in ["profit_required", "position_exists"]:
                    self.logger.warning(
                        f"🛡️ AutoTrader blocked buy for {symbol}: {result.get('message')}"
                    )
                else:
                    self.logger.info(f"🔄 AutoTrader: {symbol} - {result.get('message')}")

                return result
            except Exception as e:
                self.logger.error(f"AutoTrader error for {symbol}: {e}")
                return {"status": "error", "message": f"AutoTrader failed: {e}"}
        else:
            return {
                "status": "error",
                "message": "AutoTrader not available - comprehensive state management required",
            }

    async def _aggressive_profit_monitoring(self):
        """AGGRESSIVE position monitoring - sell for profit VERY QUICKLY"""
        self.logger.warning("🎯 AGGRESSIVE PROFIT MONITORING STARTED - 0.5 second intervals")

        while self.auto_trading_enabled:
            try:
                # Check all positions every 0.5 seconds for IMMEDIATE profit opportunities
                from ..tools.account_tools import get_positions

                positions_result = await get_positions()

                if positions_result and "Symbol:" in positions_result:
                    lines = positions_result.split("\n")
                    current_symbol = None
                    position_data = {}

                    for line in lines:
                        line = line.strip()
                        if line.startswith("Symbol:"):
                            # Process previous symbol if we have one
                            if current_symbol and position_data:
                                await self._check_aggressive_sell(current_symbol, position_data)

                            # Start new symbol
                            current_symbol = line.split("Symbol:")[1].strip()
                            position_data = {"symbol": current_symbol}
                        elif current_symbol and ":" in line:
                            key, value = line.split(":", 1)
                            position_data[key.strip().lower().replace(" ", "_")] = value.strip()

                    # Process last symbol
                    if current_symbol and position_data:
                        await self._check_aggressive_sell(current_symbol, position_data)

                # Monitor every 0.5 seconds for LIGHTNING FAST profit taking
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error in aggressive profit monitoring: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _check_aggressive_sell(self, symbol: str, position_data: dict) -> None:
        """Check if we should AGGRESSIVELY sell position for profit"""
        try:
            # Extract position details
            quantity_str = position_data.get("quantity", "0")
            unrealized_pnl_str = position_data.get("unrealized_p&l", "0")
            unrealized_pnl_percent_str = position_data.get("unrealized_p&l_%", "0")

            # Parse values
            quantity = (
                float(quantity_str.replace(",", ""))
                if quantity_str.replace(",", "").replace("-", "").replace(".", "").isdigit()
                else 0
            )
            unrealized_pnl = (
                float(unrealized_pnl_str.replace("$", "").replace(",", ""))
                if unrealized_pnl_str.replace("$", "")
                .replace(",", "")
                .replace("-", "")
                .replace(".", "")
                .isdigit()
                else 0
            )
            unrealized_pnl_percent = (
                float(unrealized_pnl_percent_str.replace("%", ""))
                if unrealized_pnl_percent_str.replace("%", "")
                .replace("-", "")
                .replace(".", "")
                .isdigit()
                else 0
            )

            # Skip if no meaningful position
            if abs(quantity) < 1:
                return

            # AGGRESSIVE PROFIT TAKING RULES
            should_sell = False
            sell_reason = ""

            # Rule 1: Family Protection - 10%+ profit = IMMEDIATE SELL
            if unrealized_pnl_percent >= 10.0:
                should_sell = True
                sell_reason = f"FAMILY PROTECTION - {unrealized_pnl_percent:.1f}% profit (${unrealized_pnl:.0f})"

            # Rule 2: Quick Profit - 3%+ gain = AUTO SELL
            elif unrealized_pnl_percent >= 3.0:
                should_sell = True
                sell_reason = (
                    f"QUICK PROFIT - {unrealized_pnl_percent:.1f}% gain (${unrealized_pnl:.0f})"
                )

            # Rule 3: Any profit above $100 = SELL (for small quick profits)
            elif unrealized_pnl >= 100.0:
                should_sell = True
                sell_reason = (
                    f"PROFIT TARGET - ${unrealized_pnl:.0f} profit ({unrealized_pnl_percent:.1f}%)"
                )

            if should_sell:
                await self._execute_aggressive_sell(symbol, int(abs(quantity)), sell_reason)

        except Exception as e:
            self.logger.error(f"Error checking aggressive sell for {symbol}: {e}")

    async def _execute_aggressive_sell(self, symbol: str, quantity: int, reason: str) -> None:
        """Execute LIGHTNING FAST sell order for profit"""
        try:
            from ..tools.market_data_tools import get_stock_quote
            from ..tools.order_tools import place_stock_order

            # Get current bid price for aggressive selling
            quote_result = await get_stock_quote(symbol)
            lines = quote_result.split("\n")
            current_bid = None

            for line in lines:
                if "Bid Price:" in line:
                    price_str = line.split("Bid Price:")[1].strip().replace("$", "")
                    current_bid = float(price_str) if price_str.replace(".", "").isdigit() else None
                    break

            if not current_bid:
                self.logger.error(f"Could not get bid price for {symbol}")
                return

            # Use bid price for instant fill (aggressive selling)
            limit_price = current_bid

            # Execute IMMEDIATE sell order
            await place_stock_order(
                symbol=symbol,
                side="sell",
                quantity=quantity,
                order_type="limit",
                limit_price=limit_price,
                time_in_force="day",
                extended_hours=True,
            )

            self.logger.warning(
                f"💰 AGGRESSIVE SELL EXECUTED: {symbol} x{quantity} @ ${limit_price} - {reason}"
            )

            # If using AutoTrader, update its profit-required tracking
            if (
                isinstance(self, Position)
                and self.auto_trader
                and symbol in self.auto_trader.profit_required_symbols
            ):
                # Remove from profit required since we sold for profit
                self.auto_trader.profit_required_symbols.remove(symbol)
                self.logger.warning(
                    f"✅ {symbol} removed from profit-required list - can buy again after profitable sale"
                )

        except Exception as e:
            self.logger.error(f"Error executing aggressive sell for {symbol}: {e}")

    async def _execute_lightning_buy_order(self, signal: dict) -> dict:
        """Execute lightning-fast buy order with streaming data for optimal pricing"""
        from ..tools.market_data_tools import get_stock_quote
        from ..tools.order_tools import place_stock_order
        from ..tools.streaming_tools import get_stock_stream_data

        symbol = signal["symbol"]
        signal_price = signal.get("price", 0)

        try:
            # Validate stock price limits
            if signal_price > self.trading_config.max_stock_price:
                return {
                    "status": "price_too_high",
                    "message": f"Stock price ${signal_price} exceeds limit ${self.trading_config.max_stock_price}",
                }

            # Get real-time streaming ask price first (fastest)
            current_ask = None
            try:
                # Ensure streaming is active for this symbol first
                from ..tools.streaming_tools import start_global_stock_stream

                await start_global_stock_stream([symbol], ["trades", "quotes"])

                stream_data = await get_stock_stream_data(symbol, "quotes", limit=1)
                self.logger.info(f"📡 RAW STREAM DATA: {stream_data[:200]}...")
                current_ask = self._extract_stream_ask_price(stream_data)
                self.logger.info(f"🚀 STREAMING ASK: {symbol} = ${current_ask}")
            except Exception as e:
                self.logger.warning(f"Streaming ask failed for {symbol}: {e}")

            # Fallback to quote API if streaming unavailable
            if current_ask is None:
                self.logger.info(f"📞 Fallback to quote API for {symbol}")
                quote_result = await get_stock_quote(symbol)
                current_ask = self._extract_ask_price(quote_result)

            if current_ask is None or current_ask > self.trading_config.max_stock_price:
                return {"status": "quote_error", "message": "Could not get valid current price"}

            # ANTI-FOMO CHECK: Don't chase if price moved too far above trough signal
            max_deviation = 0.05  # 5% maximum deviation from signal
            price_increase = (current_ask - signal_price) / signal_price if signal_price > 0 else 0

            if price_increase > max_deviation:
                self.logger.warning(
                    f"🚫 ANTI-FOMO: {symbol} ask ${current_ask:.4f} too far above trough signal ${signal_price:.4f} (+{price_increase:.1%}) - SKIPPING"
                )
                return {
                    "status": "fomo_protection",
                    "message": f"Price moved too far above signal (+{price_increase:.1%})",
                }

            self.logger.info(
                f"✅ BUY VALIDATION: {symbol} ask ${current_ask:.4f} within range of trough ${signal_price:.4f} (+{price_increase:.1%})"
            )

            # Calculate position size based on global config
            quantity = int(self.position_size_usd / current_ask)
            if quantity < 1:
                return {"status": "insufficient_funds", "message": "Position size too small"}

            # Use aggressive limit order slightly above ask for instant fill
            # For stocks >= $1.00: use penny increments (2 decimals)
            # For stocks < $1.00: use sub-penny increments (4 decimals)
            if current_ask >= 1.0:
                limit_price = round(current_ask * 1.002, 2)  # Penny increments for stocks >= $1
            else:
                limit_price = round(current_ask * 1.002, 4)  # Sub-penny for penny stocks

            # Execute buy order with IOC for lightning speed
            order_result = await place_stock_order(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                order_type="limit",
                limit_price=limit_price,
                time_in_force="day",  # DAY orders work in pre-market
                extended_hours=True,
            )

            # Extract order ID from result
            order_id = self._extract_order_id(order_result)

            if order_id:
                # Track order for monitoring
                order_info = {
                    "order_id": order_id,
                    "symbol": symbol,
                    "side": "buy",
                    "quantity": quantity,
                    "limit_price": limit_price,
                    "signal_price": signal_price,
                    "submitted_at": datetime.now(UTC),
                    "last_check": datetime.now(UTC),
                    "status": "submitted",
                }

                self.active_orders[order_id] = order_info

                # Start immediate order monitoring
                asyncio.create_task(self._monitor_order_for_fill(order_id))

                self.logger.warning(f"🚀 BUY ORDER EXECUTED: {symbol} x{quantity} @ ${limit_price}")

                return {
                    "status": "success",
                    "order_id": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "limit_price": limit_price,
                    "message": f"Lightning buy order submitted for {symbol}",
                }
            else:
                return {"status": "failed", "message": "Could not extract order ID"}

        except Exception as e:
            self.logger.error(f"Failed to execute buy order for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    async def _monitor_order_for_fill(self, order_id: str) -> None:
        """Monitor order for fill status with lightning speed"""
        from ..tools.order_tools import cancel_order_by_id, get_orders

        if order_id not in self.active_orders:
            return

        order = self.active_orders[order_id]
        order["symbol"]

        # Monitor for up to order_timeout seconds
        start_time = time.time()

        while time.time() - start_time < self.order_timeout:
            try:
                # Check order status
                orders_result = await get_orders(status="all", limit=50)

                # Check if order filled
                if order_id in orders_result and "filled" in orders_result.lower():
                    await self._handle_order_fill(order_id)
                    return
                elif "cancelled" in orders_result.lower() or "rejected" in orders_result.lower():
                    self.logger.warning(f"Order {order_id} failed to fill")
                    del self.active_orders[order_id]
                    return

                # Check every 0.5 seconds for lightning speed
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error monitoring order {order_id}: {e}")
                await asyncio.sleep(1)

        # Timeout - cancel order if still active
        try:
            await cancel_order_by_id(order_id)
            self.logger.warning(f"Cancelled order {order_id} due to timeout")
        except (ConnectionError, TimeoutError, Exception) as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")

        if order_id in self.active_orders:
            del self.active_orders[order_id]

    async def _monitor_positions_for_profit(self):
        """CRITICAL: Monitor all positions for profit-taking opportunities"""
        try:
            if not self.position_tracker or not self.position_tracker.positions:
                return

            # Import required tools
            from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs

            for symbol, position in self.position_tracker.positions.items():
                try:
                    # Get current position info - handle different position object formats
                    try:
                        # Try Alpaca position object attributes
                        quantity = float(getattr(position, "qty", getattr(position, "quantity", 0)))
                        entry_price = float(
                            getattr(
                                position, "avg_cost_basis", getattr(position, "avg_entry_price", 0)
                            )
                        )
                        unrealized_pnl = float(
                            getattr(
                                position, "unrealized_pl", getattr(position, "unrealized_pnl", 0)
                            )
                        )
                        current_price = (
                            float(getattr(position, "market_value", 0)) / quantity
                            if quantity > 0
                            else 0
                        )

                        self.logger.info(
                            f"📊 POSITION DEBUG: {symbol} qty={quantity} entry=${entry_price} pnl=${unrealized_pnl}"
                        )
                    except Exception as e:
                        self.logger.error(f"Error parsing position data for {symbol}: {e}")
                        continue

                    # Only sell for profit - NEVER SELL FOR LOSS
                    if unrealized_pnl <= 0:
                        continue  # Skip - no profit to take

                    # SELL AT PEAKS FOR ANY PROFIT - No thresholds
                    profit_percent = (unrealized_pnl / abs(quantity * entry_price)) * 100
                    self.logger.warning(
                        f"📊 POSITION: {symbol} ${unrealized_pnl:.2f} profit ({profit_percent:.1f}%) - MONITORING FOR PEAK"
                    )

                    # Check for peak signals to sell at resistance
                    try:
                        analysis = await analyze_peaks_and_troughs(
                            symbols=symbol,
                            timeframe="1Min",
                            days=1,
                            window_len=11,  # Use global config
                            lookahead=1,  # Use global config
                        )

                        # Look for ANY peak signals - sell at peaks for profit
                        if "Latest peak:" in analysis:
                            lines = analysis.split("\n")
                            for line in lines:
                                if "bars ago" in line and "PEAK" in line.upper():
                                    import re

                                    bars_match = re.search(r"(\d+)\s+bars?\s+ago", line)
                                    if bars_match:
                                        bars_ago = int(bars_match.group(1))
                                        # Sell at ANY peak if profitable - no bars_ago limit for sells
                                        await self._execute_profit_sell(
                                            symbol,
                                            quantity,
                                            "PEAK_DETECTED",
                                            f"Peak signal ({bars_ago} bars ago) - profit ${unrealized_pnl:.2f}",
                                        )
                                        break

                    except Exception as e:
                        self.logger.debug(f"Peak analysis error for {symbol}: {e}")

                    # Aggressive profit capture - sell at ANY profit above entry
                    if current_price > entry_price * 1.001:  # 0.1%+ profit spike
                        await self._execute_profit_sell(
                            symbol,
                            quantity,
                            "PROFIT_CAPTURE",
                            f"Profit detected - selling at peak - profit ${unrealized_pnl:.2f}",
                        )
                        continue

                except Exception as e:
                    self.logger.error(f"Error monitoring position {symbol}: {e}")

        except Exception as e:
            self.logger.error(f"Error in position monitoring: {e}")

    async def _execute_profit_sell(self, symbol: str, quantity: float, reason: str, details: str) -> None:
        """Execute immediate profit-taking sell order"""
        try:
            from ..tools.market_data_tools import get_stock_quote
            from ..tools.order_tools import place_stock_order

            # Get real-time bid price
            quote_result = await get_stock_quote(symbol)
            current_bid = self._extract_bid_price(quote_result)

            if not current_bid:
                self.logger.error(f"Could not get bid price for {symbol} profit sell")
                return

            # Execute sell order with exact bid price for instant fill
            await place_stock_order(
                symbol=symbol,
                side="sell",
                quantity=int(quantity),
                order_type="limit",
                limit_price=current_bid,  # Use exact bid for guaranteed fill
                time_in_force="day",  # DAY orders for pre-market
                extended_hours=True,
            )

            self.logger.warning(f"💰 PROFIT SELL EXECUTED: {symbol} - {reason} - {details}")
            self.logger.warning(f"📊 SELL ORDER: {quantity} shares @ ${current_bid}")

            # Broadcast profit-taking event
            await self._broadcast_update(
                {
                    "type": "profit_sell_executed",
                    "symbol": symbol,
                    "quantity": quantity,
                    "price": current_bid,
                    "reason": reason,
                    "details": details,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        except Exception as e:
            self.logger.error(f"Error executing profit sell for {symbol}: {e}")

    def _extract_bid_price(self, quote_result: str) -> float | None:
        """Extract bid price from quote result"""
        try:
            lines = quote_result.split("\n")
            for line in lines:
                if "Bid Price:" in line:
                    price_str = line.split("Bid Price:")[1].strip().replace("$", "")
                    return float(price_str)
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error in extract operation: {e}")
        return None

    async def _handle_order_fill(self, order_id: str) -> None:
        """Handle filled order and start position tracking"""
        from ..tools.account_tools import get_positions

        if order_id not in self.active_orders:
            return

        order = self.active_orders[order_id]
        symbol = order["symbol"]

        try:
            # Get current positions to find the new position
            positions_result = await get_positions()
            entry_price, quantity = self._extract_position_info(positions_result, symbol)

            if entry_price and quantity:
                # Create active position for profit monitoring
                position_info = {
                    "symbol": symbol,
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "current_price": entry_price,
                    "unrealized_pnl": 0.0,
                    "unrealized_pnl_percent": 0.0,
                    "opened_at": datetime.now(UTC),
                    "highest_price": entry_price,
                    "order_id": order_id,
                }

                self.active_positions[symbol] = position_info

                self.logger.warning(f"✅ POSITION OPENED: {symbol} x{quantity} @ ${entry_price}")

                # Start real-time position monitoring for profit taking
                asyncio.create_task(self._monitor_position_for_profits(symbol))

                # Send alert
                if self.alert_system:
                    await self.alert_system.send_alert(
                        f"📊 Position Opened: {symbol}",
                        f"BUY {quantity} @ ${entry_price} - Auto-trading active",
                        priority="high",
                    )

        except Exception as e:
            self.logger.error(f"Error handling order fill for {order_id}: {e}")

        # Remove from active orders
        if order_id in self.active_orders:
            del self.active_orders[order_id]

    async def _monitor_position_for_profits(self, symbol: str) -> None:
        """Monitor position for profit opportunities with real-time streaming"""
        from ..config.global_config import get_technical_config
        from ..tools.streaming_tools import get_stock_stream_data

        if symbol not in self.active_positions:
            return

        position = self.active_positions[symbol]
        tech_config = get_technical_config()

        self.logger.info(f"🔍 Started profit monitoring for {symbol}")

        while symbol in self.active_positions:
            try:
                # Get real-time streaming price
                stream_data = await get_stock_stream_data(symbol, "trades", limit=1)
                current_price = self._extract_stream_price(stream_data)

                if current_price:
                    # Update position with current price
                    position["current_price"] = current_price
                    position["unrealized_pnl"] = (
                        current_price - position["entry_price"]
                    ) * position["quantity"]
                    position["unrealized_pnl_percent"] = (
                        (current_price - position["entry_price"]) / position["entry_price"]
                    ) * 100

                    # Track highest price for profit optimization
                    if current_price > position["highest_price"]:
                        position["highest_price"] = current_price

                    # Check profit taking conditions
                    await self._check_profit_taking_conditions(
                        symbol, position, current_price, tech_config
                    )

                # Update every 2 seconds for real-time monitoring
                await asyncio.sleep(2)

            except Exception as e:
                self.logger.error(f"Error monitoring position {symbol}: {e}")
                await asyncio.sleep(5)

    async def _check_profit_taking_conditions(  # type: ignore[no-untyped-def]
        self, symbol: str, position: dict, current_price: float, tech_config
    ):
        """Check if we should sell for profit using family protection rules"""

        # Get trading config for normalized thresholds
        from alpaca_mcp_server.config.global_config import get_global_config

        config = get_global_config()

        # Family protection rule: 10%+ profit = IMMEDIATE SELL (normalized)
        if (
            position["unrealized_pnl_percent"]
            >= config.trading.family_protection_profit_threshold_percent
        ):
            await self._execute_lightning_sell_order(
                symbol,
                position,
                "family_protection",
                f"{position['unrealized_pnl_percent']:.1f}% profit (${position['unrealized_pnl']:.0f}) - FAMILY PROTECTION RULE",
            )
            return

        # 3%+ gains = automatic exit for family security (normalized)
        if position["unrealized_pnl_percent"] >= config.trading.automatic_profit_threshold_percent:
            await self._execute_lightning_sell_order(
                symbol,
                position,
                "automatic_profit",
                f"{position['unrealized_pnl_percent']:.1f}% gain (${position['unrealized_pnl']:.0f})",
            )
            return

        # Check for fresh peak signals using real-time analysis
        try:
            analysis = await analyze_peaks_and_troughs(
                symbols=symbol,
                timeframe="1Min",
                days=1,
                window_len=tech_config.hanning_window_samples,
                lookahead=tech_config.peak_trough_lookahead,
            )

            # Parse for fresh peak (≤5 bars ago)
            if "Latest peak:" in analysis:
                lines = analysis.split("\n")
                for line in lines:
                    if "Latest peak:" in line:
                        # Extract bars ago from latest peak line
                        import re

                        bars_match = re.search(r"\((\d+)\s+bars?\s+ago\)", line)
                        if bars_match:
                            bars_ago = int(bars_match.group(1))
                            # Use global config for fresh threshold
                            from ..config.global_config import get_global_config

                            config = get_global_config()
                            fresh_threshold = config.technical_analysis.hanning_window_samples

                            if bars_ago <= fresh_threshold:  # Fresh peak signal
                                await self._execute_lightning_sell_order(
                                    symbol,
                                    position,
                                    "fresh_peak",
                                    f"Fresh peak signal ({bars_ago} bars ago)",
                                )
                                return

        except Exception as e:
            self.logger.error(f"Error checking peak signals for {symbol}: {e}")

    async def _execute_lightning_sell_order(  # type: ignore[no-untyped-def]
        self, symbol: str, position: dict, reason: str, details: str
    ):
        """Execute lightning-fast sell order with streaming data for optimal pricing"""
        from ..tools.market_data_tools import get_stock_quote
        from ..tools.order_tools import place_stock_order
        from ..tools.streaming_tools import get_stock_stream_data

        try:
            # Never sell for loss rule
            if self.never_sell_for_loss and position["unrealized_pnl"] < 0:
                self.logger.warning(
                    f"🛡️ NEVER SELL FOR LOSS: {symbol} P&L=${position['unrealized_pnl']:.2f}"
                )
                return

            # Get real-time streaming bid price first (fastest)
            current_bid = None
            try:
                # Ensure streaming is active for this symbol first
                from ..tools.streaming_tools import start_global_stock_stream

                await start_global_stock_stream([symbol], ["trades", "quotes"])

                stream_data = await get_stock_stream_data(symbol, "quotes", limit=1)
                current_bid = self._extract_stream_bid_price(stream_data)
                self.logger.info(f"💰 STREAMING BID: {symbol} = ${current_bid}")
            except Exception as e:
                self.logger.warning(f"Streaming bid failed for {symbol}: {e}")

            # Fallback to quote API if streaming unavailable
            if current_bid is None:
                self.logger.info(f"📞 Fallback to quote API for {symbol}")
                quote_result = await get_stock_quote(symbol)
                current_bid = self._extract_bid_price(quote_result)

            if not current_bid:
                self.logger.error(f"Could not get bid price for {symbol}")
                return

            # Use aggressive limit order at bid for instant fill
            limit_price = round(current_bid * 0.998, 4)  # Slightly below bid for instant fill

            # Execute sell order with IOC
            await place_stock_order(
                symbol=symbol,
                side="sell",
                quantity=position["quantity"],
                order_type="limit",
                limit_price=limit_price,
                time_in_force="day",
                extended_hours=True,
            )

            self.logger.warning(f"💰 SELL ORDER EXECUTED: {symbol} - {reason} - {details}")
            self.logger.warning(
                f"📊 PROFIT: ${position['unrealized_pnl']:.2f} ({position['unrealized_pnl_percent']:.1f}%)"
            )

            # Send alert
            if self.alert_system:
                await self.alert_system.send_alert(
                    f"💰 Position Sold: {symbol}",
                    f"SELL {position['quantity']} @ ${limit_price} - {reason} - Profit: ${position['unrealized_pnl']:.2f}",
                    priority="critical",
                )

            # Remove position from tracking and sync with Alpaca
            del self.active_positions[symbol]

            # Also verify position is actually closed in Alpaca (extra safety)
            try:
                from ..tools.account_tools import get_positions

                alpaca_positions = await get_positions()
                if alpaca_positions and "positions" in alpaca_positions:
                    for pos in alpaca_positions["positions"]:  # type: ignore[index]
                        if pos.get("symbol") == symbol and abs(float(pos.get("quantity", 0))) > 0:  # type: ignore[attr-defined]
                            self.logger.warning(
                                f"⚠️ Position still exists in Alpaca after sell: {symbol} ({pos.get('quantity')} shares)"  # type: ignore[attr-defined]
                            )
            except Exception as e:
                self.logger.warning(f"Could not verify Alpaca position closure: {e}")

        except Exception as e:
            self.logger.error(f"Error executing sell order for {symbol}: {e}")

    def _extract_order_id(self, order_result) -> str | None:  # type: ignore[no-untyped-def]
        """Extract order ID from order result - handles both dict and string formats"""
        try:
            # Handle dictionary result (direct from MCP tools)
            if isinstance(order_result, dict):
                if "order" in order_result:
                    order = order_result["order"]
                    if isinstance(order, Position):
                        return str(order.id)  # type: ignore[attr-defined]
                    elif isinstance(order, dict) and "id" in order:
                        return str(order["id"])
                # Check for direct id field
                if "id" in order_result:
                    return str(order_result["id"])
                # Check for order_id field
                if "order_id" in order_result:
                    return str(order_result["order_id"])

            # Handle string result (formatted output)
            if isinstance(order_result, str):
                lines = order_result.split("\n")
                for line in lines:
                    if "Order ID:" in line:
                        return line.split("Order ID:")[1].strip()

            self.logger.error(
                f"Could not extract order ID from result: {type(order_result)} - {str(order_result)[:200]}"
            )

        except Exception as e:
            self.logger.error(f"Error extracting order ID: {e}")
        return None

    def _extract_ask_price(self, quote_result: str) -> float | None:
        """Extract ask price from quote result"""
        try:
            lines = quote_result.split("\n")
            for line in lines:
                if "Ask Price:" in line:
                    price_str = line.split("Ask Price:")[1].strip().replace("$", "")
                    return float(price_str)
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error in extract operation: {e}")
        return None

    def _extract_bid_price(self, quote_result: str) -> float | None:  # type: ignore[no-redef]
        """Extract bid price from quote result"""
        try:
            lines = quote_result.split("\n")
            for line in lines:
                if "Bid Price:" in line:
                    price_str = line.split("Bid Price:")[1].strip().replace("$", "")
                    return float(price_str)
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error in extract operation: {e}")
        return None

    def _extract_position_info(
        self, positions_result: str, symbol: str
    ) -> tuple[float | None, int | None]:
        """Extract position info from positions result"""
        try:
            lines = positions_result.split("\n")
            in_symbol_section = False
            entry_price = None
            quantity = None

            for line in lines:
                if f"Symbol: {symbol}" in line:
                    in_symbol_section = True
                elif "Symbol:" in line and symbol not in line:
                    in_symbol_section = False
                elif in_symbol_section:
                    if "Entry Price:" in line:
                        price_str = line.split("Entry Price:")[1].strip().replace("$", "")
                        entry_price = float(price_str)
                    elif "Quantity:" in line:
                        quantity = int(line.split("Quantity:")[1].strip())

            return entry_price, quantity
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error in extract operation: {e}")
        return None, None

    def _extract_stream_price(self, stream_data: str) -> float | None:
        """Extract price from streaming data"""
        try:
            lines = stream_data.split("\n")
            for line in lines:
                if "price" in line.lower() and "$" in line:
                    import re

                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        return float(price_match.group(1))
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error in extract operation: {e}")
        return None

    def _extract_stream_ask_price(self, stream_data: str) -> float | None:
        """Extract ask price from streaming quotes data"""
        try:
            lines = stream_data.split("\n")
            for line in lines:
                # Look for bid x ask format: $0.4544 x $0.4629 or $2.7500 x $2.7600
                if " x $" in line and "$" in line:
                    import re

                    # More flexible regex for ask price (second price after 'x $')
                    ask_match = re.search(r" x \$(\d+\.?\d*)", line)
                    if ask_match:
                        price = float(ask_match.group(1))
                        self.logger.debug(f"Extracted ask from: '{line}' -> ${price}")
                        return price
                    else:
                        self.logger.debug(f"Ask regex failed on: '{line}'")
            # If no exact match, try to extract any price pattern as fallback
            for line in lines:
                if "$" in line:
                    import re

                    prices = re.findall(r"\$(\d+\.?\d+)", line)
                    if len(prices) >= 2:
                        # Assume last price is ask in bid/ask pair
                        price = float(prices[-1])
                        self.logger.debug(f"Fallback ask extraction: '{line}' -> ${price}")
                        return price
        except Exception as e:
            self.logger.warning(f"Error extracting ask price: {e}")
        return None

    def _extract_stream_bid_price(self, stream_data: str) -> float | None:
        """Extract bid price from streaming quotes data"""
        try:
            lines = stream_data.split("\n")
            for line in lines:
                # Look for bid x ask format: $0.4544 x $0.4629 or $2.7500 x $2.7600
                if "$" in line and " x $" in line:
                    import re

                    # Extract the bid price (first price before ' x $')
                    bid_match = re.search(r"\$(\d+\.?\d*) x \$", line)
                    if bid_match:
                        price = float(bid_match.group(1))
                        self.logger.debug(f"Extracted bid from: '{line}' -> ${price}")
                        return price
                    else:
                        self.logger.debug(f"Bid regex failed on: '{line}'")
            # If no exact match, try to extract any price pattern as fallback
            for line in lines:
                if "$" in line:
                    import re

                    prices = re.findall(r"\$(\d+\.?\d+)", line)
                    if len(prices) >= 2:
                        # Assume first price is bid in bid/ask pair
                        price = float(prices[0])
                        self.logger.debug(f"Fallback bid extraction: '{line}' -> ${price}")
                        return price
        except Exception as e:
            self.logger.warning(f"Error extracting bid price: {e}")
        return None

    async def _sync_positions_with_alpaca(self):
        """Sync internal position tracking with actual Alpaca positions to prevent double buying"""
        try:
            from ..tools.account_tools import get_positions

            alpaca_positions = await get_positions()

            if alpaca_positions and "positions" in alpaca_positions:
                # Clear internal tracking and rebuild from Alpaca
                existing_symbols = set(self.active_positions.keys())
                alpaca_symbols = set()

                for pos in alpaca_positions["positions"]:  # type: ignore[index]
                    symbol = pos.get("symbol")  # type: ignore[attr-defined]
                    quantity = float(pos.get("quantity", 0))  # type: ignore[attr-defined]

                    if symbol and abs(quantity) > 0:
                        alpaca_symbols.add(symbol)

                        # Add to internal tracking if not already there
                        if symbol not in self.active_positions:
                            self.active_positions[symbol] = {
                                "symbol": symbol,
                                "quantity": abs(quantity),
                                "entry_price": float(pos.get("avg_entry_price", 0)),  # type: ignore[attr-defined]
                                "current_price": float(pos.get("current_price", 0)),  # type: ignore[attr-defined]
                                "unrealized_pnl": float(pos.get("unrealized_pnl", 0)),  # type: ignore[attr-defined]
                                "unrealized_pnl_percent": float(
                                    pos.get("unrealized_pnl_percent", 0)  # type: ignore[attr-defined]
                                ),
                            }
                            self.logger.info(
                                f"📊 Synced existing Alpaca position: {symbol} ({quantity} shares)"
                            )

                # Remove positions from internal tracking that don't exist in Alpaca
                for symbol in list(existing_symbols):
                    if symbol not in alpaca_symbols:
                        del self.active_positions[symbol]
                        self.logger.info(f"🧹 Removed stale position from tracking: {symbol}")

                self.logger.info(
                    f"✅ Position sync complete: {len(self.active_positions)} active positions"
                )

        except Exception as e:
            self.logger.error(f"Error syncing positions with Alpaca: {e}")

    async def get_auto_trading_status(self) -> dict:
        """Get current auto trading status"""
        # Use auto_trader status if available (includes profit_required_symbols)
        if isinstance(self, Position) and self.auto_trader:
            trader_status = self.auto_trader.get_status()
            # Override enabled status with our flag
            trader_status["enabled"] = self.auto_trading_enabled
            return trader_status

        # Fallback to basic status
        return {
            "enabled": self.auto_trading_enabled,
            "active_orders": len(self.active_orders),
            "active_positions": len(self.active_positions),
            "position_symbols": list(self.active_positions.keys()),
            "profit_required_symbols": [],
            "profit_required_count": 0,
            "config": {
                "position_size_usd": self.position_size_usd,
                "max_positions": self.max_positions,
                "never_sell_for_loss": self.never_sell_for_loss,
                "order_timeout": self.order_timeout,
            },
        }

    async def check_positions_after_order(self, order_info: dict | None = None) -> dict:
        """Check positions immediately after an order"""
        if not self.position_tracker:
            return {"status": "error", "message": "Position tracker not available"}

        try:
            # Force immediate position update
            await self.position_tracker.update_positions()
            position_count = len(self.position_tracker.positions)
            position_symbols = list(self.position_tracker.positions.keys())

            # Log the check
            if order_info:
                self.logger.warning(
                    f"🔔 POST-ORDER CHECK: After {order_info.get('action', 'order')}, found {position_count} positions: {position_symbols}"
                )
            else:
                self.logger.warning(
                    f"🔔 POSITION CHECK: Currently {position_count} positions: {position_symbols}"
                )

            # Send WebSocket update
            await self._broadcast_update(
                {
                    "type": "position_update",
                    "position_count": position_count,
                    "positions": position_symbols,
                    "order_info": order_info,
                }
            )

            # Send alert
            if self.alert_system:
                message = f"Post-order position check: {position_count} positions"
                if position_symbols:
                    message += f" ({', '.join(position_symbols)})"

                await self.alert_system.send_alert(
                    "📊 Position Status Check", message, priority="high"
                )

            # Update tracking
            self._last_position_count = position_count

            return {
                "status": "success",
                "position_count": position_count,
                "positions": position_symbols,
                "message": f"Found {position_count} positions: {position_symbols}",
            }

        except Exception as e:
            self.logger.error(f"Error checking positions after order: {e}")
            return {"status": "error", "message": str(e)}

    async def _monitoring_loop(self):
        """Main monitoring loop - runs continuously"""
        self.logger.info("🔄 Starting FastAPI monitoring loop")

        while self.active:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config.check_interval)

            except asyncio.CancelledError:
                self.logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in monitoring cycle: {e}")

                # Send error alert if too many errors
                if self.error_count % 10 == 0:
                    await self.alert_system.send_alert(
                        "🚨 Monitoring Errors",
                        f"Service has encountered {self.error_count} errors. Latest: {e}",
                        priority="warning",
                    )

                # Continue monitoring despite errors
                await asyncio.sleep(self.config.check_interval)

    async def _monitoring_cycle(self):
        """Single monitoring cycle"""
        self.last_check = datetime.now(UTC)
        self.check_count += 1

        # Log heartbeat every 100 cycles
        if self.check_count % 100 == 0:
            position_count = len(self.position_tracker.positions) if self.position_tracker else 0
            self.logger.info(
                f"💓 FastAPI Heartbeat - Cycle {self.check_count}, Watchlist: {len(self.watchlist)}, Positions: {position_count}"
            )

        # Update positions
        if self.position_tracker:
            await self.position_tracker.update_positions()

            # Log position changes
            position_count = len(self.position_tracker.positions)
            if (
                isinstance(self, Position)
                and self._last_position_count != position_count
            ):
                change_data = {
                    "type": "position_change",
                    "previous_count": getattr(self, "_last_position_count", 0),
                    "current_count": position_count,
                    "change": (
                        "increase" if position_count > self._last_position_count else "decrease"
                    ),
                }

                # Broadcast to WebSocket clients
                await self._broadcast_update(change_data)

                if position_count > self._last_position_count:
                    self.logger.warning(
                        f"🔔 NEW POSITIONS DETECTED: {position_count} total positions now active"
                    )
                elif position_count < self._last_position_count:
                    self.logger.warning(
                        f"🔔 POSITIONS CLOSED: {position_count} positions remaining (was {self._last_position_count})"
                    )

                # Alert about position changes
                if self.alert_system:
                    await self.alert_system.send_alert(
                        "📊 Position Change Detected",
                        f"Position count changed from {getattr(self, '_last_position_count', 0)} to {position_count}",
                        priority="high",
                    )

            self._last_position_count = position_count

        # **POSITION MONITORING FOR PROFIT-TAKING** - Critical for family support!
        self.logger.warning(
            f"🔍 MONITORING CHECK: auto_trading={self.auto_trading_enabled}, tracker={bool(self.position_tracker)}, has_positions={hasattr(self.position_tracker, 'positions') if self.position_tracker else False}"
        )

        if (
            self.auto_trading_enabled
            and self.position_tracker
            and hasattr(self.position_tracker, "positions")
        ):
            self.logger.warning(
                f"🔍 CALLING POSITION MONITORING - positions count: {len(self.position_tracker.positions) if self.position_tracker.positions else 0}"
            )
            await self._monitor_positions_for_profit()
        else:
            self.logger.error(
                f"🚫 POSITION MONITORING SKIPPED - auto_trading={self.auto_trading_enabled}, tracker={bool(self.position_tracker)}"
            )

        # Generate fresh signals directly from peak/trough analysis
        if self.watchlist:
            try:
                fresh_signals_data = await self.get_signals()  # This now generates fresh signals
                fresh_signals = fresh_signals_data.get("current_signals", [])

                # Process only truly fresh trough signals for auto-trading
                for signal in fresh_signals:
                    # Use global config for fresh threshold
                    from ..config.global_config import get_global_config

                    config = get_global_config()
                    fresh_threshold = config.technical_analysis.hanning_window_samples

                    if (
                        signal["signal_type"] == "fresh_trough"
                        and signal.get("bars_ago", 999) <= fresh_threshold
                        and self.auto_trading_enabled
                    ):
                        # Process signal for auto-trading
                        try:
                            trading_result = await self.process_fresh_signal_for_trading(signal)
                            if trading_result["status"] == "success":
                                self.logger.warning(
                                    f"🚀 AUTO-TRADING EXECUTED: {signal['symbol']} - {trading_result['message']}"
                                )
                            elif trading_result["status"] not in [
                                "disabled",
                                "ignored",
                                "duplicate",
                            ]:
                                self.logger.debug(
                                    f"🔄 Auto-trading: {signal['symbol']} - {trading_result['message']}"
                                )
                        except Exception as e:
                            self.logger.error(
                                f"Error in auto-trading execution for {signal['symbol']}: {e}"
                            )

                # Log fresh signals found
                trough_count = len([s for s in fresh_signals if s["signal_type"] == "fresh_trough"])
                if trough_count > 0:
                    self.logger.info(
                        f"🎯 Found {trough_count} fresh trough signals for potential trading"
                    )

            except Exception as e:
                self.logger.error(f"Error generating fresh signals: {e}")

        # Legacy signal detection (kept for compatibility)
        if self.signal_detector and self.watchlist:
            new_signals = await self.signal_detector.scan_for_signals(list(self.watchlist))

            # Process new signals
            for signal in new_signals:
                await self._process_signal(signal)

        # Automatic watchlist synchronization with scanner results
        if self.auto_scan_enabled:
            now = datetime.now(UTC)
            if (
                self.last_scan_time is None
                or (now - self.last_scan_time).total_seconds() >= self.scan_interval_seconds
            ):

                try:
                    self.logger.info(
                        f"🔍 Starting automatic watchlist sync with scanner (interval: {self.scan_interval_seconds}s)"
                    )
                    sync_result = await self.sync_with_scanner_results(self.scan_params)
                    self.last_scan_time = now

                    if sync_result.get("status") in ["success", "no_changes"]:
                        self.logger.info(
                            f"📊 Auto-scan completed: {sync_result.get('message', 'No changes')}"
                        )

                        # Log detailed scan results
                        if sync_result.get("status") == "success":
                            added = sync_result.get("added", [])
                            removed = sync_result.get("removed", [])
                            if added or removed:
                                self.logger.warning(
                                    f"📊 WATCHLIST UPDATED: +{len(added)} new explosive stocks, -{len(removed)} inactive stocks"
                                )
                                if added:
                                    self.logger.warning(
                                        f"🚀 NEW EXPLOSIVE STOCKS: {', '.join(added)}"
                                    )
                                if removed:
                                    self.logger.warning(
                                        f"🔻 REMOVED INACTIVE: {', '.join(removed)}"
                                    )

                        await self._broadcast_update(
                            {
                                "type": "auto_scan_update",
                                "result": sync_result,
                                "timestamp": now.isoformat(),
                            }
                        )
                    else:
                        self.logger.warning(
                            f"⚠️ Auto-scan had issues: {sync_result.get('message', 'Unknown error')}"
                        )

                except Exception as e:
                    self.logger.error(f"❌ Auto-scan failed: {e}")
                    self.error_count += 1

        # Check hibernation conditions after auto-scan
        if self.hibernation_enabled:
            try:
                await self.check_hibernation_conditions()
            except Exception as e:
                self.logger.error(f"❌ Hibernation check failed: {e}")

        # Save state periodically
        if self.check_count % 50 == 0:  # Every ~100 seconds
            await self._save_state()

    async def _process_signal(self, signal: dict) -> None:
        """Process a detected trading signal"""
        # Keep the existing NYC/EDT timezone from detected_at, or create new one if missing
        if "detected_at" not in signal:
            from ..utils.timezone_utils import get_eastern_time

            eastern_time, _ = get_eastern_time()
            signal["detected_at"] = eastern_time.isoformat()

        signal["timestamp"] = signal["detected_at"]  # Use the same NYC/EDT timestamp
        signal["id"] = f"{signal['symbol']}_{int(time.time())}"

        # Add to current signals
        self.current_signals.append(signal)
        self.signal_history.append(signal)

        # Keep only truly fresh signals (last 10 minutes and <5 bars ago)
        cutoff_time = time.time() - 600  # 10 minutes ago
        filtered_signals = []
        for s in self.current_signals:
            try:
                # Handle timezone-aware timestamps from signal detector
                ts_str = s.get("timestamp", s.get("detected_at", ""))
                bars_ago = s.get("bars_ago", 999)

                # Only keep signals that are recent AND fresh (≤hanning_window_samples bars ago)
                from ..config.global_config import get_global_config

                config = get_global_config()
                fresh_threshold = config.technical_analysis.hanning_window_samples

                if ts_str and bars_ago <= fresh_threshold:
                    # Parse timezone-aware timestamp
                    signal_time = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if signal_time.timestamp() > cutoff_time:
                        filtered_signals.append(s)
            except (ValueError, TypeError):
                # Don't keep signals with parsing issues - they're likely stale
                continue

        self.current_signals = filtered_signals

        # Broadcast signal to WebSocket clients
        await self._broadcast_update({"type": "new_signal", "signal": signal})

        # Send alert for high-confidence signals
        if signal.get("confidence", 0) >= self.config.signal_confidence_threshold:
            await self._send_signal_alert(signal)

        # LIGHTNING EXECUTION: Process signal for automated trading
        if self.auto_trading_enabled and signal["signal_type"] == "fresh_trough":
            try:
                trading_result = await self.process_fresh_signal_for_trading(signal)
                if trading_result["status"] == "success":
                    self.logger.warning(
                        f"🚀 AUTO-TRADING EXECUTED: {signal['symbol']} - {trading_result['message']}"
                    )
                elif trading_result["status"] not in ["disabled", "ignored"]:
                    self.logger.info(
                        f"🔄 Auto-trading: {signal['symbol']} - {trading_result['message']}"
                    )
            except Exception as e:
                self.logger.error(f"Error in auto-trading execution for {signal['symbol']}: {e}")

        # Also support legacy auto_trader if it exists
        elif (
            isinstance(self, Position)
            and self.auto_trader
            and signal["signal_type"] == "fresh_trough"
        ):
            trade_result = await self.auto_trader.process_fresh_signal(signal)
            if trade_result["status"] == "success":
                self.logger.warning(
                    f"🚀 AUTO TRADE EXECUTED: {signal['symbol']} - {trade_result['message']}"
                )
            elif trade_result["status"] in ["disabled", "ignored"]:
                pass  # Normal - auto trading disabled or non-trough signal
            else:
                self.logger.info(
                    f"Auto trade result for {signal['symbol']}: {trade_result['status']} - {trade_result['message']}"
                )

        self.logger.info(
            f"Signal detected: {signal['symbol']} - {signal['signal_type']} (confidence: {signal.get('confidence', 0):.2f})"
        )

    async def _send_signal_alert(self, signal: dict) -> None:
        """Send alert for trading signal"""
        signal_emoji = "🚀" if signal["signal_type"] == "fresh_trough" else "⚠️"

        message = (
            f"{signal_emoji} TRADING SIGNAL: {signal['symbol']}\n"
            f"Type: {signal['signal_type']}\n"
            f"Price: ${signal.get('price', 'N/A')}\n"
            f"Confidence: {signal.get('confidence', 0):.1%}\n"
            f"Action: {signal.get('action', 'analyze')}"
        )

        await self.alert_system.send_alert(
            f"Trading Signal: {signal['symbol']}", message, priority="high"
        )

    async def _broadcast_update(self, data: dict) -> None:
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return

        message = json.dumps({"timestamp": datetime.now(UTC).isoformat(), **data})

        # Send to all connected clients
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except (ConnectionResetError, ConnectionAbortedError, Exception) as e:
                self.logger.debug(f"WebSocket connection error: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        self.websocket_connections -= disconnected

    async def _save_state(self):
        """Save service state to disk"""
        try:
            state = {
                "active": self.active,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "last_check": self.last_check.isoformat() if self.last_check else None,
                "check_count": self.check_count,
                "error_count": self.error_count,
                "watchlist": sorted(self.watchlist),
                "current_signals": self.current_signals,
                "config": asdict(self.config),
            }

            state_file = self.state_dir / "fastapi_service_state.json"
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    async def _handle_trade_update(self, trade_info: dict) -> None:
        """Handle real-time trade updates from Alpaca streaming"""
        self.logger.warning(f"🔔 TRADE UPDATE: {trade_info['event']} - {trade_info['symbol']}")

        # Send desktop notification for order fills
        if trade_info["event"] == "order_filled":
            await self.desktop_notifications.send_order_fill_alert(
                symbol=trade_info["symbol"],
                side=trade_info["side"],
                quantity=int(trade_info["filled_qty"]),
                fill_price=float(trade_info["filled_avg_price"]),
            )

            # Track sell orders for wash sale prevention
            if trade_info["side"].upper() == "SELL":
                symbol = trade_info["symbol"]
                self.recently_sold_symbols[symbol] = datetime.now(UTC)
                self.logger.info(
                    f"🛇 WASH SALE TRACKING: {symbol} marked as recently sold for {self.wash_sale_cooldown_minutes} minutes"
                )

        # Broadcast to WebSocket clients
        await self._broadcast_update({"type": "trade_update", **trade_info})

        # Send alert for order fills
        if trade_info["event"] == "order_filled":
            await self.alert_system.send_alert(
                f"📊 Order Filled: {trade_info['symbol']}",
                f"{trade_info['side'].upper()} {trade_info['filled_qty']} @ ${trade_info['filled_avg_price']}",
                priority="high",
            )

            # Force position update and automatic checking
            if self.position_tracker:
                await self.position_tracker.update_positions()

            # Automatically trigger position verification
            await self.check_positions_after_order({"symbol": trade_info["symbol"]})

    async def _handle_profit_spike(self, spike_info: dict) -> None:
        """Handle real-time profit spike detection"""
        self.logger.warning(
            f"🚨 PROFIT SPIKE DETECTED: {spike_info['symbol']} +{spike_info['profit_pct']:.2f}%"
        )

        # Send desktop notification for profit spike
        await self.desktop_notifications.send_profit_spike_alert(
            symbol=spike_info["symbol"],
            profit_percent=spike_info["profit_pct"],
            current_price=spike_info["current_price"],
            profit_dollar=spike_info.get("profit_dollar", 0),
        )

        # Generate JSON profit alert
        profit_alert = {
            "id": f"profit_{spike_info['symbol']}_{int(time.time())}",
            "timestamp": spike_info["timestamp"],
            "event": "PROFIT_SPIKE",
            "symbol": spike_info["symbol"],
            "entry_price": spike_info["entry_price"],
            "current_price": spike_info["current_price"],
            "profit_pct": spike_info["profit_pct"],
            "action": "CONSIDER_EXIT",
        }

        # Save to JSON file
        alert_file = self.state_dir / "profit_alerts" / f"{profit_alert['id']}.json"
        alert_file.parent.mkdir(exist_ok=True)
        with open(alert_file, "w") as f:
            json.dump(profit_alert, f, indent=2)

        # Broadcast to all channels
        await self._broadcast_update({"type": "profit_alert", **profit_alert})

        await self.alert_system.send_alert(
            f"💰 PROFIT SPIKE: {spike_info['symbol']}",
            f"+{spike_info['profit_pct']:.2f}% profit detected! Current: ${spike_info['current_price']}",
            priority="critical",
        )

    async def _handle_market_data(self, data: dict) -> None:
        """Handle real-time market data updates"""
        # Forward to WebSocket clients
        await self._broadcast_update({"type": "market_data", **data})

    async def _load_state(self):
        """Load service state from disk"""
        try:
            state_file = self.state_dir / "fastapi_service_state.json"
            if state_file.exists():
                with open(state_file) as f:
                    state = json.load(f)

                self.watchlist = set(state.get("watchlist", []))
                self.current_signals = state.get("current_signals", [])
                self.check_count = state.get("check_count", 0)
                self.error_count = state.get("error_count", 0)

                self.logger.info(
                    f"Loaded previous state: {len(self.watchlist)} symbols in watchlist"
                )

        except Exception as e:
            self.logger.warning(f"Could not load previous state: {e}")


# Global service instance
monitoring_service = MonitoringServiceAPI()


@asynccontextmanager  # type: ignore[arg-type]
async def lifespan(app: FastAPI) -> None:  # type: ignore[misc]
    """Manage application lifespan"""
    # Startup
    await monitoring_service.startup()
    yield
    # Shutdown
    await monitoring_service.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Hybrid Trading Monitoring Service",
    description="Production-ready monitoring service with real-time trading signals and position tracking",
    version="1.0.0",
    lifespan=lifespan,
)


# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return await monitoring_service.get_health()


# Configuration Management Endpoints
@app.get("/config")
async def get_current_config():
    """Get current global configuration"""
    from ..config.global_config import get_global_config

    config = get_global_config()
    return {
        "status": "success",
        "config": {
            "trading": asdict(config.trading),
            "technical_analysis": asdict(config.technical_analysis),
            "market_hours": asdict(config.market_hours),
            "scanner": asdict(config.scanner),
            "system": asdict(config.system),
        },
    }


@app.put("/config/technical-analysis")
async def update_technical_analysis_config(request: TechnicalAnalysisUpdateRequest) -> None:
    """Update technical analysis parameters at runtime"""
    from ..config.global_config import get_global_config

    config = get_global_config()

    # Update only provided fields
    updated_fields = {}
    if request.hanning_window_samples is not None:
        # Ensure odd number for Hanning window
        if request.hanning_window_samples % 2 == 0:
            raise HTTPException(status_code=400, detail="Hanning window samples must be odd number")
        config.technical_analysis.hanning_window_samples = request.hanning_window_samples
        updated_fields["hanning_window_samples"] = request.hanning_window_samples

    if request.peak_trough_lookahead is not None:
        config.technical_analysis.peak_trough_lookahead = request.peak_trough_lookahead
        updated_fields["peak_trough_lookahead"] = request.peak_trough_lookahead

    if request.peak_trough_min_distance is not None:
        config.technical_analysis.peak_trough_min_distance = request.peak_trough_min_distance
        updated_fields["peak_trough_min_distance"] = request.peak_trough_min_distance

    # Save configuration
    try:
        config.save()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save configuration: {str(e)}"
        ) from e

    return {  # type: ignore[return-value]
        "status": "success",
        "message": "Technical analysis configuration updated",
        "updated_fields": updated_fields,
        "current_config": asdict(config.technical_analysis),
    }


@app.put("/config/trading")
async def update_trading_config(request: TradingConfigUpdateRequest) -> None:
    """Update trading parameters at runtime"""
    from ..config.global_config import get_global_config

    config = get_global_config()

    # Update only provided fields
    updated_fields = {}
    if request.trades_per_minute_threshold is not None:
        config.trading.trades_per_minute_threshold = request.trades_per_minute_threshold
        updated_fields["trades_per_minute_threshold"] = request.trades_per_minute_threshold

    if request.min_percent_change_threshold is not None:
        config.trading.min_percent_change_threshold = request.min_percent_change_threshold
        updated_fields["min_percent_change_threshold"] = request.min_percent_change_threshold  # type: ignore[assignment]

    if request.max_stock_price is not None:
        config.trading.max_stock_price = request.max_stock_price
        updated_fields["max_stock_price"] = request.max_stock_price  # type: ignore[assignment]

    if request.family_protection_profit_threshold_percent is not None:
        config.trading.family_protection_profit_threshold_percent = (
            request.family_protection_profit_threshold_percent
        )
        updated_fields["family_protection_profit_threshold_percent"] = (
            request.family_protection_profit_threshold_percent  # type: ignore[assignment]
        )

    if request.automatic_profit_threshold_percent is not None:
        config.trading.automatic_profit_threshold_percent = (
            request.automatic_profit_threshold_percent
        )
        updated_fields["automatic_profit_threshold_percent"] = (
            request.automatic_profit_threshold_percent  # type: ignore[assignment]
        )

    if request.default_position_size_usd is not None:
        config.trading.default_position_size_usd = request.default_position_size_usd
        updated_fields["default_position_size_usd"] = request.default_position_size_usd

    if request.max_concurrent_positions is not None:
        config.trading.max_concurrent_positions = request.max_concurrent_positions
        updated_fields["max_concurrent_positions"] = request.max_concurrent_positions

    # Save configuration
    try:
        config.save()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save configuration: {str(e)}"
        ) from e

    return {  # type: ignore[return-value]
        "status": "success",
        "message": "Trading configuration updated",
        "updated_fields": updated_fields,
        "current_config": asdict(config.trading),
    }


@app.post("/config/reload")
async def reload_configuration():
    """Reload configuration from file"""
    from ..config.global_config import reload_global_config

    try:
        config = reload_global_config()
        return {
            "status": "success",
            "message": "Configuration reloaded from file",
            "timestamp": datetime.now(UTC).isoformat(),
            "config": {
                "trading": asdict(config.trading),
                "technical_analysis": asdict(config.technical_analysis),
                "market_hours": asdict(config.market_hours),
                "scanner": asdict(config.scanner),
                "system": asdict(config.system),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reload configuration: {str(e)}"
        ) from e


@app.get("/status")
async def get_status():
    """Get detailed service status with watchlist and signals"""
    try:
        # Get basic status - we'll build the required fields first
        uptime_seconds = (
            time.time() - monitoring_service.start_time.timestamp()
            if monitoring_service.start_time
            else 0
        )
        watchlist_size = (
            len(monitoring_service.watchlist) if isinstance(monitoring_service, Position) else 0
        )

        # Get positions count using direct Alpaca client
        active_positions = 0
        try:
            from ..config.settings import get_trading_client

            client = get_trading_client()
            positions = client.get_all_positions()
            active_positions = len(positions) if positions else 0
        except (ConnectionError, TimeoutError, Exception) as e:
            logger.debug(f"Error getting positions count: {e}")
            active_positions = 0

        # Get signals count
        signals_detected_today = 0
        try:
            temp_signals = await monitoring_service.get_signals()
            signals_detected_today = len(temp_signals.get("current_signals", []))
        except (ValueError, IndexError, AttributeError) as e:
            logger.debug(f"Error in extract operation: {e}")

        status = ServiceStatus(
            active=monitoring_service.active,
            start_time=monitoring_service.start_time,
            last_check=monitoring_service.last_check,
            watchlist_size=watchlist_size,
            active_positions=active_positions,
            signals_detected_today=signals_detected_today,
            uptime_seconds=uptime_seconds,
            check_count=monitoring_service.check_count,
            error_count=monitoring_service.error_count,
        )

        # Get positions safely using direct Alpaca client like get_positions tool
        positions_data = {"count": 0, "symbols": [], "total_value": 0, "total_pnl": 0}
        try:
            from ..config.settings import get_trading_client

            client = get_trading_client()
            positions = client.get_all_positions()

            if positions:
                positions_data = {
                    "count": len(positions),
                    "symbols": [p.symbol for p in positions],  # type: ignore[union-attr]
                    "total_value": sum(float(p.market_value or 0) for p in positions),  # type: ignore[misc,union-attr]
                    "total_pnl": sum(float(p.unrealized_pl or 0) for p in positions),  # type: ignore[misc,union-attr]
                }
        except Exception as e:
            print(f"Position error: {e}")

        # Get signals safely
        signals_data = await monitoring_service.get_signals()

        # Get watchlist data safely
        watchlist_data = await monitoring_service.get_watchlist()

    except Exception as e:
        return {
            "error": f"Failed to get service status: {str(e)}",
            "service_status": {"active": False, "error": str(e)},
            "watchlist": {"symbols": [], "total_count": 0},
            "fresh_signals": {"signals": [], "count": 0},
            "positions": {"count": 0, "symbols": [], "total_value": 0, "total_pnl": 0},
            "summary": {"watchlist_size": 0, "active_positions": 0, "fresh_signals": 0},
        }

    # Use enhanced watchlist analysis data if available
    watchlist_with_analysis = watchlist_data.get("analysis", [])

    # If no analysis data available, fall back to basic symbol list
    if not watchlist_with_analysis:
        watchlist_with_analysis = []
        for symbol in watchlist_data.get("watchlist", []):
            watchlist_with_analysis.append(
                {
                    "symbol": symbol,
                    "latest_signal": "N/A",
                    "bars_ago": "N/A",
                    "signal_price": "N/A",
                    "current_price": "N/A",
                    "status": "monitoring",
                    "scanner_rank": "N/A",
                }
            )

    # Extract fresh signals from watchlist analysis data
    fresh_signals = []
    from ..config.global_config import get_technical_config

    tech_config = get_technical_config()
    fresh_threshold = tech_config.hanning_window_samples

    for symbol_data in watchlist_with_analysis:
        bars_ago = symbol_data.get("bars_ago")
        signal_type = symbol_data.get("signal_type", "none")

        # Only include signals that are truly fresh (≤ hanning window threshold)
        if (
            bars_ago != "N/A"
            and isinstance(bars_ago, int)
            and bars_ago <= fresh_threshold
            and signal_type in ["trough", "peak"]
        ):

            # Determine action based on signal type
            if signal_type == "trough":
                action = "buy_candidate"
                display_type = "fresh_trough"
            elif signal_type == "peak":
                action = "sell_candidate"
                display_type = "fresh_peak"
            else:
                continue

            fresh_signals.append(
                {
                    "symbol": symbol_data.get("symbol"),
                    "price": symbol_data.get("signal_price", 0),
                    "signal_type": display_type,
                    "bars_ago": bars_ago,
                    "timestamp": datetime.now(
                        UTC
                    ).isoformat(),  # Use current time since these are live
                    "action": action,
                    "current_price": symbol_data.get("current_price", 0),
                }
            )

    # Sort by bars_ago (freshest first) then by symbol
    fresh_signals.sort(key=lambda x: (x.get("bars_ago", 999), x.get("symbol", "")))
    fresh_signals = fresh_signals[:20]

    # Get auto-trader status
    auto_trader_status = await monitoring_service.get_auto_trading_status()

    return {
        "service_status": {
            "active": status.active,
            "start_time": status.start_time.isoformat() if status.start_time else None,
            "last_check": status.last_check.isoformat() if status.last_check else None,
            "uptime_seconds": status.uptime_seconds,
            "check_count": status.check_count,
            "error_count": status.error_count,
        },
        "watchlist": {
            "symbols": watchlist_with_analysis,
            "total_count": len(watchlist_with_analysis),
            "limit": watchlist_data.get("limit", 20),
            "last_updated": watchlist_data.get("last_updated"),
        },
        "fresh_signals": {
            "signals": fresh_signals,
            "count": len(fresh_signals),
            "last_updated": signals_data.get("last_updated"),
        },
        "positions": {
            "count": positions_data.get("count", 0),
            "symbols": positions_data.get("symbols", []),
            "total_value": positions_data.get("total_value", 0),
            "total_pnl": positions_data.get("total_pnl", 0),
        },
        "auto_trader": auto_trader_status,
        "summary": {
            "watchlist_size": len(watchlist_with_analysis),
            "active_positions": positions_data.get("count", 0),
            "fresh_signals": len(fresh_signals),
            "signals_detected_today": len(signals_data.get("current_signals", [])),
            "auto_trader_enabled": auto_trader_status.get("enabled", False),
        },
    }


@app.post("/stats/recalculate")
async def recalculate_stats():
    """Recalculate statistics from actual Alpaca API order history"""
    if isinstance(monitoring_service, Position) and monitoring_service.auto_trader:
        result = await monitoring_service.auto_trader.recalculate_statistics_from_api()
        return result
    else:
        return {"status": "error", "message": "AutoTrader not available"}


@app.get("/status/html", response_class=HTMLResponse)
async def get_status_html():
    """Server-rendered HTML status page with live data"""

    # Get all data server-side using the same endpoint as /status
    try:
        # Call the get_status endpoint directly to get properly formatted data
        status_response = await get_status()

        service_status = status_response["service_status"]
        auto_trader = status_response["auto_trader"]
        watchlist = status_response["watchlist"]
        fresh_signals = status_response["fresh_signals"]
        positions = status_response["positions"]
        error_msg = ""
    except Exception as e:
        # Fallback data if status fails
        service_status = {"active": True, "uptime_seconds": 0, "check_count": 0, "error_count": 1}
        auto_trader = {"enabled": False, "profit_required_symbols": [], "profit_required_count": 0}
        watchlist = {"symbols": [], "total_count": 0}
        fresh_signals = {"signals": [], "count": 0}
        positions = {"count": 0, "symbols": []}
        error_msg = f"<p style='color: #f44;'>⚠️ Error: {str(e)}</p>"

    # Simple HTML generation
    current_time = get_eastern_time_string("%Y-%m-%d %H:%M:%S %Z")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>FastAPI Trading Monitor - Live Status</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {{ font-family: monospace; background: #000; color: #0f0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #0f0; border-radius: 5px; }}
        .header {{ color: #ff0; font-size: 20px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px; text-align: left; border: 1px solid #333; }}
        th {{ background: #333; color: #ff0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">🚀 FASTAPI TRADING MONITOR - LIVE STATUS 🚀</div>
        <p>Last Updated: {current_time} | Auto-refresh: 30 seconds</p>

        <div class="section">
            <h3>📊 SERVICE STATUS</h3>
            {error_msg}
            <p>🟢 Active: {'YES' if service_status.get('active', False) else 'NO'}</p>
            <p>⏱️ Uptime: {int(service_status.get('uptime_seconds', 0))}s</p>
            <p>🔄 Check Count: {service_status.get('check_count', 0)}</p>
            <p>🤖 Auto-Trading: <strong style="color: {'#0f0' if auto_trader.get('enabled', False) else '#f44'};">{'ENABLED' if auto_trader.get('enabled', False) else 'DISABLED'}</strong></p>
            <p>🛡️ Profit Required: {auto_trader.get('profit_required_count', 0)} symbols</p>
        </div>

        <div class="section">
            <h3>👁️ WATCHLIST ({watchlist.get('total_count', 0)} symbols)</h3>
            {''.join([f'<p>📊 {symbol.get("symbol", "N/A")}: <span style="color: {get_signal_color(symbol.get("latest_signal", ""), symbol.get("bars_ago", 0))}">{symbol.get("latest_signal", "N/A")}</span> ({symbol.get("bars_ago", "N/A")} bars ago) @ ${symbol.get("current_price", "N/A")}</p>' for symbol in watchlist.get("symbols", [])]) if watchlist.get('symbols') else '<p>No symbols in watchlist</p>'}
        </div>

        <div class="section">
            <h3>🎯 FRESH TRADING SIGNALS ({fresh_signals.get("count", 0)} signals)</h3>
            {''.join([f'<p>🚀 <strong>{signal.get("symbol")}</strong>: <span style="color: {get_signal_color(signal.get("signal_type", ""), signal.get("bars_ago", 0))}">{signal.get("signal_type")}</span> at ${signal.get("price", 0):.4f} ({signal.get("bars_ago")} bars ago) - <span style="color: {"#f44" if "sell" in signal.get("action", "").lower() else "#0f0"}">{signal.get("action", "").upper()}</span></p>' for signal in fresh_signals.get("signals", [])]) if fresh_signals.get('count', 0) > 0 else '<p>No fresh trading signals</p>'}
        </div>

        <div class="section">
            <h3>💰 POSITIONS ({positions.get("count", 0)} active)</h3>
            {''.join([f'<p>💰 {symbol}</p>' for symbol in positions.get("symbols", [])]) if positions.get('count', 0) > 0 else '<p>No active positions</p>'}
            {f'<p>💵 Total Value: ${positions.get("total_value", 0):,.2f} | <span style="color: {"#f44" if positions.get("total_pnl", 0) < 0 else "#0f0"}">P&L: ${positions.get("total_pnl", 0):,.2f}</span></p>' if positions.get('count', 0) > 0 else ''}
        </div>

        <div class="section">
            <h3>🛡️ PROFIT REQUIRED SYMBOLS ({auto_trader.get('profit_required_count', 0)})</h3>
            {''.join([f'<p>🔒 {symbol}</p>' for symbol in auto_trader.get("profit_required_symbols", [])]) if auto_trader.get('profit_required_count', 0) > 0 else '<p>No symbols require profit before re-buy</p>'}
        </div>

        <div class="section">
            <h3>📈 AUTO-TRADER CONFIG</h3>
            <p>💵 Position Size: ${auto_trader.get('config', {}).get('position_size_usd', 'N/A'):,}</p>
            <p>🔢 Max Positions: {auto_trader.get('config', {}).get('max_positions', 'N/A')}</p>
            <p>💲 Max Stock Price: ${auto_trader.get('config', {}).get('max_stock_price', 'N/A')}</p>
            <p>🛡️ Never Sell Loss: {auto_trader.get('config', {}).get('never_sell_for_loss', 'N/A')}</p>
        </div>

        <div class="section">
            <h3>📊 STATISTICS</h3>
            <p>📈 Orders Placed: {auto_trader.get('stats', {}).get('orders_placed', 0)}</p>
            <p>✅ Orders Filled: {auto_trader.get('stats', {}).get('orders_filled', 0)}</p>
            <p>📈 Positions Opened: {auto_trader.get('stats', {}).get('positions_opened', 0)}</p>
            <p>💰 Positions Closed: {auto_trader.get('stats', {}).get('positions_closed', 0)}</p>
            <p>💵 Total Realized P&L: ${auto_trader.get('stats', {}).get('total_realized_pnl', 0):,.2f}</p>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content)


@app.get("/hibernation")
async def get_hibernation_status():
    """Get current hibernation status and resource optimization info"""
    return await monitoring_service.get_hibernation_status()


# Watchlist Management
@app.get("/watchlist")
async def get_watchlist():
    """Get current watchlist"""
    return await monitoring_service.get_watchlist()


@app.post("/watchlist/add")
async def add_symbols(request: AddSymbolsRequest) -> Any:
    """Add symbols to watchlist"""
    return await monitoring_service.add_symbols(request.symbols)


@app.post("/watchlist/remove")
async def remove_symbols(request: RemoveSymbolsRequest) -> Any:
    """Remove symbols from watchlist"""
    return await monitoring_service.remove_symbols(request.symbols)


@app.post("/watchlist/sync")
async def sync_watchlist_with_scanner(request: ScanSyncRequest) -> Any:
    """Sync watchlist with active scanner results"""
    scan_params = {
        "min_trades_per_minute": request.min_trades_per_minute,
        "min_percent_change": request.min_percent_change,
        "max_symbols": request.max_symbols,
        "force_update": request.force_update,
    }
    return await monitoring_service.sync_with_scanner_results(scan_params)


# Auto-trading Management
@app.post("/auto-trading/enable")
async def enable_auto_trading():
    """Enable automated trading with fresh signal execution"""
    return await monitoring_service.enable_auto_trading()


@app.post("/auto-trading/disable")
async def disable_auto_trading():
    """Disable automated trading"""
    return await monitoring_service.disable_auto_trading()


@app.get("/auto-trading/status")
async def get_auto_trading_status():
    """Get current auto trading status"""
    return await monitoring_service.get_auto_trading_status()


@app.post("/auto-trading/process-signal")
async def process_signal_for_trading(signal: dict) -> Any:
    """Process a fresh signal for automated trading"""
    return await monitoring_service.process_fresh_signal_for_trading(signal)


@app.get("/auto-trading/profit-required")
async def get_profit_required_symbols():
    """Get symbols that must sell for profit before buying again"""
    if isinstance(monitoring_service, Position) and monitoring_service.auto_trader:
        return await monitoring_service.auto_trader.get_profit_required_symbols()
    return {"symbols": [], "count": 0, "message": "Auto trader not available"}


@app.post("/auto-trading/profit-required/clear/{symbol}")
async def clear_profit_requirement(symbol: str) -> Any:
    """Manual override: Clear profit requirement for a symbol (USER CONTROL)"""
    if isinstance(monitoring_service, Position) and monitoring_service.auto_trader:
        return await monitoring_service.auto_trader.clear_profit_requirement(symbol.upper())
    return {"status": "error", "message": "Auto trader not available"}


@app.post("/auto-trading/profit-required/add/{symbol}")
async def add_profit_requirement(symbol: str) -> Any:
    """Manual control: Add symbol to profit requirement list"""
    if isinstance(monitoring_service, Position) and monitoring_service.auto_trader:
        return await monitoring_service.auto_trader.add_profit_requirement(symbol.upper())
    return {"status": "error", "message": "Auto trader not available"}


# Application startup
monitoring_service = MonitoringServiceAPI()


if __name__ == "__main__":
    uvicorn.run("fastapi_service:app", host="0.0.0.0", port=8001, reload=False, log_level="info")
