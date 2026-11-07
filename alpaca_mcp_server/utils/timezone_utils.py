"""Eastern-time (America/New_York) handling for everything the server reports.

Every time the MCP server shows a caller is in ET, labelled EST or EDT by the
real tz database. The old version guessed DST as "March 8 - November 7"; on
2026-11-01..07 that labelled EST as EDT and shifted every reported time by an
hour.

Rules for naive datetimes passed to :func:`to_et`: naive means *UTC* (that is
what alpaca-py and the REST payloads carry). Never pass a naive
``datetime.now()``: on this host that is America/Chicago wall-clock. Use
:func:`now_et` instead.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def now_et() -> datetime:
    """The current time as an aware America/New_York datetime."""
    return datetime.now(ET)


def to_et(value: datetime | float | int | str) -> datetime:
    """Convert a datetime, epoch seconds, or ISO-8601 string to aware ET.

    Naive datetimes and offset-less ISO strings are taken as UTC.
    """
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), UTC).astimezone(ET)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(ET)


def fmt_et(value: datetime | float | int | str | None = None, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format *value* (default: now) in ET; ``%Z`` renders EST or EDT."""
    return (now_et() if value is None else to_et(value)).strftime(fmt)


def get_eastern_time() -> tuple[datetime, str]:
    """Current time in ET and its abbreviation ("EST" or "EDT")."""
    now = now_et()
    return now, now.strftime("%Z")


def get_eastern_time_string(format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Current ET time formatted with *format_str* (``%Z`` -> EST/EDT)."""
    return now_et().strftime(format_str)


def get_market_time_display() -> str:
    """Current time as "HH:MM EST" / "HH:MM EDT"."""
    return now_et().strftime("%H:%M %Z")
