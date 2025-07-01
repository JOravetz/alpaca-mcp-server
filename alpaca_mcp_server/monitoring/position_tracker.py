"""Position Tracker - WebSocket-based real-time position monitoring

Uses Alpaca WebSocket trade_updates stream to track positions in real-time,
providing the foundation for genuine automated monitoring.
"""

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal

# Import existing MCP tools for position data
from ..tools.account_tools import get_positions
from ..tools.streaming_tools import get_stock_stream_data


@dataclass
class Position:
    """Represents a trading position"""

    symbol: str
    quantity: int
    entry_price: Decimal
    current_price: Decimal
    side: str  # 'long' or 'short'
    unrealized_pnl: Decimal
    unrealized_pnl_percent: float
    market_value: Decimal
    cost_basis: Decimal
    last_update: datetime
    stream_price: Decimal | None = None  # Real-time streaming price
    stream_timestamp: datetime | None = None  # Last streaming update

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": float(self.entry_price),
            "current_price": float(self.current_price),
            "side": self.side,
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_percent": self.unrealized_pnl_percent,
            "market_value": float(self.market_value),
            "cost_basis": float(self.cost_basis),
            "last_update": self.last_update.isoformat(),
            "stream_price": float(self.stream_price) if self.stream_price else None,
            "stream_timestamp": (
                self.stream_timestamp.isoformat() if self.stream_timestamp else None
            ),
        }


