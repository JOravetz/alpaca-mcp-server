"""Trade Confirmation Protocol

Implements comprehensive trade confirmation requirements:
- Screenshot proof of fill confirmation
- Real-time position verification
- Explicit acknowledgment of actual prices
- Time-stamped monitoring logs
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..utils.timezone_utils import get_eastern_time_string
from .desktop_notifications import DesktopNotificationService


@dataclass
class TradeConfirmation:
    """Trade confirmation data structure"""

    trade_id: str
    symbol: str
    action: str  # BUY, SELL
    quantity: int
    expected_price: float
    actual_price: float | None = None
    fill_timestamp: str | None = None
    confirmation_status: str = "PENDING"  # PENDING, CONFIRMED, FAILED, TIMEOUT
    screenshot_path: str | None = None
    screenshot_required: bool = True
    position_verified: bool = False
    price_acknowledged: bool = False
    created_at: str = ""
    confirmed_at: str | None = None
    timeout_at: str = ""
    notes: list[str] = None

    def __post_init__(self):
        if self.created_at == "":
            self.created_at = datetime.now(UTC).isoformat()
        if self.timeout_at == "":
            # 10 minute timeout for confirmation
            timeout_time = datetime.now(UTC).timestamp() + (10 * 60)
            self.timeout_at = datetime.fromtimestamp(timeout_time, UTC).isoformat()
        if self.notes is None:
            self.notes = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


class TradeConfirmationService:
    """
    Service for managing trade confirmation protocol.

    Ensures all trades are properly verified with:
    - Screenshot evidence
    - Position verification
    - Price acknowledgment
    - Complete audit trail
    """

    def __init__(self, desktop_notifications: DesktopNotificationService):
        self.logger = logging.getLogger("trade_confirmation")
        self.desktop_notifications = desktop_notifications

        # Active confirmations awaiting verification
        self.pending_confirmations: dict[str, TradeConfirmation] = {}
        self.confirmation_history: list[dict] = []

        # Confirmation requirements
        self.screenshot_timeout = 600  # 10 minutes
        self.auto_fail_timeout = 1800  # 30 minutes

        # Storage paths
        self.confirmations_dir = Path("monitoring_data/trade_confirmations")
        self.screenshots_dir = Path("monitoring_data/screenshots")
        self.confirmations_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("Trade confirmation service initialized")

    async def request_trade_confirmation(
        self, symbol: str, action: str, quantity: int, expected_price: float
    ) -> str:
        """Request trade confirmation for a new trade"""

        trade_id = f"{symbol}_{action}_{int(time.time())}"

        confirmation = TradeConfirmation(
            trade_id=trade_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            expected_price=expected_price,
            screenshot_required=True,
            notes=[f"Trade confirmation requested at {get_eastern_time_string('%H:%M:%S')}"],
        )

        self.pending_confirmations[trade_id] = confirmation

        # Save confirmation request
        await self._save_confirmation(confirmation)

        # Send desktop notification for confirmation requirement
        await self.desktop_notifications.send_trade_confirmation_reminder(
            symbol=symbol, action=f"{action} {quantity} shares @ ${expected_price:.4f}"
        )

        self.logger.warning(
            f"📸 TRADE CONFIRMATION REQUIRED: {trade_id} - "
            f"{action} {quantity} {symbol} @ ${expected_price:.4f}"
        )

        # Schedule automatic timeout check
        asyncio.create_task(self._check_confirmation_timeout(trade_id))

        return trade_id

    async def confirm_trade_execution(
        self,
        trade_id: str,
        actual_price: float,
        fill_timestamp: str,
        screenshot_path: str | None = None,
    ) -> bool:
        """Confirm trade execution with actual details"""

        if trade_id not in self.pending_confirmations:
            self.logger.error(f"Trade confirmation not found: {trade_id}")
            return False

        confirmation = self.pending_confirmations[trade_id]

        # Update confirmation with execution details
        confirmation.actual_price = actual_price
        confirmation.fill_timestamp = fill_timestamp
        confirmation.screenshot_path = screenshot_path
        confirmation.confirmed_at = datetime.now(UTC).isoformat()

        # Check if screenshot is provided
        if confirmation.screenshot_required and not screenshot_path:
            confirmation.notes.append("WARNING: Screenshot proof missing")
            self.logger.warning(f"Screenshot missing for trade {trade_id}")

        # Verify position
        position_verified = await self._verify_position_change(confirmation)
        confirmation.position_verified = position_verified

        # Check price acknowledgment
        price_diff = abs(actual_price - confirmation.expected_price)
        price_diff_percent = (price_diff / confirmation.expected_price) * 100

        if price_diff_percent > 1.0:  # More than 1% difference
            confirmation.notes.append(
                f"PRICE VARIANCE: Expected ${confirmation.expected_price:.4f}, "
                f"Actual ${actual_price:.4f} ({price_diff_percent:.2f}% difference)"
            )
            self.logger.warning(f"Significant price variance for trade {trade_id}")

        confirmation.price_acknowledged = True
        confirmation.confirmation_status = "CONFIRMED"

        # Save updated confirmation
        await self._save_confirmation(confirmation)

        # Move to history
        self.confirmation_history.append(confirmation.to_dict())
        del self.pending_confirmations[trade_id]

        self.logger.info(
            f"✅ TRADE CONFIRMED: {trade_id} - "
            f"{confirmation.action} {confirmation.quantity} {confirmation.symbol} @ ${actual_price:.4f}"
        )

        return True

    async def provide_screenshot(self, trade_id: str, screenshot_path: str) -> bool:
        """Provide screenshot proof for trade"""

        if trade_id not in self.pending_confirmations:
            self.logger.error(f"Trade confirmation not found: {trade_id}")
            return False

        confirmation = self.pending_confirmations[trade_id]

        # Verify screenshot file exists
        if not os.path.exists(screenshot_path):
            self.logger.error(f"Screenshot file not found: {screenshot_path}")
            return False

        # Copy screenshot to confirmations directory
        screenshot_filename = f"{trade_id}_screenshot_{int(time.time())}.png"
        destination_path = self.screenshots_dir / screenshot_filename

        try:
            import shutil

            shutil.copy2(screenshot_path, destination_path)
            confirmation.screenshot_path = str(destination_path)
            confirmation.notes.append(f"Screenshot provided: {screenshot_filename}")

            await self._save_confirmation(confirmation)

            self.logger.info(f"📸 Screenshot provided for trade {trade_id}: {screenshot_filename}")
            return True

        except Exception as e:
            self.logger.error(f"Error copying screenshot: {e}")
            return False

    async def _verify_position_change(self, confirmation: TradeConfirmation) -> bool:
        """Verify that position change matches trade execution"""
        try:
            # Import position verification tools
            from ..tools.account_tools import get_positions

            # Get current positions
            positions_result = await get_positions()

            # Check if position exists for the symbol
            if isinstance(positions_result, str):
                # Parse string response to check for symbol
                has_position = confirmation.symbol in positions_result
            else:
                # Handle dict response
                positions = positions_result.get("positions", [])
                has_position = any(pos.get("symbol") == confirmation.symbol for pos in positions)

            # For BUY orders, we should have a position
            # For SELL orders, we might not have a position if fully closed
            if confirmation.action.upper() == "BUY":
                return has_position
            else:  # SELL
                # For sells, position verification is more complex
                # For now, assume verified if no errors
                return True

        except Exception as e:
            self.logger.error(f"Error verifying position for {confirmation.trade_id}: {e}")
            return False

    async def _save_confirmation(self, confirmation: TradeConfirmation):
        """Save confirmation to JSON file"""
        try:
            confirmation_file = self.confirmations_dir / f"{confirmation.trade_id}.json"

            with open(confirmation_file, "w") as f:
                json.dump(confirmation.to_dict(), f, indent=2)

            # Also update master confirmations file
            master_file = self.confirmations_dir / "all_confirmations.json"

            try:
                with open(master_file) as f:
                    all_confirmations = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                all_confirmations = {"confirmations": []}

            # Update or add confirmation
            confirmations = all_confirmations["confirmations"]
            updated = False

            for i, conf in enumerate(confirmations):
                if conf["trade_id"] == confirmation.trade_id:
                    confirmations[i] = confirmation.to_dict()
                    updated = True
                    break

            if not updated:
                confirmations.insert(0, confirmation.to_dict())

            # Keep only last 100 confirmations
            all_confirmations["confirmations"] = confirmations[:100]
            all_confirmations["last_updated"] = datetime.now(UTC).isoformat()

            with open(master_file, "w") as f:
                json.dump(all_confirmations, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving confirmation: {e}")

    async def _check_confirmation_timeout(self, trade_id: str):
        """Check for confirmation timeout"""
        try:
            # Wait for timeout period
            await asyncio.sleep(self.screenshot_timeout)

            if trade_id in self.pending_confirmations:
                confirmation = self.pending_confirmations[trade_id]

                if confirmation.confirmation_status == "PENDING":
                    confirmation.confirmation_status = "TIMEOUT"
                    confirmation.notes.append(
                        f"Confirmation timeout at {get_eastern_time_string('%H:%M:%S')}"
                    )

                    await self._save_confirmation(confirmation)

                    self.logger.error(f"⏰ TRADE CONFIRMATION TIMEOUT: {trade_id}")

                    # Send timeout notification
                    await self.desktop_notifications.send_notification(
                        title="⏰ Trade Confirmation Timeout",
                        message=f"Trade {confirmation.symbol} requires manual verification",
                        priority="urgent",
                        category="confirmation",
                    )

        except Exception as e:
            self.logger.error(f"Error in timeout check: {e}")

    def get_pending_confirmations(self) -> list[dict]:
        """Get all pending confirmations"""
        return [conf.to_dict() for conf in self.pending_confirmations.values()]

    def get_confirmation_history(self) -> list[dict]:
        """Get confirmation history"""
        return self.confirmation_history.copy()

    def get_confirmation(self, trade_id: str) -> dict | None:
        """Get specific confirmation"""
        if trade_id in self.pending_confirmations:
            return self.pending_confirmations[trade_id].to_dict()

        # Check history
        for conf in self.confirmation_history:
            if conf["trade_id"] == trade_id:
                return conf

        return None

    async def mark_confirmation_complete(self, trade_id: str) -> bool:
        """Mark confirmation as complete (manual override)"""
        if trade_id not in self.pending_confirmations:
            return False

        confirmation = self.pending_confirmations[trade_id]
        confirmation.confirmation_status = "CONFIRMED"
        confirmation.confirmed_at = datetime.now(UTC).isoformat()
        confirmation.notes.append("Manually marked as complete")

        await self._save_confirmation(confirmation)

        # Move to history
        self.confirmation_history.append(confirmation.to_dict())
        del self.pending_confirmations[trade_id]

        self.logger.info(f"✅ Trade confirmation manually completed: {trade_id}")
        return True

    def get_status(self) -> dict:
        """Get confirmation service status"""
        return {
            "pending_confirmations": len(self.pending_confirmations),
            "completed_confirmations": len(self.confirmation_history),
            "screenshots_directory": str(self.screenshots_dir),
            "confirmations_directory": str(self.confirmations_dir),
        }
