"""Price Trigger Tools for MCP Server

Provides MCP tool interfaces for the price trigger monitoring system.
Designed for day-trading entry/exit strategies based on support/resistance levels.
"""

import logging

logger = logging.getLogger(__name__)


def setup_price_trigger_for_entry(
    symbol: str,
    trigger_price: float,
    contract_symbol: str,
    contract_type: str,  # "stock" or "option"
    side: str,  # "buy" or "sell"
    quantity: int,
    order_type: str = "market",
    limit_price: float | None = None,
    notes: str = "",
) -> str:
    """
    Set up a price trigger that will alert you when stock reaches entry level.

    This is for day-trading: when the stock price hits your trigger level,
    you'll get a desktop notification with a staged order ready to execute.

    Args:
        symbol: Stock symbol to monitor (e.g., "CMBM")
        trigger_price: Price level to trigger at (e.g., 2.86 for resistance)
        contract_symbol: Symbol to trade (stock symbol or option contract)
        contract_type: "stock" for shares, "option" for options contracts
        side: "buy" to go long, "sell" to go short
        quantity: Number of shares or contracts
        order_type: "market" for immediate fill, "limit" for price limit
        limit_price: Required if order_type="limit"
        notes: Your trading notes (e.g., "Enter PUT at resistance")

    Returns:
        Formatted result with trigger ID and status

    Example:
        setup_price_trigger_for_entry(
            symbol="CMBM",
            trigger_price=2.86,
            contract_symbol="CMBM251121P00002500",
            contract_type="option",
            side="buy",
            quantity=6,
            order_type="market",
            notes="Day-trade PUT entry at resistance - target $2.34 support"
        )
    """
    try:
        import httpx

        # Prepare staged order
        staged_order = {
            "asset_type": contract_type,
            "symbol": contract_symbol,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "time_in_force": "day",
            "extended_hours": False,
            "notes": notes,
        }

        # Prepare notification messages
        action_word = "BUY" if side == "buy" else "SELL"
        asset_desc = f"{quantity} {contract_type}"
        if contract_type == "option":
            asset_desc = f"{quantity} contracts"

        notification_title = f"🎯 ENTRY TRIGGER: {symbol} @ ${trigger_price}"
        notification_message = (
            f"{symbol} reached ${trigger_price}!\n\n"
            f"📋 Staged Order:\n"
            f"{action_word} {asset_desc}\n"
            f"{contract_symbol}\n"
            f"Type: {order_type.upper()}\n\n"
            f"✅ Execute now?"
        )

        if notes:
            notification_message += f"\n\n💡 Notes: {notes}"

        # Send request to FastAPI service
        request_data = {
            "symbol": symbol,
            "trigger_price": trigger_price,
            "trigger_type": "at_or_above",  # Trigger when price reaches or exceeds level
            "staged_order": staged_order,
            "notification_title": notification_title,
            "notification_message": notification_message,
        }

        response = httpx.post(
            "http://localhost:8001/price-triggers/add",
            json=request_data,
            timeout=10.0,
        )

        response.raise_for_status()
        result = response.json()

        trigger_id = result.get("trigger_id", "unknown")

        return f"""
✅ PRICE TRIGGER CONFIGURED

Stock to Monitor: {symbol}
Trigger Price: ${trigger_price:.2f}
Status: ACTIVE - Monitoring in background

📋 Staged Order Ready:
  {action_word} {asset_desc}
  Symbol: {contract_symbol}
  Order Type: {order_type.upper()}
  {f'Limit Price: ${limit_price:.2f}' if limit_price else ''}

🔔 When {symbol} reaches ${trigger_price:.2f}:
  1. Desktop notification will pop up
  2. Order details will be shown
  3. Click to execute or use trigger ID: {trigger_id[:16]}...

📊 Monitoring Status:
  - Background service: RUNNING
  - Check interval: Every 2 seconds
  - Notification: Desktop + audio alert

💡 Notes: {notes if notes else 'None'}

⚠️ DAY-TRADING REMINDER:
  - Close position by 4:00 PM ET
  - No overnight holds
  - This is intraday only

To view all triggers: GET http://localhost:8001/price-triggers
To cancel trigger: POST http://localhost:8001/price-triggers/{trigger_id}/cancel
"""

    except Exception as e:
        logger.error(f"Error setting up price trigger: {e}")
        return f"""
❌ ERROR: Failed to set up price trigger

Error: {str(e)}

Troubleshooting:
1. Is FastAPI monitoring service running?
   Start with: uv run python -m alpaca_mcp_server.monitoring.fastapi_service

2. Check service status:
   curl http://localhost:8001/status

3. View logs:
   tail -f fastapi_monitoring.log
"""


