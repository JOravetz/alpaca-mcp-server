"""Options trading tools and contract information."""

from datetime import date

from alpaca.data.enums import OptionsFeed
from alpaca.data.requests import OptionChainRequest, OptionLatestQuoteRequest, OptionSnapshotRequest
from alpaca.trading.enums import AssetStatus, ContractType


async def test_option_client_basic(underlying_symbol: str) -> str:
    """Test basic option client functionality."""
    try:
        from alpaca.data.historical.option import OptionHistoricalDataClient

        from ..config.settings import settings

        # Create client directly
        client = OptionHistoricalDataClient(
            api_key=settings.api_key, secret_key=settings.api_secret
        )
        return f"Option client test successful for {underlying_symbol}. Client type: {type(client)}"
    except Exception as e:
        return f"Option client test failed: {str(e)}"


async def get_option_contracts(
    underlying_symbol: str,
    expiration_date: date | None = None,
    strike_price_gte: str | None = None,
    strike_price_lte: str | None = None,
    type: ContractType | None = None,
    status: AssetStatus | None = None,
    root_symbol: str | None = None,
    limit: int | None = None,
) -> str:
    """
    Retrieves metadata for option contracts based on specified criteria.

    Args:
        underlying_symbol (str): The symbol of the underlying asset (e.g., 'AAPL')
        expiration_date (Optional[date]): Optional expiration date for the options
        strike_price_gte (Optional[str]): Optional minimum strike price
        strike_price_lte (Optional[str]): Optional maximum strike price
        type (Optional[ContractType]): Optional contract type (CALL or PUT)
        status (Optional[AssetStatus]): Optional asset status filter
        root_symbol (Optional[str]): Optional root symbol for the option
        limit (Optional[int]): Optional maximum number of contracts to return

    Returns:
        str: Formatted string containing option contract metadata
    """
    try:
        from alpaca.data.historical.option import OptionHistoricalDataClient

        from ..config.settings import settings

        # Create client directly
        client = OptionHistoricalDataClient(
            api_key=settings.api_key, secret_key=settings.api_secret
        )

        # Build request with correct parameter name
        request_params = {"underlying_symbol": underlying_symbol}
        if expiration_date:
            request_params["expiration_date"] = expiration_date
        if strike_price_gte:
            request_params["strike_price_gte"] = float(strike_price_gte)
        if strike_price_lte:
            request_params["strike_price_lte"] = float(strike_price_lte)

        request = OptionChainRequest(**request_params)
        contracts = client.get_option_chain(request)

        if not contracts:
            return f"No option contracts found for {underlying_symbol}"

        result = f"Option Contracts for {underlying_symbol}:\n" + "=" * 50 + "\n"

        # Handle contracts dict format - Debug and fix field access
        for count, (symbol, contract_data) in enumerate(contracts.items()):
            if limit and count >= limit:
                break

            # Parse contract symbol for type and strike (fallback method)
            contract_type = "N/A"
            strike_price = "N/A"
            expiration = "N/A"

            # Extract info from symbol if contract_data doesn't have direct attributes
            if hasattr(contract_data, "strike_price"):
                strike_price = f"${contract_data.strike_price}"

            # Force symbol parsing to always run
            if len(symbol) >= 15:  # Standard option symbol format
                # AAPL250801C00205000 -> 205.00 strike, Call
                try:
                    contract_type = (
                        "CALL" if symbol[-9] == "C" else "PUT" if symbol[-9] == "P" else "N/A"
                    )
                    strike_raw = symbol[-8:]  # Last 8 digits
                    strike_price = f"${float(strike_raw) / 1000:.2f}"
                except Exception as e:
                    # If parsing fails, show the error for debugging
                    strike_price = f"Parse error: {str(e)}"
            else:
                strike_price = f"Symbol too short: {len(symbol)}"

            if hasattr(contract_data, "expiration_date"):
                expiration = str(contract_data.expiration_date)

            # Force expiration parsing to always run
            if len(symbol) >= 15:
                # Extract expiration from symbol AAPL250801C00205000 -> 2025-08-01
                try:
                    exp_part = symbol[4:10]  # 250801
                    year = f"20{exp_part[:2]}"
                    month = exp_part[2:4]
                    day = exp_part[4:6]
                    expiration = f"{year}-{month}-{day}"
                except Exception as e:
                    expiration = f"Parse error: {str(e)}"

            if hasattr(contract_data, "type"):
                contract_type = str(contract_data.type)

            result += f"""
Contract: {symbol}
Strike Price: {strike_price}
Expiration: {expiration}
Type: {contract_type}
---
"""

        return result

    except Exception as e:
        return f"Error fetching option contracts: {str(e)}"


