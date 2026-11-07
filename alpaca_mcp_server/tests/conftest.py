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


def pytest_collection_modifyitems(config, items):
    """Skip `live_alpaca` tests where no Alpaca keys exist (CI runners).

    Those tests assert on real market data; without keys they can only see a
    credentials message, which says nothing about the code under test.
    """
    from alpaca_mcp_server.config.settings import settings

    if settings.api_key and settings.api_secret:
        return
    skip = pytest.mark.skip(reason="needs Alpaca API keys (none configured, e.g. on CI)")
    for item in items:
        if "live_alpaca" in item.keywords:
            item.add_marker(skip)


def pytest_configure(config):
    # Registered here, not only in pyproject: pytest.ini wins over pyproject and
    # its `[tool:pytest]` header is not read in a pytest.ini, so pyproject's
    # marker list never reached pytest.
    for marker in (
        "live_alpaca: needs real Alpaca market data; skipped when no API keys are configured (CI)",
        "integration: marks tests as integration tests",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "unit: marks tests as unit tests",
        "performance: marks tests as performance tests",
    ):
        config.addinivalue_line("markers", marker)
