"""Real-time streaming tools for day trading - fixed version."""

import asyncio
import contextlib
import os

# Import the actual module for modifying variables (not the settings instance)
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime

from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream

# Import all streaming state variables directly from settings module
from alpaca_mcp_server.config.settings import (
    get_or_create_stock_buffer as _get_or_create_stock_buffer,  # Classes and functions
)

# Get the actual module from sys.modules to avoid the Settings instance shadowing
_settings_module = sys.modules["alpaca_mcp_server.config.settings"]


# Event handlers for streaming data
async def handle_stock_trade(trade):
    """Handle incoming stock trade data"""
    try:
        symbol = trade.symbol
        buffer = _get_or_create_stock_buffer(
            symbol, "trades", _settings_module._stock_stream_config["buffer_size"]
        )

        trade_data = {
            "symbol": symbol,
            "price": float(trade.price),
            "size": int(trade.size),
            "timestamp": (
                trade.timestamp.isoformat()
                if hasattr(trade.timestamp, "isoformat")
                else str(trade.timestamp)
            ),
            "conditions": getattr(trade, "conditions", []),
            "exchange": getattr(trade, "exchange", "Unknown"),
        }

        buffer.add(trade_data)
        _settings_module._stock_stream_stats["trades"] += 1

    except Exception as e:
        print(f"Error handling stock trade: {e}")


async def handle_stock_quote(quote):
    """Handle incoming stock quote data"""
    try:
        symbol = quote.symbol
        buffer = _get_or_create_stock_buffer(
            symbol, "quotes", _settings_module._stock_stream_config["buffer_size"]
        )

        quote_data = {
            "symbol": symbol,
            "bid": float(quote.bid_price) if quote.bid_price else None,
            "ask": float(quote.ask_price) if quote.ask_price else None,
            "bid_size": int(quote.bid_size) if quote.bid_size else None,
            "ask_size": int(quote.ask_size) if quote.ask_size else None,
            "timestamp": (
                quote.timestamp.isoformat()
                if hasattr(quote.timestamp, "isoformat")
                else str(quote.timestamp)
            ),
            "bid_exchange": getattr(quote, "bid_exchange", "Unknown"),
            "ask_exchange": getattr(quote, "ask_exchange", "Unknown"),
        }

        buffer.add(quote_data)
        _settings_module._stock_stream_stats["quotes"] += 1

    except Exception as e:
        print(f"Error handling stock quote: {e}")


async def handle_stock_bar(bar):
    """Handle incoming stock bar data"""

    try:
        symbol = bar.symbol
        buffer = _get_or_create_stock_buffer(
            symbol, "bars", _settings_module._stock_stream_config["buffer_size"]
        )

        bar_data = {
            "symbol": symbol,
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": int(bar.volume),
            "timestamp": (
                bar.timestamp.isoformat()
                if hasattr(bar.timestamp, "isoformat")
                else str(bar.timestamp)
            ),
            "trade_count": getattr(bar, "trade_count", None),
            "vwap": getattr(bar, "vwap", None),
        }

        buffer.add(bar_data)
        _settings_module._stock_stream_stats["bars"] += 1

    except Exception as e:
        print(f"Error handling stock bar: {e}")


async def handle_stock_status(status):
    """Handle incoming stock status data"""

    try:
        symbol = status.symbol
        buffer = _get_or_create_stock_buffer(
            symbol, "statuses", _settings_module._stock_stream_config["buffer_size"]
        )

        status_data = {
            "symbol": symbol,
            "status": str(status.status),
            "timestamp": (
                status.timestamp.isoformat()
                if hasattr(status.timestamp, "isoformat")
                else str(status.timestamp)
            ),
            "tape": getattr(status, "tape", "Unknown"),
        }

        buffer.add(status_data)
        _settings_module._stock_stream_stats["statuses"] += 1

    except Exception as e:
        print(f"Error handling stock status: {e}")


