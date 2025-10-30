#!/usr/bin/env python3
"""
Alpaca Market Data Stream Script

This script connects to Alpaca's WebSocket streaming data service and subscribes to
various data types for specified stock symbols. It includes a robust reconnection
system to handle service disruptions.

Usage:
    python alpaca_stream.py --data-type trades --symbols AAPL MSFT TSLA
    python alpaca_stream.py --data-type quotes --symbols AAPL --feed sip
    python alpaca_stream.py --data-type bars --symbols SPY QQQ --feed iex
    python alpaca_stream.py --data-type all --symbols AAPL --feed sip
"""

import argparse
import asyncio
import logging
import os
import signal
import sys
import threading
import time
from typing import Any

from alpaca.data.enums import DataFeed

# Import alpaca-py modules
from alpaca.data.live import StockDataStream

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Set up signal handler for graceful shutdown
shutdown_event = asyncio.Event()

# Flag to prevent multiple shutdown attempts
is_shutting_down = False


def signal_handler(sig: int, frame: Any) -> None:
    """Handle SIGINT (Ctrl+C) to gracefully shut down"""
    global is_shutting_down

    # Prevent multiple shutdown attempts
    if is_shutting_down:
        logger.info("Already shutting down, please wait...")
        return

    is_shutting_down = True
    logger.info("Shutdown signal received, closing connections...")
    shutdown_event.set()

    # Force exit after 5 seconds if graceful shutdown fails
    def force_exit() -> None:
        logger.warning("Forcing exit due to timeout in graceful shutdown")
        os._exit(1)

    # Schedule force exit
    signal.signal(signal.SIGALRM, lambda sig, frame: force_exit())
    signal.alarm(5)


# Initialize signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def load_symbols_from_file(file_path: str) -> list[str]:
    """Load stock symbols from a file (one symbol per line)

    Args:
        file_path: Path to the symbols file

    Returns:
        List of stock symbols
    """
    try:
        with open(file_path) as f:
            # Read lines, strip whitespace, filter empty lines
            symbols = [line.strip() for line in f.readlines()]
            symbols = [s for s in symbols if s]  # Remove empty lines
            logger.info(f"Loaded {len(symbols)} symbols from {file_path}")
            return symbols
    except Exception as e:
        logger.error(f"Error loading symbols from {file_path}: {e}")
        return []


def get_unique_symbols(cmd_symbols: list[str], file_symbols: list[str]) -> list[str]:
    """Combine symbols from command line and file, removing duplicates

    Args:
        cmd_symbols: Symbols from command line
        file_symbols: Symbols from file

    Returns:
        List of unique symbols
    """
    # Convert to uppercase for consistency
    cmd_symbols = [s.upper() for s in cmd_symbols]
    file_symbols = [s.upper() for s in file_symbols]

    # Combine and remove duplicates while preserving order
    unique_symbols = []

    # Add file symbols first
    for symbol in file_symbols:
        if symbol not in unique_symbols:
            unique_symbols.append(symbol)

    # Add command line symbols
    for symbol in cmd_symbols:
        if symbol not in unique_symbols:
            unique_symbols.append(symbol)

    return unique_symbols


