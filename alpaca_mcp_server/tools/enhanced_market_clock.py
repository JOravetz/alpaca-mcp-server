"""Enhanced market clock with extended hours awareness."""

from datetime import datetime, time
from typing import Any

from alpaca.trading.requests import GetCalendarRequest

from ..config.settings import get_trading_client
from ..utils.timezone_utils import fmt_et, get_eastern_time


def _as_time(value: datetime | time) -> time:
    """The time-of-day part of a calendar open/close (datetime or time)."""
    return value.time() if isinstance(value, datetime) else value


async def get_extended_market_clock() -> str:
    """Enhanced market clock with pre/post market sessions."""
    try:
        client = get_trading_client()
        clock = client.get_clock()

        # Type check for proper Clock access
        if isinstance(clock, dict):
            return f"Error: Received dict response instead of Clock: {clock}"

        # Get current Eastern time
        now_et, tz_name = get_eastern_time()
        current_time = now_et.time()
        today = now_et.date()

        # Extended-hours window boundaries (fixed regardless of session length)
        premarket_start = time(4, 0)  # 4:00 AM
        postmarket_end = time(20, 0)  # 8:00 PM

        # Authoritative next regular open from Alpaca (already skips weekends/holidays).
        next_open_et = clock.next_open.astimezone(now_et.tzinfo) if clock.next_open else None

        # Determine whether *today* is an actual trading day (handles weekends AND
        # market holidays) and fetch today's real regular-session bounds (handles
        # early-close half-days) from the trading calendar. Fall back to the Alpaca
        # clock if the calendar lookup is unavailable.
        market_open = time(9, 30)  # 9:30 AM
        market_close = time(16, 0)  # 4:00 PM
        is_trading_day = clock.is_open or bool(next_open_et and next_open_et.date() == today)
        try:
            calendar = client.get_calendar(filters=GetCalendarRequest(start=today, end=today))
            # Duck-typed on .date: entries may be Calendar models or ISO-dated stand-ins.
            today_entry: Any = next(
                (d for d in calendar if str(getattr(d, "date", ""))[:10] == today.isoformat()),
                None,
            )
            if today_entry is not None:
                is_trading_day = True
                # alpaca-py's Calendar.open/close are full datetimes; the session
                # comparisons below are against now_et.time(), so keep the time part
                # (a value that is already a time is used as-is).
                market_open = _as_time(today_entry.open)
                market_close = _as_time(today_entry.close)
            elif calendar:
                # Calendar returned but today is absent -> not a trading day.
                is_trading_day = False
        except Exception:
            pass  # keep the clock-derived fallback for is_trading_day

        # Determine current session (only trading days have live sessions)
        if is_trading_day and premarket_start <= current_time < market_open:
            session = "pre_market"
            session_status = "Pre-market trading active"
            extended_hours = True
            next_session = "Regular market opens"
            next_time = now_et.replace(
                hour=market_open.hour,
                minute=market_open.minute,
                second=0,
                microsecond=0,
            )

        elif is_trading_day and market_open <= current_time < market_close:
            session = "regular_market"
            session_status = "Regular market hours"
            extended_hours = False
            next_session = "After-hours begins"
            next_time = now_et.replace(
                hour=market_close.hour,
                minute=market_close.minute,
                second=0,
                microsecond=0,
            )

        elif is_trading_day and market_close <= current_time < postmarket_end:
            session = "post_market"
            session_status = "After-hours trading active"
            extended_hours = True
            next_session = "Markets close"
            next_time = now_et.replace(hour=20, minute=0, second=0, microsecond=0)

        else:
            session = "closed"
            session_status = "Markets closed"
            extended_hours = False

            # Next extended-hours session starts at 4:00 AM on the next trading day.
            # next_open_et already accounts for weekends and holidays.
            next_session = "Pre-market opens"
            if next_open_et is not None:
                next_time = next_open_et.replace(hour=4, minute=0, second=0, microsecond=0)
            else:
                next_time = now_et.replace(hour=4, minute=0, second=0, microsecond=0)

        # Calculate time to next session
        time_to_next = next_time - now_et
        total_seconds = int(time_to_next.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        # Trading recommendations based on session
        trading_recommendations = {
            "pre_market": [
                "• Use limit orders for better execution",
                "• Expect wider bid-ask spreads",
                "• Lower volume and liquidity",
                "• Good for news/earnings reactions",
            ],
            "regular_market": [
                "• Full liquidity and tight spreads",
                "• All order types accepted",
                "• Optimal trading conditions",
                "• Market and stop orders work well",
            ],
            "post_market": [
                "• Reduced liquidity after 6:30 PM",
                "• Use limit orders recommended",
                "• Watch for earnings announcements",
                "• Some brokers limit order types",
            ],
            "closed": [
                "• No active trading sessions",
                "• Orders may be queued for next session",
                "• Good time for research and planning",
                "• Review and analyze positions",
            ],
        }

        # Market volatility indicators
        volatility_notes = {
            "pre_market": "Higher volatility expected",
            "regular_market": "Normal volatility patterns",
            "post_market": "Moderate to high volatility",
            "closed": "No market movement",
        }

        return f"""
Enhanced Market Clock
====================
Current Time (ET): {now_et.strftime(f"%Y-%m-%d %H:%M:%S {tz_name}")}
Current Session: {session_status}
Extended Hours: {"Yes" if extended_hours else "No"}
Volatility: {volatility_notes[session]}

Session Schedule:
• Pre-market:  4:00 AM - 9:30 AM ET
• Regular:     9:30 AM - 4:00 PM ET
• After-hours: 4:00 PM - 8:00 PM ET
• Closed:      8:00 PM - 4:00 AM ET

Next Event: {next_session}
Time Remaining: {hours}h {minutes}m

Alpaca API Status:
• Market Open: {clock.is_open}
• Next Open: {fmt_et(clock.next_open)}
• Next Close: {fmt_et(clock.next_close)}

Trading Recommendations:
{chr(10).join(trading_recommendations[session])}

Extended Hours Notes:
• Pre/post market: Set extended_hours=True in orders
• Limited liquidity: Wider spreads, slower fills
• Order types: Limit orders recommended over market orders
• Volume: Typically 5-10% of regular session volume
• Risk: Higher price volatility and gap risk
        """

    except Exception as e:
        return f"Error fetching enhanced market clock: {str(e)}"