async def start_global_stock_stream(
    symbols: list[str],
    data_types: list[str] = None,
    feed: str = "sip",
    duration_seconds: int | None = None,
    buffer_size_per_symbol: int | None = None,
    replace_existing: bool = False,
) -> str:
    """
    Start the global real-time stock market data stream (Alpaca allows only one stream connection).

    Args:
        symbols (List[str]): List of stock symbols to stream (e.g., ['AAPL', 'MSFT', 'NVDA'])
        data_types (List[str]): Types of stock data to stream. Options:
            - "trades": Real-time stock trade executions
            - "quotes": Stock bid/ask prices and sizes
            - "bars": 1-minute OHLCV stock bars
            - "updated_bars": Corrections to stock minute bars
            - "daily_bars": Daily OHLCV stock bars
            - "statuses": Stock trading halt/resume notifications
        feed (str): Stock data feed source ("sip" for all exchanges, "iex" for IEX only)
        duration_seconds (Optional[int]): How long to run the stock stream in seconds. None = run indefinitely
        buffer_size_per_symbol (Optional[int]): Max items per stock symbol/data_type buffer.
                                               None = unlimited (recommended for active stocks)
                                               High-velocity stocks may need 10000+ or unlimited
        replace_existing (bool): If True, stop existing stock stream and start new one

    Returns:
        str: Confirmation with stock stream details and data access instructions
    """
    if data_types is None:
        data_types = ["trades", "quotes"]
    try:
        # Check if stock stream already exists
        if _settings_module._stock_stream_active and not replace_existing:
            current_symbols = set()
            for _data_type, symbol_set in _settings_module._stock_stream_subscriptions.items():
                current_symbols.update(symbol_set)

            return f"""
❌ Global stock stream already active!

Current Stock Stream:
└── Symbols: {", ".join(sorted(current_symbols)) if current_symbols else "None"}
└── Data Types: {[dt for dt, symbols in _settings_module._stock_stream_subscriptions.items() if symbols]}
└── Feed: {_settings_module._stock_stream_config["feed"].upper()}
└── Runtime: {(time.time() - _settings_module._stock_stream_start_time) / 60:.1f} minutes

Options:
└── Use add_symbols_to_stock_stream() to add more symbols
└── Use stop_global_stock_stream() to stop current stream
└── Use replace_existing=True to replace current stream
            """

        # Stop existing stock stream if replacing
        if _settings_module._stock_stream_active and replace_existing:
            await stop_global_stock_stream()
            await asyncio.sleep(2)  # Give time for cleanup

        # Validate parameters
        valid_data_types = [
            "trades",
            "quotes",
            "bars",
            "updated_bars",
            "daily_bars",
            "statuses",
        ]
        invalid_types = [dt for dt in data_types if dt not in valid_data_types]
        if invalid_types:
            return f"Invalid data types: {invalid_types}. Valid options: {valid_data_types}"

        if feed.lower() not in ["sip", "iex"]:
            return "Feed must be 'sip' or 'iex'"

        # Convert symbols to uppercase
        symbols = [s.upper() for s in symbols]

        # Update global stock stream config
        _settings_module._stock_stream_config.update(
            {
                "feed": feed,
                "buffer_size": buffer_size_per_symbol,
                "duration_seconds": duration_seconds,
            }
        )

        # Create data feed enum
        feed_enum = DataFeed.SIP if feed.lower() == "sip" else DataFeed.IEX

        # Get API credentials directly from environment
        api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

        if not api_key or not api_secret:
            return "Error: Alpaca API credentials not found in environment variables. Please set APCA_API_KEY_ID and APCA_API_SECRET_KEY."

        # Create the single global stock stream
        _settings_module._global_stock_stream = StockDataStream(
            api_key=api_key,
            secret_key=api_secret,
            feed=feed_enum,
            raw_data=False,
        )

        # Subscribe to requested stock data types
        if "trades" in data_types:
            _settings_module._global_stock_stream.subscribe_trades(handle_stock_trade, *symbols)
            _settings_module._stock_stream_subscriptions["trades"].update(symbols)

        if "quotes" in data_types:
            _settings_module._global_stock_stream.subscribe_quotes(handle_stock_quote, *symbols)
            _settings_module._stock_stream_subscriptions["quotes"].update(symbols)

        if "bars" in data_types:
            _settings_module._global_stock_stream.subscribe_bars(handle_stock_bar, *symbols)
            _settings_module._stock_stream_subscriptions["bars"].update(symbols)

        if "updated_bars" in data_types:
            _settings_module._global_stock_stream.subscribe_updated_bars(handle_stock_bar, *symbols)
            _settings_module._stock_stream_subscriptions["updated_bars"].update(symbols)

        if "daily_bars" in data_types:
            _settings_module._global_stock_stream.subscribe_daily_bars(handle_stock_bar, *symbols)
            _settings_module._stock_stream_subscriptions["daily_bars"].update(symbols)

        if "statuses" in data_types:
            _settings_module._global_stock_stream.subscribe_trading_statuses(
                handle_stock_status, *symbols
            )
            _settings_module._stock_stream_subscriptions["statuses"].update(symbols)

        # Function to run the stock stream with duration monitoring
        def run_stock_stream():
            try:
                _settings_module._stock_stream_active = True
                _settings_module._stock_stream_start_time = time.time()
                _settings_module._stock_stream_end_time = (
                    _settings_module._stock_stream_start_time + duration_seconds
                    if duration_seconds
                    else None
                )

                print(f"Starting Alpaca stock stream for {len(symbols)} symbols...")

                # Start the stock stream
                _settings_module._global_stock_stream.run()

            except Exception as e:
                print(f"Stock stream error: {e}")
            finally:
                _settings_module._stock_stream_active = False
                print("Stock stream stopped")

        # Start the stock stream in a background thread
        _settings_module._stock_stream_thread = threading.Thread(
            target=run_stock_stream, daemon=True
        )
        _settings_module._stock_stream_thread.start()

        # Wait a moment for connection
        await asyncio.sleep(2)

        # Format response
        buffer_info = (
            "Unlimited" if buffer_size_per_symbol is None else f"{buffer_size_per_symbol:,} items"
        )
        duration_info = f"{duration_seconds:,} seconds" if duration_seconds else "Indefinite"

        return f"""
🚀 GLOBAL STOCK STREAM STARTED SUCCESSFULLY!

📊 Stock Stream Configuration:
└── Symbols: {", ".join(symbols)} ({len(symbols)} stock symbols)
└── Data Types: {", ".join(data_types)}
└── Feed: {feed.upper()}
└── Duration: {duration_info}
└── Buffer Size per Symbol: {buffer_info}
└── Start Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

💾 Stock Data Access:
└── get_stock_stream_data("AAPL", "trades") - Recent stock trades
└── get_stock_stream_buffer_stats() - Buffer statistics
└── list_active_stock_streams() - Current stream status
└── get_stock_stream_analysis("NVDA", "momentum") - Real-time analysis

⚡ Stock Stream Management:
└── add_symbols_to_stock_stream(["TSLA", "META"]) - Add more stocks
└── stop_global_stock_stream() - Stop streaming

🔥 Pro Tips for Stock Trading:
└── For active stocks like NVDA, TSLA: unlimited buffers recommended
└── Use get_stock_stream_data() with time filters for analysis
└── Combine with stock snapshots for comprehensive market view
└── Stock stream data persists until manually cleared
        """

    except Exception as e:
        return f"Error starting global stock stream: {str(e)}"


