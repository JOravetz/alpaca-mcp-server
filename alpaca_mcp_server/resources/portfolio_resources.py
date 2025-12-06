# mypy: disable-error-code="union-attr, arg-type"


"""Portfolio analytics resources implementation."""

from datetime import datetime

from ..config.settings import get_trading_client


async def get_portfolio_performance() -> dict:
    """Real-time portfolio performance metrics."""
    try:
        client = get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()

        total_unrealized_pnl = sum(float(pos.unrealized_pl or 0) for pos in positions)  # type: ignore[misc]
        total_value = float(account.portfolio_value)  # type: ignore[union-attr]
        cash_value = float(account.cash)  # type: ignore[union-attr]
        equity_value = float(account.equity)  # type: ignore[union-attr]

        # Calculate performance metrics
        day_change_pct = (
            (total_unrealized_pnl / (total_value - total_unrealized_pnl) * 100)
            if total_value > total_unrealized_pnl
            else 0
        )

        return {
            "total_value": total_value,
            "equity": equity_value,
            "cash": cash_value,
            "unrealized_pnl": total_unrealized_pnl,
            "unrealized_pnl_pct": (
                (total_unrealized_pnl / total_value * 100) if total_value > 0 else 0
            ),
            "day_change": total_unrealized_pnl,
            "day_change_pct": day_change_pct,
            "positions_count": len(positions),
            "cash_percentage": ((cash_value / total_value * 100) if total_value > 0 else 0),
            "invested_percentage": (
                ((total_value - cash_value) / total_value * 100) if total_value > 0 else 0
            ),
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


async def get_portfolio_allocation() -> dict:
    """Asset allocation breakdown with sector/position analysis."""
    try:
        client = get_trading_client()
        positions = client.get_all_positions()
        account = client.get_account()

        total_value = float(account.portfolio_value)  # type: ignore[union-attr]
        cash_value = float(account.cash)  # type: ignore[union-attr]

        allocations = {
            "cash": {
                "value": cash_value,
                "percentage": ((cash_value / total_value * 100) if total_value > 0 else 0),
                "type": "cash",
            }
        }

        # Position allocations
        winners = []
        losers = []

        for pos in positions:
            market_value = float(pos.market_value)  # type: ignore[union-attr]
            unrealized_pnl = float(pos.unrealized_pl)  # type: ignore[union-attr]
            unrealized_pnl_pct = float(pos.unrealized_plpc) * 100  # type: ignore[union-attr]

            allocation_data = {
                "value": market_value,
                "percentage": ((market_value / total_value * 100) if total_value > 0 else 0),
                "quantity": float(pos.qty),  # type: ignore[union-attr]
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "current_price": float(pos.current_price),  # type: ignore[union-attr]
                "avg_entry_price": float(pos.avg_entry_price),  # type: ignore[union-attr]
                "type": "equity",
            }

            allocations[pos.symbol] = allocation_data  # type: ignore[union-attr]

            # Track winners/losers
            if unrealized_pnl > 0:
                winners.append(
                    {
                        "symbol": pos.symbol,  # type: ignore[union-attr]
                        "pnl": unrealized_pnl,
                        "pnl_pct": unrealized_pnl_pct,
                    }
                )
            elif unrealized_pnl < 0:
                losers.append(
                    {
                        "symbol": pos.symbol,  # type: ignore[union-attr]
                        "pnl": unrealized_pnl,
                        "pnl_pct": unrealized_pnl_pct,
                    }
                )

        # Sort winners/losers
        winners.sort(key=lambda x: x["pnl"], reverse=True)
        losers.sort(key=lambda x: x["pnl"])

        return {
            "allocations": allocations,
            "total_value": total_value,
            "winners": winners[:5],  # Top 5 winners
            "losers": losers[:5],  # Top 5 losers
            "diversification_score": len(positions),  # Simple metric
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "allocations": {}}


async def get_portfolio_risk() -> dict:
    """Portfolio risk metrics and exposure analysis."""
    try:
        client = get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()

        total_value = float(account.portfolio_value)  # type: ignore[union-attr]
        cash_value = float(account.cash)  # type: ignore[union-attr]
        buying_power = float(account.buying_power)  # type: ignore[union-attr]

        # Calculate concentration risk
        position_values = [float(pos.market_value) for pos in positions]  # type: ignore[union-attr]
        max_position = max(position_values) if position_values else 0
        concentration_risk = (max_position / total_value * 100) if total_value > 0 else 0

        # Calculate leverage
        total_invested = total_value - cash_value
        leverage_ratio = total_invested / total_value if total_value > 0 else 0

        # Risk metrics
        at_risk_positions = len(
            [pos for pos in positions if float(pos.unrealized_plpc) < -0.05]  # type: ignore[union-attr]
        )  # Down >5%

        return {
            "total_exposure": total_invested,
            "cash_buffer": cash_value,
            "buying_power_available": buying_power,
            "leverage_ratio": leverage_ratio,
            "concentration_risk_pct": concentration_risk,
            "largest_position_value": max_position,
            "positions_at_risk": at_risk_positions,
            "total_positions": len(positions),
            "risk_level": (
                "HIGH"
                if concentration_risk > 20 or leverage_ratio > 0.8
                else ("MEDIUM" if concentration_risk > 10 or leverage_ratio > 0.6 else "LOW")
            ),
            "pattern_day_trader": account.pattern_day_trader,  # type: ignore[union-attr]
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "risk_level": "UNKNOWN"}
