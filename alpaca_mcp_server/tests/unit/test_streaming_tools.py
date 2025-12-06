"""
Comprehensive unit tests for streaming_tools.py
Tests all streaming functionality including handlers, stream management, and data retrieval.
"""

import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.tools import streaming_tools  # noqa: E402


class MockTrade:
    """Mock trade object for testing"""

    def __init__(self, symbol="AAPL", price=150.0, size=100):
        self.symbol = symbol
        self.price = price
        self.size = size
        self.timestamp = datetime.now(UTC)
        self.conditions = ["@"]
        self.exchange = "NASDAQ"


class MockQuote:
    """Mock quote object for testing"""

    def __init__(self, symbol="AAPL", bid=149.5, ask=150.5):
        self.symbol = symbol
        self.bid_price = bid
        self.ask_price = ask
        self.bid_size = 100
        self.ask_size = 200
        self.timestamp = datetime.now(UTC)
        self.bid_exchange = "NASDAQ"
        self.ask_exchange = "NASDAQ"


class MockBar:
    """Mock bar object for testing"""

    def __init__(self, symbol="AAPL"):
        self.symbol = symbol
        self.open = 150.0
        self.high = 151.0
        self.low = 149.0
        self.close = 150.5
        self.volume = 10000
        self.timestamp = datetime.now(UTC)
        self.trade_count = 100
        self.vwap = 150.25


class MockStatus:
    """Mock status object for testing"""

    def __init__(self, symbol="AAPL", status="trading"):
        self.symbol = symbol
        self.status = status
        self.timestamp = datetime.now(UTC)
        self.tape = "A"


class TestStreamHandlers:
    """Test event handlers for streaming data"""

    @pytest.mark.asyncio
    async def test_handle_stock_trade_success(self):
        """Test successful handling of stock trade data"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            trade = MockTrade(symbol="AAPL", price=150.25, size=100)

            await streaming_tools.handle_stock_trade(trade)

            # Verify buffer was accessed
            mock_buffer_fn.assert_called_once()
            # Verify data was added to buffer
            mock_buffer.add.assert_called_once()

            # Verify the data structure
            call_args = mock_buffer.add.call_args[0][0]
            assert call_args["symbol"] == "AAPL"
            assert call_args["price"] == 150.25
            assert call_args["size"] == 100
            assert "timestamp" in call_args
            assert "conditions" in call_args
            assert "exchange" in call_args

    @pytest.mark.asyncio
    async def test_handle_stock_trade_error_handling(self):
        """Test error handling in trade handler"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer_fn.side_effect = Exception("Buffer error")

            # Create a trade with missing attributes
            trade = MagicMock()
            trade.symbol = "AAPL"
            trade.price = 150.0
            trade.size = None  # Will cause an error

            # Should not raise exception, just print error
            await streaming_tools.handle_stock_trade(trade)

    @pytest.mark.asyncio
    async def test_handle_stock_quote_success(self):
        """Test successful handling of stock quote data"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            quote = MockQuote(symbol="MSFT", bid=149.5, ask=150.5)

            await streaming_tools.handle_stock_quote(quote)

            # Verify buffer was accessed
            mock_buffer_fn.assert_called_once()
            # Verify data was added
            mock_buffer.add.assert_called_once()

            # Verify the data structure
            call_args = mock_buffer.add.call_args[0][0]
            assert call_args["symbol"] == "MSFT"
            assert call_args["bid"] == 149.5
            assert call_args["ask"] == 150.5
            assert call_args["bid_size"] == 100
            assert call_args["ask_size"] == 200

    @pytest.mark.asyncio
    async def test_handle_stock_quote_none_prices(self):
        """Test handling quote with None prices"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            quote = MockQuote()
            quote.bid_price = None
            quote.ask_price = None

            await streaming_tools.handle_stock_quote(quote)

            # Verify data was still added with None values
            mock_buffer.add.assert_called_once()
            call_args = mock_buffer.add.call_args[0][0]
            assert call_args["bid"] is None
            assert call_args["ask"] is None

    @pytest.mark.asyncio
    async def test_handle_stock_bar_success(self):
        """Test successful handling of stock bar data"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            bar = MockBar(symbol="NVDA")

            await streaming_tools.handle_stock_bar(bar)

            # Verify buffer was accessed
            mock_buffer_fn.assert_called_once()
            # Verify data was added
            mock_buffer.add.assert_called_once()

            # Verify the data structure
            call_args = mock_buffer.add.call_args[0][0]
            assert call_args["symbol"] == "NVDA"
            assert call_args["open"] == 150.0
            assert call_args["high"] == 151.0
            assert call_args["low"] == 149.0
            assert call_args["close"] == 150.5
            assert call_args["volume"] == 10000

    @pytest.mark.asyncio
    async def test_handle_stock_status_success(self):
        """Test successful handling of stock status data"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            status = MockStatus(symbol="TSLA", status="halted")

            await streaming_tools.handle_stock_status(status)

            # Verify buffer was accessed
            mock_buffer_fn.assert_called_once()
            # Verify data was added
            mock_buffer.add.assert_called_once()

            # Verify the data structure
            call_args = mock_buffer.add.call_args[0][0]
            assert call_args["symbol"] == "TSLA"
            assert call_args["status"] == "halted"