async def stop_global_stock_stream() -> str:
    """
    Stop the global stock streaming session and provide final statistics.

    Returns:
        str: Final statistics and confirmation message
    """
    try:
        if not _settings_module._stock_stream_active:
            return "No active stock stream to stop."

        # Calculate final statistics
        runtime_minutes = (
            (time.time() - _settings_module._stock_stream_start_time) / 60
            if _settings_module._stock_stream_start_time
            else 0
        )
        total_events = sum(_settings_module._stock_stream_stats.values())

        # Stop the stream
        _settings_module._stock_stream_active = False

        if _settings_module._global_stock_stream:
            with contextlib.suppress(Exception):
                _settings_module._global_stock_stream.stop()

        # Get final buffer statistics
        total_buffered_items = sum(
            len(buffer.get_all()) for buffer in _settings_module._stock_data_buffers.values()
        )

        # Clear subscriptions
        for data_type in _settings_module._stock_stream_subscriptions:
            _settings_module._stock_stream_subscriptions[data_type].clear()

        result = "🛑 GLOBAL STOCK STREAM STOPPED\n"
        result += "=" * 40 + "\n\n"

        result += "📊 Final Stock Statistics:\n"
        result += f"  Runtime: {runtime_minutes:.1f} minutes\n"
        result += f"  Total Events Processed: {total_events:,}\n"
        result += f"  Items in Buffers: {total_buffered_items:,}\n"

        if runtime_minutes > 0:
            result += f"  Average Rate: {total_events / runtime_minutes:.1f} events/min\n"

        # Breakdown by data type
        result += "\n📈 Event Breakdown:\n"
        for data_type, count in _settings_module._stock_stream_stats.items():
            if count > 0:
                percentage = (count / total_events * 100) if total_events > 0 else 0
                result += f"  {data_type.title()}: {count:,} ({percentage:.1f}%)\n"

        # Buffer retention info
        result += "\n💾 Data Retention:\n"
        result += f"  Buffers: {len(_settings_module._stock_data_buffers)} remain in memory\n"
        result += "  Access: Use get_stock_stream_data() for historical analysis\n"
        result += "  Cleanup: Use clear_stock_stream_buffers() to free memory\n"

        result += "\n🔄 Restart Options:\n"
        result += "  start_global_stock_stream() - Start fresh stream\n"
        result += "  clear_stock_stream_buffers() - Free memory first\n"

        return result

    except Exception as e:
        return f"Error stopping stock stream: {str(e)}"


