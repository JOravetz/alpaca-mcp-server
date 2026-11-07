"""
Unit tests for the start_global_stock_stream MCP tool.

They test the MCP-registered wrapper (server_components.tool_registrations), which
fills in defaults and forwards six positional arguments to
tools.streaming_tools.start_global_stock_stream. That function is replaced by an
AsyncMock, so no test ever opens a real Alpaca stream connection.

(The previous version patched streaming_tools.start_global_stock_stream and then
called the very function it had imported before patching — so it ran the REAL
stream, and the mock was never called.)
"""

from collections.abc import Callable
from unittest.mock import AsyncMock, patch

import pytest

from alpaca_mcp_server.server_components.tool_registrations import register_streaming_tools

_TARGET = "alpaca_mcp_server.server_components.tool_registrations.streaming_tools.start_global_stock_stream"


class _CaptureMCP:
    """Stands in for FastMCP: records each function registered with @mcp.tool()."""

    def __init__(self) -> None:
        self.tools: dict[str, Callable] = {}

    def tool(self, *_args, **_kwargs):
        def decorator(fn: Callable) -> Callable:
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.fixture
def start_stream() -> Callable:
    mcp = _CaptureMCP()
    register_streaming_tools(mcp)
    return mcp.tools["start_global_stock_stream"]


class TestStartGlobalStockStream:
    """Test the start_global_stock_stream MCP tool wrapper."""

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_single_symbol(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = (
                "✅ Global stock stream started for ['AAPL'] with trades data types"
            )

            result = await start_stream(
                symbols=["AAPL"], data_types=["trades"], duration_seconds=60
            )

            mock_stream.assert_awaited_once_with(["AAPL"], ["trades"], "sip", 60, None, False)
            assert "✅" in result
            assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_multiple_symbols(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            await start_stream(
                symbols=["AAPL", "MSFT"], data_types=["trades", "quotes"], duration_seconds=120
            )

            mock_stream.assert_awaited_once_with(
                ["AAPL", "MSFT"], ["trades", "quotes"], "sip", 120, None, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_default_parameters(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            await start_stream(symbols=["SPY"])

            # data_types defaults to trades+quotes, feed to SIP
            mock_stream.assert_awaited_once_with(
                ["SPY"], ["trades", "quotes"], "sip", None, None, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_custom_feed(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            await start_stream(symbols=["QQQ"], feed="boats", buffer_size_per_symbol=1000)

            mock_stream.assert_awaited_once_with(
                ["QQQ"], ["trades", "quotes"], "boats", None, 1000, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_replace_existing(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            await start_stream(symbols=["NVDA"], replace_existing=True)

            mock_stream.assert_awaited_once_with(
                ["NVDA"], ["trades", "quotes"], "sip", None, None, True
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_error_handling(self, start_stream):
        with patch(_TARGET, new_callable=AsyncMock) as mock_stream:
            mock_stream.side_effect = Exception("Connection error")

            with pytest.raises(Exception, match="Connection error"):
                await start_stream(symbols=["INVALID"])
