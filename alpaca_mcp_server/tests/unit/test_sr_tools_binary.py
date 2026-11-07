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
