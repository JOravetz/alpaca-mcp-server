"""Market information and calendar tools."""

from datetime import datetime

import pytz

from ..config.settings import get_trading_client


async def get_market_clock() -> str:
    """
    Retrieves and formats current market status and next open/close times.

    Checks both regular market hours (9:30 AM - 4:00 PM) and extended hours (4:00 AM - 8:00 PM).
    Returns "Yes" for Is Open if within extended hours on a trading day.

    Returns:
        str: Formatted string containing:
            - Current Time
            - Market Open Status (includes extended hours)
            - Next Open Time
            - Next Close Time
    """
    try:
        client = get_trading_client()
        clock = client.get_clock()

        # Get current time in EDT/EST
        et_tz = pytz.timezone("America/New_York")
        current_et = datetime.now(et_tz)
        current_hour = current_et.hour
        current_minute = current_et.minute

        # Check if it's a trading day (next_open is today)
        next_open_et = clock.next_open.astimezone(et_tz) if clock.next_open else None
        is_trading_day = next_open_et and next_open_et.date() == current_et.date()

        # Check extended hours (4:00 AM to 8:00 PM ET)
        in_extended_hours = False
        if is_trading_day and (
            4 <= current_hour < 20 or current_hour == 20 and current_minute == 0
        ):
            in_extended_hours = True

        # Use regular market status OR extended hours
        is_open = clock.is_open or in_extended_hours

        return f"""
Market Status:
-------------
Current Time: {clock.timestamp}
Is Open: {"Yes" if is_open else "No"}
Next Open: {clock.next_open}
Next Close: {clock.next_close}
"""
    except Exception as e:
        return f"Error fetching market clock: {str(e)}"


async def get_market_calendar(start_date: str, end_date: str) -> str:
    """
    Retrieves and formats market calendar for specified date range.

    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format

    Returns:
        str: Formatted string containing market calendar information
    """
    try:
        client = get_trading_client()
        # Different API versions may use different parameter names
        try:
            calendar = client.get_calendar(start=start_date, end=end_date)
        except TypeError:
            # Try alternative parameter names
            try:
                calendar = client.get_calendar(start_date=start_date, end_date=end_date)
            except TypeError:
                calendar = client.get_calendar()
        result = f"Market Calendar ({start_date} to {end_date}):\n----------------------------\n"
        for day in calendar:
            result += f"Date: {day.date}, Open: {day.open}, Close: {day.close}\n"
        return result
    except Exception as e:
        return f"Error fetching market calendar: {str(e)}"