async def add_symbols_to_stock_stream(
    symbols: list[str], data_types: list[str] | None = None
) -> str:
    """
    Add stock symbols to the existing global stock stream (if active).

    Args:
        symbols (List[str]): List of stock symbols to add
        data_types (Optional[List[str]]): Stock data types to subscribe for new symbols.
                                         If None, uses same types as existing subscriptions.

    Returns:
        str: Confirmation message with updated stock subscription details
    """

    try:
        if not _settings_module._stock_stream_active or not _settings_module._global_stock_stream:
            return "No active global stock stream. Use start_global_stock_stream() first."

        symbols = [s.upper() for s in symbols]

        # Determine data types to subscribe
        if data_types is None:
            # Use existing subscription types
            data_types = [
                dt
                for dt, symbol_set in _settings_module._stock_stream_subscriptions.items()
                if symbol_set
            ]
            if not data_types:
                return "No existing stock subscriptions found. Specify data_types parameter."

        # Add stock subscriptions
        added_subscriptions = []

        if "trades" in data_types and "trades" in [
            dt for dt, s in _settings_module._stock_stream_subscriptions.items() if s
        ]:
            _settings_module._global_stock_stream.subscribe_trades(handle_stock_trade, *symbols)
            _settings_module._stock_stream_subscriptions["trades"].update(symbols)
            added_subscriptions.append("trades")

        if "quotes" in data_types and "quotes" in [
            dt for dt, s in _settings_module._stock_stream_subscriptions.items() if s
        ]:
            _settings_module._global_stock_stream.subscribe_quotes(handle_stock_quote, *symbols)
            _settings_module._stock_stream_subscriptions["quotes"].update(symbols)
            added_subscriptions.append("quotes")

        if "bars" in data_types and "bars" in [
            dt for dt, s in _settings_module._stock_stream_subscriptions.items() if s
        ]:
            _settings_module._global_stock_stream.subscribe_bars(handle_stock_bar, *symbols)
            _settings_module._stock_stream_subscriptions["bars"].update(symbols)
            added_subscriptions.append("bars")

        # Create buffers for new stock symbols
        for symbol in symbols:
            for data_type in data_types:
                _get_or_create_stock_buffer(
                    symbol, data_type, _settings_module._stock_stream_config["buffer_size"]
                )

        # Get current total stock symbols
        all_symbols = set()
        for symbol_set in _settings_module._stock_stream_subscriptions.values():
            all_symbols.update(symbol_set)

        return f"""
✅ SYMBOLS ADDED TO STOCK STREAM

📈 Added: {", ".join(symbols)}
📊 Data Types: {", ".join(added_subscriptions)}
🔢 Total Stock Symbols: {len(all_symbols)}
💾 Buffers Created: {len(symbols) * len(data_types)}

Current Stock Stream:
└── All Symbols: {", ".join(sorted(all_symbols))}
└── Runtime: {(time.time() - _settings_module._stock_stream_start_time) / 60:.1f} minutes
└── Total Events: {sum(_settings_module._stock_stream_stats.values()):,}
        """

    except Exception as e:
        return f"Error adding symbols to stock stream: {str(e)}"


async def stream_aware_price_monitor(symbol: str, analysis_seconds: int = 10) -> str:
    """
    Enhanced real-time price monitoring using shared stream with concurrent analysis.
    Optimized for single-stream architecture - feeds multiple concurrent processes.

    Args:
        symbol: Stock symbol to monitor
        analysis_seconds: Seconds of recent data to analyze (default: 10)

    Returns:
        Comprehensive streaming analysis with real-time calculations
    """
    try:
        if not _settings_module._stock_stream_active:
            return "❌ No active stream. Use start_global_stock_stream() first."

        symbol = symbol.upper()

        # Concurrent data pulls from single stream
        quotes_task = get_stock_stream_data(symbol, "quotes", recent_seconds=analysis_seconds)
        trades_task = get_stock_stream_data(symbol, "trades", recent_seconds=analysis_seconds)

        # Execute concurrently
        quotes_data, trades_data = await asyncio.gather(
            quotes_task, trades_task, return_exceptions=True
        )

        # Extract pricing intelligence
        current_price = None
        bid_ask_spread = None
        volume_analysis = {
            "total_volume": 0,
            "avg_trade_size": 0,
            "trade_count": 0,
            "price_range": "N/A",
            "last_trade_price": None,
        }

        # Process quotes for pricing
        if isinstance(quotes_data, str) and "Recent Quotes:" in quotes_data:
            quote_lines = [line.strip() for line in quotes_data.split("\n") if "$" in line]
            if quote_lines:
                last_quote = quote_lines[-1]
                # Extract bid/ask from format like "$20.1234 x $20.5678 @ 14:30:25"
                if " x " in last_quote:
                    bid_str, ask_str = last_quote.split(" x ")[:2]
                    try:
                        bid = float(bid_str.split("$")[1])
                        ask = float(ask_str.split("$")[1])
                        current_price = (bid + ask) / 2
                        bid_ask_spread = ask - bid
                    except (ValueError, IndexError, AttributeError):
                        pass

        # Process trades for volume
        if isinstance(trades_data, str) and "Recent Trades:" in trades_data:
            trade_lines = [
                line.strip() for line in trades_data.split("\n") if "$" in line and " x " in line
            ]
            if trade_lines:
                total_volume = 0
                trade_count = len(trade_lines)
                prices = []

                for trade in trade_lines:
                    try:
                        # Extract from format like "$20.1234 x 1,000 @ 14:30:25"
                        parts = trade.split(" x ")
                        if len(parts) >= 2:
                            price = float(parts[0].split("$")[1])
                            volume_part = parts[1].split(" @")[0].replace(",", "")
                            volume = int(volume_part)
                            total_volume += volume
                            prices.append(price)
                    except (ValueError, IndexError, AttributeError):
                        continue

                volume_analysis = {
                    "total_volume": total_volume,
                    "avg_trade_size": total_volume // trade_count if trade_count > 0 else 0,
                    "trade_count": trade_count,
                    "price_range": f"${min(prices):.4f} - ${max(prices):.4f}" if prices else "N/A",
                    "last_trade_price": prices[-1] if prices else None,
                }

                # Use last trade price if no quote price available
                if current_price is None and prices:
                    current_price = prices[-1]

        # Format intelligent response
        result = f"📊 STREAM-AWARE MONITORING: {symbol}\n"
        result += "=" * 50 + "\n\n"

        result += (
            f"💰 Current Price: ${current_price:.4f}\n"
            if current_price
            else "💰 Current Price: Pending data\n"
        )
        result += (
            f"📈 Bid-Ask Spread: ${bid_ask_spread:.4f}\n"
            if bid_ask_spread
            else "📈 Bid-Ask Spread: N/A\n"
        )
        result += f"📊 Volume Analysis ({analysis_seconds}s):\n"
        result += f"  └── Trades: {volume_analysis['trade_count']}\n"
        result += f"  └── Total Volume: {volume_analysis['total_volume']:,} shares\n"
        result += f"  └── Avg Trade Size: {volume_analysis['avg_trade_size']:,} shares\n"
        result += f"  └── Price Range: {volume_analysis['price_range']}\n"

        # Real-time status indicators
        result += "\n⚡ Stream Health:\n"
        result += f"  └── Data Age: <{analysis_seconds}s (real-time)\n"
        result += "  └── Stream Status: Active\n"
        result += f"  └── Feed Type: {_settings_module._stock_stream_config.get('feed', 'Unknown').upper()}\n"

        # Trading signals
        if current_price and bid_ask_spread:
            spread_pct = (bid_ask_spread / current_price) * 100
            result += "\n🎯 Trading Conditions:\n"
            result += (
                f"  └── Spread: {spread_pct:.3f}% {'(Tight)' if spread_pct < 0.5 else '(Wide)'}\n"
            )
            trade_count = int(volume_analysis.get("trade_count", 0))
            result += f"  └── Liquidity: {'Good' if isinstance(trade_count, int) and trade_count > 5 else 'Limited'}\n"

        return result

    except Exception as e:
        return f"❌ Stream monitoring error: {str(e)}"


