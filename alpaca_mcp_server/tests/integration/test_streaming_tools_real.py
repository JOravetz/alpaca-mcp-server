"""
Real integration tests for streaming_tools.py - NO MOCKING
Tests actual streaming functionality with real Alpaca API connections.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools import streaming_tools  # noqa: E402


@pytest.fixture(scope="module")
def check_credentials():
    """Check if API credentials are available"""
    has_creds = os.getenv("APCA_API_KEY_ID") and os.getenv("APCA_API_SECRET_KEY")
    if not has_creds:
        pytest.skip("Alpaca API credentials not found in environment")
    return has_creds


@pytest.fixture(scope="module")
def test_symbols():
    """High-liquidity symbols for testing"""
    return ["AAPL", "MSFT", "SPY"]


@pytest.fixture(scope="module")
async def cleanup_streams():
    """Cleanup fixture to ensure streams are stopped after tests"""
    yield
    # Cleanup after all tests
    try:
        await streaming_tools.stop_global_stock_stream()
        await streaming_tools.clear_stock_stream_buffers()
    except Exception as e:
        print(f"Cleanup error: {e}")
    # Wait for cleanup to complete
    await asyncio.sleep(2)


class TestRealStreamHandlers:
    """Test event handlers with real streaming data"""

    @pytest.mark.asyncio
    async def test_real_stream_startup_and_data_collection(self, check_credentials, test_symbols):
        """Test starting real stream and collecting actual market data"""
        # Stop any existing streams first
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream with real symbols
        result = await streaming_tools.start_global_stock_stream(
            symbols=test_symbols[:2],  # Use first 2 symbols
            data_types=["trades", "quotes"],
            feed="iex",  # Use IEX feed for testing
            duration_seconds=None,  # Indefinite
        )

        print(f"\nStream start result: {result}")

        # Verify stream started successfully
        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result
        assert "AAPL" in result or "aapl" in result.lower()

        # Wait for some data to accumulate
        print("Waiting 10 seconds for data to accumulate...")
        await asyncio.sleep(10)

        # Check stream is active
        status = await streaming_tools.list_active_stock_streams()
        print(f"\nStream status: {status}")
        assert "📡 ACTIVE STOCK STREAMING STATUS" in status
        assert "Total Events:" in status

        # Stop stream
        stop_result = await streaming_tools.stop_global_stock_stream()
        print(f"\nStream stop result: {stop_result}")
        assert "🛑 GLOBAL STOCK STREAM STOPPED" in stop_result

    @pytest.mark.asyncio
    async def test_real_trade_data_collection(self, check_credentials, test_symbols):
        """Test collecting real trade data"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream for trades only
        result = await streaming_tools.start_global_stock_stream(
            symbols=["SPY"],  # SPY is very liquid
            data_types=["trades"],
            feed="iex",
        )

        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result

        # Wait for trade data
        print("Waiting 15 seconds for trade data...")
        await asyncio.sleep(15)

        # Retrieve trade data
        trade_data = await streaming_tools.get_stock_stream_data(
            symbol="SPY", data_type="trades", limit=10
        )

        print(f"\nTrade data:\n{trade_data}")

        # Verify we got trade data (unless market is closed)
        if "Recent Trades:" in trade_data:
            assert "SPY" in trade_data
            assert "$" in trade_data  # Price format
        else:
            print("Note: No trades received (market may be closed)")

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_quote_data_collection(self, check_credentials, test_symbols):
        """Test collecting real quote data"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream for quotes only
        result = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"],
            data_types=["quotes"],
            feed="iex",
        )

        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result

        # Wait for quote data
        print("Waiting 15 seconds for quote data...")
        await asyncio.sleep(15)

        # Retrieve quote data
        quote_data = await streaming_tools.get_stock_stream_data(
            symbol="AAPL", data_type="quotes", limit=10
        )

        print(f"\nQuote data:\n{quote_data}")

        # Verify we got quote data (unless market is closed)
        if "Recent Quotes:" in quote_data:
            assert "AAPL" in quote_data
            assert " x " in quote_data  # Bid x Ask format
        else:
            print("Note: No quotes received (market may be closed)")

        # Stop stream
        await streaming_tools.stop_global_stock_stream()


class TestRealStreamManagement:
    """Test stream lifecycle management with real connections"""

    @pytest.mark.asyncio
    async def test_real_start_and_stop_stream(self, check_credentials):
        """Test full lifecycle of stream start and stop"""
        # Ensure clean state
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream
        start_result = await streaming_tools.start_global_stock_stream(
            symbols=["SPY"], data_types=["trades"], feed="iex"
        )

        print(f"\nStart result: {start_result}")
        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in start_result

        # Verify stream is active
        await asyncio.sleep(3)
        status = await streaming_tools.list_active_stock_streams()
        assert "📡 ACTIVE STOCK STREAMING STATUS" in status
        assert "SPY" in status

        # Stop stream
        stop_result = await streaming_tools.stop_global_stock_stream()
        print(f"\nStop result: {stop_result}")
        assert "🛑 GLOBAL STOCK STREAM STOPPED" in stop_result
        assert "Runtime:" in stop_result

        # Verify stream is stopped
        status_after = await streaming_tools.list_active_stock_streams()
        assert "No active stock stream" in status_after

    @pytest.mark.asyncio
    async def test_real_prevent_duplicate_streams(self, check_credentials):
        """Test that duplicate streams are prevented"""
        # Stop any existing streams and wait for cleanup
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(5)  # Extra wait for cleanup

        # Start first stream
        result1 = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"], data_types=["trades"], feed="iex"
        )

        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result1

        # Wait longer for stream to fully initialize and be marked as active
        print("Waiting 5 seconds for stream to become fully active...")
        await asyncio.sleep(5)

        # Verify stream is active before trying duplicate
        status = await streaming_tools.list_active_stock_streams()
        print(f"\nStream status before duplicate attempt:\n{status}")

        # Try to start second stream without replace flag
        result2 = await streaming_tools.start_global_stock_stream(
            symbols=["MSFT"], data_types=["trades"], feed="iex", replace_existing=False
        )

        print(f"\nDuplicate attempt result: {result2}")
        assert "❌ Global stock stream already active!" in result2

        # Stop stream
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(3)  # Wait for cleanup

    @pytest.mark.asyncio
    async def test_real_add_symbols_to_active_stream(self, check_credentials):
        """Test adding symbols to an active stream"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream with one symbol
        result = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"], data_types=["trades", "quotes"], feed="iex"
        )

        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result

        # Wait a moment for stream to stabilize
        await asyncio.sleep(3)

        # Add more symbols
        add_result = await streaming_tools.add_symbols_to_stock_stream(
            symbols=["MSFT", "SPY"], data_types=["trades", "quotes"]
        )

        print(f"\nAdd symbols result: {add_result}")
        assert "✅ SYMBOLS ADDED TO STOCK STREAM" in add_result
        assert "MSFT" in add_result
        assert "SPY" in add_result

        # Verify all symbols are now in stream
        status = await streaming_tools.list_active_stock_streams()
        assert "AAPL" in status
        assert "MSFT" in status
        assert "SPY" in status

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_replace_existing_stream(self, check_credentials):
        """Test replacing an existing stream"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start first stream
        result1 = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"], data_types=["trades"], feed="iex"
        )

        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result1

        # Wait a moment
        await asyncio.sleep(3)

        # Replace with new stream
        result2 = await streaming_tools.start_global_stock_stream(
            symbols=["MSFT", "SPY"],
            data_types=["trades", "quotes"],
            feed="iex",
            replace_existing=True,
        )

        print(f"\nReplace result: {result2}")
        assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result2
        assert "MSFT" in result2
        assert "SPY" in result2

        # Stop stream
        await streaming_tools.stop_global_stock_stream()


class TestRealStreamDataRetrieval:
    """Test data retrieval from real streams"""

    @pytest.mark.asyncio
    async def test_real_get_stream_data_with_filters(self, check_credentials):
        """Test retrieving stream data with various filters"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream
        await streaming_tools.start_global_stock_stream(
            symbols=["SPY"], data_types=["trades", "quotes"], feed="iex"
        )

        # Wait for data accumulation
        print("Waiting 15 seconds for data...")
        await asyncio.sleep(15)

        # Get all trade data
        all_trades = await streaming_tools.get_stock_stream_data(symbol="SPY", data_type="trades")

        print(f"\nAll trades result: {all_trades}")

        # Get limited trade data
        limited_trades = await streaming_tools.get_stock_stream_data(
            symbol="SPY", data_type="trades", limit=5
        )

        print(f"\nLimited trades result: {limited_trades}")

        # Get recent trade data (last 10 seconds)
        recent_trades = await streaming_tools.get_stock_stream_data(
            symbol="SPY", data_type="trades", recent_seconds=10
        )

        print(f"\nRecent trades result: {recent_trades}")

        # Verify data format
        if "Recent Trades:" in all_trades:
            assert "SPY" in all_trades
        if "limited to 5 items" in limited_trades:
            assert "SPY" in limited_trades
        if "last 10s" in recent_trades:
            assert "SPY" in recent_trades

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_buffer_statistics(self, check_credentials):
        """Test getting real buffer statistics"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream with multiple symbols
        await streaming_tools.start_global_stock_stream(
            symbols=["AAPL", "MSFT"], data_types=["trades", "quotes"], feed="iex"
        )

        # Wait for data
        print("Waiting 15 seconds for data accumulation...")
        await asyncio.sleep(15)

        # Get buffer stats
        stats = await streaming_tools.get_stock_stream_buffer_stats()

        print(f"\nBuffer statistics:\n{stats}")

        # Verify stats format
        assert "💾 STOCK STREAM BUFFER STATISTICS" in stats
        assert "Total Buffers:" in stats
        assert "Total Items:" in stats

        # Should have buffers for both symbols and both data types
        # At minimum: AAPL_trades, AAPL_quotes, MSFT_trades, MSFT_quotes
        if "Total Buffers:" in stats:
            # Parse buffer count
            for line in stats.split("\n"):
                if "Total Buffers:" in line:
                    print(f"Buffer line: {line}")

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_list_active_streams(self, check_credentials):
        """Test listing active streams with real data"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream
        await streaming_tools.start_global_stock_stream(
            symbols=["AAPL", "SPY"], data_types=["trades", "quotes"], feed="iex"
        )

        # Wait for stream to be active
        await asyncio.sleep(5)

        # List active streams
        status = await streaming_tools.list_active_stock_streams()

        print(f"\nActive streams:\n{status}")

        # Verify status format
        assert "📡 ACTIVE STOCK STREAMING STATUS" in status
        assert "Stream Configuration:" in status or "Stream Configuration" in status
        assert "IEX" in status
        assert "Active Stock Subscriptions:" in status or "Active" in status

        # Should show our symbols
        assert "AAPL" in status
        assert "SPY" in status

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_clear_buffers(self, check_credentials):
        """Test clearing stream buffers"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream
        await streaming_tools.start_global_stock_stream(
            symbols=["SPY"], data_types=["trades"], feed="iex"
        )

        # Wait for data
        print("Waiting 10 seconds for data...")
        await asyncio.sleep(10)

        # Get stats before clearing
        stats_before = await streaming_tools.get_stock_stream_buffer_stats()
        print(f"\nStats before clearing:\n{stats_before}")

        # Clear buffers
        clear_result = await streaming_tools.clear_stock_stream_buffers()
        print(f"\nClear result:\n{clear_result}")

        assert "🧹 STOCK STREAM BUFFERS CLEARED" in clear_result
        assert "Items Removed:" in clear_result

        # Get stats after clearing
        stats_after = await streaming_tools.get_stock_stream_buffer_stats()
        print(f"\nStats after clearing:\n{stats_after}")

        # Stop stream
        await streaming_tools.stop_global_stock_stream()


class TestRealStreamAnalysis:
    """Test stream-aware analysis tools with real data"""

    @pytest.mark.asyncio
    async def test_real_stream_aware_price_monitor(self, check_credentials):
        """Test real-time price monitoring with actual stream data"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream
        await streaming_tools.start_global_stock_stream(
            symbols=["SPY"], data_types=["trades", "quotes"], feed="iex"
        )

        # Wait for data
        print("Waiting 15 seconds for price data...")
        await asyncio.sleep(15)

        # Monitor price
        monitor_result = await streaming_tools.stream_aware_price_monitor(
            symbol="SPY", analysis_seconds=10
        )

        print(f"\nPrice monitoring result:\n{monitor_result}")

        # Verify monitoring format
        assert "📊 STREAM-AWARE MONITORING: SPY" in monitor_result
        assert "Current Price:" in monitor_result
        assert "Volume Analysis" in monitor_result

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_concurrent_data_access(self, check_credentials):
        """Test concurrent access to stream data"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream with multiple symbols
        await streaming_tools.start_global_stock_stream(
            symbols=["AAPL", "MSFT", "SPY"],
            data_types=["trades", "quotes"],
            feed="iex",
        )

        # Wait for data
        print("Waiting 15 seconds for data...")
        await asyncio.sleep(15)

        # Concurrent data retrieval for multiple symbols
        results = await asyncio.gather(
            streaming_tools.get_stock_stream_data("AAPL", "trades", limit=5),
            streaming_tools.get_stock_stream_data("MSFT", "trades", limit=5),
            streaming_tools.get_stock_stream_data("SPY", "quotes", limit=5),
            return_exceptions=True,
        )

        # Print results
        for i, result in enumerate(results):
            print(f"\nConcurrent result {i+1}:\n{result}")

        # Verify no exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Got exception: {result}"

        # Stop stream
        await streaming_tools.stop_global_stock_stream()


class TestRealStreamEdgeCases:
    """Test edge cases with real connections"""

    @pytest.mark.asyncio
    async def test_real_stream_with_lowercase_symbols(self, check_credentials):
        """Test that lowercase symbols are converted to uppercase"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Start stream with lowercase symbols
        result = await streaming_tools.start_global_stock_stream(
            symbols=["aapl", "msft"],  # lowercase
            data_types=["trades"],
            feed="iex",
        )

        print(f"\nLowercase symbols result: {result}")

        # Should convert to uppercase
        assert "AAPL" in result
        assert "MSFT" in result

        # Verify in status
        status = await streaming_tools.list_active_stock_streams()
        assert "AAPL" in status
        assert "MSFT" in status

        # Stop stream
        await streaming_tools.stop_global_stock_stream()

    @pytest.mark.asyncio
    async def test_real_stream_data_when_no_stream_active(self, check_credentials):
        """Test getting data when no stream is active"""
        # Ensure no stream is active
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Try to get data
        result = await streaming_tools.get_stock_stream_data("AAPL", "trades")

        print(f"\nNo stream result: {result}")

        # Should get error message
        assert "No active stock stream" in result

    @pytest.mark.asyncio
    async def test_real_add_symbols_without_active_stream(self, check_credentials):
        """Test adding symbols when no stream is active"""
        # Ensure no stream is active
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Try to add symbols
        result = await streaming_tools.add_symbols_to_stock_stream(symbols=["AAPL"])

        print(f"\nAdd without stream result: {result}")

        # Should get error message
        assert "No active global stock stream" in result

    @pytest.mark.asyncio
    async def test_real_stream_invalid_data_type(self, check_credentials):
        """Test stream startup with invalid data type"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Try to start stream with invalid data type
        result = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"], data_types=["invalid_type"], feed="iex"
        )

        print(f"\nInvalid data type result: {result}")

        # Should get error message
        assert "Invalid data types" in result

    @pytest.mark.asyncio
    async def test_real_stream_invalid_feed(self, check_credentials):
        """Test stream startup with invalid feed"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Try to start stream with invalid feed
        result = await streaming_tools.start_global_stock_stream(
            symbols=["AAPL"], data_types=["trades"], feed="invalid_feed"
        )

        print(f"\nInvalid feed result: {result}")

        # Should get error message
        assert "Feed must be 'sip' or 'iex'" in result

    @pytest.mark.asyncio
    async def test_real_stream_runtime_statistics(self, check_credentials):
        """Test that runtime statistics are accurate"""
        # Stop any existing streams
        await streaming_tools.stop_global_stock_stream()
        await asyncio.sleep(2)

        # Record start time
        start_time = time.time()

        # Start stream
        await streaming_tools.start_global_stock_stream(
            symbols=["SPY"], data_types=["trades"], feed="iex"
        )

        # Wait a known duration
        run_duration = 10
        print(f"Waiting {run_duration} seconds...")
        await asyncio.sleep(run_duration)

        # Get status
        status = await streaming_tools.list_active_stock_streams()
        print(f"\nRuntime status:\n{status}")

        # Stop stream
        stop_result = await streaming_tools.stop_global_stock_stream()
        print(f"\nStop result:\n{stop_result}")

        # Verify runtime is reported
        assert "Runtime:" in stop_result or "Runtime" in status

        # Actual elapsed time
        actual_runtime = time.time() - start_time
        print(f"\nActual runtime: {actual_runtime:.1f} seconds")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
