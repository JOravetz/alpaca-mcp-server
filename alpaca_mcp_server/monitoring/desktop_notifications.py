"""Desktop Notification System for Trading Alerts

Provides cross-platform desktop notifications for critical trading events:
- Profit spike alerts
- Order fill notifications
- Position change alerts
- Trade confirmation reminders
"""

import asyncio
import json
import logging
import platform
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..utils.timezone_utils import get_eastern_time_string


@dataclass
class DesktopNotification:
    """Desktop notification data structure"""

    title: str
    message: str
    priority: str = "normal"  # low, normal, urgent, critical
    category: str = "trading"  # trading, profit, alert, confirmation
    sound: bool = True
    timeout: int = 10  # seconds
    actions: list[str] | None = None  # ["Sell Now", "Hold"]
    metadata: dict | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "category": self.category,
            "sound": self.sound,
            "timeout": self.timeout,
            "actions": self.actions,
            "metadata": self.metadata,
        }


class DesktopNotificationService:
    """
    Cross-platform desktop notification service for trading alerts.

    Supports:
    - Linux: notify-send, dunst
    - macOS: osascript
    - Windows: toast notifications
    - Fallback: terminal bell and logging
    """

    def __init__(self):
        self.logger = logging.getLogger("desktop_notifications")
        self.platform = platform.system().lower()
        self.notification_history: list[dict] = []
        self.enabled = True

        # Sound configurations for different alert types
        self.sound_configs = {
            "profit_spike": {"sound": True, "urgency": "critical"},
            "order_fill": {"sound": True, "urgency": "normal"},
            "position_change": {"sound": False, "urgency": "low"},
            "trade_confirmation": {"sound": True, "urgency": "urgent"},
        }

        # Check if notification system is available
        self._check_notification_support()

        self.logger.info(f"Desktop notification service initialized for {self.platform}")

    def _check_notification_support(self):
        """Check if desktop notifications are supported on this platform"""
        try:
            if self.platform == "linux":
                # Check for notify-send
                result = subprocess.run(["which", "notify-send"], capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.warning("notify-send not available, using fallback notifications")
                    self.enabled = False

            elif self.platform == "darwin":  # macOS
                # osascript should be available on all macOS systems
                pass

            elif self.platform == "windows":
                # Check for Windows toast notification support
                try:
                    import win10toast

                    self.logger.info("Windows toast notifications available")
                except ImportError:
                    self.logger.warning("win10toast not installed, using fallback notifications")
                    self.enabled = False
            else:
                self.logger.warning(
                    f"Unsupported platform: {self.platform}, using fallback notifications"
                )
                self.enabled = False

        except Exception as e:
            self.logger.error(f"Error checking notification support: {e}")
            self.enabled = False

    async def send_notification(self, notification: DesktopNotification) -> bool:
        """Send desktop notification"""
        try:
            # Log notification
            self.logger.info(f"Sending notification: {notification.title} - {notification.message}")

            # Add to history
            notification_record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "notification": notification.to_dict(),
            }
            self.notification_history.append(notification_record)

            # Keep history manageable
            if len(self.notification_history) > 100:
                self.notification_history = self.notification_history[-100:]

            # Save notification to JSON file for visibility
            await self._save_notification_to_file(notification_record)

            if not self.enabled:
                return await self._fallback_notification(notification)

            # Send platform-specific notification
            if self.platform == "linux":
                return await self._send_linux_notification(notification)
            elif self.platform == "darwin":
                return await self._send_macos_notification(notification)
            elif self.platform == "windows":
                return await self._send_windows_notification(notification)
            else:
                return await self._fallback_notification(notification)

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return await self._fallback_notification(notification)

    async def _send_linux_notification(self, notification: DesktopNotification) -> bool:
        """Send Linux desktop notification using notify-send"""
        try:
            # Build notify-send command
            cmd = ["notify-send"]

            # Set urgency
            urgency_map = {
                "low": "low",
                "normal": "normal",
                "urgent": "critical",
                "critical": "critical",
            }
            cmd.extend(["-u", urgency_map.get(notification.priority, "normal")])

            # Set timeout (in milliseconds)
            cmd.extend(["-t", str(notification.timeout * 1000)])

            # Set category
            cmd.extend(["-c", notification.category])

            # Add icon based on category
            icon_map = {
                "trading": "applications-office",
                "profit": "face-smile",
                "alert": "dialog-warning",
                "confirmation": "dialog-question",
            }
            icon = icon_map.get(notification.category, "dialog-information")
            cmd.extend(["-i", icon])

            # Add title and message
            cmd.append(notification.title)
            cmd.append(notification.message)

            # Execute notification
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.debug("Linux notification sent successfully")
                return True
            else:
                self.logger.error(f"notify-send failed: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending Linux notification: {e}")
            return False

    async def _send_macos_notification(self, notification: DesktopNotification) -> bool:
        """Send macOS notification using osascript"""
        try:
            # Build AppleScript command
            script = f"""
            display notification "{notification.message}" ¬
                with title "{notification.title}" ¬
                subtitle "Trading Alert" ¬
                sound name "{"Glass" if notification.sound else ""}
            """

            # Execute osascript
            process = await asyncio.create_subprocess_exec(
                "osascript",
                "-e",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                self.logger.debug("macOS notification sent successfully")
                return True
            else:
                self.logger.error(f"osascript failed: {stderr.decode()}")
                return False

        except Exception as e:
            self.logger.error(f"Error sending macOS notification: {e}")
            return False

    async def _send_windows_notification(self, notification: DesktopNotification) -> bool:
        """Send Windows toast notification"""
        try:
            # This would require win10toast package
            # For now, use fallback
            return await self._fallback_notification(notification)

        except Exception as e:
            self.logger.error(f"Error sending Windows notification: {e}")
            return False

    async def _fallback_notification(self, notification: DesktopNotification) -> bool:
        """Fallback notification using terminal output and system bell"""
        try:
            # Print to console with formatting
            priority_symbols = {"low": "ℹ️", "normal": "📢", "urgent": "⚠️", "critical": "🚨"}

            symbol = priority_symbols.get(notification.priority, "📢")

            print(f"\n{symbol} {notification.title}")
            print(f"   {notification.message}")
            print(f"   Priority: {notification.priority.upper()}")
            print(f"   Time: {get_eastern_time_string('%H:%M:%S')}")
            print("-" * 50)

            # System bell for urgent/critical notifications
            if notification.priority in ["urgent", "critical"] and notification.sound:
                print("\a")  # ASCII bell character

            return True

        except Exception as e:
            self.logger.error(f"Error in fallback notification: {e}")
            return False

    async def _save_notification_to_file(self, notification_record: dict):
        """Save notification to JSON file for visibility"""
        try:
            # Save to monitoring_data/alerts/notifications.json
            notifications_file = Path("monitoring_data/alerts/desktop_notifications.json")
            notifications_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing notifications or create new list
            try:
                with open(notifications_file) as f:
                    notifications_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                notifications_data = {"notifications": []}

            # Add new notification
            notifications_data["notifications"].insert(0, notification_record)

            # Keep only last 50 notifications
            notifications_data["notifications"] = notifications_data["notifications"][:50]
            notifications_data["last_updated"] = notification_record["timestamp"]

            # Save updated notifications
            with open(notifications_file, "w") as f:
                json.dump(notifications_data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Error saving notification to file: {e}")

    async def send_profit_spike_alert(
        self, symbol: str, profit_percent: float, current_price: float, profit_dollar: float
    ) -> bool:
        """Send profit spike desktop notification"""

        # Determine priority based on profit percentage
        if profit_percent >= 15.0:
            priority = "critical"
            title = f"🚨 CRITICAL PROFIT SPIKE: {symbol}"
            action_msg = "SELL IMMEDIATELY!"
        elif profit_percent >= 10.0:
            priority = "urgent"
            title = f"⚠️ MAJOR PROFIT: {symbol}"
            action_msg = "Consider selling now!"
        elif profit_percent >= 5.0:
            priority = "urgent"
            title = f"🚀 SUBSTANTIAL PROFIT: {symbol}"
            action_msg = "Monitor for sell opportunity!"
        else:
            priority = "normal"
            title = f"📈 Profit Alert: {symbol}"
            action_msg = "Building profit detected"

        message = (
            f"${current_price:.4f} (+{profit_percent:.2f}%)\n"
            f"Profit: ${profit_dollar:.2f}\n"
            f"{action_msg}"
        )

        notification = DesktopNotification(
            title=title,
            message=message,
            priority=priority,
            category="profit",
            sound=True,
            timeout=15 if priority in ["urgent", "critical"] else 10,
            metadata={
                "symbol": symbol,
                "profit_percent": profit_percent,
                "current_price": current_price,
                "profit_dollar": profit_dollar,
            },
        )

        return await self.send_notification(notification)

    async def send_order_fill_alert(
        self, symbol: str, side: str, quantity: int, fill_price: float
    ) -> bool:
        """Send order fill desktop notification"""

        title = f"✅ Order Filled: {symbol}"
        message = (
            f"{side.upper()} {quantity} shares @ ${fill_price:.4f}\n"
            f"Total: ${quantity * fill_price:.2f}"
        )

        notification = DesktopNotification(
            title=title,
            message=message,
            priority="normal",
            category="trading",
            sound=True,
            timeout=8,
            metadata={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "fill_price": fill_price,
            },
        )

        return await self.send_notification(notification)

    async def send_position_change_alert(self, symbol: str, change_type: str) -> bool:
        """Send position change desktop notification"""

        if change_type == "opened":
            title = f"📊 Position Opened: {symbol}"
            message = "New position detected in portfolio"
        elif change_type == "closed":
            title = f"📊 Position Closed: {symbol}"
            message = "Position removed from portfolio"
        else:
            title = f"📊 Position Updated: {symbol}"
            message = f"Position {change_type}"

        notification = DesktopNotification(
            title=title,
            message=message,
            priority="low",
            category="trading",
            sound=False,
            timeout=5,
            metadata={"symbol": symbol, "change_type": change_type},
        )

        return await self.send_notification(notification)

    async def send_trade_confirmation_reminder(self, symbol: str, action: str) -> bool:
        """Send trade confirmation reminder"""

        title = "📸 Trade Confirmation Required"
        message = (
            f"Action: {action} {symbol}\n"
            f"Please provide screenshot proof\n"
            f"and verify execution details"
        )

        notification = DesktopNotification(
            title=title,
            message=message,
            priority="urgent",
            category="confirmation",
            sound=True,
            timeout=20,
            actions=["Screenshot Taken", "Skip"],
            metadata={"symbol": symbol, "action": action},
        )

        return await self.send_notification(notification)

    def get_notification_history(self) -> list[dict]:
        """Get recent notification history"""
        return self.notification_history.copy()

    def enable_notifications(self):
        """Enable desktop notifications"""
        self.enabled = True
        self.logger.info("Desktop notifications enabled")

    def disable_notifications(self):
        """Disable desktop notifications"""
        self.enabled = False
        self.logger.info("Desktop notifications disabled")

    def get_status(self) -> dict:
        """Get notification service status"""
        return {
            "enabled": self.enabled,
            "platform": self.platform,
            "notification_count": len(self.notification_history),
            "last_notification": (
                self.notification_history[0]["timestamp"] if self.notification_history else None
            ),
        }
