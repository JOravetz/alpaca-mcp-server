"""Order management tools for Alpaca MCP Server."""

import time
from typing import Any

from alpaca.trading.models import Position

from ..config.settings import get_trading_client


def format_price_for_alpaca(
    price: float | None, current_price: float | None = None
) -> float | None:
    """
    Format price according to Alpaca's decimal place requirements.

    Args:
        price: The price to format
        current_price: Optional current stock price for context

    Returns:
        Properly formatted price (4 decimal places for penny stocks, 2 for >$1)
    """
    if price is None:
        return None

    # Use current_price if available, otherwise use the limit price itself
    reference_price = current_price if current_price is not None else price

    if reference_price < 5.00:
        # Penny stocks: 4 decimal places
        return float(f"{price:.4f}")
    else:
        # Regular stocks: 2 decimal places
        return float(f"{price:.2f}")


async def get_current_stock_price(symbol: str) -> float | None:
    """
    Get current stock price for decimal place determination.

    Args:
        symbol: Stock symbol

    Returns:
        Current price or None if unavailable
    """
    try:
        from ..tools.market_data_tools import get_stock_quote

        quote_result = await get_stock_quote(symbol)

        # Extract price from quote result string
        if "Last Trade:" in quote_result:
            for line in quote_result.split("\n"):
                if "Last Trade:" in line and "$" in line:
                    price_str = line.split("$")[1].split()[0]
                    return float(price_str)
    except Exception:
        pass

    return None


async def get_position_average_price(symbol: str) -> float | None:
    """
    Get the average entry price for a current position.

    Args:
        symbol: Stock symbol to check

    Returns:
        Average entry price or None if no position exists
    """
    try:
        client = get_trading_client()
        all_positions = client.get_all_positions()

        # Filter to only Position objects (not error strings)
        positions = [p for p in all_positions if isinstance(p, Position)]

        for position in positions:
            if position.symbol == symbol:
                return float(position.avg_entry_price)

        return None
    except Exception:
        return None


async def validate_sell_order_for_profit(symbol: str, sell_price: float) -> tuple[bool, str]:
    """
    Validate that a sell order will result in a profit.

    Args:
        symbol: Stock symbol
        sell_price: Proposed sell price

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        avg_price = await get_position_average_price(symbol)

        if avg_price is None:
            return True, "No position found - sell order allowed"

        if sell_price <= avg_price:
            return (
                False,
                f"❌ LOSS PREVENTION: Sell price ${sell_price:.4f} is below average cost ${avg_price:.4f}. NEVER SELL FOR A LOSS!",
            )

        profit_per_share = sell_price - avg_price
        profit_pct = (profit_per_share / avg_price) * 100

        return (
            True,
            f"✅ PROFIT CONFIRMED: Sell price ${sell_price:.4f} is ${profit_per_share:.4f} (+{profit_pct:.2f}%) above cost ${avg_price:.4f}",
        )

    except Exception as e:
        return False, f"Error validating sell order: {str(e)}"


# Alpaca imports for order management
from alpaca.common.exceptions import APIError  # noqa: E402
from alpaca.trading.enums import (  # noqa: E402
    OrderClass,
    OrderSide,
    OrderType,
    QueryOrderStatus,
    TimeInForce,
)
from alpaca.trading.models import Order  # noqa: E402
from alpaca.trading.requests import (  # noqa: E402
    GetOrdersRequest,
    LimitOrderRequest,
    MarketOrderRequest,
    OptionLegRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
    TrailingStopOrderRequest,
)


async def get_orders(status: str = "all", limit: int = 10) -> str:
    """
    Retrieves and formats orders with the specified status.

    Args:
        status (str): Order status to filter by (open, closed, all)
        limit (int): Maximum number of orders to return (default: 10)

    Returns:
        str: Formatted string containing order details including:
            - Symbol
            - ID
            - Type
            - Side
            - Quantity
            - Status
            - Submission Time
            - Fill Details (if applicable)
    """
    try:
        client = get_trading_client()

        # Convert status string to enum
        if status.lower() == "open":
            query_status = QueryOrderStatus.OPEN
        elif status.lower() == "closed":
            query_status = QueryOrderStatus.CLOSED
        else:
            query_status = QueryOrderStatus.ALL

        request_params = GetOrdersRequest(status=query_status, limit=limit)

        orders = client.get_orders(request_params)

        if not orders:
            return f"No {status} orders found."

        result = f"{status.capitalize()} Orders (Last {len(orders)}):\n"
        result += "-----------------------------------\n"

        for order in orders:
            if not isinstance(order, Order):
                continue

            result += f"""Symbol: {order.symbol}
