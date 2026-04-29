"""Options trading tools and contract information."""

from datetime import date
from typing import Any

from alpaca.data.enums import OptionsFeed
from alpaca.data.models import Quote
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
            request_params["expiration_date"] = expiration_date  # type: ignore[assignment]
        if strike_price_gte:
            request_params["strike_price_gte"] = float(strike_price_gte)  # type: ignore[assignment]
        if strike_price_lte:
            request_params["strike_price_lte"] = float(strike_price_lte)  # type: ignore[assignment]

        request = OptionChainRequest(**request_params)  # type: ignore[arg-type]
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
                # OCC format: [UNDERLYING][YYMMDD][C|P][STRIKE_8DIGITS]. Underlying length varies
                # (e.g. AMD=3, AAPL=4, KIDZ1=5 for adjusted symbols), so anchor from the right.
                try:
                    exp_part = symbol[-15:-9]  # 6 chars immediately before C/P
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

            # Type check for proper Quote access
            if not isinstance(q, Quote):
                return f"Error: Received unexpected quote format: {type(q)}"

            # alpaca-py Quote uses ask_price / bid_price (not ask / bid).
            # Render None as 0.00 so the downstream parser regex `[\d.]+`
            # still matches on illiquid / stale contracts.
            ask_raw = getattr(q, "ask_price", None)
            bid_raw = getattr(q, "bid_price", None)
            ask_price = ask_raw if ask_raw is not None else 0.0
            bid_price = bid_raw if bid_raw is not None else 0.0
            ask_size = getattr(q, "ask_size", None) or 0
            bid_size = getattr(q, "bid_size", None) or 0

            if ask_raw is None and bid_raw is None:
                return f"No quote data found for {symbol} (illiquid or stale contract)"

            return f"""
Latest Quote for {symbol}:
-------------------------
Ask Price: ${ask_price}
Ask Size: {ask_size}
Bid Price: ${bid_price}
Bid Size: {bid_size}
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

        # alpaca-py uses `symbol_or_symbols` for OptionSnapshotRequest. Older
        # versions accepted `symbols=[...]` but now raise pydantic
        # ValidationError, which the previous TypeError-only handler missed.
        request = OptionSnapshotRequest(symbol_or_symbols=symbol)

        snapshot = client.get_option_snapshot(request)

        if not snapshot:
            return f"No snapshot data found for {symbol}"

        # alpaca-py returns {symbol: OptionsSnapshot} rather than a bare
        # snapshot object. Unwrap it before reading attributes.
        if isinstance(snapshot, dict):
            snapshot = snapshot.get(symbol)
            if snapshot is None:
                return f"No snapshot data found for {symbol}"

        # Open Interest lives on the Trading API's OptionContract model,
        # not on the historical-data OptionsSnapshot. Fetch it separately
        # and merge. Failures are non-fatal — OI just renders as N/A.
        open_interest: Any = "N/A"
        open_interest_date: Any = "N/A"
        close_price: Any = "N/A"
        try:
            from ..config.settings import get_trading_client
            trading_client = get_trading_client()
            contract = trading_client.get_option_contract(symbol)
            open_interest = getattr(contract, "open_interest", None) or "N/A"
            open_interest_date = getattr(contract, "open_interest_date", None) or "N/A"
            close_price = getattr(contract, "close_price", None) or "N/A"
        except Exception:
            pass

        # alpaca-py field names:
        #   Quote  → ask_price / bid_price (NOT ask / bid)
        #   OptionsSnapshot.greeks → delta / gamma / theta / vega / rho
        #   OptionsSnapshot has no open_interest field — fetched above
        lq = getattr(snapshot, "latest_quote", None)
        lt = getattr(snapshot, "latest_trade", None)
        greeks = getattr(snapshot, "greeks", None)

        ask = getattr(lq, "ask_price", None) if lq else None
        bid = getattr(lq, "bid_price", None) if lq else None
        ask_size = getattr(lq, "ask_size", None) if lq else None
        bid_size = getattr(lq, "bid_size", None) if lq else None
        last_price = getattr(lt, "price", None) if lt else None
        last_size = getattr(lt, "size", None) if lt else None
        last_exchange = getattr(lt, "exchange", "N/A") if lt else "N/A"

        delta = getattr(greeks, "delta", None) if greeks else None
        gamma = getattr(greeks, "gamma", None) if greeks else None
        theta = getattr(greeks, "theta", None) if greeks else None
        vega = getattr(greeks, "vega", None) if greeks else None

        def _num(v: Any, default: float = 0.0) -> Any:
            return v if v is not None else default

        return f"""
Option Snapshot for {symbol}:
============================
Latest Quote:
  Ask: ${_num(ask)} x {_num(ask_size, 0)}
  Bid: ${_num(bid)} x {_num(bid_size, 0)}

Latest Trade:
  Price: ${_num(last_price)}
  Size: {_num(last_size, 0)}
  Exchange: {last_exchange}

Greeks (if available):
  Delta: {delta if delta is not None else "N/A"}
  Gamma: {gamma if gamma is not None else "N/A"}
  Theta: {theta if theta is not None else "N/A"}
  Vega: {vega if vega is not None else "N/A"}

Implied Volatility: {getattr(snapshot, "implied_volatility", "N/A")}
Open Interest: {open_interest}
Open Interest Date: {open_interest_date}
Prior Close: ${close_price}
"""

    except Exception as e:
        return f"Error fetching option snapshot: {str(e)}"
