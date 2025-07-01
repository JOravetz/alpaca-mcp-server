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
