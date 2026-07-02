"""Tests for scanner freshness-cutoff computation and timestamp helpers."""

import time
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytz

from alpaca_mcp_server.tools import freshness


def _reset_cache():
    freshness._cache["value"] = None
    freshness._cache["expires"] = 0.0


class TestParseIsoEpoch:
    def test_known_value(self):
        # date -u -d "2026-06-08T20:00:00Z" +%s -> 1780948800
        assert freshness.parse_iso_epoch("2026-06-08T20:00:00Z") == 1780948800

    def test_fractional_seconds_ignored(self):
        assert freshness.parse_iso_epoch("2026-06-08T20:00:00.123456789Z") == 1780948800

    def test_malformed_returns_none(self):
        assert freshness.parse_iso_epoch("garbage") is None
        assert freshness.parse_iso_epoch("") is None
        assert freshness.parse_iso_epoch(None) is None

    def test_negative_offset_with_fraction(self):
        # 16:00 EDT == 20:00 UTC — the offset must be honored, not dropped
        assert (
            freshness.parse_iso_epoch("2026-06-08T16:00:00.123456789-04:00")
            == 1780948800
        )

    def test_naive_timestamp_is_utc(self):
        # Matches the C parser: naive strings are UTC, never local time
        assert freshness.parse_iso_epoch("2026-06-08T20:00:00") == 1780948800


class TestIsStale:
    def test_older_than_cutoff_is_stale(self):
        assert freshness.is_stale("2026-06-08T20:00:00Z", cutoff_epoch=1780948801)

    def test_at_cutoff_is_fresh(self):
        assert not freshness.is_stale("2026-06-08T20:00:00Z", cutoff_epoch=1780948800)

    def test_missing_timestamp_fails_closed(self):
        assert freshness.is_stale(None, cutoff_epoch=1)
        assert freshness.is_stale("garbage", cutoff_epoch=1)

    def test_disabled_cutoff_never_stale(self):
        assert not freshness.is_stale(None, cutoff_epoch=0)


class TestFreshnessCutoff:
    def _client_with_sessions(self, dates):
        client = MagicMock()
        client.get_calendar.return_value = [
            SimpleNamespace(date=d.isoformat()) for d in dates
        ]
        return client

    def test_calendar_cutoff_is_prev_trading_day_0400_et(self):
        _reset_cache()
        eastern = pytz.timezone("America/New_York")
        today = datetime.now(eastern).date()
        prev_day = today - timedelta(days=3)  # pretend a long weekend
        client = self._client_with_sessions(
            [today, prev_day, prev_day - timedelta(days=1)]
        )
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            return_value=client,
        ):
            cutoff, source = freshness.freshness_cutoff()
        expected = int(
            eastern.localize(
                datetime.combine(prev_day, freshness._PREMARKET_START)
            ).timestamp()
        )
        assert source == "calendar"
        assert cutoff == expected

    def test_fallback_when_calendar_unavailable(self):
        _reset_cache()
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            side_effect=RuntimeError("api down"),
        ):
            before = time.time()
            cutoff, source = freshness.freshness_cutoff()
        assert source == "fallback"
        assert abs(cutoff - (before - 96 * 3600)) < 5

    def test_result_is_cached(self):
        _reset_cache()
        client = self._client_with_sessions(
            [date.today() - timedelta(days=1)]
        )
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            return_value=client,
        ) as mock_get:
            first = freshness.freshness_cutoff()
            second = freshness.freshness_cutoff()
        assert first == second
        assert mock_get.call_count == 1


class TestFormatting:
    def test_format_trade_age_recent(self):
        two_hours_ago = datetime.now(pytz.UTC) - timedelta(hours=2, minutes=5)
        iso = two_hours_ago.strftime("%Y-%m-%dT%H:%M:%S") + ".123Z"
        out = freshness.format_trade_age(iso)
        assert " ET (" in out
        assert out.endswith("ago)")
        assert "2h" in out

    def test_format_trade_age_days(self):
        old = datetime.now(pytz.UTC) - timedelta(days=23, hours=1)
        iso = old.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        assert "23d" in freshness.format_trade_age(iso)

    def test_format_trade_age_malformed(self):
        assert freshness.format_trade_age("garbage") == "unknown"

    def test_format_cutoff(self):
        # 1782806400 == 2026-06-30 04:00 ET (date -u -d "2026-06-30T04:00:00-04:00" +%s)
        assert freshness.format_cutoff(1782806400) == "2026-06-30 04:00 ET"


class TestAnalyzerCutoffFlag:
    def _run_analyze(self, **kwargs):
        from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import CStockAnalyzer

        captured = {}

        def fake_run(cmd, **_kw):
            captured["cmd"] = cmd
            return SimpleNamespace(
                stdout='{"results_count": 0, "stocks": []}', stderr="", returncode=0
            )

        with patch(
            "alpaca_mcp_server.tools.c_stock_analyzer_wrapper.subprocess.run",
            side_effect=fake_run,
        ):
            CStockAnalyzer().analyze(symbols="AAPL", **kwargs)
        return captured["cmd"]

    def test_min_trade_ts_appends_T_flag(self):
        cmd = self._run_analyze(min_trade_ts=1782806400)
        assert "-T" in cmd
        assert cmd[cmd.index("-T") + 1] == "1782806400"

    def test_no_min_trade_ts_no_T_flag(self):
        cmd = self._run_analyze()
        assert "-T" not in cmd
