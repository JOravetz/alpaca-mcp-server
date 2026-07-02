"""Shared freshness-cutoff logic for scanner staleness gating.

A print is *fresh* iff its latestTrade timestamp is at or after 04:00 ET
(pre-market start) of the previous trading day per the Alpaca market
calendar. Halted/delisted symbols keep their last pre-halt print in
snapshots indefinitely; this cutoff is what filters them out of scanner
results (see docs/superpowers/specs/2026-07-01-scanner-freshness-gating-design.md).
"""

import logging
import time as _time
from datetime import date, datetime, time, timedelta

import pytz

logger = logging.getLogger(__name__)

_EASTERN = pytz.timezone("America/New_York")
_PREMARKET_START = time(4, 0)
_CACHE_TTL_SECONDS = 900  # 15 minutes
_FALLBACK_WINDOW_HOURS = 96

_cache: dict = {"value": None, "expires": 0.0}


def freshness_cutoff() -> tuple[int, str]:
    """Return (cutoff_epoch_seconds, source).

    source is "calendar" normally, or "fallback" (now - 96h) when the
    market calendar is unavailable. Results are cached for 15 minutes.
    """
    now = _time.time()
    if _cache["value"] is not None and now < _cache["expires"]:
        return _cache["value"]

    try:
        value = (_calendar_cutoff(), "calendar")
    except Exception as exc:
        logger.warning("Market calendar unavailable, using 96h fallback: %s", exc)
        value = (int(now - _FALLBACK_WINDOW_HOURS * 3600), "fallback")

    _cache["value"] = value
    _cache["expires"] = now + _CACHE_TTL_SECONDS
    return value


def _calendar_cutoff() -> int:
    """Cutoff = 04:00 ET on the most recent trading day before today (ET)."""
    from alpaca.trading.requests import GetCalendarRequest

    from ..config.settings import get_trading_client

    client = get_trading_client()
    today_et = datetime.now(_EASTERN).date()
    calendar = client.get_calendar(
        filters=GetCalendarRequest(
            start=(today_et - timedelta(days=10)).isoformat(),
            end=today_et.isoformat(),
        )
    )
    session_dates = sorted(
        d
        for d in (_session_date(entry) for entry in calendar)
        if d is not None and d < today_et
    )
    if not session_dates:
        raise RuntimeError("no prior trading sessions in calendar response")
    cutoff_dt = _EASTERN.localize(
        datetime.combine(session_dates[-1], _PREMARKET_START)
    )
    return int(cutoff_dt.timestamp())


def _session_date(entry) -> date | None:
    """Calendar entries expose .date as a date or an ISO string."""
    try:
        return date.fromisoformat(str(entry.date)[:10])
    except (AttributeError, ValueError):
        return None


def parse_iso_epoch(iso_timestamp: str | None) -> int | None:
    """ISO-8601 UTC timestamp -> epoch seconds; None if unparseable.

    Fractional seconds of any precision are ignored (Alpaca uses
    nanoseconds, which datetime.fromisoformat cannot digest).
    """
    if not iso_timestamp:
        return None
    try:
        head = iso_timestamp.replace("Z", "+00:00")
        if "." in head:
            base, _, frac = head.partition(".")
            plus = frac.find("+")
            head = base + (frac[plus:] if plus != -1 else "+00:00")
        return int(datetime.fromisoformat(head).timestamp())
    except (ValueError, AttributeError, TypeError):
        return None


def is_stale(iso_timestamp: str | None, cutoff_epoch: int) -> bool:
    """True iff the print predates the cutoff. Fail closed: a missing or
    unparseable timestamp is stale whenever a cutoff is active."""
    if cutoff_epoch <= 0:
        return False
    epoch = parse_iso_epoch(iso_timestamp)
    if epoch is None:
        return True
    return epoch < cutoff_epoch


def format_trade_age(iso_timestamp: str | None) -> str:
    """Render '2026-07-01 19:59 ET (1h 26m ago)' for scanner output."""
    epoch = parse_iso_epoch(iso_timestamp)
    if epoch is None:
        return "unknown"
    dt_et = datetime.fromtimestamp(epoch, _EASTERN)
    age = max(0, int(_time.time()) - epoch)
    days, rem = divmod(age, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        age_str = f"{days}d {hours}h ago"
    elif hours:
        age_str = f"{hours}h {minutes}m ago"
    else:
        age_str = f"{minutes}m ago"
    return f"{dt_et.strftime('%Y-%m-%d %H:%M')} ET ({age_str})"


def format_cutoff(cutoff_epoch: int) -> str:
    """Render the cutoff as '2026-06-30 04:00 ET'."""
    return datetime.fromtimestamp(cutoff_epoch, _EASTERN).strftime(
        "%Y-%m-%d %H:%M ET"
    )
