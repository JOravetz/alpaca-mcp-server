"""
Pytest configuration for Alpaca MCP Server tests.
Real data testing with actual API connections.
"""

import asyncio
import os

import pytest

# Ensure test environment
os.environ["PAPER"] = "true"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_symbols():
    """High-liquidity symbols for real testing."""
    return ["AAPL", "MSFT", "NVDA", "TSLA", "SPY"]


@pytest.fixture
def workflow_params():
    """Real workflow parameters for testing."""
    return {
        "scan_type": "quick",
        "symbol": "AAPL",
        "timeframe": "comprehensive",
        "session_type": "market_open",
    }


@pytest.fixture(autouse=True)
def _fresh_global_config():
    """Drop the cached GlobalConfig after every test.

    get_global_config() caches one GlobalConfig per process. Tests that reload it
    from temp files or edit its fields left that state behind, so a later test read
    another test's values instead of config/global_config.json (streaming_real saw
    500 against the file's 1000, but only in a full-suite run).
    """
    yield
    from alpaca_mcp_server.config import global_config

    global_config._global_config = None


@pytest.fixture(autouse=True)
def _charts_in_tmp(tmp_path, monkeypatch):
    """Chart HTML/PNG files from a test go to its own tmp dir, not the shared plot dir."""
    monkeypatch.setenv("ALPACA_PLOT_DIR", str(tmp_path / "plots"))
