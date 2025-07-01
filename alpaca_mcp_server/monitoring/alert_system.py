"""Alert System - Multi-channel notification system

Provides reliable alert delivery through multiple channels to ensure
critical trading signals and system events reach the user.
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

from ..utils.timezone_utils import get_eastern_time_string


class AlertSystem:
    """
    Multi-channel alert system for trading signals and system events.

    Supports multiple alert channels:
    - File-based alerts (JSON logs)
    - Console notifications
    - Desktop notifications (Linux notify-send)
    - Discord webhooks (optional)
    - Future: SMS, email, audio alerts
    """

    def __init__(self, channels: Optional[List[str]] = None):
        self.logger = logging.getLogger("alert_system")

        # Default channels if none specified
        self.channels = channels or ["file", "console"]

        # Alert history
        self.alert_history: List[Dict[str, Any]] = []
        self.alerts_sent_today = 0

        # Configuration
        self.alerts_dir = Path("monitoring_data/alerts")
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

        # Channel configurations
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")

        # Alert file for latest alerts
        self.latest_alerts_file = self.alerts_dir / "latest_alerts.json"

        self.logger.info(f"AlertSystem initialized with channels: {self.channels}")

    async def send_alert(
        self, title: str, message: str, priority: str = "info", metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send alert through all configured channels.

        Args:
            title: Alert title/subject
            message: Alert message body
            priority: Alert priority (info, warning, high, critical)
            metadata: Additional metadata for the alert
        """
        try:
            # Create alert object
            alert = {
                "id": f"alert_{int(datetime.now(UTC).timestamp())}",
                "timestamp": datetime.now(UTC).isoformat(),
                "title": title,
                "message": message,
                "priority": priority,
                "metadata": metadata or {},
                "channels_sent": [],
            }

            # Send through each configured channel
            tasks = []

            if "file" in self.channels:
                tasks.append(self._send_file_alert(alert))

            if "console" in self.channels:
                tasks.append(self._send_console_alert(alert))

            if "desktop" in self.channels:
                tasks.append(self._send_desktop_alert(alert))

            if "discord" in self.channels and self.discord_webhook:
                tasks.append(self._send_discord_alert(alert))

            # Execute all alert tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Track which channels succeeded
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    alert["channels_sent"].append(self.channels[i])

            # Add to history
            self.alert_history.append(alert)
            self.alerts_sent_today += 1

            # Keep history manageable
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]

            # Update latest alerts file
            await self._update_latest_alerts()

            self.logger.info(
                f"Alert sent: {title} (priority: {priority}, channels: {alert['channels_sent']})"
            )

        except Exception as e:
            self.logger.error(f"Error sending alert '{title}': {e}")

    async def _send_file_alert(self, alert: dict):
        """Send alert to file system"""
        try:
            # Daily alert file
            date_str = get_eastern_time_string("%Y-%m-%d")
            alert_file = self.alerts_dir / f"alerts_{date_str}.jsonl"

            # Append to daily file (JSONL format)
            with open(alert_file, "a") as f:
                f.write(json.dumps(alert) + "\n")

            # Also update the latest alerts file for easy access
            return True

        except Exception as e:
            self.logger.error(f"Error sending file alert: {e}")
            return False

    async def _send_console_alert(self, alert: dict):
        """Send alert to console/terminal"""
        try:
            priority = alert["priority"]
            title = alert["title"]
            message = alert["message"]
            timestamp = get_eastern_time_string("%H:%M:%S")

            # Color coding based on priority
            color_codes = {
                "info": "\033[36m",  # Cyan
                "warning": "\033[33m",  # Yellow
                "high": "\033[35m",  # Magenta
                "critical": "\033[31m",  # Red
            }
            reset_code = "\033[0m"

            color = color_codes.get(priority, "")

            # Format console message
            console_msg = (
                f"{color}[{timestamp}] {priority.upper()}: {title}{reset_code}\n"
                f"{message}\n"
                f"{'-' * 50}"
            )

            print(console_msg)
            return True

        except Exception as e:
            self.logger.error(f"Error sending console alert: {e}")
            return False

    async def _send_desktop_alert(self, alert: dict):
        """Send desktop notification (Linux notify-send)"""
        try:
            title = alert["title"]
            message = alert["message"]
            priority = alert["priority"]

            # Map priority to notify-send urgency
            urgency_map = {
                "info": "low",
                "warning": "normal",
                "high": "critical",
                "critical": "critical",
            }
            urgency = urgency_map.get(priority, "normal")

            # Send desktop notification
            cmd = [
                "notify-send",
                "--urgency",
                urgency,
                "--app-name",
                "Trading Monitor",
                "--icon",
                "dialog-information",
                title,
                message,
            ]

            # Run notification command
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return True
            else:
                self.logger.warning(f"Desktop notification failed: {result.stderr}")
                return False

        except FileNotFoundError:
            # notify-send not available (not Linux or not installed)
            return False
        except Exception as e:
            self.logger.error(f"Error sending desktop alert: {e}")
            return False

    async def _send_discord_alert(self, alert: dict):
        """Send alert to Discord webhook"""
        try:
            if not self.discord_webhook:
                return False

            title = alert["title"]
            message = alert["message"]
            priority = alert["priority"]
            timestamp = alert["timestamp"]

            # Color coding for Discord embeds
            color_map = {
                "info": 0x3498DB,  # Blue
                "warning": 0xF39C12,  # Orange
                "high": 0x9B59B6,  # Purple
                "critical": 0xE74C3C,  # Red
            }

            # Create Discord embed
            embed = {
                "title": title,
                "description": message,
                "color": color_map.get(priority, 0x3498DB),
                "timestamp": timestamp,
                "footer": {"text": f"Trading Monitor | Priority: {priority.upper()}"},
            }

            payload = {"username": "Trading Monitor", "embeds": [embed]}

            # Send to Discord
            response = requests.post(self.discord_webhook, json=payload, timeout=10)

            return response.status_code == 204

        except Exception as e:
            self.logger.error(f"Error sending Discord alert: {e}")
            return False

    async def _update_latest_alerts(self):
        """Update the latest alerts file for easy access"""
        try:
            # Keep last 50 alerts in the latest file
            latest_alerts = self.alert_history[-50:]

            with open(self.latest_alerts_file, "w") as f:
                json.dump(
                    {
                        "last_updated": datetime.now(UTC).isoformat(),
                        "alert_count": len(latest_alerts),
                        "alerts": latest_alerts,
                    },
                    f,
                    indent=2,
                )

        except Exception as e:
            self.logger.error(f"Error updating latest alerts file: {e}")

    async def send_service_startup_alert(self):
        """Send alert when service starts"""
        await self.send_alert(
            "🚀 Trading Monitor Started",
            "Hybrid trading service has started and is now monitoring positions.",
            priority="info",
            metadata={"event_type": "service_startup"},
        )

    async def send_service_shutdown_alert(self, uptime_seconds: float):
        """Send alert when service stops"""
        await self.send_alert(
            "🛑 Trading Monitor Stopped",
            f"Hybrid trading service stopped after {uptime_seconds:.0f} seconds uptime.",
            priority="warning",
            metadata={"event_type": "service_shutdown", "uptime_seconds": uptime_seconds},
        )

    async def send_position_alert(self, symbol: str, pnl_percent: float, pnl_dollar: float):
        """Send position-related alert"""
        if pnl_percent > 0:
            emoji = "🚀"
            alert_type = "PROFIT"
            priority = "high"
        else:
            emoji = "⚠️"
            alert_type = "LOSS"
            priority = "warning"

        await self.send_alert(
            f"{emoji} {alert_type}: {symbol}",
            f"Position: {symbol}\nP&L: {pnl_percent:+.2%} (${pnl_dollar:+.2f})",
            priority=priority,
            metadata={"event_type": "position_alert", "symbol": symbol, "pnl_percent": pnl_percent},
        )

    async def send_signal_alert(self, signal: dict):
        """Send trading signal alert"""
        symbol = signal["symbol"]
        signal_type = signal["signal_type"]
        confidence = signal.get("confidence", 0)
        price = signal.get("price", "N/A")

        emoji = "🎯" if signal_type == "fresh_trough" else "📈"

        await self.send_alert(
            f"{emoji} Trading Signal: {symbol}",
            f"Signal: {signal_type}\nPrice: ${price}\nConfidence: {confidence:.1%}\nAction: {signal.get('action', 'analyze')}",
            priority="high",
            metadata={"event_type": "trading_signal", "signal": signal},
        )

    async def send_error_alert(self, error_message: str, error_count: int):
        """Send system error alert"""
        await self.send_alert(
            "🚨 System Error",
            f"Error occurred: {error_message}\nTotal errors: {error_count}",
            priority="warning",
            metadata={"event_type": "system_error", "error_count": error_count},
        )

    def get_recent_alerts(self, count: int = 10) -> list[dict]:
        """Get recent alerts"""
        return self.alert_history[-count:] if self.alert_history else []

    def get_alerts_by_priority(self, priority: str) -> list[dict]:
        """Get alerts by priority level"""
        return [alert for alert in self.alert_history if alert.get("priority") == priority]

    def get_status(self) -> dict:
        """Get alert system status"""
        return {
            "active_channels": self.channels,
            "alerts_sent_today": self.alerts_sent_today,
            "total_alerts_in_history": len(self.alert_history),
            "latest_alerts_file": str(self.latest_alerts_file),
            "discord_configured": bool(self.discord_webhook),
            "recent_alert_count": len(self.get_recent_alerts(10)),
        }


# Utility functions for alert management
async def test_alert_system(alert_system: AlertSystem):
    """Test all alert channels"""
    await alert_system.send_alert(
        "🧪 Alert System Test",
        "This is a test alert to verify all channels are working correctly.",
        priority="info",
        metadata={"test": True},
    )


async def send_startup_notification():
    """Send notification that the monitoring system is starting"""
    alert_system = AlertSystem()
    await alert_system.send_service_startup_alert()
