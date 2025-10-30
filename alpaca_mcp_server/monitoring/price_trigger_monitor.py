"""Price Trigger Monitoring System

Monitors stock prices and triggers notifications when specified price levels are reached.
Designed for day-trading entry/exit strategies based on support/resistance levels.

Key Features:
- Real-time price monitoring using streaming data
- Desktop notifications when triggers fire
- Optional order staging for one-click execution
- Support for both stock and options contracts
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class TriggerType(Enum):
    """Types of price triggers"""

    ABOVE = "above"  # Trigger when price goes above level
    BELOW = "below"  # Trigger when price goes below level
    AT_OR_ABOVE = "at_or_above"  # Trigger when price reaches or exceeds level
    AT_OR_BELOW = "at_or_below"  # Trigger when price reaches or falls below level


class TriggerStatus(Enum):
    """Status of price trigger"""

    PENDING = "pending"  # Waiting for price level
    TRIGGERED = "triggered"  # Price level reached, notification sent
    EXECUTED = "executed"  # User executed the staged order
    CANCELLED = "cancelled"  # User cancelled the trigger
    EXPIRED = "expired"  # Trigger expired (e.g., end of trading day)


@dataclass
class StagedOrder:
    """Staged order for one-click execution"""

    asset_type: str  # "stock" or "option"
    symbol: str  # Stock symbol or option contract
    side: str  # "buy" or "sell"
    quantity: int  # Number of shares/contracts
    order_type: str = "market"  # "market" or "limit"
    limit_price: float | None = None  # Limit price if order_type=limit
    time_in_force: str = "day"  # "day", "gtc", "ioc", "fok"
    extended_hours: bool = False  # Allow extended hours trading
    notes: str = ""  # User notes about the trade


@dataclass
class PriceTrigger:
    """Price trigger configuration"""

    trigger_id: str  # Unique identifier
    symbol: str  # Stock symbol to monitor
    trigger_price: float  # Price level to trigger at
    trigger_type: TriggerType  # Type of trigger
    status: TriggerStatus = TriggerStatus.PENDING
    staged_order: StagedOrder | None = None  # Optional order to stage
    notification_title: str = ""  # Custom notification title
    notification_message: str = ""  # Custom notification message
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    triggered_at: datetime | None = None
    executed_at: datetime | None = None
    last_checked_price: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "trigger_id": self.trigger_id,
            "symbol": self.symbol,
            "trigger_price": self.trigger_price,
            "trigger_type": self.trigger_type.value,
            "status": self.status.value,
            "staged_order": (
                {
                    "asset_type": self.staged_order.asset_type,
                    "symbol": self.staged_order.symbol,
                    "side": self.staged_order.side,
                    "quantity": self.staged_order.quantity,
                    "order_type": self.staged_order.order_type,
                    "limit_price": self.staged_order.limit_price,
                    "time_in_force": self.staged_order.time_in_force,
                    "extended_hours": self.staged_order.extended_hours,
                    "notes": self.staged_order.notes,
                }
                if self.staged_order
                else None
            ),
            "notification_title": self.notification_title,
            "notification_message": self.notification_message,
            "created_at": self.created_at.isoformat(),
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "last_checked_price": self.last_checked_price,
            "metadata": self.metadata,
        }


class PriceTriggerMonitor:
    """
    Monitors stock prices and triggers notifications when price levels are reached.

    Engineering notes:
    - Uses existing streaming infrastructure for real-time prices
    - Checks triggers every 1-5 seconds (configurable)
    - Desktop notifications via DesktopNotificationService
    - Thread-safe trigger management
    """

    def __init__(self, notification_service=None):
        self.logger = logging.getLogger("price_trigger_monitor")
        self.notification_service = notification_service

        # Active triggers by trigger_id
        self.triggers: dict[str, PriceTrigger] = {}

        # Track which symbols we're monitoring
        self.monitored_symbols: set[str] = set()

        # Lock for thread-safe trigger management
        self._lock = asyncio.Lock()

        # Check interval (seconds)
        self.check_interval = 2.0  # Check every 2 seconds

        # Monitoring task
        self._monitoring_task: asyncio.Task | None = None
        self._active = False

        self.logger.info("PriceTriggerMonitor initialized")

    async def add_trigger(
        self,
        symbol: str,
        trigger_price: float,
        trigger_type: TriggerType,
        staged_order: StagedOrder | None = None,
        notification_title: str = "",
        notification_message: str = "",
        metadata: dict | None = None,
    ) -> str:
        """
        Add a new price trigger.

        Returns:
            trigger_id: Unique identifier for the trigger
        """
        async with self._lock:
            # Generate unique trigger ID
            trigger_id = f"{symbol}_{trigger_price}_{datetime.now(UTC).timestamp()}"

            # Create trigger
            trigger = PriceTrigger(
                trigger_id=trigger_id,
                symbol=symbol.upper(),
                trigger_price=trigger_price,
                trigger_type=trigger_type,
                staged_order=staged_order,
                notification_title=notification_title or f"Price Alert: {symbol}",
                notification_message=(
                    notification_message
                    or f"{symbol} reached ${trigger_price:.2f} - Execute trade?"
                ),
                metadata=metadata or {},
            )

            self.triggers[trigger_id] = trigger
            self.monitored_symbols.add(symbol.upper())

            self.logger.info(
                f"Added price trigger: {symbol} @ ${trigger_price} ({trigger_type.value}) - ID: {trigger_id}"
            )

            return trigger_id

    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove a price trigger"""
        async with self._lock:
            if trigger_id in self.triggers:
                trigger = self.triggers[trigger_id]
                del self.triggers[trigger_id]

                # Clean up monitored symbols if no more triggers for this symbol
                if not any(t.symbol == trigger.symbol for t in self.triggers.values()):
                    self.monitored_symbols.discard(trigger.symbol)

                self.logger.info(f"Removed price trigger: {trigger_id}")
                return True

            return False

    async def get_trigger(self, trigger_id: str) -> PriceTrigger | None:
        """Get trigger by ID"""
        return self.triggers.get(trigger_id)

    async def get_all_triggers(self) -> list[PriceTrigger]:
        """Get all triggers"""
        return list(self.triggers.values())

    async def get_pending_triggers(self) -> list[PriceTrigger]:
        """Get all pending (not yet triggered) triggers"""
        return [t for t in self.triggers.values() if t.status == TriggerStatus.PENDING]

    async def cancel_trigger(self, trigger_id: str) -> bool:
        """Cancel a pending trigger"""
        async with self._lock:
            if trigger_id in self.triggers:
                trigger = self.triggers[trigger_id]
                if trigger.status == TriggerStatus.PENDING:
                    trigger.status = TriggerStatus.CANCELLED
                    self.logger.info(f"Cancelled price trigger: {trigger_id}")
                    return True

            return False

    async def mark_executed(self, trigger_id: str) -> bool:
        """Mark trigger as executed (user confirmed order)"""
        async with self._lock:
            if trigger_id in self.triggers:
                trigger = self.triggers[trigger_id]
                trigger.status = TriggerStatus.EXECUTED
                trigger.executed_at = datetime.now(UTC)
                self.logger.info(f"Marked trigger as executed: {trigger_id}")
                return True

            return False

    def _check_trigger_condition(self, trigger: PriceTrigger, current_price: float) -> bool:
        """
        Check if trigger condition is met.

        Returns:
            True if trigger should fire
        """
        if trigger.status != TriggerStatus.PENDING:
            return False

        if trigger.trigger_type == TriggerType.ABOVE:
            return current_price > trigger.trigger_price
        elif trigger.trigger_type == TriggerType.BELOW:
            return current_price < trigger.trigger_price
        elif trigger.trigger_type == TriggerType.AT_OR_ABOVE:
            return current_price >= trigger.trigger_price
        elif trigger.trigger_type == TriggerType.AT_OR_BELOW:
            return current_price <= trigger.trigger_price

        return False

    async def check_price(self, symbol: str, current_price: float) -> list[str]:
        """
        Check if any triggers should fire for this symbol/price.

        Returns:
            List of triggered trigger_ids
        """
        triggered_ids = []

        async with self._lock:
            for trigger_id, trigger in self.triggers.items():
                if trigger.symbol.upper() != symbol.upper():
                    continue

                # Update last checked price
                trigger.last_checked_price = current_price

                # Check if trigger condition met
                if self._check_trigger_condition(trigger, current_price):
                    # Fire trigger
                    trigger.status = TriggerStatus.TRIGGERED
                    trigger.triggered_at = datetime.now(UTC)
                    triggered_ids.append(trigger_id)

                    self.logger.warning(
                        f"🔔 PRICE TRIGGER FIRED: {symbol} @ ${current_price:.2f} (target: ${trigger.trigger_price:.2f})"
                    )

                    # Send notification
                    await self._send_trigger_notification(trigger, current_price)

        return triggered_ids

    async def _send_trigger_notification(self, trigger: PriceTrigger, current_price: float) -> None:
        """Send desktop notification when trigger fires"""
        if not self.notification_service:
            self.logger.warning("No notification service available")
            return

        try:
            # Build notification message
            message = trigger.notification_message.replace(
                "${price}", f"${current_price:.2f}"
            ).replace("${trigger_price}", f"${trigger.trigger_price:.2f}")

            # Add staged order info if present
            if trigger.staged_order:
                order = trigger.staged_order
                message += "\n\n📋 Staged Order:"
                message += f"\n{order.side.upper()} {order.quantity} {order.asset_type}"
                message += f"\n{order.symbol}"
                if order.order_type == "limit" and order.limit_price:
                    message += f"\nLimit: ${order.limit_price:.2f}"

                message += f"\n\n✅ Click to execute or use trigger ID: {trigger.trigger_id[:8]}"

            # Import DesktopNotification here to avoid circular import
            from .desktop_notifications import DesktopNotification

            notification = DesktopNotification(
                title=trigger.notification_title,
                message=message,
                priority="urgent",
                category="trading",
                sound=True,
                timeout=30,  # Longer timeout for trade decisions
                metadata={
                    "trigger_id": trigger.trigger_id,
                    "symbol": trigger.symbol,
                    "trigger_price": trigger.trigger_price,
                    "current_price": current_price,
                    "staged_order": trigger.staged_order is not None,
                },
            )

            await self.notification_service.send_notification(notification)

        except Exception as e:
            self.logger.error(f"Error sending trigger notification: {e}")

    def get_status(self) -> dict:
        """Get monitor status"""
        pending = [t for t in self.triggers.values() if t.status == TriggerStatus.PENDING]
        triggered = [t for t in self.triggers.values() if t.status == TriggerStatus.TRIGGERED]

        return {
            "active": self._active,
            "total_triggers": len(self.triggers),
            "pending_triggers": len(pending),
            "triggered_triggers": len(triggered),
            "monitored_symbols": list(self.monitored_symbols),
            "check_interval": self.check_interval,
        }
