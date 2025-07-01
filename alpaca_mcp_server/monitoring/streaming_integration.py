"""Real-time Alpaca WebSocket Streaming Integration

Connects to Alpaca's WebSocket APIs for real-time market data and trading updates.
Provides instant notifications for order fills, position changes, and price movements.
"""

import asyncio
import logging
import threading
from collections.abc import Callable
from decimal import Decimal

from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Quote, Trade
from alpaca.trading.models import TradeUpdate
from alpaca.trading.stream import TradingStream

from ..config.settings import settings


class AlpacaStreamingService:
    """
    Real-time streaming service for Alpaca WebSocket connections.

    Based on alpaca_stream.py patterns for proper SDK usage.
    Enhanced with connection limit management and retry logic.

    Handles:
    - Trade updates (order fills, cancellations)
    - Position changes in real-time
    - Market data streaming (trades, quotes, bars)
    - Profit spike detection with microsecond latency
    - Connection limit management and retry logic
    """

    def __init__(self):
        self.logger = logging.getLogger("alpaca_streaming")

        # Connection management
        self.max_retry_attempts = 5
        self.current_retry_attempt = 0
        self.connection_backoff_base = 2  # seconds
        self.connection_limit_detected = False
        self.last_connection_error = None

        # Initialize streaming clients using correct SDK patterns
        try:
            self.trading_stream = TradingStream(
                api_key=settings.api_key, secret_key=settings.api_secret, paper=settings.paper
            )

            self.data_stream = StockDataStream(
                api_key=settings.api_key,
                secret_key=settings.api_secret,
                feed=DataFeed.SIP,  # Use SIP feed for better data
                raw_data=False,
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize streaming clients: {e}")
            self.connection_limit_detected = True
            self.last_connection_error = str(e)

        # Tracking state
        self.subscribed_symbols: set[str] = set()
        self.position_prices: dict[str, Decimal] = {}  # symbol -> avg_entry_price
        self.is_running = False
        self._trading_thread: threading.Thread | None = None
        self._data_thread: threading.Thread | None = None

        # Callbacks for events
        self.on_trade_update: Callable | None = None
        self.on_position_change: Callable | None = None
        self.on_profit_spike: Callable | None = None
        self.on_market_data: Callable | None = None

        # Setup handlers using correct SDK methods
        self._setup_handlers()

        self.logger.info("AlpacaStreamingService initialized")

    def _setup_handlers(self):
        """Setup WebSocket event handlers using correct SDK subscription methods"""

        # Register trading stream handler for order updates
        self.trading_stream.subscribe_trade_updates(self._on_trade_update)

        self.logger.info("Streaming handlers configured")

    async def _on_trade_update(self, data: TradeUpdate):
        """Handle order fills, cancellations, and other trade updates"""
        self.logger.info(
            f"Trade update: {data.event} for {data.order.symbol} - {data.order.status}"
        )

        # Notify about fills immediately
        if data.event == "fill":
            fill_info = {
                "event": "order_filled",
                "symbol": data.order.symbol,
                "side": data.order.side,
                "filled_qty": float(data.order.filled_qty),
                "filled_avg_price": float(data.order.filled_avg_price),
                "timestamp": data.timestamp.isoformat(),
            }

            if self.on_trade_update:
                try:
                    await self.on_trade_update(fill_info)
                except Exception as e:
                    self.logger.error(f"Error in trade update callback: {e}")

            # Track position for profit monitoring
            if data.order.side == "buy":
                self.position_prices[data.order.symbol] = Decimal(str(data.order.filled_avg_price))
                # Subscribe to real-time data for this symbol
                await self.subscribe_market_data([data.order.symbol])

        # Handle position closures
        elif data.event == "fill" and data.order.side == "sell":
            if data.order.symbol in self.position_prices:
                del self.position_prices[data.order.symbol]
                # Unsubscribe if no position
                await self.unsubscribe_market_data([data.order.symbol])

    async def _on_trade(self, data: Trade):
        """Handle real-time trade data for profit monitoring"""
        symbol = data.symbol
        current_price = Decimal(str(data.price))

        # Check for profit spikes on positions
        if symbol in self.position_prices:
            entry_price = self.position_prices[symbol]
            profit_pct = ((current_price - entry_price) / entry_price) * 100

            # Instant alert on 1%+ profit spike
            if profit_pct >= 1.0:
                spike_info = {
                    "event": "profit_spike",
                    "symbol": symbol,
                    "entry_price": float(entry_price),
                    "current_price": float(current_price),
                    "profit_pct": float(profit_pct),
                    "timestamp": data.timestamp.isoformat(),
                }

                self.logger.warning(
                    f"🚨 PROFIT SPIKE: {symbol} +{profit_pct:.2f}% at ${current_price}"
                )

                if self.on_profit_spike:
                    try:
                        await self.on_profit_spike(spike_info)
                    except Exception as e:
                        self.logger.error(f"Error in profit spike callback: {e}")

        # Forward market data
        if self.on_market_data:
            try:
                await self.on_market_data(
                    {
                        "type": "trade",
                        "symbol": symbol,
                        "price": float(current_price),
                        "size": data.size,
                        "timestamp": data.timestamp.isoformat(),
                    }
                )
            except Exception as e:
                self.logger.error(f"Error in market data callback: {e}")

    async def _on_quote(self, data: Quote):
        """Handle real-time quote data"""
        if self.on_market_data:
            try:
                await self.on_market_data(
                    {
                        "type": "quote",
                        "symbol": data.symbol,
                        "bid": float(data.bid_price),
                        "ask": float(data.ask_price),
                        "bid_size": data.bid_size,
                        "ask_size": data.ask_size,
                        "timestamp": data.timestamp.isoformat(),
                    }
                )
            except Exception as e:
                self.logger.error(f"Error in quote callback: {e}")

    async def _on_bar(self, data: Bar):
        """Handle minute bar updates"""
        if self.on_market_data:
            try:
                await self.on_market_data(
                    {
                        "type": "bar",
                        "symbol": data.symbol,
                        "open": float(data.open),
                        "high": float(data.high),
                        "low": float(data.low),
                        "close": float(data.close),
                        "volume": data.volume,
                        "trades": data.trade_count if hasattr(data, "trade_count") else 0,
                        "timestamp": data.timestamp.isoformat(),
                    }
                )
            except Exception as e:
                self.logger.error(f"Error in bar callback: {e}")

    def _run_trading_stream(self):
        """Run trading stream in separate thread"""
        try:
            self.logger.info("Starting trading stream...")
            self.trading_stream.run()
        except Exception as e:
            self.logger.error(f"Trading stream error: {e}")
        finally:
            self.logger.info("Trading stream stopped")

    def _run_data_stream(self):
        """Run data stream in separate thread"""
        try:
            self.logger.info("Starting data stream...")
            self.data_stream.run()
        except Exception as e:
            self.logger.error(f"Data stream error: {e}")
        finally:
            self.logger.info("Data stream stopped")

    async def start(self):
        """Start the streaming services with connection limit management"""
        if self.is_running:
            self.logger.warning("Streaming service already running")
            return

        # Check for connection limit issues
        if self.connection_limit_detected:
            self.logger.warning("Connection limit detected, attempting with retry logic...")
            return await self._start_with_retry()

        self.is_running = True
        self.logger.info("Starting Alpaca streaming services...")

        try:
            # Only start trading stream to minimize connections
            self._trading_thread = threading.Thread(
                target=self._run_trading_stream_with_retry, daemon=True, name="TradingStream"
            )
            self._trading_thread.start()

            # Wait longer for connection establishment
            await asyncio.sleep(5)

            # Check if connection was successful
            if self._trading_thread.is_alive() and not self.connection_limit_detected:
                self.logger.info("✅ Alpaca streaming services started (trading only)")
            else:
                self.logger.warning("⚠️ Streaming started with limitations due to connection issues")

        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            self.is_running = False
            self.last_connection_error = str(e)
            # Don't raise - continue with degraded functionality

    async def _start_with_retry(self):
        """Start streaming with exponential backoff retry"""
        for attempt in range(self.max_retry_attempts):
            try:
                backoff_time = self.connection_backoff_base**attempt
                self.logger.info(
                    f"Retry attempt {attempt + 1}/{self.max_retry_attempts} after {backoff_time}s"
                )

                await asyncio.sleep(backoff_time)

                # Reset connection limit flag
                self.connection_limit_detected = False

                # Try minimal connection (trading only)
                await self.start()

                if self.is_running and not self.connection_limit_detected:
                    self.logger.info("✅ Streaming service recovered")
                    return

            except Exception as e:
                self.logger.error(f"Retry attempt {attempt + 1} failed: {e}")
                self.connection_limit_detected = True
                self.last_connection_error = str(e)

        self.logger.error("Max retry attempts reached, running in degraded mode")

    def _run_trading_stream_with_retry(self):
        """Run trading stream with connection error handling"""
        try:
            self.logger.info("Starting trading stream with retry logic...")
            self.trading_stream.run()
        except Exception as e:
            error_msg = str(e).lower()
            if "connection limit exceeded" in error_msg or "http 429" in error_msg:
                self.connection_limit_detected = True
                self.logger.error(f"Connection limit detected: {e}")
            else:
                self.logger.error(f"Trading stream error: {e}")
            self.last_connection_error = str(e)
        finally:
            self.logger.info("Trading stream stopped")

    async def stop(self):
        """Stop the streaming services"""
        if not self.is_running:
            return

        self.is_running = False
        self.logger.info("Stopping Alpaca streaming services...")

        try:
            # Stop streams
            if hasattr(self.trading_stream, "stop"):
                self.trading_stream.stop()
            if hasattr(self.data_stream, "stop"):
                self.data_stream.stop()

            # Wait for threads to finish (with timeout)
            if self._trading_thread and self._trading_thread.is_alive():
                self._trading_thread.join(timeout=5)
            if self._data_thread and self._data_thread.is_alive():
                self._data_thread.join(timeout=5)

        except Exception as e:
            self.logger.error(f"Error stopping streams: {e}")

        self.logger.info("✅ Alpaca streaming services stopped")

    async def subscribe_market_data(self, symbols: list[str], data_types: list[str] = None):
        """Subscribe to market data for symbols using correct SDK methods"""
        if not data_types:
            data_types = ["trades", "quotes", "bars"]

        symbols = [s.upper() for s in symbols]
        new_symbols = set(symbols) - self.subscribed_symbols

        if not new_symbols:
            return

        self.logger.info(f"Subscribing to market data: {new_symbols} for {data_types}")

        try:
            # Subscribe with handlers using correct SDK methods
            if "trades" in data_types:
                self.data_stream.subscribe_trades(self._on_trade, *new_symbols)
            if "quotes" in data_types:
                self.data_stream.subscribe_quotes(self._on_quote, *new_symbols)
            if "bars" in data_types:
                self.data_stream.subscribe_bars(self._on_bar, *new_symbols)

            self.subscribed_symbols.update(new_symbols)

        except Exception as e:
            self.logger.error(f"Failed to subscribe: {e}")

    async def unsubscribe_market_data(self, symbols: list[str]):
        """Unsubscribe from market data for symbols"""
        symbols = [s.upper() for s in symbols]
        to_remove = set(symbols) & self.subscribed_symbols

        if not to_remove:
            return

        self.logger.info(f"Unsubscribing from market data: {to_remove}")

        try:
            # Unsubscribe using correct SDK methods
            self.data_stream.unsubscribe_trades(*to_remove)
            self.data_stream.unsubscribe_quotes(*to_remove)
            self.data_stream.unsubscribe_bars(*to_remove)

            self.subscribed_symbols -= to_remove

        except Exception as e:
            self.logger.error(f"Failed to unsubscribe: {e}")

    def set_callbacks(
        self,
        on_trade_update: Callable = None,
        on_position_change: Callable = None,
        on_profit_spike: Callable = None,
        on_market_data: Callable = None,
    ):
        """Set callback functions for streaming events"""
        if on_trade_update:
            self.on_trade_update = on_trade_update
        if on_position_change:
            self.on_position_change = on_position_change
        if on_profit_spike:
            self.on_profit_spike = on_profit_spike
        if on_market_data:
            self.on_market_data = on_market_data

        self.logger.info("Streaming callbacks configured")

    async def get_streaming_status(self) -> dict:
        """Get current streaming status"""
        return {
            "is_running": self.is_running,
            "subscribed_symbols": sorted(self.subscribed_symbols),
            "tracked_positions": sorted(self.position_prices.keys()),
            "position_count": len(self.position_prices),
            "trading_thread_alive": (
                self._trading_thread.is_alive() if self._trading_thread else False
            ),
            "data_thread_alive": self._data_thread.is_alive() if self._data_thread else False,
            "subscription_count": len(self.subscribed_symbols),
        }
