"""Intraday P&L resource with configurable parameters."""

from datetime import datetime, time, timedelta

from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from ..config.settings import get_trading_client


async def get_intraday_pnl(
    days_back: int = 0,
    include_open_positions: bool = True,
    min_trade_value: float = 0.0,
    symbol_filter: str = None,
) -> dict:
    """Calculate actual intraday P&L from trades with configurable parameters.

    Args:
        days_back: Number of days back to analyze (0 = today only, default: 0)
        include_open_positions: Include unrealized P&L from open positions (default: True)
        min_trade_value: Minimum trade value to include in analysis (default: 0.0)
        symbol_filter: Filter trades by specific symbol (default: None for all symbols)
    """
    try:
        client = get_trading_client()
        account = client.get_account()

        # Calculate date range - Include full trading day with pre-market and extended hours
        target_date = datetime.now().date() - timedelta(days=days_back)
        # Start at 4:00 AM (pre-market open) and end at 8:00 PM (post-market close)
        day_start = datetime.combine(target_date, time(4, 0))
        day_end = datetime.combine(target_date, time(20, 0))

        # Get orders for the specified period
        orders_request = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            after=day_start,
            until=day_end,
            limit=500,  # Increased limit for active traders
        )

        orders = client.get_orders(orders_request)

        # Filter by symbol if specified
        if symbol_filter:
            orders = [
                order
                for order in orders
                if hasattr(order, "symbol") and order.symbol.upper() == symbol_filter.upper()
            ]

        # Calculate realized P&L from filled orders
        realized_pnl = 0
        trade_count = 0
        day_trades = 0
        from typing import Any

        trades_by_symbol: dict[str, dict[str, Any]] = {}
        total_volume = 0
        largest_win = 0
        largest_loss = 0
        winning_trades = 0
        losing_trades = 0

        for order in orders:
            if order.filled_at and order.filled_at.date() == target_date:
                if order.filled_avg_price and order.filled_qty:
                    trade_value = float(order.filled_avg_price) * float(order.filled_qty)

                    # Apply minimum trade value filter
                    if trade_value < min_trade_value:
                        continue

                    total_volume += trade_value

                    symbol = order.symbol
                    if symbol not in trades_by_symbol:
                        trades_by_symbol[symbol] = {
                            "trades": [],
                            "realized_pnl": 0,
                            "volume": 0,
                            "trade_count": 0,
                        }

                    trade_data = {
                        "side": order.side.value,
                        "qty": float(order.filled_qty),
                        "price": float(order.filled_avg_price),
                        "value": trade_value,
                        "time": order.filled_at,
                        "order_id": order.id,
                    }

                    trades_by_symbol[symbol]["trades"].append(trade_data)
                    trades_by_symbol[symbol]["volume"] += trade_value
                    trades_by_symbol[symbol]["trade_count"] += 1

                    trade_count += 1

        # Calculate day trades and P&L for each symbol
        for symbol, symbol_data in trades_by_symbol.items():
            symbol_trades = symbol_data["trades"]
            symbol_trades.sort(key=lambda x: x["time"])

            # Simple P&L calculation (buy negative, sell positive)
            symbol_pnl = 0
            position = 0
            avg_cost = 0

            for trade in symbol_trades:
                if trade["side"] == "buy":
                    # Update average cost
                    total_shares = position + trade["qty"]
                    if total_shares > 0:
                        avg_cost = (
                            (position * avg_cost) + (trade["qty"] * trade["price"])
                        ) / total_shares
                    position += trade["qty"]
                else:  # sell
                    if position > 0:  # Had position to sell
                        # Calculate P&L for this sell
                        pnl = (trade["price"] - avg_cost) * min(trade["qty"], position)
                        symbol_pnl += pnl

                        if pnl > 0:
                            winning_trades += 1
                            largest_win = max(largest_win, pnl)
                        else:
                            losing_trades += 1
                            largest_loss = min(largest_loss, pnl)

                        # Check if this constitutes a day trade
                        day_trades += 1

                    position -= trade["qty"]

            trades_by_symbol[symbol]["realized_pnl"] = round(symbol_pnl, 2)
            realized_pnl += symbol_pnl

        # Get unrealized P&L from current positions (if requested and analyzing today)
        unrealized_pnl = 0
        current_positions_count = 0

        if include_open_positions and days_back == 0:
            positions = client.get_all_positions()

            # Filter positions by symbol if specified
            if symbol_filter:
                positions = [
                    pos
                    for pos in positions
                    if hasattr(pos, "symbol") and pos.symbol.upper() == symbol_filter.upper()
                ]

            unrealized_pnl = sum(float(pos.unrealized_pl or 0) for pos in positions)
            current_positions_count = len(positions)

        # Calculate day trade limits
        pdt_status = account.pattern_day_trader
        remaining_day_trades = max(0, 3 - day_trades) if not pdt_status else 999

        # Calculate performance metrics
        win_rate = (
            (winning_trades / (winning_trades + losing_trades) * 100)
            if (winning_trades + losing_trades) > 0
            else 0
        )
        avg_win = largest_win / winning_trades if winning_trades > 0 else 0
        avg_loss = abs(largest_loss) / losing_trades if losing_trades > 0 else 0
        profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf") if avg_win > 0 else 0

        return {
            "analysis_date": target_date.isoformat(),
            "days_back": days_back,
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": (round(unrealized_pnl, 2) if include_open_positions else None),
            "total_pnl": round(realized_pnl + (unrealized_pnl if include_open_positions else 0), 2),
            "trade_count": trade_count,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate_pct": round(win_rate, 1),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": (round(profit_factor, 2) if profit_factor != float("inf") else "inf"),
            "total_volume": round(total_volume, 2),
            "day_trades_used": day_trades,
            "remaining_day_trades": remaining_day_trades,
            "pdt_status": pdt_status,
            "current_positions_count": current_positions_count,
            "trades_by_symbol": trades_by_symbol,
            "parameters": {
                "days_back": days_back,
                "include_open_positions": include_open_positions,
                "min_trade_value": min_trade_value,
                "symbol_filter": symbol_filter,
            },
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "analysis_date": (datetime.now().date() - timedelta(days=days_back)).isoformat(),
            "parameters": {
                "days_back": days_back,
                "include_open_positions": include_open_positions,
                "min_trade_value": min_trade_value,
                "symbol_filter": symbol_filter,
            },
            "last_updated": datetime.now().isoformat(),
        }
