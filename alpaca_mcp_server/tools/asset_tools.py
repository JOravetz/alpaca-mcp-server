"""Asset tools for retrieving information about tradeable assets."""

from alpaca.trading.enums import AssetClass, AssetStatus
from alpaca.trading.requests import GetAssetsRequest

from ..config.settings import get_trading_client


async def get_all_assets(
    status: str = None,
    asset_class: str = None,
    exchange: str = None,
    attributes: str = None,
    tradable_only: bool = True,
    max_symbol_length: int = 4,
) -> str:
    """
    Get all available assets with optional filtering.

    Args:
        status: Asset status (active, inactive)
        asset_class: Asset class (us_equity, crypto, etc.)
        exchange: Exchange name
        attributes: Asset attributes
        tradable_only: If True, only return tradable assets (default: True)
        max_symbol_length: Maximum symbol length to filter by (default: 4 for symbols with 4 or fewer characters)

    Returns:
        Formatted string with asset information
    """
    try:
        client = get_trading_client()

        # Build filter request
        request_params = {}

        if status:
            if status.lower() == "active":
                request_params["status"] = AssetStatus.ACTIVE
            elif status.lower() == "inactive":
                request_params["status"] = AssetStatus.INACTIVE

        if asset_class:
            if asset_class.lower() == "us_equity":
                request_params["asset_class"] = AssetClass.US_EQUITY
            elif asset_class.lower() == "crypto":
                request_params["asset_class"] = AssetClass.CRYPTO

        # Create request
        if request_params:
            request = GetAssetsRequest(**request_params)
            assets = client.get_all_assets(request)
        else:
            assets = client.get_all_assets()

        # Apply additional filters
        if exchange:
            assets = [asset for asset in assets if asset.exchange == exchange.upper()]

        # Filter for tradable assets only if requested
        if tradable_only:
            assets = [asset for asset in assets if asset.tradable]

        # Apply attributes filter after basic filters
        if attributes and attributes.lower() == "shortable":
            assets = [asset for asset in assets if asset.shortable]

        # Filter by symbol length if requested
        if max_symbol_length is not None:
            assets = [asset for asset in assets if len(asset.symbol) <= max_symbol_length]

        # Format output
        total_count = len(assets)

        # Show first 20 assets to avoid overwhelming output
        display_assets = assets[:20]

        result = f"Assets Found: {total_count}\n"
        result += f"Showing: First {len(display_assets)} assets\n"
        result += "=" * 80 + "\n"

        for asset in display_assets:
            result += f"Symbol: {asset.symbol}\n"
            result += f"  Name: {asset.name}\n"
            result += f"  Class: {asset.asset_class}\n"
            result += f"  Exchange: {asset.exchange}\n"
            result += f"  Status: {asset.status}\n"
            result += f"  Tradable: {'Yes' if asset.tradable else 'No'}\n"
            result += f"  Marginable: {'Yes' if asset.marginable else 'No'}\n"
            result += f"  Shortable: {'Yes' if asset.shortable else 'No'}\n"
            result += "-" * 40 + "\n"

        if total_count > 20:
            result += f"\n... and {total_count - 20} more assets\n"
            result += "Use more specific filters to narrow results\n"

        return result

    except Exception as e:
        return f"Error retrieving assets: {str(e)}"


async def get_asset_info(symbol: str) -> str:
    """
    Get detailed information about a specific asset.

    Args:
        symbol: Stock symbol to get information for

    Returns:
        Formatted string with detailed asset information
    """
    try:
        client = get_trading_client()
        asset = client.get_asset(symbol.upper())

        result = f"Asset Information: {asset.symbol}\n"
        result += "=" * 50 + "\n"
        result += f"Name: {asset.name}\n"
        result += f"Asset Class: {asset.asset_class}\n"
        result += f"Exchange: {asset.exchange}\n"
        result += f"Status: {asset.status}\n"
        result += f"Tradable: {'Yes' if asset.tradable else 'No'}\n"
        result += f"Marginable: {'Yes' if asset.marginable else 'No'}\n"
        result += f"Shortable: {'Yes' if asset.shortable else 'No'}\n"
        result += f"Easy to Borrow: {'Yes' if asset.easy_to_borrow else 'No'}\n"
        result += f"Fractionable: {'Yes' if asset.fractionable else 'No'}\n"

        # Add attributes if available
        if hasattr(asset, "attributes") and asset.attributes:
            result += f"Attributes: {', '.join(asset.attributes)}\n"

        return result

    except Exception as e:
        return f"Error retrieving asset information for {symbol}: {str(e)}"