class TestStreamManagement:
    """Test stream lifecycle management functions"""

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_basic(self):
        """Test basic stream startup"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch("alpaca_mcp_server.tools.streaming_tools.StockDataStream") as mock_stream_class,
            patch.dict(
                "os.environ", {"APCA_API_KEY_ID": "test_key", "APCA_API_SECRET_KEY": "test_secret"}
            ),
        ):

            # Setup mock settings
            mock_settings._stock_stream_active = False
            mock_settings._stock_stream_subscriptions = {
                "trades": set(),
                "quotes": set(),
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }
            mock_settings._stock_stream_config = {"buffer_size": None}
            mock_settings._stock_stream_stats = {}
            mock_settings._stock_stream_start_time = None

            # Setup mock stream
            mock_stream = MagicMock()
            mock_stream_class.return_value = mock_stream
            mock_settings._global_stock_stream = mock_stream

            # Mock threading
            with patch("alpaca_mcp_server.tools.streaming_tools.threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                result = await streaming_tools.start_global_stock_stream(
                    symbols=["AAPL", "MSFT"],
                    data_types=["trades", "quotes"],
                    feed="sip",
                )

                # Verify success message
                assert "🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!" in result
                assert "AAPL" in result
                assert "MSFT" in result

                # Verify thread was started
                mock_thread_instance.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_already_active(self):
        """Test starting stream when one is already active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = True
            mock_settings._stock_stream_subscriptions = {
                "trades": {"AAPL"},
                "quotes": {"AAPL"},
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }
            mock_settings._stock_stream_config = {"feed": "sip"}
            mock_settings._stock_stream_start_time = time.time()

            result = await streaming_tools.start_global_stock_stream(
                symbols=["MSFT"], replace_existing=False
            )

            # Should return error message about active stream
            assert "❌ Global stock stream already active!" in result
            assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_invalid_data_type(self):
        """Test starting stream with invalid data type"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.start_global_stock_stream(
                symbols=["AAPL"], data_types=["invalid_type"]
            )

            # Should return error about invalid data type
            assert "Invalid data types" in result
            assert "invalid_type" in result

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_invalid_feed(self):
        """Test starting stream with invalid feed"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.start_global_stock_stream(
                symbols=["AAPL"], feed="invalid_feed"
            )

            # Should return error about invalid feed
            assert "Feed must be 'sip' or 'iex'" in result

    @pytest.mark.asyncio
    async def test_start_global_stock_stream_missing_credentials(self):
        """Test starting stream without API credentials"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_settings._stock_stream_active = False

            result = await streaming_tools.start_global_stock_stream(symbols=["AAPL"])

            # Should return error about missing credentials
            assert "Alpaca API credentials not found" in result

    @pytest.mark.asyncio
    async def test_stop_global_stock_stream_success(self):
        """Test stopping an active stream"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Setup active stream
            mock_settings._stock_stream_active = True
            mock_settings._stock_stream_start_time = time.time() - 60  # 1 minute ago
            mock_settings._stock_stream_stats = {"trades": 1000, "quotes": 2000}
            mock_settings._stock_data_buffers = {}
            mock_settings._stock_stream_subscriptions = {
                "trades": set(),
                "quotes": set(),
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }

            # Mock stream object
            mock_stream = MagicMock()
            mock_settings._global_stock_stream = mock_stream

            result = await streaming_tools.stop_global_stock_stream()

            # Verify success message
            assert "🛑 GLOBAL STOCK STREAM STOPPED" in result
            assert "Runtime:" in result
            assert "Total Events Processed:" in result

            # Verify stream was stopped
            mock_stream.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_global_stock_stream_not_active(self):
        """Test stopping when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.stop_global_stock_stream()

            # Should return message about no active stream
            assert "No active stock stream to stop" in result

    @pytest.mark.asyncio
    async def test_add_symbols_to_stock_stream_success(self):
        """Test adding symbols to existing stream"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch(
                "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
            ) as mock_buffer_fn,
        ):

            # Setup active stream
            mock_stream = MagicMock()
            mock_settings._stock_stream_active = True
            mock_settings._global_stock_stream = mock_stream
            mock_settings._stock_stream_subscriptions = {
                "trades": {"AAPL"},
                "quotes": {"AAPL"},
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }
            mock_settings._stock_stream_config = {"buffer_size": None}
            mock_settings._stock_stream_start_time = time.time()
            mock_settings._stock_stream_stats = {"trades": 100}

            result = await streaming_tools.add_symbols_to_stock_stream(
                symbols=["MSFT", "NVDA"], data_types=["trades", "quotes"]
            )

            # Verify success message
            assert "✅ SYMBOLS ADDED TO STOCK STREAM" in result
            assert "MSFT" in result
            assert "NVDA" in result

    @pytest.mark.asyncio
    async def test_add_symbols_to_stock_stream_no_active_stream(self):
        """Test adding symbols when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.add_symbols_to_stock_stream(symbols=["AAPL"])

            # Should return error message
            assert "No active global stock stream" in result


class TestStreamDataRetrieval:
    """Test functions for retrieving streaming data"""

    @pytest.mark.asyncio
    async def test_get_stock_stream_data_trades(self):
        """Test retrieving trade data from stream"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Setup mock buffer with trade data
            mock_buffer = MagicMock()
            mock_buffer.get_all.return_value = [
                {
                    "symbol": "AAPL",
                    "price": 150.25,
                    "size": 100,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                {
                    "symbol": "AAPL",
                    "price": 150.30,
                    "size": 200,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            ]
            mock_buffer.get_stats.return_value = {
                "current_size": 2,
                "max_size": None,
                "total_added": 2,
                "last_update": time.time(),
            }

            mock_settings._stock_stream_active = True
            mock_settings._stock_data_buffers = {"AAPL_trades": mock_buffer}

            result = await streaming_tools.get_stock_stream_data(symbol="AAPL", data_type="trades")

            # Verify result contains trade data
            assert "📊 STOCK STREAM DATA: AAPL - TRADES" in result
            assert "Recent Trades:" in result
            assert "150.25" in result or "150.3" in result

    @pytest.mark.asyncio
    async def test_get_stock_stream_data_no_active_stream(self):
        """Test retrieving data when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.get_stock_stream_data(symbol="AAPL", data_type="trades")

            # Should return error message
            assert "No active stock stream" in result

    @pytest.mark.asyncio
    async def test_get_stock_stream_data_buffer_not_found(self):
        """Test retrieving data for non-existent buffer"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = True
            mock_settings._stock_data_buffers = {}

            result = await streaming_tools.get_stock_stream_data(symbol="AAPL", data_type="trades")

            # Should return error message
            assert "No stock data buffer found" in result

    @pytest.mark.asyncio
    async def test_get_stock_stream_data_with_limit(self):
        """Test retrieving data with item limit"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Create mock buffer with many items
            mock_buffer = MagicMock()
            trade_data = [
                {
                    "symbol": "AAPL",
                    "price": 150.0 + i * 0.1,
                    "size": 100,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                for i in range(20)
            ]
            mock_buffer.get_all.return_value = trade_data
            mock_buffer.get_stats.return_value = {
                "current_size": 20,
                "max_size": None,
                "total_added": 20,
                "last_update": time.time(),
            }

            mock_settings._stock_stream_active = True
            mock_settings._stock_data_buffers = {"AAPL_trades": mock_buffer}

            result = await streaming_tools.get_stock_stream_data(
                symbol="AAPL", data_type="trades", limit=5
            )

            # Should mention the limit
            assert "limited to 5 items" in result

    @pytest.mark.asyncio
    async def test_list_active_stock_streams_success(self):
        """Test listing active streams"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = True
            mock_settings._stock_stream_start_time = time.time() - 300  # 5 minutes ago
            mock_settings._stock_stream_config = {
                "feed": "sip",
                "buffer_size": None,
                "duration_seconds": None,
            }
            mock_settings._stock_stream_subscriptions = {
                "trades": {"AAPL", "MSFT"},
                "quotes": {"AAPL", "MSFT"},
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }
            mock_settings._stock_stream_stats = {"trades": 1000, "quotes": 2000}
            mock_settings._stock_data_buffers = {}

            result = await streaming_tools.list_active_stock_streams()

            # Verify result contains stream info
            assert "📡 ACTIVE STOCK STREAMING STATUS" in result
            assert "AAPL" in result
            assert "MSFT" in result
            assert "SIP" in result

    @pytest.mark.asyncio
    async def test_list_active_stock_streams_no_stream(self):
        """Test listing when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.list_active_stock_streams()

            # Should return message about no active stream
            assert "No active stock stream" in result

    @pytest.mark.asyncio
    async def test_get_stock_stream_buffer_stats_success(self):
        """Test getting buffer statistics"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Create mock buffers
            mock_buffer1 = MagicMock()
            mock_buffer1.get_stats.return_value = {
                "current_size": 100,
                "max_size": None,
                "total_added": 100,
                "last_update": time.time(),
            }
            mock_buffer1.get_all.return_value = [{}] * 100

            mock_buffer2 = MagicMock()
            mock_buffer2.get_stats.return_value = {
                "current_size": 50,
                "max_size": None,
                "total_added": 50,
                "last_update": time.time(),
            }
            mock_buffer2.get_all.return_value = [{}] * 50

            mock_settings._stock_data_buffers = {
                "AAPL_trades": mock_buffer1,
                "AAPL_quotes": mock_buffer2,
            }

            result = await streaming_tools.get_stock_stream_buffer_stats()

            # Verify result contains buffer stats
            assert "💾 STOCK STREAM BUFFER STATISTICS" in result
            assert "Total Buffers: 2" in result
            assert "Total Items: 150" in result
            assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_get_stock_stream_buffer_stats_no_buffers(self):
        """Test getting stats when no buffers exist"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_data_buffers = {}

            result = await streaming_tools.get_stock_stream_buffer_stats()

            # Should return message about no buffers
            assert "No stock stream buffers exist" in result

    @pytest.mark.asyncio
    async def test_clear_stock_stream_buffers_success(self):
        """Test clearing stream buffers"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Create mock buffers
            mock_buffer1 = MagicMock()
            mock_buffer1.get_all.return_value = [{}] * 100

            mock_buffer2 = MagicMock()
            mock_buffer2.get_all.return_value = [{}] * 50

            mock_settings._stock_data_buffers = {
                "AAPL_trades": mock_buffer1,
                "AAPL_quotes": mock_buffer2,
            }

            result = await streaming_tools.clear_stock_stream_buffers()

            # Verify buffers were cleared
            assert "🧹 STOCK STREAM BUFFERS CLEARED" in result
            assert "Buffers Cleared: 2" in result
            assert "Items Removed: 150" in result

            # Verify clear was called on each buffer
            mock_buffer1.clear.assert_called_once()
            mock_buffer2.clear.assert_called_once()


class TestStreamAnalysisTools:
    """Test stream-aware analysis and trading tools"""

    @pytest.mark.asyncio
    async def test_stream_aware_price_monitor_success(self):
        """Test stream-aware price monitoring"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch("alpaca_mcp_server.tools.streaming_tools.get_stock_stream_data") as mock_get_data,
        ):

            mock_settings._stock_stream_active = True
            mock_settings._stock_stream_config = {"feed": "sip"}

            # Mock quote and trade data responses
            mock_get_data.side_effect = [
                "Recent Quotes:\n  1. $150.00 x $150.50 @ 14:30:25\n  2. $150.10 x $150.60 @ 14:30:26",
                "Recent Trades:\n  1. $150.25 x 100 @ 14:30:25\n  2. $150.30 x 200 @ 14:30:26",
            ]

            result = await streaming_tools.stream_aware_price_monitor(
                symbol="AAPL", analysis_seconds=10
            )

            # Verify result contains monitoring data
            assert "📊 STREAM-AWARE MONITORING: AAPL" in result
            assert "Current Price:" in result
            assert "Volume Analysis" in result

    @pytest.mark.asyncio
    async def test_stream_aware_price_monitor_no_stream(self):
        """Test price monitoring when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.stream_aware_price_monitor(symbol="AAPL")

            # Should return error message
            assert "❌ No active stream" in result

    @pytest.mark.asyncio
    async def test_stream_optimized_order_placement_success(self):
        """Test stream-optimized order placement"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch("alpaca_mcp_server.tools.streaming_tools.get_stock_stream_data") as mock_get_data,
            patch("alpaca_mcp_server.tools.order_tools.place_stock_order") as mock_place_order,
        ):

            mock_settings._stock_stream_active = True

            # Mock stream quote data
            mock_get_data.return_value = "Recent Quotes:\n  1. $150.00 x $150.50 @ 14:30:25"

            # Mock order placement
            mock_place_order.return_value = "Order placed successfully"

            result = await streaming_tools.stream_optimized_order_placement(
                symbol="AAPL", side="buy", quantity=10, order_type="limit"
            )

            # Verify result contains order placement info
            assert "🎯 STREAM-OPTIMIZED ORDER PLACEMENT" in result
            assert "AAPL" in result

            # Verify order was placed with correct price (ask price for buy)
            mock_place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_optimized_order_placement_no_stream(self):
        """Test order placement when no stream is active"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            mock_settings._stock_stream_active = False

            result = await streaming_tools.stream_optimized_order_placement(
                symbol="AAPL", side="buy", quantity=10
            )

            # Should return error message
            assert "❌ No active stream" in result

    @pytest.mark.asyncio
    async def test_stream_optimized_order_placement_with_fallback(self):
        """Test order placement with fallback to quote API"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch("alpaca_mcp_server.tools.streaming_tools.get_stock_stream_data") as mock_get_data,
            patch("alpaca_mcp_server.tools.market_data_tools.get_stock_quote") as mock_get_quote,
            patch("alpaca_mcp_server.tools.order_tools.place_stock_order") as mock_place_order,
        ):

            mock_settings._stock_stream_active = True

            # Stream data returns no usable pricing
            mock_get_data.return_value = "No data available"

            # Fallback quote API provides pricing
            mock_get_quote.return_value = "Symbol: AAPL\nBid Price: $149.50\nAsk Price: $150.50"

            # Mock order placement
            mock_place_order.return_value = "Order placed successfully"

            result = await streaming_tools.stream_optimized_order_placement(
                symbol="AAPL", side="buy", quantity=10, order_type="limit"
            )

            # Verify fallback was used
            mock_get_quote.assert_called_once()
            # Verify order was placed
            mock_place_order.assert_called_once()


class TestStreamEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_handle_trade_with_non_isoformat_timestamp(self):
        """Test handling trade with non-ISO timestamp"""
        with patch(
            "alpaca_mcp_server.tools.streaming_tools._get_or_create_stock_buffer"
        ) as mock_buffer_fn:
            mock_buffer = MagicMock()
            mock_buffer_fn.return_value = mock_buffer

            trade = MockTrade()
            trade.timestamp = "2024-01-01 12:00:00"  # Non-ISO format

            # Should handle gracefully
            await streaming_tools.handle_stock_trade(trade)

            # Verify data was still added
            mock_buffer.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stream_data_with_recent_seconds_filter(self):
        """Test retrieving recent data with time filter"""
        with patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings:
            # Create mock buffer
            mock_buffer = MagicMock()
            recent_timestamp = datetime.now(UTC).isoformat()
            mock_buffer.get_recent.return_value = [
                {"symbol": "AAPL", "price": 150.0, "size": 100, "timestamp": recent_timestamp}
            ]
            mock_buffer.get_stats.return_value = {
                "current_size": 1,
                "max_size": None,
                "total_added": 1,
                "last_update": time.time(),
            }

            mock_settings._stock_stream_active = True
            mock_settings._stock_data_buffers = {"AAPL_trades": mock_buffer}

            result = await streaming_tools.get_stock_stream_data(
                symbol="AAPL", data_type="trades", recent_seconds=10
            )

            # Verify get_recent was called
            mock_buffer.get_recent.assert_called_once_with(10)
            # Verify result contains filtered data
            assert "last 10s" in result

    @pytest.mark.asyncio
    async def test_stream_startup_uppercase_conversion(self):
        """Test that symbols are converted to uppercase on stream start"""
        with (
            patch("alpaca_mcp_server.tools.streaming_tools._settings_module") as mock_settings,
            patch("alpaca_mcp_server.tools.streaming_tools.StockDataStream") as mock_stream_class,
            patch.dict(
                "os.environ", {"APCA_API_KEY_ID": "test_key", "APCA_API_SECRET_KEY": "test_secret"}
            ),
        ):

            mock_settings._stock_stream_active = False
            mock_settings._stock_stream_subscriptions = {
                "trades": set(),
                "quotes": set(),
                "bars": set(),
                "updated_bars": set(),
                "daily_bars": set(),
                "statuses": set(),
            }
            mock_settings._stock_stream_config = {"buffer_size": None}

            mock_stream = MagicMock()
            mock_stream_class.return_value = mock_stream
            mock_settings._global_stock_stream = mock_stream

            with patch("alpaca_mcp_server.tools.streaming_tools.threading.Thread"):
                result = await streaming_tools.start_global_stock_stream(
                    symbols=["aapl", "msft"],  # lowercase
                    data_types=["trades"],
                )

                # Verify uppercase symbols appear in result
                assert "AAPL" in result
                assert "MSFT" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