def get_active_price_triggers() -> str:
    """
    Get all active price triggers currently being monitored.

    Returns:
        Formatted list of all triggers with their status
    """
    try:
        import httpx

        response = httpx.get(
            "http://localhost:8001/price-triggers",
            timeout=10.0,
        )

        response.raise_for_status()
        result = response.json()

        triggers = result.get("triggers", [])
        monitor_status = result.get("monitor_status", {})

        if not triggers:
            return """
📊 ACTIVE PRICE TRIGGERS

No active triggers.

Set up a trigger with: setup_price_trigger_for_entry()
"""

        output = "📊 ACTIVE PRICE TRIGGERS\n\n"
        output += f"Total Triggers: {len(triggers)}\n"
        output += f"Pending: {monitor_status.get('pending_triggers', 0)}\n"
        output += f"Triggered: {monitor_status.get('triggered_triggers', 0)}\n"
        output += f"Monitored Symbols: {', '.join(monitor_status.get('monitored_symbols', []))}\n\n"

        for trigger in triggers:
            status_icon = {
                "pending": "⏳",
                "triggered": "🔔",
                "executed": "✅",
                "cancelled": "❌",
                "expired": "⏰",
            }.get(trigger["status"], "❓")

            output += f"{status_icon} {trigger['symbol']} @ ${trigger['trigger_price']:.2f}\n"
            output += f"  Status: {trigger['status'].upper()}\n"
            output += f"  Type: {trigger['trigger_type']}\n"
            output += f"  ID: {trigger['trigger_id'][:16]}...\n"

            if trigger.get("last_checked_price"):
                output += f"  Last Price: ${trigger['last_checked_price']:.2f}\n"

            if trigger.get("staged_order"):
                order = trigger["staged_order"]
                output += (
                    f"  Staged: {order['side'].upper()} {order['quantity']} {order['asset_type']}\n"
                )

            if trigger.get("triggered_at"):
                output += f"  Triggered: {trigger['triggered_at']}\n"

            output += "\n"

        return output

    except Exception as e:
        logger.error(f"Error getting price triggers: {e}")
        return f"❌ Error: {str(e)}\nIs FastAPI service running?"


def cancel_price_trigger(trigger_id: str) -> str:
    """
    Cancel a pending price trigger.

    Args:
        trigger_id: The trigger ID (from setup_price_trigger_for_entry output)

    Returns:
        Confirmation message
    """
    try:
        import httpx

        response = httpx.post(
            f"http://localhost:8001/price-triggers/{trigger_id}/cancel",
            timeout=10.0,
        )

        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            return f"✅ Price trigger cancelled: {trigger_id[:16]}..."
        else:
            return f"❌ {result.get('message', 'Failed to cancel trigger')}"

    except Exception as e:
        logger.error(f"Error cancelling price trigger: {e}")
        return f"❌ Error: {str(e)}"


def mark_trigger_executed(trigger_id: str) -> str:
    """
    Mark a triggered order as executed (you manually placed the order).

    Args:
        trigger_id: The trigger ID

    Returns:
        Confirmation message
    """
    try:
        import httpx

        response = httpx.post(
            f"http://localhost:8001/price-triggers/{trigger_id}/execute",
            timeout=10.0,
        )

        response.raise_for_status()
        result = response.json()

        if result.get("status") == "success":
            return f"✅ Trigger marked as executed: {trigger_id[:16]}..."
        else:
            return f"❌ {result.get('message', 'Failed to mark as executed')}"

    except Exception as e:
        logger.error(f"Error marking trigger as executed: {e}")
        return f"❌ Error: {str(e)}"


def get_monitoring_service_status() -> str:
    """
    Check if the FastAPI monitoring service is running and responsive.

    Returns:
        Service status and health information
    """
    try:
        import httpx

        response = httpx.get(
            "http://localhost:8001/status",
            timeout=5.0,
        )

        response.raise_for_status()
        result = response.json()

        output = "🟢 MONITORING SERVICE STATUS\n\n"
        output += "Service: RUNNING\n"
        output += f"Active: {result.get('active', False)}\n"
        output += f"Uptime: {result.get('uptime_seconds', 0):.0f} seconds\n"
        output += f"Watchlist Size: {result.get('watchlist_size', 0)}\n"
        output += f"Active Positions: {result.get('position_count', 0)}\n\n"

        output += "Price Trigger Monitor:\n"
        output += "  URL: http://localhost:8001/price-triggers\n"
        output += "  Ready: YES\n\n"

        output += "To set up price trigger:\n"
        output += "  setup_price_trigger_for_entry(...)\n"

        return output

    except Exception as e:
        logger.error(f"Error checking monitoring service: {e}")
        return f"""
🔴 MONITORING SERVICE NOT RESPONDING

Error: {str(e)}

To start the service:
  uv run python -m alpaca_mcp_server.monitoring.fastapi_service

Or check if it's running:
  ps aux | grep fastapi_service
"""
