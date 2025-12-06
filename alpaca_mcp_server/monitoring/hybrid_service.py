"""Core Hybrid Trading Service

Provides genuine automated monitoring that runs independently of Claude,
using existing MCP tools for signal detection and position tracking.
"""

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .alert_system import AlertSystem
from .position_tracker import PositionTracker
from .signal_detector import SignalDetector


@dataclass
class ServiceConfig:
    """Configuration for the hybrid trading service"""

    check_interval: int = 60  # seconds between monitoring cycles
    signal_confidence_threshold: float = 0.0
    max_concurrent_positions: int = 5
    watchlist_size_limit: int = 50
    enable_auto_alerts: bool = True
    state_file: str = "hybrid_service_state.json"
    log_file: str = "hybrid_monitoring.log"
    alert_channels: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.alert_channels is None:
            self.alert_channels = ["file", "console"]


@dataclass
class ServiceStatus:
    """Current status of the hybrid service"""

    active: bool
    start_time: datetime | None
    last_check: datetime | None
    watchlist_size: int
    active_positions: int
    signals_detected_today: int
    uptime_seconds: float
    check_count: int
    error_count: int


class HybridTradingService:
    """
    Core hybrid trading service that provides genuine automated monitoring.

    This service runs independently of Claude and provides:
    - Real-time position tracking via WebSocket
    - Automated signal detection using existing MCP tools
    - Multi-channel alerting system
    - Verifiable audit trail
    - JSON-based communication with Claude
    """

    def __init__(self, config: ServiceConfig | None = None):
        self.config = config or ServiceConfig()
        self.logger = self._setup_logging()

        # Service state
        self.active = False
        self.start_time: datetime | None = None
        self.last_check: datetime | None = None
        self.check_count = 0
        self.error_count = 0

        # Components
        self.position_tracker: PositionTracker | None = None
        self.signal_detector: SignalDetector | None = None
        self.alert_system: AlertSystem | None = None

        # Monitoring state
        self.watchlist: set[str] = set()
        self.current_signals: list[dict] = []
        self.signal_history: list[dict] = []
        self.monitoring_task: asyncio.Task | None = None

        # Communication files
        self.state_dir = Path("monitoring_data")
        self.state_dir.mkdir(exist_ok=True)

        self.logger.info("HybridTradingService initialized")

    def _setup_logging(self) -> logging.Logger:
        """Set up structured logging for audit trail"""
        logger = logging.getLogger("hybrid_trading_service")
        logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # File handler for permanent audit trail
        log_path = Path(self.config.log_file)
        fh = logging.FileHandler(log_path)
        fh.setLevel(logging.INFO)

        # Console handler for real-time monitoring
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)

        # Structured formatter for audit compliance
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    async def start_service(self) -> dict:
        """Start the hybrid trading service"""
        if self.active:
            return {"status": "error", "message": "Service already active"}

        try:
            self.logger.info("🚀 Starting Hybrid Trading Service")

            # Initialize components
            self.position_tracker = PositionTracker()
            self.signal_detector = SignalDetector()
            self.alert_system = AlertSystem(self.config.alert_channels)

            # Load previous state if exists
            await self._load_state()

            # Mark service as active
            self.active = True
            self.start_time = datetime.now(UTC)
            self.last_check = None
            self.check_count = 0
            self.error_count = 0

            # CRITICAL: Check positions immediately on startup
            if self.position_tracker:
                await self.position_tracker.update_positions()
                initial_position_count = len(self.position_tracker.positions)
                self._last_position_count = initial_position_count

                if initial_position_count > 0:
                    position_symbols = list(self.position_tracker.positions.keys())
                    self.logger.warning(
                        f"🔔 STARTUP: Found {initial_position_count} existing positions: {position_symbols}"
                    )

                    # Alert Claude about existing positions
                    await self.alert_system.send_alert(
                        "📊 Existing Positions Detected at Startup",
                        f"Found {initial_position_count} open positions: {', '.join(position_symbols)}",
                        priority="high",
                    )
                else:
                    self.logger.info("✅ STARTUP: No existing positions found")

            # Start monitoring task
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

            # Send startup alert
            await self.alert_system.send_alert(
                "🚀 Hybrid Trading Service STARTED",
                "Genuine automated monitoring is now active",
                priority="info",
            )

            # Save initial state
            await self._save_state()

            # Register global service instance for tool access
            set_service_instance(self)

            self.logger.info("✅ Hybrid Trading Service started successfully")

            return {
                "status": "success",
                "message": "Hybrid trading service started",
                "start_time": self.start_time.isoformat(),
                "config": asdict(self.config),
                "state_file": str(self.state_dir / self.config.state_file),
            }

        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            self.active = False
            return {"status": "error", "message": f"Service startup failed: {e}"}

    async def stop_service(self) -> dict:
        """Stop the hybrid trading service gracefully"""
        if not self.active:
            return {"status": "error", "message": "Service not active"}

        try:
            self.logger.info("🛑 Stopping Hybrid Trading Service")

            # Mark as inactive
            self.active = False

            # Cancel monitoring task
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.monitoring_task

            # Clean shutdown of components
            if self.position_tracker:
                await self.position_tracker.stop()

            # Save final state
            await self._save_state()

            # Send shutdown alert
            if self.alert_system:
                uptime = time.time() - self.start_time.timestamp()  # type: ignore[union-attr]
                await self.alert_system.send_alert(
                    "🛑 Hybrid Trading Service STOPPED",
                    f"Service stopped after {uptime:.0f} seconds uptime. "
                    f"Completed {self.check_count} monitoring cycles.",
                    priority="warning",
                )

            self.logger.info("✅ Hybrid Trading Service stopped gracefully")

            return {
                "status": "success",
                "message": "Service stopped gracefully",
                "uptime_seconds": time.time() - self.start_time.timestamp(),  # type: ignore[union-attr]
                "final_check_count": self.check_count,
                "final_error_count": self.error_count,
            }

        except Exception as e:
            self.logger.error(f"Error during service shutdown: {e}")
            return {"status": "error", "message": f"Shutdown error: {e}"}

    async def get_status(self) -> ServiceStatus:
        """Get current service status"""
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
                    if s.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))
                ]
            ),
            uptime_seconds=uptime,
            check_count=self.check_count,
            error_count=self.error_count,
        )

    async def add_to_watchlist(self, symbols: list[str]) -> dict:
        """Add symbols to monitoring watchlist"""
        try:
            added = []
            for symbol in symbols:
                symbol = symbol.upper().strip()
                if len(self.watchlist) >= self.config.watchlist_size_limit:
                    break
                if symbol not in self.watchlist:
                    self.watchlist.add(symbol)
                    added.append(symbol)

            if added:
                await self._save_state()
                self.logger.info(f"Added to watchlist: {added}")

                if self.alert_system:
                    await self.alert_system.send_alert(
                        "📊 Watchlist Updated",
                        f"Added symbols: {', '.join(added)}. Total watchlist: {len(self.watchlist)}",
                        priority="info",
                    )

            return {
                "status": "success",
                "added": added,
                "watchlist_size": len(self.watchlist),
                "current_watchlist": sorted(self.watchlist),
            }

        except Exception as e:
            self.logger.error(f"Error adding to watchlist: {e}")
            return {"status": "error", "message": str(e)}

    async def remove_from_watchlist(self, symbols: list[str]) -> dict:
        """Remove symbols from monitoring watchlist"""
        try:
            removed = []
            for symbol in symbols:
                symbol = symbol.upper().strip()
                if symbol in self.watchlist:
                    self.watchlist.remove(symbol)
                    removed.append(symbol)

            if removed:
                await self._save_state()
                self.logger.info(f"Removed from watchlist: {removed}")

                if self.alert_system:
                    await self.alert_system.send_alert(
                        "📊 Watchlist Updated",
                        f"Removed symbols: {', '.join(removed)}. Total watchlist: {len(self.watchlist)}",
                        priority="info",
                    )

            return {
                "status": "success",
                "removed": removed,
                "watchlist_size": len(self.watchlist),
                "current_watchlist": sorted(self.watchlist),
            }

        except Exception as e:
            self.logger.error(f"Error removing from watchlist: {e}")
            return {"status": "error", "message": str(e)}

    async def add_symbols_to_watchlist(self, symbols: list[str]) -> dict:
        """Add symbols to the monitoring watchlist"""
        try:
            added = []

            for symbol in symbols:
                symbol = symbol.upper().strip()
                if symbol not in self.watchlist:
                    if len(self.watchlist) >= self.config.watchlist_size_limit:
                        self.logger.warning(
                            f"Watchlist limit reached ({self.config.watchlist_size_limit}). Cannot add {symbol}"
                        )
                        break

                    self.watchlist.add(symbol)
                    added.append(symbol)

            if added:
                await self._save_state()
                self.logger.info(f"Added to watchlist: {added}")

                if self.alert_system:
                    await self.alert_system.send_alert(
                        "📊 Watchlist Updated",
                        f"Added symbols: {', '.join(added)}. Total watchlist: {len(self.watchlist)}",
                        priority="info",
                    )

            return {
                "status": "success",
                "added": added,
                "watchlist_size": len(self.watchlist),
                "current_watchlist": sorted(self.watchlist),
            }

        except Exception as e:
            self.logger.error(f"Error adding to watchlist: {e}")
            return {"status": "error", "message": str(e)}

    async def get_current_signals(self) -> list[dict]:
        """Get current trading signals"""
        return self.current_signals.copy()

    async def check_positions_after_order(self, order_info: dict = None) -> dict:  # type: ignore[assignment]
        """
        Check positions immediately after an order is processed.
        This ensures Claude gets immediate feedback on position changes.
        """
        if not self.position_tracker:
            return {"status": "error", "message": "Position tracker not available"}

        try:
            # Force immediate position update
            await self.position_tracker.update_positions()
            position_count = len(self.position_tracker.positions)
            position_symbols = list(self.position_tracker.positions.keys())

            # Log the check for Claude awareness
            if order_info:
                self.logger.warning(
                    f"🔔 POST-ORDER CHECK: After {order_info.get('action', 'order')}, found {position_count} positions: {position_symbols}"
                )
            else:
                self.logger.warning(
                    f"🔔 POSITION CHECK: Currently {position_count} positions: {position_symbols}"
                )

            # Send alert about current position status
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
        self.logger.info("🔄 Starting monitoring loop")

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
                    await self.alert_system.send_alert(  # type: ignore[union-attr]
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

        # Log heartbeat every 100 cycles with position summary
        if self.check_count % 100 == 0:
            position_count = len(self.position_tracker.positions) if self.position_tracker else 0
            self.logger.info(
                f"💓 Heartbeat - Cycle {self.check_count}, Watchlist: {len(self.watchlist)}, Positions: {position_count}"
            )

        # Update positions - CRITICAL for Claude monitoring
        if self.position_tracker:
            await self.position_tracker.update_positions()

            # Log position changes for Claude awareness
            position_count = len(self.position_tracker.positions)
            if isinstance(self, AlertSystem) and self._last_position_count != position_count:
                if position_count > self._last_position_count:
                    self.logger.warning(
                        f"🔔 NEW POSITIONS DETECTED: {position_count} total positions now active"
                    )
                elif position_count < self._last_position_count:
                    self.logger.warning(
                        f"🔔 POSITIONS CLOSED: {position_count} positions remaining (was {self._last_position_count})"
                    )

                # Alert Claude about position changes
                if self.alert_system:
                    await self.alert_system.send_alert(
                        "📊 Position Change Detected",
                        f"Position count changed from {getattr(self, '_last_position_count', 0)} to {position_count}",
                        priority="high",
                    )

            self._last_position_count = position_count

        # Detect signals for watchlist
        if self.signal_detector and self.watchlist:
            new_signals = await self.signal_detector.scan_for_signals(list(self.watchlist))

            # Process new signals
            for signal in new_signals:
                await self._process_signal(signal)

        # Save state periodically
        if self.check_count % 50 == 0:  # Every ~100 seconds
            await self._save_state()

    async def _process_signal(self, signal: dict) -> None:
        """Process a detected trading signal"""
        signal["timestamp"] = datetime.now(UTC).isoformat()
        signal["id"] = f"{signal['symbol']}_{int(time.time())}"

        # Add to current signals
        self.current_signals.append(signal)
        self.signal_history.append(signal)

        # Keep only recent signals in current list
        cutoff_time = time.time() - 3600  # 1 hour
        self.current_signals = [
            s
            for s in self.current_signals
            if datetime.fromisoformat(s["timestamp"].replace("Z", "+00:00")).timestamp()
            > cutoff_time
        ]

        # Send alert for high-confidence signals
        if signal.get("confidence", 0) >= self.config.signal_confidence_threshold:
            await self._send_signal_alert(signal)

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

        await self.alert_system.send_alert(  # type: ignore[union-attr]
            f"Trading Signal: {signal['symbol']}", message, priority="high"
        )

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

            state_file = self.state_dir / self.config.state_file
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    async def _load_state(self):
        """Load service state from disk"""
        try:
            state_file = self.state_dir / self.config.state_file
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
_service_instance: HybridTradingService | None = None


def get_service_instance() -> HybridTradingService | None:
    """Get the global service instance"""
    return _service_instance


def set_service_instance(service: HybridTradingService) -> None:
    """Set the global service instance"""
    global _service_instance
    _service_instance = service
