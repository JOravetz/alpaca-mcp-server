"""Market resources implementation."""

from datetime import datetime

from ..config.settings import get_trading_client


async def get_market_conditions() -> dict:
    """Current market status and conditions."""
    try:
        client = get_trading_client()
        clock = client.get_clock()

        return {
            "is_open": clock.is_open,  # type: ignore[union-attr]
            "next_open": clock.next_open.isoformat(),  # type: ignore[union-attr]
            "next_close": clock.next_close.isoformat(),  # type: ignore[union-attr]
            "current_time": clock.timestamp.isoformat(),  # type: ignore[union-attr]
            "market_status": "OPEN" if clock.is_open else "CLOSED",  # type: ignore[union-attr]
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "market_status": "UNKNOWN"}