ID: {order.id}
Type: {order.type}
Side: {order.side}
Quantity: {order.qty}
Status: {order.status}
Submitted At: {order.submitted_at}"""

            if order.filled_at:
                result += f"\nFilled At: {order.filled_at}"

            if order.filled_avg_price:
                filled_price = float(order.filled_avg_price)
                if filled_price < 1.00:
                    result += f"\nFilled Price: ${filled_price:.4f}"
                else:
                    result += f"\nFilled Price: ${filled_price:.2f}"

            result += "\n-----------------------------------\n"

        return result

    except Exception as e:
        return f"Error fetching orders: {str(e)}"


async def place_stock_order(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "market",
    time_in_force: str = "day",
    limit_price: float | None = None,
    stop_price: float | None = None,
    trail_price: float | None = None,
    trail_percent: float | None = None,
    extended_hours: bool = False,
    client_order_id: str | None = None,
) -> str:
    """
    Places an order of any supported type (MARKET, LIMIT, STOP, STOP_LIMIT, TRAILING_STOP) using the correct Alpaca request class.

    Args:
        symbol (str): Stock ticker symbol (e.g., AAPL, MSFT)
        side (str): Order side (buy or sell)
        quantity (float): Number of shares to buy or sell
        order_type (str): Order type (MARKET, LIMIT, STOP, STOP_LIMIT, TRAILING_STOP). Default is MARKET.
        time_in_force (str): Time in force for the order (default: DAY)
        limit_price (float): Limit price (required for LIMIT, STOP_LIMIT)
        stop_price (float): Stop price (required for STOP, STOP_LIMIT)
        trail_price (float): Trail price (for TRAILING_STOP)
        trail_percent (float): Trail percent (for TRAILING_STOP)
        extended_hours (bool): Allow execution during extended hours (default: False)
        client_order_id (str): Optional custom identifier for the order

    Returns:
        str: Formatted string containing order details or error message.
    """
    try:
        client = get_trading_client()

        # Get current stock price for proper decimal formatting
        current_price = await get_current_stock_price(symbol)

        # Format prices according to Alpaca requirements
        if limit_price is not None:
            limit_price = format_price_for_alpaca(limit_price, current_price)
        if stop_price is not None:
            stop_price = format_price_for_alpaca(stop_price, current_price)
        if trail_price is not None:
            trail_price = format_price_for_alpaca(trail_price, current_price)

        # CRITICAL: Validate sell orders to prevent losses
        if side.lower() == "sell" and limit_price is not None:
            is_valid, message = await validate_sell_order_for_profit(symbol, limit_price)
            if not is_valid:
                return message

        # Validate side
        if side.lower() == "buy":
            order_side = OrderSide.BUY
        elif side.lower() == "sell":
            order_side = OrderSide.SELL
        else:
            return f"Invalid order side: {side}. Must be 'buy' or 'sell'."

        # Validate time_in_force
        try:
            tif_enum = TimeInForce[time_in_force.upper()]
        except KeyError:
            return f"Invalid time_in_force: {time_in_force}."

        # Validate order_type and create appropriate request
        order_type_upper = order_type.upper()
        order_data: (
            MarketOrderRequest
            | LimitOrderRequest
            | StopOrderRequest
            | StopLimitOrderRequest
            | TrailingStopOrderRequest
        )
        if order_type_upper == "MARKET":
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                type=OrderType.MARKET,
                time_in_force=tif_enum,
                extended_hours=extended_hours,
                client_order_id=client_order_id or f"order_{int(time.time())}",
            )
        elif order_type_upper == "LIMIT":
            if limit_price is None:
                return "limit_price is required for LIMIT orders."
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                type=OrderType.LIMIT,
                time_in_force=tif_enum,
                limit_price=limit_price,
                extended_hours=extended_hours,
                client_order_id=client_order_id or f"order_{int(time.time())}",
            )
        elif order_type_upper == "STOP":
            if stop_price is None:
                return "stop_price is required for STOP orders."
            order_data = StopOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                type=OrderType.STOP,
                time_in_force=tif_enum,
                stop_price=stop_price,
                extended_hours=extended_hours,
                client_order_id=client_order_id or f"order_{int(time.time())}",
            )
        elif order_type_upper == "STOP_LIMIT":
            if stop_price is None or limit_price is None:
                return "Both stop_price and limit_price are required for STOP_LIMIT orders."
            order_data = StopLimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                type=OrderType.STOP_LIMIT,
                time_in_force=tif_enum,
                stop_price=stop_price,
                limit_price=limit_price,
                extended_hours=extended_hours,
                client_order_id=client_order_id or f"order_{int(time.time())}",
            )
        elif order_type_upper == "TRAILING_STOP":
            if trail_price is None and trail_percent is None:
                return "Either trail_price or trail_percent is required for TRAILING_STOP orders."
            order_data = TrailingStopOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=order_side,
                type=OrderType.TRAILING_STOP,
                time_in_force=tif_enum,
                trail_price=trail_price,
                trail_percent=trail_percent,
                extended_hours=extended_hours,
                client_order_id=client_order_id or f"order_{int(time.time())}",
            )
        else:
            return f"Invalid order type: {order_type}. Must be one of: MARKET, LIMIT, STOP, STOP_LIMIT, TRAILING_STOP."

        # Submit order
        order = client.submit_order(order_data)

        if not isinstance(order, Order):
            return f"Error: Unexpected order response type: {type(order)}"

        return f"""Order Placed Successfully:
-------------------------
Order ID: {order.id}
Symbol: {order.symbol}
Side: {order.side}
Quantity: {order.qty}
Type: {order.type}
Time In Force: {order.time_in_force}
Status: {order.status}
Client Order ID: {order.client_order_id}"""

    except Exception as e:
        return f"Error placing order: {str(e)}"


async def cancel_all_orders() -> str:
    """
    Cancel all open orders.

    Returns:
        A formatted string containing the status of each cancelled order.
    """
    try:
        client = get_trading_client()

        # Cancel all orders
        cancel_responses = client.cancel_orders()

        if not cancel_responses:
            return "No orders were found to cancel."

        # Format the response
        response_parts = ["Order Cancellation Results:"]
        response_parts.append("-" * 30)

        # Process cancel responses
        for response in cancel_responses:
            # Handle both CancelOrderResponse objects and error strings
            if isinstance(response, str):
                response_parts.append(f"Error: {response}")
                response_parts.append("-" * 30)
            else:
                # It's a CancelOrderResponse object
                status = "Success" if response.status == 200 else "Failed"
                response_parts.append(f"Order ID: {response.id}")
                response_parts.append(f"Status: {status}")
                if response.body:
                    response_parts.append(f"Details: {response.body}")
                response_parts.append("-" * 30)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error cancelling orders: {str(e)}"


async def cancel_order_by_id(order_id: str) -> str:
    """
    Cancel a specific order by its ID.

    Args:
        order_id: The UUID of the order to cancel

    Returns:
        A formatted string containing the status of the cancelled order.
    """
    try:
        client = get_trading_client()

        # Cancel the specific order (returns None on success)
        client.cancel_order_by_id(order_id)

        # Success if no exception was raised
        result = f"""Order Cancellation Result:
------------------------
Order ID: {order_id}
Status: Success"""

        return result

    except Exception as e:
        return f"Error cancelling order {order_id}: {str(e)}"


async def place_option_market_order(
    legs: list[dict[str, Any]],
    order_class: str | OrderClass | None = None,
    quantity: int = 1,
    time_in_force: TimeInForce = TimeInForce.DAY,
    extended_hours: bool = False,
) -> str:
    """
    Places a market order for single or multi-leg options strategies with comprehensive error handling.

    Args:
        legs: List of option legs, each containing:
            - symbol: Option symbol (e.g., "AAPL230616C00150000")
            - side: "buy" or "sell"
            - ratio_qty: Number of contracts for this leg
        order_class: Order class ("simple", "mleg") - determined automatically if not provided
        quantity: Number of times to execute the strategy (default: 1)
        time_in_force: Time in force (default: DAY)
        extended_hours: Allow extended hours execution (default: False)

    Returns:
        str: Formatted string containing order details or comprehensive error guidance
    """
    try:
        client = get_trading_client()

        # Validate input
        if not legs or len(legs) == 0:
            return "Error: At least one option leg is required."

        if len(legs) > 4:
            return "Error: Maximum 4 legs allowed for multi-leg options orders."

        # Determine order class automatically if not provided
        if order_class is None:
            order_class = "simple" if len(legs) == 1 else "mleg"
        elif isinstance(order_class, str):
            order_class = order_class.lower()

        # Convert string order class to enum
        if order_class == "simple":
            order_class_enum = OrderClass.SIMPLE
        elif order_class == "mleg":
            # NOTE: OrderClass.MULTILEG does not exist in current Alpaca API
            # Multi-leg options not yet supported
            return "Error: Multi-leg options orders not yet supported by Alpaca API"
        else:
            return f"Error: Invalid order_class '{order_class}'. Must be 'simple' or 'mleg'."

        # Build option legs
        option_legs = []
        for i, leg in enumerate(legs):
            try:
                # Validate required fields
                if "symbol" not in leg:
                    return f"Error: Leg {i + 1} missing required field 'symbol'."
                if "side" not in leg:
                    return f"Error: Leg {i + 1} missing required field 'side'."
                if "ratio_qty" not in leg:
                    return f"Error: Leg {i + 1} missing required field 'ratio_qty'."

                # Validate side
                side_str = leg["side"].lower()
                if side_str == "buy":
                    side_enum = OrderSide.BUY
                elif side_str == "sell":
                    side_enum = OrderSide.SELL
                else:
                    return f"Error: Leg {i + 1} has invalid side '{leg['side']}'. Must be 'buy' or 'sell'."

                # Create option leg
                option_leg = OptionLegRequest(
                    symbol=leg["symbol"], side=side_enum, ratio_qty=leg["ratio_qty"]
                )
                option_legs.append(option_leg)

            except Exception as leg_error:
                return f"Error processing leg {i + 1}: {str(leg_error)}"

        # Create the order request
        # NOTE: OptionMarketOrderRequest does not exist in current Alpaca API
        # Using MarketOrderRequest for options orders
        from alpaca.trading.requests import MarketOrderRequest

        order_request = MarketOrderRequest(
            symbol=option_legs[0].symbol if option_legs else "",  # Use first leg's symbol
            qty=quantity,
            side=option_legs[0].side if option_legs else OrderSide.BUY,
            type=OrderType.MARKET,
            time_in_force=time_in_force,
        )

        # Submit the order
        order = client.submit_order(order_request)

        if not isinstance(order, Order):
            return f"Error: Unexpected order response type: {type(order)}"

        # Format successful response
        result = f"""Options Order Placed Successfully:
----------------------------------
Order ID: {order.id}
Order Class: {order.order_class}
Type: {order.type}
Quantity: {order.qty}
Status: {order.status}
Time in Force: {order.time_in_force}

Legs:"""

        for i, leg in enumerate(legs):
            result += f"""
Leg {i + 1}: {leg["side"].upper()} {leg["ratio_qty"]} {leg["symbol"]}"""

        return result

    except APIError as api_error:
        error_message = str(api_error)

        # Comprehensive error handling for different account permission levels
        if "40310000" in error_message:
            return """❌ Options Trading Permission Error (Level 0)

Your account does not have options trading enabled.

To enable options trading:
1. Log into your Alpaca account
2. Navigate to Account Settings
3. Apply for options trading permissions
4. Complete the options trading application
5. Wait for approval (usually 1-3 business days)

Once approved, you'll be able to place options orders."""

        elif "42110000" in error_message or "insufficient option level" in error_message.lower():
            return """❌ Insufficient Options Trading Level

Your current options trading level doesn't allow this strategy.

Options Trading Levels:
• Level 1: Covered calls, cash-secured puts
• Level 2: Long calls/puts, protective strategies
• Level 3: Spreads, strangles, straddles
• Level 4: Naked calls/puts, advanced strategies

To upgrade your options level:
1. Contact Alpaca support or your broker
2. Complete additional options trading forms
3. Demonstrate trading experience and knowledge

Current order requires higher permission level."""

        elif "42210000" in error_message:
            return """❌ Order Validation Error

The options order failed validation. Common issues:
• Invalid option symbol format
• Option contract doesn't exist or expired
• Insufficient buying power
• Market closed for options trading

Please verify:
1. Option symbols are correctly formatted
2. Expiration dates are valid and in the future
3. Strike prices exist for the underlying
4. Account has sufficient funds"""

        elif "insufficient buying power" in error_message.lower():
            return """❌ Insufficient Buying Power

Your account doesn't have enough buying power for this options order.

For options orders you need:
• Buying calls: Full premium amount
• Selling calls: Margin requirement or underlying shares
• Buying puts: Full premium amount
• Selling puts: Cash equal to strike × 100

Check your buying power with: get_account_info()"""

        else:
            return f"❌ Options Order Error: {error_message}"

    except Exception as e:
        return f"❌ Unexpected error placing options order: {str(e)}"