async def get_stock_stream_data(
    symbol: str,
    data_type: str,
    recent_seconds: int | None = None,
    limit: int | None = None,
) -> str:
    """
    Retrieve streaming stock market data for a symbol with flexible filtering.

    Args:
        symbol (str): Stock symbol
        data_type (str): Type of stock data ("trades", "quotes", "bars", etc.)
        recent_seconds (Optional[int]): Get stock data from last N seconds. None = all data
        limit (Optional[int]): Maximum number of items to return. None = no limit

    Returns:
        str: Formatted streaming stock data with statistics
    """
    try:
        if not _settings_module._stock_stream_active:
            return "No active stock stream. Use start_global_stock_stream() to begin streaming."

        symbol = symbol.upper()
        buffer_key = f"{symbol}_{data_type}"

        if buffer_key not in _settings_module._stock_data_buffers:
            return f"No stock data buffer found for {symbol} {data_type}. Check if stock symbol is subscribed."

        buffer = _settings_module._stock_data_buffers[buffer_key]

        # Get data based on filters
        if recent_seconds is not None:
            data = buffer.get_recent(recent_seconds)
            time_filter = f"last {recent_seconds}s"
        else:
            data = buffer.get_all()
            time_filter = "all time"

        # Apply limit if specified
        if limit is not None and len(data) > limit:
            data = data[-limit:]  # Get most recent items
            limit_info = f", limited to {limit} items"
        else:
            limit_info = ""

        if not data:
            return f"No {data_type} data found for {symbol} ({time_filter})"

        # Get buffer statistics
        buffer_stats = buffer.get_stats()

        # Format the response
        result = f"📊 STOCK STREAM DATA: {symbol} - {data_type.upper()}\n"
        result += "=" * 60 + "\n\n"

        result += f"🔍 Filter: {time_filter}{limit_info}\n"
        result += f"📈 Results: {len(data)} items\n"
        utilization = (
            "100%"
            if buffer_stats.get("max_size") is None
            else (
                f"{(buffer_stats['current_size'] / buffer_stats['max_size'] * 100):.1f}%"
                if buffer_stats.get("max_size", 0) > 0
                else "0%"
            )
        )
        result += f"💾 Buffer: {buffer_stats['current_size']} total items (utilization: {utilization})\n\n"

        # Show recent data samples
        if data_type == "trades":
            result += "Recent Trades:\n"
            for i, trade in enumerate(data[-10:], 1):  # Last 10 trades
                # Extract time portion from timestamp
                timestamp_str = str(trade["timestamp"])
                if "T" in timestamp_str:
                    # ISO format: extract time part
                    time_part = timestamp_str.split("T")[1][:12]  # HH:MM:SS.mmm
                else:
                    # Unix timestamp: convert to readable time
                    try:
                        from datetime import datetime

                        ts = float(timestamp_str)
                        time_part = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:12]
                    except (ValueError, OSError):
                        time_part = timestamp_str[-12:]  # fallback
                result += f"  {i:2d}. ${trade['price']:8.4f} x {trade['size']:,} @ {time_part}\n"

        elif data_type == "quotes":
            result += "Recent Quotes:\n"
            for i, quote in enumerate(data[-10:], 1):  # Last 10 quotes
                bid = f"${quote['bid']:.4f}" if quote["bid"] else "N/A"
                ask = f"${quote['ask']:.4f}" if quote["ask"] else "N/A"
                # Extract time portion from timestamp
                timestamp_str = str(quote["timestamp"])
                if "T" in timestamp_str:
                    # ISO format: extract time part
                    time_part = timestamp_str.split("T")[1][:12]  # HH:MM:SS.mmm
                else:
                    # Unix timestamp: convert to readable time
                    try:
                        from datetime import datetime

                        ts = float(timestamp_str)
                        time_part = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:12]
                    except (ValueError, OSError):
                        time_part = timestamp_str[-12:]  # fallback
                result += f"  {i:2d}. {bid} x {ask} @ {time_part}\n"

        elif data_type == "bars":
            result += "Recent Bars:\n"
            for i, bar in enumerate(data[-5:], 1):  # Last 5 bars
                result += f"  {i}. O:${bar['open']:.4f} H:${bar['high']:.4f} L:${bar['low']:.4f} C:${bar['close']:.4f} V:{bar['volume']:,}\n"

        # Add analysis summary for trades
        if data_type == "trades" and len(data) > 1:
            prices = [t["price"] for t in data]
            volumes = [t["size"] for t in data]

            result += "\n📊 Quick Analysis:\n"
            result += f"  Price Range: ${min(prices):.4f} - ${max(prices):.4f}\n"
            result += f"  Last Price: ${prices[-1]:.4f}\n"
            result += f"  Total Volume: {sum(volumes):,} shares\n"
            result += f"  Avg Trade Size: {sum(volumes) / len(volumes):.0f} shares\n"

        return result

    except Exception as e:
        return f"Error retrieving stock stream data: {str(e)}"


