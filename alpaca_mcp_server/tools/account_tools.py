from alpaca.trading.models import Position
"""Account management tools for Alpaca MCP Server."""

from ..config.settings import get_trading_client


async def get_account_info() -> str:
    """
    Retrieves and formats the current account information including balances and status.

    Returns:
        str: Formatted string containing account details including:
            - Account ID
            - Status
            - Currency
            - Buying Power
            - Cash Balance
            - Portfolio Value
            - Equity
            - Market Values
            - Pattern Day Trader Status
            - Day Trades Remaining
    """
    try:
        client = get_trading_client()
        account = client.get_account()

        # Type check for proper account access
        if isinstance(account, dict):
            return f"Error: Received dict response instead of TradeAccount: {account}"

        info = f"""Account Information:
-------------------
Account ID: {account.id}
Status: {account.status}
Currency: {account.currency}
Buying Power: ${float(account.buying_power or 0):.2f}
Cash: ${float(account.cash or 0):.2f}
Portfolio Value: ${float(account.portfolio_value or 0):.2f}
Equity: ${float(account.equity or 0):.2f}
Long Market Value: ${float(account.long_market_value or 0):.2f}
Short Market Value: ${float(account.short_market_value or 0):.2f}
Pattern Day Trader: {"Yes" if account.pattern_day_trader else "No"}
Day Trades Remaining: {account.daytrade_count if hasattr(account, "daytrade_count") else "Unknown"}"""

        return info

    except Exception as e:
        return f"Error retrieving account information: {str(e)}"


async def get_positions() -> str:
    """
    Retrieves and formats all current positions in the portfolio.

    Returns:
        str: Formatted string containing details of all open positions including:
            - Symbol
            - Quantity
            - Market Value
            - Average Entry Price
            - Current Price
            - Unrealized P/L
    """
    try:
        client = get_trading_client()
        positions = client.get_all_positions()

        if not positions:
            return "No open positions found."

        result = "Current Positions:\n-------------------\n"
        for position in positions:
            if not isinstance(position, Position):
                continue

            result += f"""Symbol: {position.symbol}
Quantity: {position.qty} shares
Market Value: ${float(position.market_value or 0):.2f}
Average Entry Price: ${float(position.avg_entry_price or 0):.2f}
Current Price: ${float(position.current_price or 0):.2f}
Unrealized P/L: ${float(position.unrealized_pl or 0):.2f} ({float(position.unrealized_plpc or 0) * 100:.2f}%)
-------------------
"""
        return result

    except Exception as e:
        return f"Error retrieving positions: {str(e)}"


async def get_open_position(symbol: str) -> str:
    """
    Retrieves and formats details for a specific open position.

    Args:
        symbol (str): The symbol name of the asset to get position for (e.g., 'AAPL', 'MSFT')

    Returns:
        str: Formatted string containing the position details or an error message
    """
    try:
        client = get_trading_client()
        position = client.get_open_position(symbol)

        # Check if it's an options position by looking for the options symbol pattern
        is_option = len(symbol) > 6 and any(c in symbol for c in ["C", "P"])

        # Type check
        if isinstance(position, dict):
            return f"Error: Received dict response: {position}"

        # Format quantity based on asset type
        quantity_text = f"{position.qty} contracts" if is_option else f"{position.qty}"

        return f"""Position Details for {symbol}:
---------------------------
Quantity: {quantity_text}
Market Value: ${float(position.market_value or 0):.2f}
Average Entry Price: ${float(position.avg_entry_price or 0):.2f}
Current Price: ${float(position.current_price or 0):.2f}
Unrealized P/L: ${float(position.unrealized_pl or 0):.2f}"""

    except Exception as e:
        return f"Error fetching position for {symbol}: {str(e)}"
