"""sr_tools drives bottom_barrel's bb-sr-alpaca (split-adjusted), not the old sr_alpaca.

The old ~/autotrade/bin/sr_alpaca had no adjustment option, so S/R over a window
crossing a split mixed pre- and post-split prices (SOXX after its 3:1 split on
2026-11-05). A fake binary that echoes its argv stands in for bb-sr-alpaca, so
this runs anywhere (the CI runner has no bottom_barrel build).
"""

import stat

import pytest

from alpaca_mcp_server.tools import sr_tools


def test_default_binary_is_bb_sr_alpaca():
    assert sr_tools.SR_ALPACA_BINARY.name == "bb-sr-alpaca"


@pytest.fixture
def fake_binary(tmp_path, monkeypatch):
    script = tmp_path / "bb-sr-alpaca"
    script.write_text(
        "#!/bin/sh\n"
        'echo "SOXX Support: 134.790 | Resistance: 140.360 | Current: 137.200"\n'
        'echo "ARGV: $*"\n'
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(sr_tools, "SR_ALPACA_BINARY", script)
    return script


@pytest.mark.asyncio
async def test_passes_through_and_never_sends_vwap(fake_binary):
    out = await sr_tools.get_support_resistance(
        "soxx", timeframe="1Day", days=60, clusters=5, vwap=True, volume_profile=True
    )
    argv = next(line for line in out.splitlines() if line.startswith("ARGV:"))
    assert "-s SOXX" in argv and "-t 1Day" in argv and "-d 60" in argv and "-c 5" in argv
    assert "--volume-profile" in argv
    assert "--vwap" not in argv  # bb-sr-alpaca has no VWAP mode
    assert "VWAP-based S/R is not available" in out
    assert "Support: 134.790" in out


@pytest.mark.asyncio
async def test_no_vwap_note_when_not_requested(fake_binary):
    out = await sr_tools.get_support_resistance("SOXX", vwap=False)
    assert "VWAP" not in out


@pytest.mark.asyncio
async def test_missing_binary_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(sr_tools, "SR_ALPACA_BINARY", tmp_path / "nope")
    out = await sr_tools.get_support_resistance("SOXX")
    assert "bb-sr-alpaca binary not found" in out


# bb-sr-alpaca's -d counts BARS; the tools take trading DAYS (as the old binary did).
# Passing days through gave get_intraday_sr_levels(days=5) on 5Min bars 5 bars.


@pytest.mark.parametrize(
    ("days", "timeframe", "bars"),
    [
        (5, "5Min", 960),
        (60, "1Hour", 960),
        (3, "1Min", 2880),
        (252, "1Day", 252),
        (10, "1Week", 2),
        (1, "1Month", 1),
    ],
)
def test_days_to_bars(days, timeframe, bars):
    assert sr_tools.days_to_bars(days, timeframe) == bars


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "kwargs", "expected_d"),
    [
        ("get_intraday_sr_levels", {"days": 5}, "-d 960"),  # 5Min
        ("get_swing_sr_levels", {"days": 60}, "-d 960"),  # 1Hour
        ("get_daily_sr_levels", {"days": 252}, "-d 252"),  # 1Day
    ],
)
async def test_tools_send_bars_not_days(fake_binary, tool, kwargs, expected_d):
    out = await getattr(sr_tools, tool)("SOXX", **kwargs)
    argv = next(line for line in out.splitlines() if line.startswith("ARGV:"))
    assert f" {expected_d} " in f" {argv.split('ARGV: ', 1)[1]} "


@pytest.mark.asyncio
async def test_sample_cap_never_truncates_the_window(fake_binary):
    # 30 days of 1Min is 28,800 bars; -n must not stay at the 10,000 default.
    out = await sr_tools.get_support_resistance("SOXX", timeframe="1Min", days=30)
    argv = next(line for line in out.splitlines() if line.startswith("ARGV:")).split()
    assert argv[argv.index("-d") + 1] == "28800"
    assert int(argv[argv.index("-n") + 1]) >= 28800


_FIVE_MIN_TOOLS = [
    "get_support_resistance",
    "get_support_resistance_comprehensive",
    "get_volume_profile",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", _FIVE_MIN_TOOLS)
async def test_5min_tools_default_to_5_days(fake_binary, tool):
    # 5 trading days of 5Min = 960 bars (was 30 days = 5,760).
    out = await getattr(sr_tools, tool)("SOXX")
    argv = next(line for line in out.splitlines() if line.startswith("ARGV:")).split()
    assert argv[argv.index("-t") + 1] == "5Min"
    assert argv[argv.index("-d") + 1] == "960"


def test_mcp_wrappers_default_to_5_days():
    import inspect

    from alpaca_mcp_server.server_components.tool_registrations import register_sr_tools

    registered: dict = {}

    class _Capture:
        def tool(self, *a, **k):
            def deco(fn):
                registered[fn.__name__] = fn
                return fn

            return deco

    register_sr_tools(_Capture())
    for name in _FIVE_MIN_TOOLS:
        assert inspect.signature(registered[name]).parameters["days"].default == 5, name