async def list_active_stock_streams() -> str:
    """
    List all active stock streaming subscriptions and their status.

    Returns:
        str: Detailed information about active stock streams
    """
    try:
        if not _settings_module._stock_stream_active:
            return "No active stock stream. Use start_global_stock_stream() to begin streaming."

        runtime_minutes = (
            (time.time() - _settings_module._stock_stream_start_time) / 60
            if _settings_module._stock_stream_start_time
            else 0
        )

        result = "📡 ACTIVE STOCK STREAMING STATUS\n"
        result += "=" * 50 + "\n\n"

        # Stream configuration
        result += "🔧 Stream Configuration:\n"
        result += f"  Feed: {_settings_module._stock_stream_config['feed'].upper()}\n"
        result += f"  Runtime: {runtime_minutes:.1f} minutes\n"
        buffer_size_info = (
            "Unlimited"
            if _settings_module._stock_stream_config["buffer_size"] is None
            else f"{_settings_module._stock_stream_config['buffer_size']:,} per buffer"
        )
        result += f"  Buffer Size: {buffer_size_info}\n"

        if _settings_module._stock_stream_config["duration_seconds"]:
            remaining = (
                _settings_module._stock_stream_config["duration_seconds"]
                - (time.time() - _settings_module._stock_stream_start_time)
            ) / 60
            result += f"  Duration: {_settings_module._stock_stream_config['duration_seconds'] / 60:.1f} min ({remaining:.1f} min remaining)\n"
        else:
            result += "  Duration: Indefinite\n"

        # Active subscriptions
        result += "\n📊 Active Stock Subscriptions:\n"
        total_symbols = set()

        for data_type, symbol_set in _settings_module._stock_stream_subscriptions.items():
            if symbol_set:
                result += f"  {data_type.upper()}: {', '.join(sorted(symbol_set))} ({len(symbol_set)} symbols)\n"
                total_symbols.update(symbol_set)

        result += f"\nTotal Unique Symbols: {len(total_symbols)}\n"

        # Statistics
        total_events = sum(_settings_module._stock_stream_stats.values())
        result += "\n📈 Streaming Statistics:\n"
        result += f"  Total Events: {total_events:,}\n"
        if runtime_minutes > 0:
            result += f"  Rate: {total_events / runtime_minutes:.1f} events/min\n"

        for data_type, count in _settings_module._stock_stream_stats.items():
            if count > 0:
                result += f"  {data_type.title()}: {count:,}\n"

        # Buffer status
        result += "\n💾 Buffer Status:\n"
        result += f"  Total Buffers: {len(_settings_module._stock_data_buffers)}\n"
        total_buffered = sum(
            len(buffer.get_all()) for buffer in _settings_module._stock_data_buffers.values()
        )
        result += f"  Total Items Buffered: {total_buffered:,}\n"

        # Quick access commands
        result += "\n🔧 Management Commands:\n"
        result += '  get_stock_stream_data("AAPL", "trades") - View recent trades\n'
        result += "  get_stock_stream_buffer_stats() - Detailed buffer stats\n"
        result += '  add_symbols_to_stock_stream(["TSLA"]) - Add more symbols\n'
        result += "  stop_global_stock_stream() - Stop streaming\n"

        return result

    except Exception as e:
        return f"Error listing active stock streams: {str(e)}"


