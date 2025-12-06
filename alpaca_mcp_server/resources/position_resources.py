# mypy: disable-error-code="arg-type"


"""Position resources implementation."""

from datetime import datetime

from ..config.settings import get_trading_client


async def get_current_positions() -> dict:
    """Live position data with P&L updates."""
    try:
        client = get_trading_client()
        positions = client.get_all_positions()

        position_summary = []
        total_unrealized_pnl = 0.0

        for pos in positions:
            unrealized_pnl = float(pos.unrealized_pl)  # type: ignore[union-attr]
            total_unrealized_pnl += unrealized_pnl

            position_summary.append(
                {
                    "symbol": pos.symbol,  # type: ignore[union-attr]
                    "quantity": float(pos.qty),  # type: ignore[union-attr]
                    "market_value": float(pos.market_value),  # type: ignore[union-attr]
                    "avg_entry_price": float(pos.avg_entry_price),  # type: ignore[union-attr]
                    "current_price": float(pos.current_price),  # type: ignore[union-attr]
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": float(pos.unrealized_plpc) * 100,  # type: ignore[union-attr]
                }
            )

        return {
            "positions": position_summary,
            "total_positions": len(positions),
            "total_unrealized_pnl": total_unrealized_pnl,
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "positions": []}