async def get_option_latest_quote(symbol: str, feed: OptionsFeed | None = None) -> str:
    """
    Retrieves and formats the latest quote for an option contract.

    Args:
        symbol (str): The option contract symbol (e.g., 'AAPL230616C00150000')
        feed (Optional[OptionsFeed]): The source feed of the data

    Returns:
        str: Formatted string containing the latest quote information
    """
    try:
        from alpaca.data.historical.option import OptionHistoricalDataClient

        from ..config.settings import settings

        # Create client directly
        client = OptionHistoricalDataClient(
            api_key=settings.api_key, secret_key=settings.api_secret
        )
        request = OptionLatestQuoteRequest(symbol_or_symbols=symbol, feed=feed)

        quote = client.get_option_latest_quote(request)

        if symbol in quote:
            q = quote[symbol]
            return f"""
Latest Quote for {symbol}:
-------------------------
Ask Price: ${q.ask}
Ask Size: {q.ask_size}
Bid Price: ${q.bid}
Bid Size: {q.bid_size}
Ask Exchange: {q.ask_exchange}
Bid Exchange: {q.bid_exchange}
Timestamp: {q.timestamp}
"""
        else:
            return f"No quote data found for {symbol}"

    except Exception as e:
        return f"Error fetching option quote: {str(e)}"


async def get_option_snapshot(symbol: str) -> str:
    """
    Get comprehensive option snapshot with latest quote, trade, and Greeks.

    Args:
        symbol (str): The option contract symbol

    Returns:
        str: Formatted string containing comprehensive option data
    """
    try:
        from alpaca.data.historical.option import OptionHistoricalDataClient

        from ..config.settings import settings

        # Create client directly
        client = OptionHistoricalDataClient(
            api_key=settings.api_key, secret_key=settings.api_secret
        )

        # Try different parameter names for OptionSnapshotRequest
        try:
            request = OptionSnapshotRequest(symbols=[symbol])
        except TypeError:
            try:
                request = OptionSnapshotRequest(symbol_or_symbols=symbol)
            except TypeError:
                # Fallback: pass symbol directly if no request wrapper needed
                snapshot = client.get_option_snapshot(symbol)
                # Format the direct response
                if not snapshot:
                    return f"No snapshot data found for {symbol}"
                return f"""
Option Snapshot for {symbol}:
============================
{snapshot}
"""

        snapshot = client.get_option_snapshot(request)

        if not snapshot:
            return f"No snapshot data found for {symbol}"

        return f"""
Option Snapshot for {symbol}:
============================
Latest Quote:
  Ask: ${snapshot.latest_quote.ask} x {snapshot.latest_quote.ask_size}
  Bid: ${snapshot.latest_quote.bid} x {snapshot.latest_quote.bid_size}

Latest Trade:
  Price: ${snapshot.latest_trade.price}
  Size: {snapshot.latest_trade.size}
  Exchange: {snapshot.latest_trade.exchange}

Greeks (if available):
  Delta: {getattr(snapshot, "delta", "N/A")}
  Gamma: {getattr(snapshot, "gamma", "N/A")}
  Theta: {getattr(snapshot, "theta", "N/A")}
  Vega: {getattr(snapshot, "vega", "N/A")}

Implied Volatility: {getattr(snapshot, "implied_volatility", "N/A")}
Open Interest: {getattr(snapshot, "open_interest", "N/A")}
"""

    except Exception as e:
        return f"Error fetching option snapshot: {str(e)}"