async def get_stock_stream_buffer_stats() -> str:
    """
    Get detailed statistics about all streaming data buffers.

    Returns:
        str: Comprehensive buffer statistics
    """
    try:
        if not _settings_module._stock_data_buffers:
            return "No stock stream buffers exist. Start streaming first with start_global_stock_stream()."

        result = "💾 STOCK STREAM BUFFER STATISTICS\n"
        result += "=" * 60 + "\n\n"

        total_items = 0
        total_buffers = len(_settings_module._stock_data_buffers)

        # Group by symbol
        from typing import Any

        symbol_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"buffers": 0, "total_items": 0, "data_types": []}
        )

        for buffer_key, buffer in _settings_module._stock_data_buffers.items():
            symbol, data_type = buffer_key.rsplit("_", 1)
            stats = buffer.get_stats()

            symbol_stats[symbol]["buffers"] += 1
            symbol_stats[symbol]["total_items"] += stats["current_size"]
            symbol_stats[symbol]["data_types"].append(data_type)
            total_items += stats["current_size"]

        # Summary stats
        result += "📊 Summary:\n"
        result += f"  Total Buffers: {total_buffers}\n"
        result += f"  Total Items: {total_items:,}\n"
        result += f"  Unique Symbols: {len(symbol_stats)}\n"
        result += f"  Avg Items per Buffer: {total_items / total_buffers:.1f}\n\n"

        # Per-symbol breakdown
        result += "📈 Per-Symbol Breakdown:\n"
        for symbol, stats in sorted(symbol_stats.items()):
            result += f"  {symbol}:\n"
            result += f"    Buffers: {stats['buffers']} ({', '.join(str(dt) for dt in stats['data_types'])})\n"
            result += f"    Items: {stats['total_items']:,}\n"
            buffers_count = stats["buffers"]
            total_items = stats["total_items"]
            avg_per_buffer = total_items / buffers_count if buffers_count > 0 else 0
            result += f"    Avg per Buffer: {avg_per_buffer:.1f}\n"

        # Detailed buffer info
        result += "\n🔍 Detailed Buffer Information:\n"
        for buffer_key, buffer in sorted(_settings_module._stock_data_buffers.items()):
            stats = buffer.get_stats()
            last_update = (
                datetime.fromtimestamp(stats["last_update"]).strftime("%H:%M:%S")
                if stats["last_update"]
                else "Never"
            )
            result += f"  {buffer_key}:\n"
            utilization = (
                "100%"
                if stats.get("max_size") is None
                else (
                    f"{(stats['current_size'] / stats['max_size'] * 100):.1f}%"
                    if stats.get("max_size", 0) > 0
                    else "0%"
                )
            )
            result += f"    Size: {utilization}\n"
            result += f"    Total Added: {stats['total_added']:,}\n"
            result += f"    Last Update: {last_update}\n"

        # Memory usage estimate
        avg_item_size = 200  # Rough estimate in bytes
        estimated_memory_mb = (total_items * avg_item_size) / (1024 * 1024)
        result += f"\n🖥️  Estimated Memory Usage: {estimated_memory_mb:.1f} MB\n"

        # Cleanup options
        result += "\n🧹 Cleanup Options:\n"
        result += "  clear_stock_stream_buffers() - Clear all buffers\n"
        result += "  Individual buffer access via get_stock_stream_data()\n"

        return result

    except Exception as e:
        return f"Error getting buffer statistics: {str(e)}"


