"""Account resources implementation."""

# mypy: disable-error-code="arg-type"

from datetime import datetime

from ..config.settings import get_trading_client


async def get_account_status() -> dict:
    """Real-time account health and trading capacity."""
    try:
        client = get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()

        return {
            "account_id": account.id,  # type: ignore[union-attr]
            "buying_power": float(account.buying_power),  # type: ignore[union-attr]
            "cash": float(account.cash),  # type: ignore[union-attr]
            "portfolio_value": float(account.portfolio_value),  # type: ignore[union-attr]
            "equity": float(account.equity),  # type: ignore[union-attr]
            "day_trades_remaining": getattr(account, "daytrade_count", "Unknown"),
            "pattern_day_trader": account.pattern_day_trader,  # type: ignore[union-attr]
            "positions_count": len(positions),
            "account_status": account.status,  # type: ignore[union-attr]
            "currency": account.currency,  # type: ignore[union-attr]
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}
