"""Core business logic services for the FastAPI monitoring service."""

import logging
from datetime import datetime
from typing import Optional

from ....config import get_scanner_config, get_system_config, get_trading_config
from ...alert_system import AlertSystem
from ...auto_trader import AutoTrader
from ...desktop_notifications import DesktopNotificationService
from ...hybrid_service import ServiceConfig, ServiceStatus
from ...position_tracker import PositionTracker
from ...signal_detector import SignalDetector
from ...streaming_integration import AlpacaStreamingService
from ...trade_confirmation import TradeConfirmationService
from ..models import TechnicalAnalysisUpdateRequest, TradingConfigUpdateRequest


def get_signal_color(signal_type: str, bars_ago: int) -> str:
    """Get color for signal based on type and staleness

    Returns:
        - Green (#0f0): Fresh trough signals (≤11 bars ago) - BUY
        - Red (#f44): Fresh peak signals (≤11 bars ago) - SELL
        - Orange (#ff8c00): Stale signals (>11 bars ago) - WARNING/OLD
    """
    if bars_ago > 11:
        return "#ff8c00"

    if "peak" in signal_type.lower():
        return "#f44"
    else:
        return "#0f0"


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

        # Initialize core components
        self.position_tracker = PositionTracker()
        self.signal_detector = SignalDetector()
        self.alert_system = AlertSystem()
        self.desktop_notifications = DesktopNotificationService()
        self.trade_confirmation = TradeConfirmationService(self.desktop_notifications)

        # Initialize auto trader lazily to avoid async issues
        self.auto_trader = None
        self._auto_trader_initialized = False

        # Optional streaming (may not be available)
        self.streaming_service: AlpacaStreamingService | None = None

        # Initialize state
        self.watchlist: set = set()
        self.current_signals = {}
        self.auto_scan_enabled = False
        self.auto_scan_task = None

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the service"""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _ensure_auto_trader(self):
        """Initialize auto trader if not already done"""
        if not self._auto_trader_initialized:
            try:
                self.auto_trader = AutoTrader()
                self._auto_trader_initialized = True
                self.logger.info("AutoTrader initialized successfully")
            except Exception as e:
                self.logger.warning(f"AutoTrader initialization failed: {e}")
                self.auto_trader = None
                self._auto_trader_initialized = True

    async def start_monitoring(self, **kwargs):
        """Start the monitoring service"""
        if self.active:
            return {"status": "already_running", "message": "Service already active"}

        try:
            self.active = True
            self.start_time = datetime.now()
            self.check_count = 0
            self.error_count = 0

            self.logger.info("Monitoring service started")

            return {
                "status": "success",
                "message": "Monitoring service started successfully",
                "start_time": self.start_time.isoformat(),
                "config": {
                    "check_interval": kwargs.get("check_interval", 2),
                    "max_concurrent_positions": kwargs.get("max_concurrent_positions", 5),
                    "signal_confidence_threshold": kwargs.get("signal_confidence_threshold", 0.75),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to start monitoring service: {e}")
            self.active = False
            return {"status": "error", "message": f"Failed to start: {str(e)}"}

    async def stop_monitoring(self):
        """Stop the monitoring service"""
        if not self.active:
            return {"status": "not_running", "message": "Service not active"}

        try:
            self.active = False
            if self.auto_scan_task:
                self.auto_scan_task.cancel()
                self.auto_scan_task = None

            self.logger.info("Monitoring service stopped")

            return {"status": "success", "message": "Monitoring service stopped successfully"}

        except Exception as e:
            self.logger.error(f"Error stopping monitoring service: {e}")
            return {"status": "error", "message": f"Failed to stop: {str(e)}"}

    def get_status(self):
        """Get current service status"""
        return {
            "active": self.active,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "check_count": self.check_count,
            "error_count": self.error_count,
            "watchlist_size": len(self.watchlist),
            "auto_scan_enabled": self.auto_scan_enabled,
            "auto_trader_enabled": (
                getattr(self.auto_trader, "enabled", False) if self.auto_trader else False
            ),
        }

    async def update_technical_config(self, request: TechnicalAnalysisUpdateRequest):
        """Update technical analysis configuration"""
        try:
            from ....config.global_config import get_global_config

            config = get_global_config()
            updates = {}

            if request.hanning_window_samples is not None:
                if request.hanning_window_samples % 2 == 0:
                    raise ValueError("Hanning window samples must be odd")
                config.technical_analysis.hanning_window_samples = request.hanning_window_samples
                updates["hanning_window_samples"] = request.hanning_window_samples

            if request.peak_trough_lookahead is not None:
                config.technical_analysis.peak_trough_lookahead = request.peak_trough_lookahead
                updates["peak_trough_lookahead"] = request.peak_trough_lookahead

            if request.peak_trough_min_distance is not None:
                config.technical_analysis.peak_trough_min_distance = (
                    request.peak_trough_min_distance
                )
                updates["peak_trough_min_distance"] = request.peak_trough_min_distance

            # Save configuration changes
            config.save()

            return {
                "status": "success",
                "message": "Technical analysis configuration updated",
                "updates": updates,
            }

        except Exception as e:
            self.logger.error(f"Failed to update technical config: {e}")
            return {"status": "error", "message": str(e)}

    async def update_trading_config(self, request: TradingConfigUpdateRequest):
        """Update trading configuration"""
        try:
            from ....config.global_config import get_global_config

            config = get_global_config()
            updates = {}

            if request.trades_per_minute_threshold is not None:
                config.trading.trades_per_minute_threshold = request.trades_per_minute_threshold
                updates["trades_per_minute_threshold"] = request.trades_per_minute_threshold

            if request.min_percent_change_threshold is not None:
                config.trading.min_percent_change_threshold = request.min_percent_change_threshold
                updates["min_percent_change_threshold"] = request.min_percent_change_threshold

            if request.max_stock_price is not None:
                config.trading.max_stock_price = request.max_stock_price
                updates["max_stock_price"] = request.max_stock_price

            if request.family_protection_profit_threshold_percent is not None:
                config.trading.family_protection_profit_threshold_percent = (
                    request.family_protection_profit_threshold_percent
                )
                updates["family_protection_profit_threshold_percent"] = (
                    request.family_protection_profit_threshold_percent
                )

            if request.automatic_profit_threshold_percent is not None:
                config.trading.automatic_profit_threshold_percent = (
                    request.automatic_profit_threshold_percent
                )
                updates["automatic_profit_threshold_percent"] = (
                    request.automatic_profit_threshold_percent
                )

            if request.default_position_size_usd is not None:
                config.trading.default_position_size_usd = request.default_position_size_usd
                updates["default_position_size_usd"] = request.default_position_size_usd

            if request.max_concurrent_positions is not None:
                config.trading.max_concurrent_positions = request.max_concurrent_positions
                updates["max_concurrent_positions"] = request.max_concurrent_positions

            # Save configuration changes
            config.save()

            return {
                "status": "success",
                "message": "Trading configuration updated",
                "updates": updates,
            }

        except Exception as e:
            self.logger.error(f"Failed to update trading config: {e}")
            return {"status": "error", "message": str(e)}

    async def get_watchlist_with_analysis(self):
        """Get current watchlist with peak/trough analysis"""
        try:
            from ....config.global_config import get_technical_config
            from ....tools.peak_trough_analysis_tool import analyze_peaks_and_troughs_with_plot_py

            watchlist_analysis = []
            tech_config = get_technical_config()

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

            return {
                "watchlist": sorted(self.watchlist),
                "size": len(self.watchlist),
                "limit": self.config.watchlist_size_limit,
                "last_updated": self.last_check.isoformat() if self.last_check else None,
                "analysis": watchlist_analysis,
                "symbols": watchlist_analysis,
            }

        except Exception as e:
            self.logger.error(f"Error getting watchlist analysis: {e}")
            return {
                "watchlist": sorted(self.watchlist),
                "size": len(self.watchlist),
                "error": str(e),
            }

    def _extract_watchlist_analysis(self, symbol: str, analysis: str):
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
                if "Current price:" in line or "Latest price:" in line:
                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        current_price = float(price_match.group(1))
                        break
                elif symbol in line and "CURRENT" in line.upper():
                    price_match = re.search(r"(\d+\.\d+)", line)
                    if price_match:
                        current_price = float(price_match.group(1))
                        break

            # Look for signal information
            for line in lines:
                if "signal" in line.lower() and symbol in line:
                    if "peak" in line.lower():
                        signal_type = "peak"
                        latest_signal = "SELL Signal"
                    elif "trough" in line.lower():
                        signal_type = "trough"
                        latest_signal = "BUY Signal"

                    # Extract bars ago
                    bars_match = re.search(r"(\d+)\s*bars?\s*ago", line)
                    if bars_match:
                        bars_ago = int(bars_match.group(1))

                    # Extract signal price
                    price_match = re.search(r"\$?(\d+\.\d+)", line)
                    if price_match:
                        signal_price = float(price_match.group(1))
                    break

            return {
                "symbol": symbol,
                "latest_signal": latest_signal,
                "signal_type": signal_type,
                "bars_ago": bars_ago,
                "signal_price": signal_price,
                "current_price": current_price,
                "analysis_status": "✅ Analyzed",
                "scanner_rank": "N/A",
            }

        except Exception as e:
            self.logger.error(f"Error extracting analysis for {symbol}: {e}")
            return {
                "symbol": symbol,
                "latest_signal": "Parse Error",
                "signal_type": "error",
                "bars_ago": 999,
                "signal_price": 0.0,
                "current_price": 0.0,
                "analysis_status": "❌ Parse Error",
                "scanner_rank": "N/A",
            }
