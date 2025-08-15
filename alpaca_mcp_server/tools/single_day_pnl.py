"""Single day P&L tool for accurate daily trading analysis."""

from datetime import datetime, time
from typing import Any
import pytz

from alpaca.trading.enums import QueryOrderStatus
from alpaca.trading.requests import GetOrdersRequest

from ..config.settings import get_trading_client

# NYC timezone for proper market time display
NYC_TZ = pytz.timezone('America/New_York')


def format_currency(value: float) -> str:
    """Format a number as currency."""
    return f"${value:,.2f}"


async def get_single_day_pnl(
    date: str,
    symbol_filter: str | None = None,
    min_trade_value: float = 0.0,
) -> str:
    """Calculate P&L for a SINGLE specific trading day only.

    Args:
        date: Date to analyze in YYYY-MM-DD format (e.g., "2025-07-08")
        symbol_filter: Optional symbol to filter trades
        min_trade_value: Minimum trade value to include (default: 0)

    Returns:
        Formatted P&L report for that specific day only
    """
    try:
        client = get_trading_client()

        # Parse the specific date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Set time boundaries for the full trading day (4 AM to 8 PM ET)
        day_start = datetime.combine(target_date, time(4, 0))
        day_end = datetime.combine(target_date, time(20, 0))

        # Fetch orders for this specific day only
        orders_request = GetOrdersRequest(
            status=QueryOrderStatus.CLOSED,
            after=day_start,
            until=day_end,
            limit=10000,
        )

        orders = client.get_orders(orders_request)

        # Filter by symbol if specified
        if symbol_filter:
            orders = [
                order
                for order in orders
                if hasattr(order, "symbol") and order.symbol.upper() == symbol_filter.upper()
            ]

        # Process trades for this day only
        trades_by_symbol: dict[str, dict[str, Any]] = {}
        total_volume = 0
        trade_count = 0

        for order in orders:
            # STRICT date filtering - only trades filled on the target date
            if not order.filled_at or order.filled_at.date() != target_date:
                continue

            if not order.filled_avg_price or not order.filled_qty:
                continue

            trade_value = float(order.filled_avg_price) * float(order.filled_qty)

            # Apply minimum trade value filter
            if trade_value < min_trade_value:
                continue

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
                "time": order.filled_at.astimezone(NYC_TZ).strftime("%H:%M:%S EDT"),
                "order_id": order.id,
            }

            trades_by_symbol[symbol]["trades"].append(trade_data)
            trades_by_symbol[symbol]["volume"] += trade_value
            trades_by_symbol[symbol]["trade_count"] += 1
            total_volume += trade_value
            trade_count += 1

        # Calculate P&L for each symbol
        total_realized_pnl = 0
        winning_trades = 0
        losing_trades = 0

        for symbol, symbol_data in trades_by_symbol.items():
            symbol_trades = symbol_data["trades"]
            symbol_trades.sort(key=lambda x: x["time"])

            # P&L calculation
            symbol_pnl = 0
            position = 0
            avg_price = 0

            for trade in symbol_trades:
                if trade["side"] == "buy":
                    if position >= 0:  # Long or flat
                        if position == 0:
                            avg_price = trade["price"]
                        else:
                            avg_price = (
                                (position * avg_price) + (trade["qty"] * trade["price"])
                            ) / (position + trade["qty"])
                        position += trade["qty"]
                    else:  # Short position
                        qty_to_cover = min(trade["qty"], abs(position))
                        pnl = (avg_price - trade["price"]) * qty_to_cover
                        symbol_pnl += pnl

                        if pnl > 0:
                            winning_trades += 1
                        elif pnl < 0:
                            losing_trades += 1

                        position += trade["qty"]
                        if position > 0:
                            avg_price = trade["price"]
                        elif position == 0:
                            avg_price = 0

                else:  # sell
                    if position <= 0:  # Short or flat
                        if position == 0:
                            avg_price = trade["price"]
                        else:
                            avg_price = (
                                (abs(position) * avg_price) + (trade["qty"] * trade["price"])
                            ) / (abs(position) + trade["qty"])
                        position -= trade["qty"]
                    else:  # Long position
                        qty_to_sell = min(trade["qty"], position)
                        pnl = (trade["price"] - avg_price) * qty_to_sell
                        symbol_pnl += pnl

                        if pnl > 0:
                            winning_trades += 1
                        elif pnl < 0:
                            losing_trades += 1

                        position -= trade["qty"]
                        if position < 0:
                            avg_price = trade["price"]
                        elif position == 0:
                            avg_price = 0

            trades_by_symbol[symbol]["realized_pnl"] = round(symbol_pnl, 2)
            total_realized_pnl += symbol_pnl

        # Format the output
        output = []
        # Get current NYC time for report header
        current_time_nyc = datetime.now(NYC_TZ).strftime("%I:%M %p EDT")
        output.append(f"📊 SINGLE DAY P&L REPORT: {target_date.strftime('%A, %B %d, %Y')}")
        output.append(f"⏰ Report Generated: {current_time_nyc}")
        output.append("=" * 60)

        if trade_count == 0:
            output.append("❌ NO TRADES FOUND ON THIS DATE")
            return "\n".join(output)

        # Overall summary
        pnl_emoji = "🟢" if total_realized_pnl >= 0 else "🔴"
        output.append(f"\n{pnl_emoji} TOTAL P&L: {format_currency(total_realized_pnl)}")
        output.append(f"📈 Total Volume: {format_currency(total_volume)}")
        output.append(f"🔄 Total Trades: {trade_count}")
        output.append(f"✅ Winning Trades: {winning_trades}")
        output.append(f"❌ Losing Trades: {losing_trades}")

        if winning_trades + losing_trades > 0:
            win_rate = (winning_trades / (winning_trades + losing_trades)) * 100
            output.append(f"📊 Win Rate: {win_rate:.1f}%")

        # Symbol breakdown
        output.append("\n" + "=" * 60)
        output.append("BREAKDOWN BY SYMBOL:")
        output.append("-" * 60)

        # Sort by P&L
        sorted_symbols = sorted(
            trades_by_symbol.items(), key=lambda x: x[1]["realized_pnl"], reverse=True
        )

        for symbol, data in sorted_symbols:
            pnl = data["realized_pnl"]
            emoji = "✅" if pnl >= 0 else "❌"
            output.append(
                f"{emoji} {symbol:6} | P&L: {format_currency(pnl):>12} | "
                f"Trades: {data['trade_count']:3} | Volume: {format_currency(data['volume'])}"
            )

        output.append("=" * 60)

        return "\n".join(output)

    except Exception as e:
        return f"❌ Error calculating single day P&L: {str(e)}"
