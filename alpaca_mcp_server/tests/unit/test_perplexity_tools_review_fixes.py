"""Regression tests for the code-review findings in tools/perplexity_tools.py.

No network: a fake PerplexityClient and SimpleNamespace snapshots stand in for
Perplexity and Alpaca, so these also run on CI, where perplexity-client (a
private repo) is not installed.
"""

import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from alpaca_mcp_server.tools import perplexity_tools as pt


class _FakeClient:
    """Async context manager with the PerplexityClient methods the tools call."""

    def __init__(self, movers=None, quotes=None):
        self._movers = movers or {}
        self._quotes = quotes or []

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetch_json(self, _path):
        return self._movers

    async def fetch_many(self, paths):
        return self._quotes or [{} for _ in paths]


@pytest.mark.asyncio
async def test_movers_keep_sub_dollar_precision(monkeypatch):
    movers = {
        "gainers": [{"symbol": "SNTI", "price": 0.1568, "changesPercentage": 12.3}],
        "losers": [{"symbol": "SOXL", "price": 45.97, "changesPercentage": -4.1}],
    }
    monkeypatch.setattr(pt, "PerplexityClient", _FakeClient(movers=movers))
    out = await pt.get_perplexity_movers()
    assert "$0.1568" in out  # was "$0.16" at 2 decimals
    assert "$45.97" in out
    snti, soxl = (
        next(line for line in out.splitlines() if sym in line) for sym in ("SNTI", "SOXL")
    )
    assert snti.index("$") + len("$0.1568") == soxl.index("$") + len(
        "$45.97"
    )  # right-justified column


@pytest.mark.asyncio
async def test_alpaca_lookup_runs_off_the_event_loop(monkeypatch):
    seen: list[str] = []

    def fake_quotes(symbols):
        seen.append(threading.current_thread().name)
        return {}

    monkeypatch.setattr(pt, "PerplexityClient", _FakeClient())
    monkeypatch.setattr(pt, "_alpaca_realtime_quotes", fake_quotes)
    await pt.get_perplexity_quote("SNTI")
    assert seen and seen[0] != threading.main_thread().name  # blocking HTTP is in a worker thread


@pytest.mark.asyncio
async def test_missing_client_is_reported_not_raised(monkeypatch):
    monkeypatch.setattr(pt, "PerplexityClient", None)
    for result in (
        await pt.get_perplexity_quote("SNTI"),
        await pt.get_perplexity_movers(),
        await pt.get_perplexity_comprehensive("SNTI"),
    ):
        assert "perplexity-client is not installed" in result


def _snapshot(prev_close, day_close, last, trade_age_s=10):
    now = datetime.now(UTC)
    return SimpleNamespace(
        latest_trade=SimpleNamespace(price=last, timestamp=now - timedelta(seconds=trade_age_s)),
        latest_quote=SimpleNamespace(bid_price=last - 0.01, ask_price=last + 0.01),
        daily_bar=SimpleNamespace(
            close=day_close,
            volume=1000,
            low=day_close - 1,
            high=day_close + 1,
            timestamp=now - timedelta(hours=12),
        ),
        previous_daily_bar=SimpleNamespace(close=prev_close),
    )


def test_pre_market_change_is_from_last_session_close():
    # Pre-market: daily_bar is still yesterday's session (close 0.20); the day
    # before closed 0.17. A 0.25 print is +25% on the day, not +47%.
    nq = pt._normalize_alpaca_snapshot("X", _snapshot(0.17, 0.20, 0.25), pre_market=True)
    assert nq is not None
    assert nq["prev_close"] == pytest.approx(0.20)
    assert nq["change_pct"] == pytest.approx(25.0)


def test_regular_hours_change_is_from_previous_close():
    nq = pt._normalize_alpaca_snapshot("X", _snapshot(0.17, 0.20, 0.25), pre_market=False)
    assert nq["prev_close"] == pytest.approx(0.17)


def test_old_print_is_flagged_stale():
    cutoff = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
    fresh = pt._normalize_alpaca_snapshot(
        "X", _snapshot(1, 1, 1, trade_age_s=60), cutoff_epoch=cutoff
    )
    stale = pt._normalize_alpaca_snapshot(
        "X", _snapshot(1, 1, 1, trade_age_s=3 * 86400), cutoff_epoch=cutoff
    )
    assert fresh["stale"] is False
    assert stale["stale"] is True  # a halted name's weeks-old print is no longer "real-time"
