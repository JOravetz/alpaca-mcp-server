"""Corporate actions tools module."""

from datetime import date, timedelta

from alpaca.trading.enums import CorporateActionDateType, CorporateActionType
from alpaca.trading.models import CorporateActionAnnouncement
from alpaca.trading.requests import GetCorporateAnnouncementsRequest

from ..config.settings import get_trading_client


async def get_corporate_announcements(
    ca_types: list[str],
    since: str,
    until: str,
    symbol: str | None = None,
    cusip: str | None = None,
    date_type: str | None = None,
) -> str:
    """
    Get corporate action announcements for specified criteria.

    Args:
        ca_types: List of corporate action types ("dividend", "merger", "spinoff", "split")
        since: Start date in YYYY-MM-DD format (inclusive) - automatically adjusted if >90 days from until
        until: End date in YYYY-MM-DD format (inclusive)
        symbol: Optional symbol filter
        cusip: Optional CUSIP filter
        date_type: Optional date type filter ("declaration_date", "ex_date", "record_date", "payable_date")

    Note:
        Alpaca API limits date ranges to 90 days. If the requested range exceeds this limit,
        the 'since' date will be automatically adjusted to 90 days before the 'until' date.

    Returns:
        Formatted corporate announcements information
    """
    try:
        trading_client = get_trading_client()

        # Convert string ca_types to enum values
        ca_type_enums = []
        for ca_type in ca_types:
            if ca_type.lower() == "dividend":
                ca_type_enums.append(CorporateActionType.DIVIDEND)
            elif ca_type.lower() == "merger":
                ca_type_enums.append(CorporateActionType.MERGER)
            elif ca_type.lower() == "spinoff":
                ca_type_enums.append(CorporateActionType.SPINOFF)
            elif ca_type.lower() == "split":
                ca_type_enums.append(CorporateActionType.SPLIT)

        # Convert date strings to date objects
        since_date = date.fromisoformat(since)
        until_date = date.fromisoformat(until)

        # Validate date range - Alpaca limits to 90 days (use 89 to be safe)
        date_diff = (until_date - since_date).days
        result_note = ""

        if date_diff >= 90:
            # Adjust the since date to be exactly 89 days before until date
            original_since = since_date
            since_date = until_date - timedelta(days=89)
            final_diff = (until_date - since_date).days
            result_note = f"Note: Date range adjusted from {date_diff} days to {final_diff} days (Alpaca API 90-day limit). Changed from {original_since} to {since_date}.\n\n"

        # Convert date_type if provided
        date_type_enum = None
        if date_type:
            if date_type.lower() == "declaration_date":
                date_type_enum = CorporateActionDateType.DECLARATION_DATE
            elif date_type.lower() == "ex_date":
                date_type_enum = CorporateActionDateType.EX_DATE
            elif date_type.lower() == "record_date":
                date_type_enum = CorporateActionDateType.RECORD_DATE
            elif date_type.lower() == "payable_date":
                date_type_enum = CorporateActionDateType.PAYABLE_DATE

        # Create request
        request = GetCorporateAnnouncementsRequest(
            ca_types=ca_type_enums,
            since=since_date,
            until=until_date,
            symbol=symbol,
            cusip=cusip,
            date_type=date_type_enum,
        )

        # Get announcements
        announcements = trading_client.get_corporate_announcements(request)

        if not announcements:
            return f"{result_note}No corporate announcements found for the specified criteria.\n\nFilters:\n- Types: {', '.join(ca_types)}\n- Date Range: {since_date} to {until_date}\n- Symbol: {symbol or 'All'}"

        # Format results
        result = f"{result_note}Corporate Announcements ({len(announcements)} found):\n"
        result += "=" * 60 + "\n\n"

        for announcement in announcements:
            result += f"Symbol: {announcement.initiating_symbol}\n"  # type: ignore[union-attr]
            result += f"Type: {announcement.ca_type.value.upper()}\n"  # type: ignore[union-attr]

            if isinstance(announcement, CorporateActionAnnouncement) and announcement.ca_sub_type:  # type: ignore[name-defined]
                result += f"Sub-Type: {announcement.ca_sub_type}\n"

            # Key dates
            if announcement.declaration_date:  # type: ignore[union-attr]
                result += f"Declaration Date: {announcement.declaration_date}\n"  # type: ignore[union-attr]
            if announcement.ex_date:  # type: ignore[union-attr]
                result += f"Ex-Date: {announcement.ex_date}\n"  # type: ignore[union-attr]
            if announcement.record_date:  # type: ignore[union-attr]
                result += f"Record Date: {announcement.record_date}\n"  # type: ignore[union-attr]
            if announcement.payable_date:  # type: ignore[union-attr]
                result += f"Payable Date: {announcement.payable_date}\n"  # type: ignore[union-attr]

            # Financial details
            if isinstance(announcement, CorporateActionAnnouncement) and announcement.cash:  # type: ignore[name-defined]
                result += f"Cash Amount: ${announcement.cash:.4f} per share\n"

            if isinstance(announcement, CorporateActionAnnouncement) and announcement.old_rate:  # type: ignore[name-defined]
                result += f"Old Rate: {announcement.old_rate}\n"
            if isinstance(announcement, CorporateActionAnnouncement) and announcement.new_rate:  # type: ignore[name-defined]
                result += f"New Rate: {announcement.new_rate}\n"

            if isinstance(announcement, CorporateActionAnnouncement) and announcement.target_symbol:  # type: ignore[name-defined]
                result += f"Target Symbol: {announcement.target_symbol}\n"

            result += "-" * 40 + "\n"

        return result

    except Exception as e:
        return f"Error retrieving corporate announcements: {str(e)}"


__all__ = ["get_corporate_announcements"]