@dataclass
class ProfitSpikeAlert:
    """Real-time profit spike alert"""

    alert_type: str = "PROFIT_SPIKE"
    symbol: str = ""
    entry_price: float = 0.0
    current_price: float = 0.0
    stream_price: float = 0.0
    profit_percent: float = 0.0
    profit_dollar: float = 0.0
    spike_magnitude: float = 0.0  # How big the spike was
    timestamp: str = ""
    action_required: str = "CONSIDER_SELL"
    urgency: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class PositionTracker:
    """
    Real-time position tracking using WebSocket and existing MCP tools.

    This class provides genuine position monitoring by:
    1. Using existing get_positions() MCP tool for current state
    2. Planning WebSocket integration for real-time updates
    3. Maintaining position history and P&L tracking
    4. Providing alerts for significant position changes
    """

    def __init__(self):
        self.logger = logging.getLogger("position_tracker")

        # Position state
        self.positions: dict[str, Position] = {}
        self.position_history: list[dict] = []

        # Tracking state
        self.last_update: datetime | None = None
        self.update_count = 0
        self.error_count = 0

        # Alert thresholds (updated based on APVO session learning)
        self.profit_alert_threshold = 0.05  # 5% profit (substantial profit threshold)
        self.major_profit_threshold = 0.10  # 10% profit (urgent sell consideration)
        self.loss_alert_threshold = -0.05  # 5% loss

        # Callbacks for position changes
        self.position_callbacks: list[Callable] = []

        self.logger.info("PositionTracker initialized")

    async def start(self):
        """Start position tracking"""
        self.logger.info("🎯 Starting position tracking")
        await self.update_positions()

    async def stop(self):
        """Stop position tracking"""
        self.logger.info("🛑 Stopping position tracking")
        # Future: Close WebSocket connections here

    async def update_positions(self):
        """Update positions using existing MCP tools"""
        try:
            self.last_update = datetime.now(UTC)
            self.update_count += 1

            # Use existing MCP tool to get current positions
            positions_result = await get_positions()

            # Parse string response from MCP tool
            if isinstance(positions_result, str):
                await self._parse_positions_string(positions_result)
            elif isinstance(positions_result, dict) and positions_result.get("status") == "success":
                positions_data = positions_result.get("positions", [])
                await self._process_position_data(positions_data)
            else:
                self.logger.warning(f"Failed to get positions: {positions_result}")

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error updating positions: {e}")
            raise

    async def _parse_positions_string(self, positions_string: str):
        """Parse positions from string response"""
        try:
            import re

            # Extract position data from string format
            if "Symbol:" in positions_string and "Quantity:" in positions_string:
                lines = positions_string.split("\n")
                current_position = {}

                for line in lines:
                    line = line.strip()
                    if line.startswith("Symbol:"):
                        current_position["symbol"] = line.split("Symbol:")[1].strip()
                    elif line.startswith("Quantity:"):
                        qty_match = re.search(r"(\d+)", line)
                        if qty_match:
                            current_position["qty"] = qty_match.group(1)
                    elif line.startswith("Average Entry Price:"):
                        price_match = re.search(r"\$([0-9.]+)", line)
                        if price_match:
                            current_position["avg_entry_price"] = price_match.group(1)
                    elif line.startswith("Current Price:"):
                        price_match = re.search(r"\$([0-9.]+)", line)
                        if price_match:
                            current_position["current_price"] = price_match.group(1)
                    elif line.startswith("Market Value:"):
                        value_match = re.search(r"\$([0-9.]+)", line)
                        if value_match:
                            current_position["market_value"] = value_match.group(1)
                    elif line.startswith("Unrealized P/L:"):
                        # Extract both dollar amount and percentage
                        pnl_match = re.search(r"\$([0-9.-]+)", line)
                        pct_match = re.search(r"\(([0-9.-]+)%\)", line)
                        if pnl_match:
                            current_position["unrealized_pl"] = pnl_match.group(1)
                        if pct_match:
                            current_position["unrealized_plpc"] = float(pct_match.group(1)) / 100

                # Calculate cost basis
                if all(k in current_position for k in ["qty", "avg_entry_price"]):
                    cost_basis = float(current_position["qty"]) * float(
                        current_position["avg_entry_price"]
                    )
                    current_position["cost_basis"] = str(cost_basis)

                if current_position.get("symbol"):
                    await self._process_position_data([current_position])

            else:
                self.logger.info("No positions found")
                # Clear positions
                self.positions = {}

        except Exception as e:
            self.logger.error(f"Error parsing positions string: {e}")

    async def _process_position_data(self, positions_data: list[dict]):
        """Process position data from Alpaca API"""
        new_positions = {}

        for pos_data in positions_data:
            try:
                symbol = pos_data["symbol"]

                position = Position(
                    symbol=symbol,
                    quantity=int(pos_data["qty"]),
                    entry_price=Decimal(str(pos_data["avg_entry_price"])),
                    current_price=Decimal(str(pos_data["current_price"])),
                    side="long" if int(pos_data["qty"]) > 0 else "short",
                    unrealized_pnl=Decimal(str(pos_data["unrealized_pl"])),
                    unrealized_pnl_percent=float(pos_data["unrealized_plpc"]),
                    market_value=Decimal(str(pos_data["market_value"])),
                    cost_basis=Decimal(str(pos_data["cost_basis"])),
                    last_update=self.last_update,
                )

                new_positions[symbol] = position

                # Check for significant changes
                await self._check_position_alerts(position)

            except (KeyError, ValueError, TypeError) as e:
                self.logger.error(f"Error processing position data for {pos_data}: {e}")
                continue

        # Update positions and track changes
        old_symbols = set(self.positions.keys())
        new_symbols = set(new_positions.keys())

        # Log position changes
        added = new_symbols - old_symbols
        removed = old_symbols - new_symbols

        if added:
            self.logger.info(f"New positions opened: {added}")
        if removed:
            self.logger.info(f"Positions closed: {removed}")

        self.positions = new_positions

        # Add to history
        self.position_history.append(
            {
                "timestamp": self.last_update.isoformat(),
                "position_count": len(self.positions),
                "symbols": sorted(self.positions.keys()),
                "total_unrealized_pnl": sum(
                    float(p.unrealized_pnl) for p in self.positions.values()
                ),
            }
        )

        # Keep history manageable (last 1000 updates)
        if len(self.position_history) > 1000:
            self.position_history = self.position_history[-1000:]

        # Notify callbacks
        for callback in self.position_callbacks:
            try:
                await callback(self.positions)
            except Exception as e:
                self.logger.error(f"Error in position callback: {e}")

    async def _check_position_alerts(self, position: Position):
        """Check if position meets alert criteria"""
        pnl_percent = position.unrealized_pnl_percent

        # Update position with real-time streaming data
        await self._update_position_with_streaming_data(position)

        # ALWAYS check for profit updates regardless of threshold - JSON generation happens here
        # Check for major profit alert (urgent sell consideration)
        if pnl_percent >= self.major_profit_threshold:
            await self._trigger_major_profit_alert(position)

        # Check for profit alert
        elif pnl_percent >= self.profit_alert_threshold:
            await self._trigger_profit_alert(position)

        # Check for loss alert
        elif pnl_percent <= self.loss_alert_threshold:
            await self._trigger_loss_alert(position)

        # CRITICAL: Always update streaming data for JSON generation when profitable
        elif pnl_percent > 0:  # Any profit at all
            # This ensures JSON updates are generated for ANY profit
            pass

    async def _trigger_major_profit_alert(self, position: Position):
        """Trigger alert for major profit threshold - URGENT SELL CONSIDERATION"""
        self.logger.warning(
            f"🚨 MAJOR PROFIT ALERT - CONSIDER SELLING: {position.symbol} at +{position.unrealized_pnl_percent:.2%} "
            f"(${position.unrealized_pnl:.2f}) - BE DILIGENT ON SELLING!"
        )

        # Future: Send high-priority alerts through alert system

    async def _trigger_profit_alert(self, position: Position):
        """Trigger alert for substantial profit threshold"""
        self.logger.warning(
            f"🚀 SUBSTANTIAL PROFIT: {position.symbol} at +{position.unrealized_pnl_percent:.2%} "
            f"(${position.unrealized_pnl:.2f}) - Monitor for sell opportunity"
        )

        # Future: Send alerts through alert system

    async def _trigger_loss_alert(self, position: Position):
        """Trigger alert for loss threshold"""
        self.logger.warning(
            f"⚠️ LOSS ALERT: {position.symbol} at {position.unrealized_pnl_percent:.2%} "
            f"(${position.unrealized_pnl:.2f})"
        )

        # Future: Send alerts through alert system

    def add_position_callback(self, callback: Callable):
        """Add callback for position updates"""
        self.position_callbacks.append(callback)

    def remove_position_callback(self, callback: Callable):
        """Remove position callback"""
        if callback in self.position_callbacks:
            self.position_callbacks.remove(callback)

    def get_position(self, symbol: str) -> Position | None:
        """Get position for specific symbol"""
        return self.positions.get(symbol.upper())

    def get_all_positions(self) -> dict[str, Position]:
        """Get all current positions"""
        return self.positions.copy()

    def get_position_count(self) -> int:
        """Get number of open positions"""
        return len(self.positions)

    def get_total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L across all positions"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_total_market_value(self) -> Decimal:
        """Get total market value of all positions"""
        return sum(pos.market_value for pos in self.positions.values())

    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in symbol"""
        return symbol.upper() in self.positions

    def get_status(self) -> dict:
        """Get position tracker status"""
        return {
            "active": True,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "position_count": len(self.positions),
            "total_unrealized_pnl": float(self.get_total_unrealized_pnl()),
            "total_market_value": float(self.get_total_market_value()),
            "tracked_symbols": sorted(self.positions.keys()),
        }

    def get_positions_summary(self) -> dict:
        """Get summary of all positions for reporting"""
        if not self.positions:
            return {"message": "No open positions"}

        summary = {
            "position_count": len(self.positions),
            "total_unrealized_pnl": float(self.get_total_unrealized_pnl()),
            "total_market_value": float(self.get_total_market_value()),
            "positions": {},
        }

        for symbol, position in self.positions.items():
            summary["positions"][symbol] = {
                "quantity": position.quantity,
                "entry_price": float(position.entry_price),
                "current_price": float(position.current_price),
                "unrealized_pnl": float(position.unrealized_pnl),
                "unrealized_pnl_percent": position.unrealized_pnl_percent,
                "side": position.side,
            }

        return summary

    async def _update_position_with_streaming_data(self, position: Position):
        """Update position with real-time streaming data and check for profit spikes"""
        try:
            # Get recent streaming data for this symbol
            stream_result = await get_stock_stream_data(
                symbol=position.symbol, data_type="trades", recent_seconds=10, limit=5
            )

            if isinstance(stream_result, dict) and stream_result.get("status") == "success":
                stream_data = stream_result.get("data", [])

                if stream_data:
                    # Get the most recent trade price
                    latest_trade = stream_data[-1]  # Most recent trade
                    stream_price = Decimal(str(latest_trade.get("price", 0)))
                    stream_timestamp = datetime.now(UTC)

                    # Update position with streaming data
                    position.stream_price = stream_price
                    position.stream_timestamp = stream_timestamp

                    # Calculate profit using streaming price
                    if stream_price > 0:
                        stream_profit_dollar = (
                            stream_price - position.entry_price
                        ) * position.quantity
                        stream_profit_percent = float(
                            (stream_price - position.entry_price) / position.entry_price * 100
                        )

                        # Generate regular JSON profit updates when profitable
                        if stream_profit_percent > 0:  # ANY profit
                            await self._generate_profit_update(
                                position=position,
                                stream_price=float(stream_price),
                                stream_profit_percent=stream_profit_percent,
                                stream_profit_dollar=float(stream_profit_dollar),
                                update_type="PROFIT_UPDATE",
                            )

                        # Check for profit spike (difference between current and streaming price)
                        if position.current_price > 0:
                            price_spike = float(
                                (stream_price - position.current_price)
                                / position.current_price
                                * 100
                            )

                            # Generate JSON profit spike alert if significant spike detected
                            if (
                                abs(price_spike) >= 2.0 and stream_profit_percent >= 3.0
                            ):  # 2% price spike + 3% total profit
                                await self._generate_profit_spike_alert(
                                    position=position,
                                    stream_price=float(stream_price),
                                    stream_profit_percent=stream_profit_percent,
                                    stream_profit_dollar=float(stream_profit_dollar),
                                    spike_magnitude=price_spike,
                                )

        except Exception as e:
            self.logger.error(f"Error updating position {position.symbol} with streaming data: {e}")

    async def _generate_profit_update(
        self,
        position: Position,
        stream_price: float,
        stream_profit_percent: float,
        stream_profit_dollar: float,
        update_type: str,
    ):
        """Generate regular JSON profit update for Claude orchestrator"""
        try:
            # Determine status based on profit percentage
            if stream_profit_percent >= 10.0:
                status = "MAJOR_PROFIT"
                action = "CONSIDER_SELL"
            elif stream_profit_percent >= 5.0:
                status = "GOOD_PROFIT"
                action = "MONITOR_CLOSELY"
            elif stream_profit_percent >= 2.0:
                status = "BUILDING_PROFIT"
                action = "CONTINUE_MONITORING"
            else:
                status = "SMALL_PROFIT"
                action = "HOLD"

            # Create profit update
            update = {
                "update_type": update_type,
                "symbol": position.symbol,
                "entry_price": float(position.entry_price),
                "current_price": float(position.current_price),
                "stream_price": stream_price,
                "profit_percent": stream_profit_percent,
                "profit_dollar": stream_profit_dollar,
                "quantity": position.quantity,
                "timestamp": datetime.now(UTC).isoformat(),
                "status": status,
                "action_suggested": action,
            }

            # Save JSON update to monitoring_data directory
            update_filename = f"profit_update_{position.symbol}_{int(time.time())}.json"
            update_filepath = os.path.join("monitoring_data", "alerts", update_filename)

            # Ensure alerts directory exists
            os.makedirs(os.path.dirname(update_filepath), exist_ok=True)

            # Write JSON update
            with open(update_filepath, "w") as f:
                json.dump(update, f, indent=2)

            # Log the update
            self.logger.info(
                f"📊 PROFIT UPDATE: {position.symbol} - "
                f"Stream: ${stream_price:.4f} (+{stream_profit_percent:.2f}%) "
                f"Status: {status} - {action} - JSON: {update_filename}"
            )

            # Also save to latest profit updates for immediate visibility
            latest_updates_file = os.path.join(
                "monitoring_data", "alerts", "latest_profit_updates.json"
            )

            # Load existing updates or create new list
            try:
                with open(latest_updates_file) as f:
                    latest_updates = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                latest_updates = {"updates": []}

            # Add new update to beginning of list
            latest_updates["updates"].insert(0, update)

            # Keep only last 20 updates
            latest_updates["updates"] = latest_updates["updates"][:20]
            latest_updates["last_updated"] = update["timestamp"]

            # Save updated latest updates
            with open(latest_updates_file, "w") as f:
                json.dump(latest_updates, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error generating profit update for {position.symbol}: {e}")

    async def _generate_profit_spike_alert(
        self,
        position: Position,
        stream_price: float,
        stream_profit_percent: float,
        stream_profit_dollar: float,
        spike_magnitude: float,
    ):
        """Generate JSON profit spike alert for Claude orchestrator"""
        try:
            # Determine urgency based on profit percentage and spike magnitude
            if stream_profit_percent >= 15.0 or abs(spike_magnitude) >= 5.0:
                urgency = "CRITICAL"
                action = "SELL_IMMEDIATELY"
            elif stream_profit_percent >= 10.0 or abs(spike_magnitude) >= 3.0:
                urgency = "HIGH"
                action = "CONSIDER_SELL_NOW"
            elif stream_profit_percent >= 5.0:
                urgency = "MEDIUM"
                action = "CONSIDER_SELL"
            else:
                urgency = "LOW"
                action = "MONITOR"

            # Create profit spike alert
            alert = ProfitSpikeAlert(
                alert_type="PROFIT_SPIKE",
                symbol=position.symbol,
                entry_price=float(position.entry_price),
                current_price=float(position.current_price),
                stream_price=stream_price,
                profit_percent=stream_profit_percent,
                profit_dollar=stream_profit_dollar,
                spike_magnitude=spike_magnitude,
                timestamp=datetime.now(UTC).isoformat(),
                action_required=action,
                urgency=urgency,
            )

            # Save JSON alert to monitoring_data directory
            alert_filename = f"profit_spike_{position.symbol}_{int(time.time())}.json"
            alert_filepath = os.path.join("monitoring_data", "alerts", alert_filename)

            # Ensure alerts directory exists
            os.makedirs(os.path.dirname(alert_filepath), exist_ok=True)

            # Write JSON alert
            with open(alert_filepath, "w") as f:
                json.dump(alert.to_dict(), f, indent=2)

            # Log the alert
            self.logger.warning(
                f"🚨 PROFIT SPIKE ALERT: {position.symbol} - "
                f"Stream Price: ${stream_price:.4f} (+{stream_profit_percent:.2f}%) "
                f"Spike: {spike_magnitude:+.2f}% - {urgency} - {action} - "
                f"JSON: {alert_filename}"
            )

            # Also save to latest alerts for immediate visibility
            latest_alerts_file = os.path.join(
                "monitoring_data", "alerts", "latest_profit_spikes.json"
            )

            # Load existing alerts or create new list
            try:
                with open(latest_alerts_file) as f:
                    latest_alerts = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                latest_alerts = {"alerts": []}

            # Add new alert to beginning of list
            latest_alerts["alerts"].insert(0, alert.to_dict())

            # Keep only last 10 alerts
            latest_alerts["alerts"] = latest_alerts["alerts"][:10]
            latest_alerts["last_updated"] = alert.timestamp

            # Save updated latest alerts
            with open(latest_alerts_file, "w") as f:
                json.dump(latest_alerts, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error generating profit spike alert for {position.symbol}: {e}")


# WebSocket Integration Plan (Future Implementation)
class WebSocketPositionTracker:
    """
    Future implementation for real-time WebSocket position tracking.

    This will use Alpaca's trade_updates stream to get instant position updates
    using the position_qty field confirmed in our research.
    """

    def __init__(self, position_tracker: PositionTracker):
        self.position_tracker = position_tracker
        self.websocket = None
        self.logger = logging.getLogger("websocket_position_tracker")

    async def start_streaming(self):
        """Start WebSocket streaming for trade updates"""
        # Future implementation:
        # 1. Connect to Alpaca WebSocket
        # 2. Subscribe to trade_updates stream
        # 3. Process position_qty updates in real-time
        # 4. Update PositionTracker instantly

        self.logger.info("WebSocket position tracking planned for Phase 2")

    async def on_trade_update(self, trade_update):
        """Handle trade update from WebSocket"""
        # Future implementation:
        # - Extract position_qty from trade update
        # - Calculate new position state
        # - Update PositionTracker in real-time
        # - Trigger immediate alerts if needed
        pass
