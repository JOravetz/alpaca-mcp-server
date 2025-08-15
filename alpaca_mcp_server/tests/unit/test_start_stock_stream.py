"""
Unit tests for the start_global_stock_stream MCP tool.
Tests the new streaming functionality with global configuration.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the streaming tools module to access the start_global_stock_stream function
from alpaca_mcp_server.tools.streaming_tools import start_global_stock_stream  # noqa: E402


class TestStartGlobalStockStream:
    """Test the start_global_stock_stream MCP tool functionality."""

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_single_symbol(self):
        """Test streaming with a single symbol."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            # Mock successful execution
            mock_stream.return_value = (
                "✅ Global stock stream started for ['AAPL'] with trades,quotes data types"
            )

            result = await start_global_stock_stream(
                symbols=["AAPL"], data_types=["trades"], duration_seconds=60
            )

            # Verify the function was called correctly
            mock_stream.assert_called_once_with(["AAPL"], ["trades"], "sip", 60, None, False)

            # Verify response format
            assert "✅" in result
            assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_multiple_symbols(self):
        """Test streaming with multiple symbols."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            mock_stream.return_value = (
                "✅ Global stock stream started for ['AAPL', 'MSFT'] with trades,quotes data types"
            )

            await start_global_stock_stream(
                symbols=["AAPL", "MSFT"], data_types=["trades", "quotes"], duration_seconds=120
            )

            # Check function call
            mock_stream.assert_called_once_with(
                ["AAPL", "MSFT"], ["trades", "quotes"], "sip", 120, None, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_default_parameters(self):
        """Test streaming with default parameters."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            mock_stream.return_value = "✅ Global stock stream started with defaults"

            await start_global_stock_stream(symbols=["SPY"])

            # Check defaults are applied
            mock_stream.assert_called_once_with(
                ["SPY"], ["trades", "quotes"], "sip", None, None, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_custom_feed(self):
        """Test streaming with custom feed."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            mock_stream.return_value = "✅ Global stock stream started with IEX feed"

            await start_global_stock_stream(
                symbols=["QQQ"], feed="iex", buffer_size_per_symbol=1000
            )

            mock_stream.assert_called_once_with(
                ["QQQ"], ["trades", "quotes"], "iex", None, 1000, False
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_replace_existing(self):
        """Test streaming with replace existing option."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            mock_stream.return_value = "✅ Global stock stream replaced existing streams"

            await start_global_stock_stream(symbols=["NVDA"], replace_existing=True)

            mock_stream.assert_called_once_with(
                ["NVDA"], ["trades", "quotes"], "sip", None, None, True
            )

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_error_handling(self):
        """Test error handling when streaming fails."""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools.start_global_stock_stream"
        ) as mock_stream:
            # Mock failed execution
            mock_stream.side_effect = Exception("Connection error")

            with pytest.raises(Exception, match="Connection error"):
                await start_global_stock_stream(symbols=["INVALID"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
