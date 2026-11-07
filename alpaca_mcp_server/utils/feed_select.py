"""Pick the market-data feed for *live* (latest-print) requests: BOATS overnight, SIP otherwise.

The overnight session (Blue Ocean ATS, "BOATS") runs 20:00-04:00 ET on the
nights before trading days (Sun-Thu nights, holiday-aware). During it the
consolidated SIP tape is silent, so the latest trade/quote/minute bar must come
from BOATS. Outside it BOATS has nothing, and SIP stays the feed.

BOATS is ONLY for live prints. Its daily bars cover just the overnight session
(SOXL 2026-11-05: 11.1M shares vs SIP's 549M; close $62.07 vs SIP $40.87), so
daily bars and any session-level numbers always stay on SIP.

Needs alpaca-py >= 0.41 for ``DataFeed.BOATS`` (pinned >= 0.45.0).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from alpaca.data.enums import DataFeed

from .timezone_utils import ET, now_et
from .trading_calendar import _NYSE


def _is_trading_day(d: date) -> bool:
    try:
        return len(_NYSE.valid_days(start_date=d, end_date=d)) > 0
    except Exception:  # calendar failure: fall back to Mon-Fri
        return d.weekday() < 5


def overnight_active(as_of: datetime | None = None) -> bool:
    """True during the BOATS overnight session (20:00-04:00 ET before a trading day)."""
    t = now_et() if as_of is None else as_of.astimezone(ET)
    if t.hour >= 20:
        return _is_trading_day(t.date() + timedelta(days=1))
    if t.hour < 4:
        return _is_trading_day(t.date())
    return False


def live_feed(as_of: datetime | None = None) -> DataFeed:
    """Feed for latest-print requests right now: BOATS overnight, else SIP."""
    return DataFeed.BOATS if overnight_active(as_of) else DataFeed.SIP


def feed_label(feed: DataFeed) -> str:
    """Human label for tool output, e.g. "BOATS (overnight)" or "SIP"."""
    return "BOATS (overnight)" if feed == DataFeed.BOATS else feed.value.upper()
