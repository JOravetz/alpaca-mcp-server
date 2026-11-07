"""Configuration settings for Alpaca MCP Server."""

import os
import subprocess
import threading
import time
from collections import defaultdict, deque
from datetime import UTC
from typing import Any

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.live.stock import StockDataStream

# Alpaca imports
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

# Load environment variables (non-credential settings; .env must not hold keys)
load_dotenv()

# ============================================================================
# Alpaca credentials come from ~/.secrets, the operator's single source of truth
# ============================================================================
# The keys rotate. A copy in this repo's .env (or in an MCP config "env" block)
# goes stale silently and 401s every call while the operator's real keys work —
# hit 2026-05-31, 2026-10-10 and 2026-11-07. So the file wins over whatever the
# launching process exported and over .env.
#
# ~/.secrets is a bash script, not a dotenv file: it defines _alpaca_paper /
# _alpaca_live and picks one by ALPACA_MODE (default paper), so it is sourced
# by bash in an otherwise empty environment and only the Alpaca variables are
# read back. ALPACA_MODE inherited from the launcher (`alpaca-live`) still
# selects live. ALPACA_SECRETS_FILE overrides the path; set it to "" to
# disable the file and use the inherited environment as-is.

SECRETS_FILE_DEFAULT = os.path.expanduser("~/.secrets")
_SECRET_VARS = ("APCA_API_KEY_ID", "APCA_API_SECRET_KEY", "APCA_API_BASE_URL", "ALPACA_MODE")
_SOURCE_SECRETS = (
    '. "$1" >/dev/null 2>&1; shift; '
    'for v in "$@"; do printf "%s\\0%s\\0" "$v" "$(printenv "$v")"; done'
)


def load_alpaca_secrets(path: str | None = None, mode: str | None = None) -> dict[str, str]:
    """Return the Alpaca variables the secrets file defines ({} if unavailable).

    Never raises. Adds PAPER ("true"/"false") derived from the file's base URL so
    the trading client always targets the endpoint the keys belong to.
    """
    if path is None:
        path = os.environ.get("ALPACA_SECRETS_FILE", SECRETS_FILE_DEFAULT)
    if not path or not os.path.isfile(path):
        return {}
    env = {"PATH": "/usr/bin:/bin", "HOME": os.path.expanduser("~")}
    if mode:
        env["ALPACA_MODE"] = mode
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv; the path is an argument, never code
            ["/bin/bash", "-c", _SOURCE_SECRETS, "bash", path, *_SECRET_VARS],
            env=env,
            capture_output=True,
            check=True,
        ).stdout.decode()
    except (OSError, subprocess.CalledProcessError):
        return {}
    parts = out.split("\0")
    found = {k: v for k, v in zip(parts[0::2], parts[1::2], strict=False) if v}
    if not (found.get("APCA_API_KEY_ID") and found.get("APCA_API_SECRET_KEY")):
        return {}
    base_url = found.get("APCA_API_BASE_URL")
    if base_url:
        found["PAPER"] = "true" if "paper-api" in base_url else "false"
    return found


def apply_alpaca_secrets() -> dict[str, str]:
    """Overwrite os.environ's Alpaca variables from the secrets file; return them."""
    found = load_alpaca_secrets(mode=os.environ.get("ALPACA_MODE"))
    os.environ.update(found)
    return found


_secrets_applied = apply_alpaca_secrets()


class Settings:
    """Configuration settings for Alpaca MCP Server."""

    def __init__(self, require_credentials: bool = True) -> None:
        # API credentials - support both naming conventions
        self.api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")

        # Paper trading flag
        self.paper = os.getenv("PAPER", "true").lower() in ["true", "1", "yes"]
        self.paper_trading = self.paper  # Alias for compatibility

        # Optional URL overrides
        self.trade_api_url = os.getenv("TRADE_API_URL")
        self.trade_api_wss = os.getenv("TRADE_API_WSS")
        self.data_api_url = os.getenv("DATA_API_URL")
        self.stream_data_wss = os.getenv("STREAM_DATA_WSS")

        # Server configuration
        self.server_name = "alpaca-trading"
        self.version = "2.0.0"

        # Track if credentials are available
        self.credentials_available = bool(self.api_key and self.api_secret)

        # Validate required credentials (can be disabled for testing/CI)
        # Check CI_MODE or TESTING environment variables to allow running without credentials
        ci_mode = os.getenv("CI", "").lower() in ["true", "1", "yes"]
        testing_mode = os.getenv("TESTING", "").lower() in ["true", "1", "yes"]

        if (
            require_credentials
            and not self.credentials_available
            and not ci_mode
            and not testing_mode
        ):
            raise ValueError("Alpaca API credentials not found in environment variables.")


