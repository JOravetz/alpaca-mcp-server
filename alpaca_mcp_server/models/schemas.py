"""Trading data models and schemas for Alpaca MCP Server."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# ============================================================================
# Trading Data Models
# ============================================================================


@dataclass
class TradingPosition:
    """Represents a trading position."""

    symbol: str
    quantity: float
    side: str
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    current_price: float
    entry_price: float


@dataclass
class OrderDetails:
    """Represents order information."""

    symbol: str
    quantity: float
    side: str
    order_type: str
    time_in_force: str
    status: str
    filled_qty: float = 0
    limit_price: float | None = None
    stop_price: float | None = None


@dataclass
class MarketData:
    """Represents market data for a symbol."""

    symbol: str
    price: float
    timestamp: datetime
    volume: int | None = None
    bid: float | None = None
    ask: float | None = None


class OrderSide(Enum):
    """Order side enumeration."""

    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(Enum):
    """Time in force enumeration."""

    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"
