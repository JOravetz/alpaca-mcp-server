"""
Regression tests for Perplexity quote freshness.

Root cause being guarded: Perplexity Finance's /rest/finance/quote endpoint
serves the *prior session's close* (observed ~17h stale intraday), but the
comprehensive/quote tools rendered it as a live "QUOTE". These tests pin the
fix: the QUOTE block must prefer authoritative Alpaca real-time data, and any
fallback to the Perplexity feed must be timestamp-labeled and flagged STALE
when old.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools.perplexity_tools import (  # noqa: E402
    _format_comprehensive,
    _format_quote_block,
    _normalize_alpaca_snapshot,
    _normalize_pplx_quote,
)


def _fake_snapshot(price, prev_close, low, high, volume):
    eastern_ts = datetime(2026, 6, 30, 13, 35, 46, tzinfo=UTC)
    return SimpleNamespace(
        latest_trade=SimpleNamespace(price=price, timestamp=eastern_ts, size=1000),
        latest_quote=SimpleNamespace(bid_price=price, ask_price=price + 0.01),
        daily_bar=SimpleNamespace(close=price, low=low, high=high, volume=volume, timestamp=eastern_ts),
        previous_daily_bar=SimpleNamespace(close=prev_close),
        minute_bar=None,
    )


def test_alpaca_snapshot_computes_change_from_prev_close():
    nq = _normalize_alpaca_snapshot("CELZ", _fake_snapshot(4.08, 0.81, 2.60, 4.08, 58_000_000))
    assert nq is not None
    assert nq["source"] == "alpaca"
    assert abs(nq["price"] - 4.08) < 1e-6
    assert abs(nq["change_pct"] - ((4.08 - 0.81) / 0.81 * 100)) < 0.01
    assert nq["stale"] is False
    assert nq["as_of"]  # has a timestamp label


def test_pplx_quote_flagged_stale_when_old():
    # Perplexity quote timestamped at yesterday's close, "now" is next morning.
    yday_close = int(datetime(2026, 6, 29, 20, 0, 1, tzinfo=UTC).timestamp())
    now = int(datetime(2026, 6, 30, 13, 40, 0, tzinfo=UTC).timestamp())
    q = {"price": 0.81, "previousClose": 1.2, "changesPercentage": -32.48,
         "volume": 40_575_118, "dayLow": 0.79, "dayHigh": 1.25, "timestamp": yday_close}
    nq = _normalize_pplx_quote(q, now_epoch=now)
    assert nq is not None
    assert nq["source"] == "perplexity"
    assert nq["stale"] is True
    block = "\n".join(_format_quote_block(nq))
    assert "STALE" in block
    assert "2026-06-29" in block  # the actual as-of date is surfaced


def test_pplx_quote_fresh_not_flagged():
    now = int(datetime(2026, 6, 30, 13, 40, 0, tzinfo=UTC).timestamp())
    q = {"price": 4.08, "previousClose": 0.81, "changesPercentage": 403.7,
         "volume": 58_000_000, "timestamp": now - 30}
    nq = _normalize_pplx_quote(q, now_epoch=now)
    assert nq["stale"] is False
    assert "STALE" not in "\n".join(_format_quote_block(nq))


def test_alpaca_block_labeled_realtime():
    nq = _normalize_alpaca_snapshot("CELZ", _fake_snapshot(4.08, 0.81, 2.60, 4.08, 58_000_000))
    block = "\n".join(_format_quote_block(nq))
    assert "Alpaca" in block
    assert "STALE" not in block


def test_comprehensive_prefers_override_quote_over_stale_raw():
    # raw carries the stale Perplexity quote; override is the live Alpaca quote.
    raw = {"quote": {"price": 0.81, "previousClose": 1.2, "changesPercentage": -32.48,
                     "volume": 40_575_118, "timestamp": 0}}
    override = _normalize_alpaca_snapshot("CELZ", _fake_snapshot(4.08, 0.81, 2.60, 4.08, 58_000_000))
    out = _format_comprehensive("CELZ", raw, quote=override)
    assert "$4.08" in out
    assert "$0.81 (-32.48%)" not in out  # stale Perplexity price must not appear
