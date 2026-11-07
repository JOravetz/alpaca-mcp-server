"""NYSE trading-calendar helpers: resolve *trading* days, not sequential calendar days.

Tools/programs should size their lookback windows by TRADING days (holiday- and
weekend-aware) so results always run through the LATEST trading day instead of
guessing with ``timedelta(days=N)``. Backed by ``pandas_market_calendars`` (NYSE),
which is local (no API call) and already a project dependency.

Typical use for a "last N trading-day bars" request::

    from ..utils.trading_calendar import trading_days_window_start
    req = StockBarsRequest(..., start=trading_days_window_start(days),
                           end=datetime.now(UTC), limit=days, sort=Sort.DESC)
    # end MUST be aware: alpaca-py sends a naive datetime as UTC (5-6 h stale on a CST host).
    # sort=DESC + limit keeps the N most-recent (trading-day) bars; reverse for display.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import pandas_market_calendars as mcal  # type: ignore[import-untyped]

_NYSE = mcal.get_calendar("NYSE")


def _now_eastern(as_of: datetime | None = None) -> pd.Timestamp:
    """Current (or supplied) time as an America/New_York pandas Timestamp."""
    if as_of is None:
        return pd.Timestamp.now(tz="America/New_York")
    ts = pd.Timestamp(as_of)
    return (
        ts.tz_localize("America/New_York")
        if ts.tzinfo is None
        else ts.tz_convert("America/New_York")
    )


def _recent_valid_days(n: int, as_of: datetime | None = None) -> pd.DatetimeIndex:
    """The last ``n`` NYSE trading days on or before ``as_of`` (inclusive of today if it trades)."""
    n = max(int(n), 1)
    today = _now_eastern(as_of).normalize().date()
    # Look back generously (~1.7 calendar days per trading day + holiday pad) then trim.
    lookback = today - timedelta(days=int(n * 1.7) + 12)
    valid = _NYSE.valid_days(start_date=lookback, end_date=today)
    return valid[-n:] if len(valid) >= n else valid


def latest_trading_day(as_of: datetime | None = None) -> date:
    """The most recent NYSE trading day on or before now.

    Returns today's date if today is a trading day, otherwise the prior trading session
    (skipping weekends and holidays). Use to assert a report/tool is showing data from
    the latest trading day.
    """
    days = _recent_valid_days(1, as_of)
    if len(days) > 0:
        return days[-1].date()
    # Extreme fallback: walk back to the nearest weekday.
    d = _now_eastern(as_of).date()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def trading_days_window_start(days: int, as_of: datetime | None = None) -> datetime:
    """A naive-UTC ``start`` datetime spanning at least the last ``days`` NYSE trading days.

    Pair with ``sort=DESC`` + ``limit=days`` on a daily-bars request to return exactly the
    ``days`` most-recent trading-day bars (newest == latest trading day). Falls back to a
    wide calendar-day window if the calendar lookup yields nothing (never raises).
    """
    valid = _recent_valid_days(days, as_of)
    if len(valid) == 0:
        base = as_of or datetime.now()
        return base - timedelta(days=int(max(int(days), 1) * 1.7) + 12)
    start_ts = valid[0]
    # 00:00 UTC of the earliest trading day, minus a 1-day safety pad so its bar is included.
    # (limit + sort=DESC caps the result to the newest `days`, so an extra older day is harmless.)
    return datetime(start_ts.year, start_ts.month, start_ts.day) - timedelta(days=1)
