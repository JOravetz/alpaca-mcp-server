"""Enhanced market clock with extended hours awareness."""

from datetime import time, timedelta

from ..config.settings import get_trading_client
from ..utils.timezone_utils import get_eastern_time


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

        # Define trading sessions
        premarket_start = time(4, 0)  # 4:00 AM
        market_open = time(9, 30)  # 9:30 AM
        market_close = time(16, 0)  # 4:00 PM
        postmarket_end = time(20, 0)  # 8:00 PM

        # Determine current session
        if premarket_start <= current_time < market_open:
            session = "pre_market"
            session_status = "Pre-market trading active"
            extended_hours = True
            next_session = "Regular market opens"
            next_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

        elif market_open <= current_time < market_close:
            session = "regular_market"
            session_status = "Regular market hours"
            extended_hours = False
            next_session = "After-hours begins"
            next_time = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

        elif market_close <= current_time < postmarket_end:
            session = "post_market"
            session_status = "After-hours trading active"
            extended_hours = True
            next_session = "Markets close"
            next_time = now_et.replace(hour=20, minute=0, second=0, microsecond=0)

        else:
            session = "closed"
            session_status = "Markets closed"
            extended_hours = False

            # Determine next opening
            if current_time >= postmarket_end:
                # After 8 PM - next is pre-market tomorrow
                next_session = "Pre-market opens"
                next_time = (now_et + timedelta(days=1)).replace(
                    hour=4, minute=0, second=0, microsecond=0
                )
            else:
                # Before 4 AM - next is pre-market today
                next_session = "Pre-market opens"
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
• Next Open: {clock.next_open.strftime("%Y-%m-%d %H:%M:%S %Z")}
• Next Close: {clock.next_close.strftime("%Y-%m-%d %H:%M:%S %Z")}

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