async def stream_optimized_order_placement(
    symbol: str, side: str, quantity: float, order_type: str = "limit"
) -> str:
    """
    Place order using optimal pricing from active stream.
    Single-stream architecture optimized for real-time execution.

    Args:
        symbol: Stock symbol
        side: "buy" or "sell"
        quantity: Number of shares
        order_type: "limit", "market", etc.

    Returns:
        Order placement result with stream-derived pricing
    """
    try:
        if not _settings_module._stock_stream_active:
            return "❌ No active stream for optimal pricing. Use start_global_stock_stream() first."

        symbol = symbol.upper()

        # Get real-time pricing from stream (last 5 seconds for freshest data)
        stream_quotes = await get_stock_stream_data(symbol, "quotes", recent_seconds=5)

        # Extract optimal pricing
        optimal_price = None

        if isinstance(stream_quotes, str) and "Recent Quotes:" in stream_quotes:
            quote_lines = [
                line.strip() for line in stream_quotes.split("\n") if "$" in line and " x " in line
            ]
            if quote_lines:
                last_quote = quote_lines[-1]
                try:
                    # Extract bid/ask from format like "   1. $20.1234 x $20.5678 @ 14:30:25"
                    # First remove the number prefix if present
                    if ". " in last_quote:
                        last_quote = last_quote.split(". ", 1)[1]

                    # Now extract bid/ask
                    if " x " in last_quote:
                        parts = last_quote.split(" x ")
                        if len(parts) >= 2:
                            bid_str = parts[0].strip()
                            ask_part = parts[1].split(" @")[0].strip()

                            # Remove $ and convert to float
                            bid = float(bid_str.replace("$", ""))
                            ask = float(ask_part.replace("$", ""))

                            # Calculate optimal limit price
                            optimal_price = ask if side.lower() == "buy" else bid
                except Exception as e:
                    print(f"Debug: Error parsing quote '{last_quote}': {e}")
                    pass

        # If stream data didn't provide pricing, try fallback methods
        if optimal_price is None:
            print(f"Debug: Stream data failed for {symbol}, trying fallback methods...")

            # Try to get real-time quote as fallback
            try:
                from alpaca_mcp_server.tools.market_data_tools import get_stock_quote

                quote_result = await get_stock_quote(symbol)

                # Parse quote data for bid/ask prices
                if "Ask Price:" in quote_result and "Bid Price:" in quote_result:
                    lines = quote_result.split("\n")
                    ask_price = None
                    bid_price = None

                    for line in lines:
                        if "Ask Price:" in line:
                            ask_str = line.split("$")[1]
                            ask_price = float(ask_str)
                        elif "Bid Price:" in line:
                            bid_str = line.split("$")[1]
                            bid_price = float(bid_str)

                    if ask_price and bid_price:
                        optimal_price = ask_price if side.lower() == "buy" else bid_price
                        print(f"Debug: Fallback quote pricing successful - {optimal_price}")
            except Exception as e:
                print(f"Debug: Quote fallback failed: {e}")

            # If quote fallback failed, try snapshot as final fallback
            if optimal_price is None:
                try:
                    from alpaca_mcp_server.tools.market_data_tools import get_stock_snapshots

                    snapshot_result = await get_stock_snapshots(symbol)

                    # Parse snapshot data for bid/ask prices
                    if "Bid:" in snapshot_result and "Ask:" in snapshot_result:
                        lines = snapshot_result.split("\n")
                        ask_price = None
                        bid_price = None

                        for line in lines:
                            if "• Ask:" in line:
                                # Extract from format like "• Ask: $20.34 (Size: 100)"
                                ask_part = line.split("$")[1].split(" ")[0]
                                ask_price = float(ask_part)
                            elif "• Bid:" in line:
                                # Extract from format like "• Bid: $20.32 (Size: 200)"
                                bid_part = line.split("$")[1].split(" ")[0]
                                bid_price = float(bid_part)

                        if ask_price and bid_price:
                            optimal_price = ask_price if side.lower() == "buy" else bid_price
                            print(f"Debug: Fallback snapshot pricing successful - {optimal_price}")
                except Exception as e:
                    print(f"Debug: Snapshot fallback failed: {e}")

        if optimal_price is None:
            return f"❌ Unable to determine optimal price for {symbol} from stream data or fallback methods. Ensure symbol is valid and market data is available."

        # Import order placement tool
        from alpaca_mcp_server.tools.order_tools import format_price_for_alpaca, place_stock_order

        # Format optimal price for penny stocks
        if optimal_price is not None:
            optimal_price = format_price_for_alpaca(optimal_price, optimal_price)

        # Execute with stream-derived pricing
        # Determine time_in_force based on order_type parameter
        if order_type.lower() == "ioc":
            actual_order_type = "limit"
            time_in_force = "ioc"
        else:
            actual_order_type = order_type
            time_in_force = "day"

        order_result = await place_stock_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=actual_order_type,
            limit_price=optimal_price if actual_order_type == "limit" else None,
            time_in_force=time_in_force,
            extended_hours=True,  # Enable extended hours
        )

        # Determine pricing source for response
        pricing_source = "Stream Data"
        if "Recent Quotes:" not in str(stream_quotes):
            pricing_source = "Fallback API"

        # Enhanced response with stream context
        result = "🎯 STREAM-OPTIMIZED ORDER PLACEMENT\n"
        result += "=" * 45 + "\n\n"
        result += "📊 Pricing Analysis:\n"
        result += f"  └── Symbol: {symbol}\n"
        result += f"  └── Optimal Price: ${optimal_price:.4f}\n"
        result += f"  └── Pricing Source: {pricing_source}\n"
        result += f"  └── Order Type: {order_type.upper()}\n"
        result += "  └── Execution: IOC (Fast Fill)\n\n"

        result += "📋 Order Result:\n"
        result += order_result.replace("\n", "\n  ")  # Indent the order result

        return result

    except Exception as e:
        return f"❌ Stream-optimized order error: {str(e)}"


async def clear_stock_stream_buffers() -> str:
    """
    Clear all streaming data buffers to free memory.

    Returns:
        str: Confirmation message with cleared buffer count
    """

    try:
        buffer_count = len(_settings_module._stock_data_buffers)
        total_items = sum(
            len(buffer.get_all()) for buffer in _settings_module._stock_data_buffers.values()
        )

        # Clear all buffers
        for buffer in _settings_module._stock_data_buffers.values():
            buffer.clear()

        return f"""
🧹 STOCK STREAM BUFFERS CLEARED

📊 Cleanup Summary:
  Buffers Cleared: {buffer_count}
  Items Removed: {total_items:,}
  Memory Freed: ~{(total_items * 200) / (1024 * 1024):.1f} MB

💾 Status:
  Buffers remain allocated but empty
  Streaming continues if active
  Use get_stock_stream_data() to verify clearing
        """

    except Exception as e:
        return f"Error clearing stock buffers: {str(e)}"