# Global settings instance
settings = Settings()

# ============================================================================
# Client Factory Functions (Singleton Pattern)
# ============================================================================

_trading_client: TradingClient | None = None
_stock_historical_client: StockHistoricalDataClient | None = None
_stock_data_stream_client: StockDataStream | None = None
_option_historical_client: OptionHistoricalDataClient | None = None


def get_trading_client() -> TradingClient:
    """Get or create trading client instance."""
    global _trading_client
    if _trading_client is None:
        _trading_client = TradingClient(
            settings.api_key,
            settings.api_secret,
            paper=settings.paper,
            url_override=settings.trade_api_url,
        )
    return _trading_client


def get_stock_historical_client() -> StockHistoricalDataClient:
    """Get or create stock historical data client instance."""
    global _stock_historical_client
    if _stock_historical_client is None:
        _stock_historical_client = StockHistoricalDataClient(
            settings.api_key, settings.api_secret, url_override=settings.data_api_url
        )
    return _stock_historical_client


def get_stock_stream_client() -> StockDataStream:
    """Get or create stock data stream client instance."""
    global _stock_data_stream_client
    if _stock_data_stream_client is None:
        _stock_data_stream_client = StockDataStream(
            api_key=settings.api_key or "",
            secret_key=settings.api_secret or "",
            url_override=settings.stream_data_wss,
        )
    return _stock_data_stream_client


def get_option_historical_client() -> OptionHistoricalDataClient:
    """Get or create option historical data client instance."""
    global _option_historical_client
    if _option_historical_client is None:
        if not settings.api_key or not settings.api_secret:
            raise ValueError("API credentials are required for option data client")
        _option_historical_client = OptionHistoricalDataClient(
            api_key=settings.api_key, secret_key=settings.api_secret
        )
    return _option_historical_client


# ============================================================================
# Global Stock Streaming State (Alpaca allows only ONE stream connection)
# ============================================================================

_global_stock_stream: Any | None = None
_stock_stream_thread: Any | None = None
_stock_stream_active: bool = False
_stock_stream_subscriptions: dict[str, set[str]] = {
    "trades": set(),
    "quotes": set(),
    "bars": set(),
    "updated_bars": set(),
    "daily_bars": set(),
    "statuses": set(),
}

# Configurable stock data buffers - no artificial limits for active stocks
_stock_data_buffers: dict[str, Any] = {}
_stock_stream_stats: defaultdict[str, int] = defaultdict(int)
_stock_stream_start_time: float | None = None
_stock_stream_end_time: float | None = None
_stock_stream_config: dict[str, Any] = {
    "feed": "sip",
    "buffer_size": None,  # Unlimited by default
    "duration_seconds": None,  # No time limit by default
}

# ============================================================================
# Stock Streaming Helper Classes and Functions
# ============================================================================


class ConfigurableStockDataBuffer:
    """Thread-safe buffer with configurable size limits for stock market data"""

    def __init__(self, max_size: int | None = None) -> None:
        """
        Initialize buffer with optional size limit.

        Args:
            max_size: Maximum number of items to store. None = unlimited.
                     For active stocks, consider 10000+ or unlimited.
        """
        self.data: deque[Any]
        if max_size is None:
            self.data = deque()  # Unlimited
        else:
            self.data = deque(maxlen=max_size)  # Limited

        self.lock = threading.Lock()
        self.last_update = time.time()
        self.max_size = max_size
        self.total_items_added = 0  # Track total even if some are dropped

    def add(self, item: Any) -> None:
        with self.lock:
            self.data.append(item)
            self.last_update = time.time()
            self.total_items_added += 1

    def get_recent(self, seconds: int = 60) -> list[Any]:
        with self.lock:
            cutoff = time.time() - seconds
            result = []
            for item in self.data:
                timestamp = item.get("timestamp", 0)
                # Handle both string and numeric timestamps
                if isinstance(timestamp, str):
                    try:
                        # Try parsing ISO format with proper timezone handling
                        import re
                        from datetime import datetime

                        # Parse timestamp correctly based on timezone info
                        if timestamp.endswith("Z"):
                            # UTC timestamp with Z suffix
                            timestamp_clean = timestamp[:-1]
                            dt = datetime.fromisoformat(timestamp_clean).replace(tzinfo=UTC)
                        elif re.search(r"[+-]\d{2}:\d{2}$", timestamp):
                            # Timezone-aware timestamp
                            dt = datetime.fromisoformat(timestamp)
                        else:
                            # No timezone info, assume local time
                            dt = datetime.fromisoformat(timestamp)

                        # Convert to UTC timestamp
                        timestamp = dt.timestamp()
                    except (ValueError, TypeError):
                        try:
                            # Fallback to direct float conversion
                            timestamp = float(timestamp)
                        except (ValueError, TypeError):
                            continue  # Skip invalid timestamps
                elif isinstance(timestamp, int | float):
                    # Already a numeric timestamp
                    pass
                else:
                    continue  # Skip invalid types

                if timestamp > cutoff:
                    result.append(item)
            return result

    def get_all(self) -> list[Any]:
        with self.lock:
            return list(self.data)

    def get_stats(self) -> dict[str, Any]:
        with self.lock:
            return {
                "current_size": len(self.data),
                "max_size": self.max_size,
                "total_added": self.total_items_added,
                "last_update": self.last_update,
                "is_unlimited": self.max_size is None,
            }

    def clear(self) -> None:
        with self.lock:
            self.data.clear()
            self.total_items_added = 0