class AlpacaStreamClient:
    """
    Client for Alpaca's WebSocket streaming data service with automatic reconnection.
    """

    _subscriptions: dict[str, Any]

    def __init__(self, api_key: str, api_secret: str, feed: str = "sip", raw_data: bool = False):
        """Initialize WebSocket client

        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
            feed: Data feed ('iex' or 'sip')
            raw_data: Whether to return raw data or parsed objects
        """
        self.api_key = api_key
        self.api_secret = api_secret

        # Validate feed type
        if feed.lower() not in ("iex", "sip"):
            raise ValueError("Feed must be either 'iex' or 'sip'")

        # Create the data feed enum
        self.feed = DataFeed.IEX if feed.lower() == "iex" else DataFeed.SIP
        self.raw_data = raw_data

        # Initialize event counters
        self.counters = {
            "trades": 0,
            "quotes": 0,
            "bars": 0,
            "updated_bars": 0,
            "daily_bars": 0,
            "statuses": 0,
            "corrections": 0,
            "cancels": 0,
        }

        # Subscription tracking
        self._subscriptions = {
            "trades": set(),
            "quotes": set(),
            "bars": set(),
            "updated_bars": set(),
            "daily_bars": set(),
            "statuses": set(),
            "corrections": False,
            "cancels": False,
        }

        # WebSocket connection parameters
        self._websocket_params = {"ping_interval": 10, "ping_timeout": 180, "max_queue": 10000}

        # Reconnection settings
        self._last_message_time = time.time()
        self._max_silence_seconds = 30  # Maximum time without messages before reconnecting
        self._reconnect_attempt = 1
        self._max_reconnect_attempts = 5
        self._reconnect_loop_running = False
        self._stream_running = False

        # Create the stream
        self._create_stream()

        logger.info(f"Initialized AlpacaStreamClient with {feed.upper()} feed")

    def _create_stream(self) -> None:
        """Create a new stream instance"""
        self.stream = StockDataStream(
            api_key=self.api_key,
            secret_key=self.api_secret,
            feed=self.feed,
            raw_data=self.raw_data,
            websocket_params=self._websocket_params,
        )

    def _update_last_message_time(self) -> None:
        """Update the timestamp of the last received message"""
        self._last_message_time = time.time()

    async def print_trade(self, trade):
        """Handle and print trade data"""
        self._update_last_message_time()
        self.counters["trades"] += 1

        if self.raw_data:
            logger.info(f"Trade: {trade}")
        else:
            logger.info(
                f"Trade: {trade.symbol} @ ${trade.price:.4f} - Size: {trade.size} - "
                f"Exchange: {trade.exchange} - Timestamp: {trade.timestamp}"
            )

    async def print_quote(self, quote):
        """Handle and print quote data"""
        self._update_last_message_time()
        self.counters["quotes"] += 1

        if self.raw_data:
            logger.info(f"Quote: {quote}")
        else:
            logger.info(
                f"Quote: {quote.symbol} - Bid: ${quote.bid_price:.4f} x {quote.bid_size} - "
                f"Ask: ${quote.ask_price:.4f} x {quote.ask_size} - "
                f"Timestamp: {quote.timestamp}"
            )

    async def print_bar(self, bar):
        """Handle and print bar data"""
        self._update_last_message_time()
        self.counters["bars"] += 1

        if self.raw_data:
            logger.info(f"Bar: {bar}")
        else:
            logger.info(
                f"Bar: {bar.symbol} - O: ${bar.open:.4f} H: ${bar.high:.4f} L: ${bar.low:.4f} C: ${bar.close:.4f} - "
                f"Volume: {bar.volume} - Timestamp: {bar.timestamp}"
            )

    async def print_updated_bar(self, bar):
        """Handle and print updated bar data"""
        self._update_last_message_time()
        self.counters["updated_bars"] += 1

        if self.raw_data:
            logger.info(f"Updated Bar: {bar}")
        else:
            logger.info(
                f"Updated Bar: {bar.symbol} - O: ${bar.open:.4f} H: ${bar.high:.4f} L: ${bar.low:.4f} C: ${bar.close:.4f} - "
                f"Volume: {bar.volume} - Timestamp: {bar.timestamp}"
            )

    async def print_daily_bar(self, bar):
        """Handle and print daily bar data"""
        self._update_last_message_time()
        self.counters["daily_bars"] += 1

        if self.raw_data:
            logger.info(f"Daily Bar: {bar}")
        else:
            logger.info(
                f"Daily Bar: {bar.symbol} - O: ${bar.open:.4f} H: ${bar.high:.4f} L: ${bar.low:.4f} C: ${bar.close:.4f} - "
                f"Volume: {bar.volume} - Timestamp: {bar.timestamp}"
            )

    async def print_status(self, status):
        """Handle and print trading status data"""
        self._update_last_message_time()
        self.counters["statuses"] += 1

        if self.raw_data:
            logger.info(f"Status: {status}")
        else:
            logger.info(
                f"Status: {status.symbol} - Status: {status.status} - "
                f"Reason: {status.reason} - Timestamp: {status.timestamp}"
            )

    async def print_correction(self, correction):
        """Handle and print trade correction data"""
        self._update_last_message_time()
        self.counters["corrections"] += 1

        if self.raw_data:
            logger.info(f"Correction: {correction}")
        else:
            logger.info(
                f"Correction: {correction.symbol} - Trade ID: {correction.id} - "
                f"Original Price: ${correction.original_price:.4f} - "
                f"Corrected Price: ${correction.price:.4f} - "
                f"Timestamp: {correction.timestamp}"
            )

    async def print_cancel(self, cancel):
        """Handle and print trade cancel data"""
        self._update_last_message_time()
        self.counters["cancels"] += 1

        if self.raw_data:
            logger.info(f"Cancel: {cancel}")
        else:
            logger.info(
                f"Cancel: {cancel.symbol} - Trade ID: {cancel.id} - "
                f"Price: ${cancel.price:.4f} - Size: {cancel.size} - "
                f"Timestamp: {cancel.timestamp}"
            )

    def subscribe_to_trades(self, symbols: list[str]) -> None:
        """Subscribe to trades for specified symbols"""
        self.stream.subscribe_trades(self.print_trade, *symbols)
        self._subscriptions["trades"].update(symbols)
        logger.info(f"Subscribed to trades for: {', '.join(symbols)}")

    def subscribe_to_quotes(self, symbols: list[str]) -> None:
        """Subscribe to quotes for specified symbols"""
        self.stream.subscribe_quotes(self.print_quote, *symbols)
        self._subscriptions["quotes"].update(symbols)
        logger.info(f"Subscribed to quotes for: {', '.join(symbols)}")

    def subscribe_to_bars(self, symbols: list[str]) -> None:
        """Subscribe to minute bars for specified symbols"""
        self.stream.subscribe_bars(self.print_bar, *symbols)
        self._subscriptions["bars"].update(symbols)
        logger.info(f"Subscribed to minute bars for: {', '.join(symbols)}")

    def subscribe_to_updated_bars(self, symbols: list[str]) -> None:
        """Subscribe to updated bars for specified symbols"""
        self.stream.subscribe_updated_bars(self.print_updated_bar, *symbols)
        self._subscriptions["updated_bars"].update(symbols)
        logger.info(f"Subscribed to updated bars for: {', '.join(symbols)}")

    def subscribe_to_daily_bars(self, symbols: list[str]) -> None:
        """Subscribe to daily bars for specified symbols"""
        self.stream.subscribe_daily_bars(self.print_daily_bar, *symbols)
        self._subscriptions["daily_bars"].update(symbols)
        logger.info(f"Subscribed to daily bars for: {', '.join(symbols)}")

    def subscribe_to_statuses(self, symbols: list[str]) -> None:
        """Subscribe to trading statuses for specified symbols"""
        self.stream.subscribe_trading_statuses(self.print_status, *symbols)
        self._subscriptions["statuses"].update(symbols)
        logger.info(f"Subscribed to trading statuses for: {', '.join(symbols)}")

    def register_for_corrections(self) -> None:
        """Register for trade corrections"""
        self.stream.register_trade_corrections(self.print_correction)
        self._subscriptions["corrections"] = True
        logger.info("Registered for trade corrections")

    def register_for_cancels(self) -> None:
        """Register for trade cancels"""
        self.stream.register_trade_cancels(self.print_cancel)
        self._subscriptions["cancels"] = True
        logger.info("Registered for trade cancels")

    def _reapply_subscriptions(self) -> None:
        """Reapply all subscriptions after reconnect"""
        # Apply trades subscription
        if self._subscriptions["trades"]:
            symbols = list(self._subscriptions["trades"])
            self.stream.subscribe_trades(self.print_trade, *symbols)
            logger.info(f"Resubscribed to trades for: {', '.join(symbols)}")

            # Reapply corrections and cancels if previously subscribed
            if self._subscriptions["corrections"]:
                self.stream.register_trade_corrections(self.print_correction)
                logger.info("Resubscribed to trade corrections")

            if self._subscriptions["cancels"]:
                self.stream.register_trade_cancels(self.print_cancel)
                logger.info("Resubscribed to trade cancels")

        # Apply quotes subscription
        if self._subscriptions["quotes"]:
            symbols = list(self._subscriptions["quotes"])
            self.stream.subscribe_quotes(self.print_quote, *symbols)
            logger.info(f"Resubscribed to quotes for: {', '.join(symbols)}")

        # Apply bars subscription
        if self._subscriptions["bars"]:
            symbols = list(self._subscriptions["bars"])
            self.stream.subscribe_bars(self.print_bar, *symbols)
            logger.info(f"Resubscribed to minute bars for: {', '.join(symbols)}")

        # Apply updated bars subscription
        if self._subscriptions["updated_bars"]:
            symbols = list(self._subscriptions["updated_bars"])
            self.stream.subscribe_updated_bars(self.print_updated_bar, *symbols)
            logger.info(f"Resubscribed to updated bars for: {', '.join(symbols)}")

        # Apply daily bars subscription
        if self._subscriptions["daily_bars"]:
            symbols = list(self._subscriptions["daily_bars"])
            self.stream.subscribe_daily_bars(self.print_daily_bar, *symbols)
            logger.info(f"Resubscribed to daily bars for: {', '.join(symbols)}")

        # Apply statuses subscription
        if self._subscriptions["statuses"]:
            symbols = list(self._subscriptions["statuses"])
            self.stream.subscribe_trading_statuses(self.print_status, *symbols)
            logger.info(f"Resubscribed to trading statuses for: {', '.join(symbols)}")

    def _start_reconnect_monitor(self) -> None:
        """Monitor connection health and reconnect if needed"""
        if self._reconnect_loop_running:
            return

        self._reconnect_loop_running = True
        self._last_message_time = time.time()

        def monitor_loop() -> None:
            """Background thread that monitors connection health"""
            while self._reconnect_loop_running and not shutdown_event.is_set():
                current_time = time.time()
                silence_duration = current_time - self._last_message_time

                # If the connection is active and we haven't received messages for too long
                if self._stream_running and silence_duration > self._max_silence_seconds:
                    logger.warning(
                        f"No messages received for {silence_duration:.1f} seconds, reconnecting..."
                    )

                    # Stop existing connection
                    try:
                        self.stream.stop()
                        logger.info("Stream stopped due to inactivity")
                    except Exception as e:
                        logger.error(f"Error stopping stream during reconnect: {e}")

                    # Exponential backoff
                    wait_time = min(30, 2**self._reconnect_attempt)
                    self._reconnect_attempt += 1

                    if self._reconnect_attempt > self._max_reconnect_attempts:
                        logger.error("Maximum reconnection attempts reached")
                        self._reconnect_loop_running = False
                        break

                    logger.info(
                        f"Waiting {wait_time}s before reconnection attempt {self._reconnect_attempt}"
                    )
                    time.sleep(wait_time)

                    # Create new stream instance
                    self._create_stream()
                    logger.info("Created new stream instance")

                    # Re-subscribe to all data types
                    self._reapply_subscriptions()

                    # Reset timestamp
                    self._last_message_time = time.time()

                    # Restart stream
                    self._stream_running = False
                    stream_thread = threading.Thread(target=self._run_stream, daemon=True)
                    stream_thread.start()
                    logger.info("Reconnected and restarted stream")

                # Check every 5 seconds
                time.sleep(5)

        # Start monitor in a thread
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Started connection health monitor")

    def _run_stream(self) -> None:
        """Run the stream and handle termination"""
        try:
            self._stream_running = True
            self.stream.run()
        except Exception as e:
            logger.error(f"Stream error: {e}")
        finally:
            self._stream_running = False
            logger.info("Stream thread exited")

    def start(self) -> None:
        """Start the WebSocket connection with reconnection monitoring"""
        try:
            logger.info("Starting WebSocket stream...")

            # Start the reconnection monitor
            self._start_reconnect_monitor()

            # Start the stream
            self._run_stream()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt detected")
        except Exception as e:
            logger.error(f"Error in stream: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the WebSocket connection and cleanup"""
        logger.info("Stopping WebSocket stream...")
        try:
            # Stop reconnection monitor
            self._reconnect_loop_running = False

            # Stop the stream
            if self._stream_running:
                self.stream.stop()
                self._stream_running = False

            logger.info("Stream stopped")

            # Print final counters
            logger.info("Event counters:")
            for data_type, count in self.counters.items():
                if count > 0:
                    logger.info(f"  {data_type}: {count}")
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")

        # Ensure the script exits
        if is_shutting_down:
            logger.info("Shutdown complete")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Alpaca Market Data Stream Client")

    parser.add_argument(
        "--data-type",
        choices=["trades", "quotes", "bars", "updated-bars", "daily-bars", "statuses", "all"],
        required=True,
        help="Type of data to stream",
    )

    parser.add_argument(
        "--symbols", nargs="+", default=[], help="Stock symbols to subscribe to (e.g., AAPL MSFT)"
    )

    parser.add_argument(
        "--symbols-file", type=str, help="Path to a file containing stock symbols (one per line)"
    )

    parser.add_argument(
        "--feed",
        choices=["iex", "sip"],
        default="sip",
        help="Data feed to use (default: sip, both require subscription but sip has more complete data)",
    )

    parser.add_argument(
        "--raw", action="store_true", help="Output raw data instead of formatted data"
    )

    parser.add_argument(
        "--duration", type=int, default=60, help="Duration to run in seconds (default: 60)"
    )

    parser.add_argument(
        "--silent-timeout",
        type=int,
        default=30,
        help="Seconds without messages before reconnecting (default: 30)",
    )

    return parser.parse_args()


async def run_with_timeout(client, data_type, symbols, duration):
    """Run the client with a timeout"""
    # Subscribe to requested data
    if data_type == "trades" or data_type == "all":
        client.subscribe_to_trades(symbols)
        client.register_for_corrections()
        client.register_for_cancels()

    if data_type == "quotes" or data_type == "all":
        client.subscribe_to_quotes(symbols)

    if data_type == "bars" or data_type == "all":
        client.subscribe_to_bars(symbols)

    if data_type == "updated-bars" or data_type == "all":
        client.subscribe_to_updated_bars(symbols)

    if data_type == "daily-bars" or data_type == "all":
        client.subscribe_to_daily_bars(symbols)

    if data_type == "statuses" or data_type == "all":
        client.subscribe_to_statuses(symbols)

    # Run the stream in a separate thread
    stream_thread = threading.Thread(target=client.start)
    stream_thread.daemon = True  # Set as daemon so it exits when main thread exits
    stream_thread.start()

    # Wait for either timeout or shutdown signal
    try:
        # Use a loop with small sleeps to check for shutdown event
        # This allows for more responsive SIGINT handling
        for _ in range(duration):
            if shutdown_event.is_set():
                break
            await asyncio.sleep(1)

        if not shutdown_event.is_set():
            logger.info(f"Timeout of {duration} seconds reached")
    finally:
        # Stop the stream
        client.stop()

        # Wait a short time for the thread to exit
        stream_thread.join(timeout=2)

        # If thread is still alive, it's stuck
        if stream_thread.is_alive():
            logger.warning("Stream thread did not exit cleanly, forcing exit")
            # We'll let the force_exit function handle this


def main() -> None:
    """Main entry point"""
    args = parse_arguments()

    # Get API keys from environment variables
    api_key = os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("APCA_API_SECRET_KEY")

    if not api_key or not api_secret:
        logger.error(
            "API key and secret must be set as environment variables: "
            "APCA_API_KEY_ID and APCA_API_SECRET_KEY"
        )
        sys.exit(1)

    # Get symbols from command line and/or file
    cmd_symbols = args.symbols
    file_symbols = []

    if args.symbols_file:
        file_symbols = load_symbols_from_file(args.symbols_file)

    # Combine symbols from both sources, removing duplicates
    symbols = get_unique_symbols(cmd_symbols, file_symbols)

    if not symbols:
        logger.error("No symbols specified. Use --symbols or --symbols-file to specify symbols.")
        sys.exit(1)

    # Create client
    client = AlpacaStreamClient(
        api_key=api_key, api_secret=api_secret, feed=args.feed, raw_data=args.raw
    )

    # Set reconnection parameters
    client._max_silence_seconds = args.silent_timeout

    logger.info(
        f"Starting Alpaca stream for {len(symbols)} symbols "
        f"with {args.feed.upper()} feed for {args.duration} seconds "
        f"(reconnect after {args.silent_timeout}s silence)"
    )

    # Run the client with asyncio
    asyncio.run(
        run_with_timeout(
            client=client, data_type=args.data_type, symbols=symbols, duration=args.duration
        )
    )

    logger.info("Script completed")


if __name__ == "__main__":
    main()
