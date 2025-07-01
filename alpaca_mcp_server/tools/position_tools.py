"""Position management tools for Alpaca MCP Server."""

from alpaca.common.exceptions import APIError
from alpaca.trading.requests import ClosePositionRequest

from ..config.settings import get_trading_client


async def close_position(symbol: str, qty: str | None = None, percentage: str | None = None) -> str:
    """
    Closes a specific position for a single symbol.

    Args:
        symbol (str): The symbol of the position to close
        qty (Optional[str]): Optional number of shares to liquidate
        percentage (Optional[str]): Optional percentage of shares to liquidate (must result in at least 1 share)

    Returns:
        str: Formatted string containing position closure details or error message
    """
    try:
        client = get_trading_client()

        # Create close position request if options are provided
        close_options = None
        if qty or percentage:
            close_options = ClosePositionRequest(qty=qty, percentage=percentage)

        # Close the position
        order = client.close_position(symbol, close_options)

        order_id = getattr(order, "id", "Unknown")
        order_status = getattr(order, "status", "Unknown")
        return f"""Position Closed Successfully:
----------------------------
Symbol: {symbol}
Order ID: {order_id}
Status: {order_status}"""

    except APIError as api_error:
        error_message = str(api_error)
        if "42210000" in error_message and "would result in order size of zero" in error_message:
            return """Error: Invalid position closure request.

The requested percentage would result in less than 1 share.
Please either:
1. Use a higher percentage
2. Close the entire position (100%)
3. Specify an exact quantity using the qty parameter"""
        else:
            return f"Error closing position: {error_message}"

    except Exception as e:
        return f"Error closing position for {symbol}: {str(e)}"


async def close_all_positions(cancel_orders: bool = False) -> str:
    """
    Closes all open positions.

    Args:
        cancel_orders (bool): If True, cancels all open orders before liquidating positions

    Returns:
        str: Formatted string containing position closure results
    """
    try:
        client = get_trading_client()

        # Close all positions
        close_responses = client.close_all_positions(cancel_orders=cancel_orders)

        if not close_responses:
            return "No positions were found to close."

        # Format the response
        response_parts = ["Position Closure Results:"]
        response_parts.append("-" * 30)

        for response in close_responses:
            symbol = getattr(response, "symbol", "Unknown")
            status = getattr(response, "status", "Unknown")
            order_id = getattr(response, "order_id", None)
            response_parts.append(f"Symbol: {symbol}")
            response_parts.append(f"Status: {status}")
            if order_id:
                response_parts.append(f"Order ID: {order_id}")
            response_parts.append("-" * 30)

        return "\n".join(response_parts)

    except Exception as e:
        return f"Error closing all positions: {str(e)}"
