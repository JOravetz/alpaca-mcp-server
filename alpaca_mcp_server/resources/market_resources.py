"""Market resources implementation."""

from datetime import datetime

from ..config.settings import get_trading_client


async def get_market_conditions() -> dict:
    """Current market status and conditions."""
    try:
        client = get_trading_client()
        clock = client.get_clock()

        return {
            "is_open": clock.is_open,
            "next_open": clock.next_open.isoformat(),
            "next_close": clock.next_close.isoformat(),
            "current_time": clock.timestamp.isoformat(),
            "market_status": "OPEN" if clock.is_open else "CLOSED",
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "market_status": "UNKNOWN"}
