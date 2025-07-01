"""Account resources implementation."""

from datetime import datetime

from ..config.settings import get_trading_client


async def get_account_status() -> dict:
    """Real-time account health and trading capacity."""
    try:
        client = get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()

        return {
            "account_id": account.id,
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "equity": float(account.equity),
            "day_trades_remaining": getattr(account, "daytrade_count", "Unknown"),
            "pattern_day_trader": account.pattern_day_trader,
            "positions_count": len(positions),
            "account_status": account.status,
            "currency": account.currency,
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}