def get_or_create_stock_buffer(
    symbol: str, data_type: str, buffer_size: int | None = None
) -> ConfigurableStockDataBuffer:
    """Get or create a buffer for a stock symbol/data_type combination"""
    buffer_key = f"{symbol}_{data_type}"
    if buffer_key not in _stock_data_buffers:
        effective_size = (
            buffer_size if buffer_size is not None else _stock_stream_config.get("buffer_size")
        )
        # Ensure effective_size is None or int
        if effective_size is not None and not isinstance(effective_size, int):
            effective_size = int(effective_size) if str(effective_size).isdigit() else None
        _stock_data_buffers[buffer_key] = ConfigurableStockDataBuffer(effective_size)

    buffer = _stock_data_buffers[buffer_key]
    if not isinstance(buffer, ConfigurableStockDataBuffer):
        # This should never happen but let's be safe
        buffer = ConfigurableStockDataBuffer(buffer_size)
        _stock_data_buffers[buffer_key] = buffer
    return buffer


def check_stock_stream_duration_limit() -> bool:
    """Check if stock stream should stop due to duration limit"""
    if _stock_stream_config["duration_seconds"] and _stock_stream_start_time:
        elapsed = time.time() - _stock_stream_start_time
        if elapsed >= _stock_stream_config["duration_seconds"]:
            return True
    return False


# Global handler functions for stock streaming
async def handle_stock_trade(trade: Any) -> None:
    """Global handler for stock trade data"""
    try:
        if check_stock_stream_duration_limit():
            return

        trade_data = {
            "type": "trade",
            "symbol": trade.symbol,
            "price": float(trade.price),
            "size": trade.size,
            "exchange": trade.exchange,
            "timestamp": time.time(),
            "datetime": trade.timestamp.isoformat(),
            "conditions": getattr(trade, "conditions", []),
            "tape": getattr(trade, "tape", None),
        }

        buffer = get_or_create_stock_buffer(
            trade.symbol, "trades", _stock_stream_config.get("buffer_size")
        )
        buffer.add(trade_data)
        _stock_stream_stats["trades"] += 1

    except Exception as e:
        print(f"Error handling trade: {e}")


async def handle_stock_quote(quote: Any) -> None:
    """Global handler for stock quote data"""
    try:
        if check_stock_stream_duration_limit():
            return

        quote_data = {
            "type": "quote",
            "symbol": quote.symbol,
            "bid_price": float(quote.bid_price),
            "ask_price": float(quote.ask_price),
            "bid_size": quote.bid_size,
            "ask_size": quote.ask_size,
            "spread": float(quote.ask_price - quote.bid_price),
            "timestamp": time.time(),
            "datetime": quote.timestamp.isoformat(),
            "bid_exchange": getattr(quote, "bid_exchange", None),
            "ask_exchange": getattr(quote, "ask_exchange", None),
        }

        buffer = get_or_create_stock_buffer(
            quote.symbol, "quotes", _stock_stream_config.get("buffer_size")
        )
        buffer.add(quote_data)
        _stock_stream_stats["quotes"] += 1

    except Exception as e:
        print(f"Error handling quote: {e}")


async def handle_stock_bar(bar: Any) -> None:
    """Global handler for stock bar data"""
    try:
        if check_stock_stream_duration_limit():
            return

        bar_data = {
            "type": "bar",
            "symbol": bar.symbol,
            "open": float(bar.open),
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close),
            "volume": bar.volume,
            "trade_count": getattr(bar, "trade_count", None),
            "vwap": float(getattr(bar, "vwap", 0)),
            "timestamp": time.time(),
            "datetime": bar.timestamp.isoformat(),
        }

        buffer = get_or_create_stock_buffer(
            bar.symbol, "bars", _stock_stream_config.get("buffer_size")
        )
        buffer.add(bar_data)
        _stock_stream_stats["bars"] += 1

    except Exception as e:
        print(f"Error handling bar: {e}")
