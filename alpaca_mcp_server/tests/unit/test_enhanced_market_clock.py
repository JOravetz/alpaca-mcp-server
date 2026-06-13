"""Unit tests for get_extended_market_clock session classification.

Regression coverage for the weekend bug: the session state must be driven by
the trading calendar (weekend/holiday aware), not by time-of-day alone. On a
weekend the tool must report "Markets closed" even though the wall-clock time
falls inside the 4:00 AM - 9:30 AM pre-market window.

Only the Alpaca trading client is mocked; real datetime objects are used so
the tool's time math (.time(), .date(), .replace(), arithmetic) runs for real.
"""

import sys
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools.enhanced_market_clock import (  # noqa: E402
    get_extended_market_clock,
)

ET = timezone(timedelta(hours=-4))  # EDT

# Monday 2026-06-15 regular session bounds, used by several cases.
MON_OPEN = datetime(2026, 6, 15, 9, 30, tzinfo=ET)
MON_CLOSE = datetime(2026, 6, 15, 16, 0, tzinfo=ET)


def _make_clock(is_open, next_open, next_close):
    clock = MagicMock()
    clock.is_open = is_open
    clock.next_open = next_open
    clock.next_close = next_close
    clock.timestamp = next_open
    return clock


def _make_calendar_day(d, open_t, close_t):
    day = MagicMock()
    day.date = d
    day.open = open_t
    day.close = close_t
    return day


def _make_client(clock, calendar_days):
    client = MagicMock()
    client.get_clock.return_value = clock
    client.get_calendar.return_value = calendar_days
    return client


def _section(output, prefix):
    """Pull the value after 'Prefix: ' from the rendered clock output."""
    line = next(line for line in output.splitlines() if line.startswith(prefix))
    return line.split(": ", 1)[1].strip()


async def _run(now_et, clock, calendar_days):
    client = _make_client(clock, calendar_days)
    with (
        patch(
            "alpaca_mcp_server.tools.enhanced_market_clock.get_trading_client",
            return_value=client,
        ),
        patch(
            "alpaca_mcp_server.tools.enhanced_market_clock.get_eastern_time",
            return_value=(now_et, "EDT"),
        ),
    ):
        return await get_extended_market_clock()


class TestExtendedMarketClockWeekend:
    """The session must respect trading days, not just time-of-day."""

    @pytest.mark.asyncio
    async def test_saturday_morning_reports_closed(self):
        """Sat 08:42 ET sits in the pre-market time window but is NOT a
        trading day, so it must report closed and point at the next open."""
        now_et = datetime(2026, 6, 13, 8, 42, tzinfo=ET)
        clock = _make_clock(False, MON_OPEN, MON_CLOSE)
        # Empty calendar for today => weekend, not a trading day.
        output = await _run(now_et, clock, [])

        assert _section(output, "Current Session") == "Markets closed"
        assert _section(output, "Extended Hours") == "No"
        assert _section(output, "Next Event") == "Pre-market opens"
        # Must NOT regress to the time-of-day-only behavior.
        assert "Pre-market trading active" not in output

    @pytest.mark.asyncio
    async def test_weekday_premarket_reports_active(self):
        """Contrast case: the same 08:42 clock time on a real trading day must
        report pre-market active, proving the calendar gating discriminates
        rather than always reporting closed."""
        now_et = datetime(2026, 6, 15, 8, 42, tzinfo=ET)
        clock = _make_clock(False, MON_OPEN, MON_CLOSE)
        today = _make_calendar_day(date(2026, 6, 15), dtime(9, 30), dtime(16, 0))
        output = await _run(now_et, clock, [today])

        assert _section(output, "Current Session") == "Pre-market trading active"
        assert _section(output, "Extended Hours") == "Yes"
        assert _section(output, "Next Event") == "Regular market opens"
