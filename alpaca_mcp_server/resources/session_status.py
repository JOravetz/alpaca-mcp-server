"""Market session status resource with extended hours awareness."""

from datetime import datetime, time

import pandas as pd
import pandas_market_calendars as mcal  # type: ignore[import-untyped]

from ..config.settings import get_trading_client


def get_eastern_time():
    """Get current time in Eastern timezone."""
    # Use pandas for proper timezone handling with DST
    return pd.Timestamp.now(tz="America/New_York")


async def get_session_status() -> dict:
    """Trading session and market status with extended hours awareness."""
    try:
        client = get_trading_client()
        clock = client.get_clock()

        # Get current Eastern time
        now_et = get_eastern_time()
        current_time = now_et.time()

        # Get NYSE calendar
        nyse = mcal.get_calendar("NYSE")

        # Check if today is a trading day
        today = now_et.date()
        schedule = nyse.schedule(start_date=today, end_date=today)
        is_trading_day = len(schedule) > 0

        # Define all trading sessions
        premarket_start = time(4, 0)  # 4:00 AM ET
        market_open = time(9, 30)  # 9:30 AM ET
        market_close = time(16, 0)  # 4:00 PM ET
        postmarket_end = time(20, 0)  # 8:00 PM ET

        # If it's not a trading day (weekend or holiday), market is closed
        if not is_trading_day:
            current_session = "closed"
            session_description = "Markets closed (weekend/holiday)"
            is_extended_hours = False
            progress_percent = None

            # Find next trading day
            next_trading_days = nyse.valid_days(
                start_date=today + pd.Timedelta(days=1),
                end_date=today + pd.Timedelta(days=7),
            )
            if len(next_trading_days) > 0:
                next_trading_day = next_trading_days[0].date()
                next_event = "market_open"
                next_event_time = pd.Timestamp(next_trading_day, tz="America/New_York").replace(
                    hour=9, minute=30, second=0, microsecond=0
                )
            else:
                # Fallback if no trading days found in next week
                next_event = "market_open"
                next_event_time = now_et + pd.Timedelta(days=1)

        # Determine current session for trading days
        elif premarket_start <= current_time < market_open:
            current_session = "pre_market"
            session_description = "Pre-market trading"
            is_extended_hours = True
            next_event = "market_open"
            next_event_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            progress_percent = None

        elif market_open <= current_time < market_close:
            current_session = "regular_market"
            session_description = "Regular market hours"
            is_extended_hours = False
            next_event = "market_close"
            next_event_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

            # Calculate session progress
            session_start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            session_end = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            session_duration = (session_end - session_start).total_seconds()
            elapsed = (now_et - session_start).total_seconds()
            progress_percent = max(0, min(100, (elapsed / session_duration) * 100))

        elif market_close <= current_time < postmarket_end:
            current_session = "post_market"
            session_description = "After-hours trading"
            is_extended_hours = True
            next_event = "markets_close"
            next_event_time = now_et.replace(hour=20, minute=0, second=0, microsecond=0)
            progress_percent = None

        else:
            current_session = "closed"
            session_description = "Markets closed"
            is_extended_hours = False
            progress_percent = None

            # Determine next opening
            if current_time >= postmarket_end:
                # After 8 PM - next is pre-market tomorrow (if it's a trading day)
                tomorrow = today + pd.Timedelta(days=1)
                tomorrow_schedule = nyse.schedule(start_date=tomorrow, end_date=tomorrow)
                if len(tomorrow_schedule) > 0:
                    next_event = "premarket_open"
                    next_event_time = pd.Timestamp(tomorrow, tz="America/New_York").replace(
                        hour=4, minute=0, second=0, microsecond=0
                    )
                else:
                    # Tomorrow is not a trading day, find next trading day
                    next_trading_days = nyse.valid_days(
                        start_date=tomorrow, end_date=tomorrow + pd.Timedelta(days=7)
                    )
                    if len(next_trading_days) > 0:
                        next_trading_day = next_trading_days[0].date()
                        next_event = "premarket_open"
                        next_event_time = pd.Timestamp(
                            next_trading_day, tz="America/New_York"
                        ).replace(hour=4, minute=0, second=0, microsecond=0)
                    else:
                        next_event = "premarket_open"
                        next_event_time = now_et + pd.Timedelta(days=1)
            else:
                # Before 4 AM - next is pre-market today
                next_event = "premarket_open"
                next_event_time = now_et.replace(hour=4, minute=0, second=0, microsecond=0)

        # Calculate time to next event
        time_to_next = next_event_time - now_et
        time_to_next_minutes = int(time_to_next.total_seconds() / 60)
        time_to_next_formatted = f"{time_to_next_minutes // 60}h {time_to_next_minutes % 60}m"

        # Session phase for regular market
        if current_session == "regular_market" and progress_percent is not None:
            if progress_percent < 5:
                session_phase = "opening"
            elif progress_percent < 25:
                session_phase = "morning"
            elif progress_percent < 75:
                session_phase = "midday"
            else:
                session_phase = "closing"
        else:
            session_phase = current_session

        # Trading recommendations based on session
        trading_notes = {
            "pre_market": [
                "Limited liquidity - use limit orders",
                "Wider bid-ask spreads expected",
                "News and earnings reactions common",
            ],
            "regular_market": [
                "Full liquidity available",
                "All order types accepted",
                "Optimal execution conditions",
            ],
            "post_market": [
                "Reduced liquidity after 6:30 PM",
                "Use limit orders for better fills",
                "Earnings and news reactions",
            ],
            "closed": [
                "No trading available",
                "Orders queued for next session",
                "Use this time for analysis and planning",
            ],
        }

        return {
            "current_session": current_session,
            "session_description": session_description,
            "session_phase": session_phase,
            "is_extended_hours": is_extended_hours,
            "alpaca_market_open": clock.is_open,  # type: ignore[union-attr]
            "progress_percent": (
                round(progress_percent, 1) if progress_percent is not None else None
            ),
            "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
            "next_event": next_event,
            "next_event_time": next_event_time.strftime("%Y-%m-%d %H:%M:%S ET"),
            "time_to_next_minutes": time_to_next_minutes,
            "time_to_next_formatted": time_to_next_formatted,
            "session_schedule": {
                "premarket": "4:00 AM - 9:30 AM ET",
                "regular": "9:30 AM - 4:00 PM ET",
                "postmarket": "4:00 PM - 8:00 PM ET",
                "closed": "8:00 PM - 4:00 AM ET",
            },
            "trading_notes": trading_notes.get(current_session, []),
            "alpaca_times": {
                "next_open": clock.next_open.isoformat(),  # type: ignore[union-attr]
                "next_close": clock.next_close.isoformat(),  # type: ignore[union-attr]
                "current_timestamp": clock.timestamp.isoformat(),  # type: ignore[union-attr]
            },
        }

    except Exception as e:
        return {
            "error": str(e),
            "current_session": "unknown",
            "session_description": "Unable to determine session",
            "current_time_et": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
