"""Watchlist management tools."""

from alpaca.trading.requests import CreateWatchlistRequest, UpdateWatchlistRequest

from ..config.settings import get_trading_client


async def create_watchlist(name: str, symbols: list[str]) -> str:
    """
    Creates a new watchlist with specified symbols.

    Args:
        name (str): Name of the watchlist
        symbols (List[str]): List of symbols to include in the watchlist

    Returns:
        str: Confirmation message with watchlist creation status
    """
    try:
        client = get_trading_client()
        watchlist_data = CreateWatchlistRequest(name=name, symbols=symbols)
        client.create_watchlist(watchlist_data)
        return f"Watchlist '{name}' created successfully with {len(symbols)} symbols."
    except Exception as e:
        return f"Error creating watchlist: {str(e)}"


async def get_watchlists() -> str:
    """Get all watchlists for the account."""
    try:
        client = get_trading_client()
        watchlists = client.get_watchlists()
        result = "Watchlists:\n------------\n"
        for wl in watchlists:
            if hasattr(wl, "name"):
                result += f"Name: {wl.name}\n"
                result += f"ID: {wl.id}\n"
                result += f"Created: {wl.created_at}\n"
                result += f"Updated: {wl.updated_at}\n"
            else:
                result += f"Watchlist: {wl}\n"
            result += f"Symbols: {', '.join(getattr(wl, 'symbols', []) or [])}\n\n"
        return result
    except Exception as e:
        return f"Error fetching watchlists: {str(e)}"


async def update_watchlist(
    watchlist_id: str, name: str | None = None, symbols: list[str] | None = None
) -> str:
    """Update an existing watchlist."""
    try:
        client = get_trading_client()
        update_request = UpdateWatchlistRequest(name=name, symbols=symbols)
        watchlist = client.update_watchlist_by_id(watchlist_id, update_request)
        name_str = getattr(watchlist, "name", str(watchlist))
        return f"Watchlist updated successfully: {name_str}"
    except Exception as e:
        return f"Error updating watchlist: {str(e)}"
