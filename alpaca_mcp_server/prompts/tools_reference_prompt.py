"""Tools reference prompt for listing all available MCP tools."""


async def list_all_tools() -> str:
    """
    List all available MCP tools with descriptions and usage examples.

    Returns:
        Comprehensive reference of all tools organized by category
    """

    tools_reference = """# Alpaca MCP Server - Available Tools Reference

## 🔥 Featured Tool - NEW Peak/Trough Analysis

### `get_stock_peak_trough_analysis(symbols, timeframe="1Min", window_len=21, lookahead=1)`
**Advanced technical analysis using zero-phase Hanning filtering for day trading signals**

Perfect for the trading lesson: **"SCAN LONGER before entry"** - provides precise entry/exit points
- Returns BUY/LONG and SELL/SHORT signals
- Identifies support/resistance levels
- Multi-symbol analysis in one call
- Example: `get_stock_peak_trough_analysis("CGTL,HCTI", timeframe="1Min")`

---

## Account & Portfolio Management

| Tool | Description | Example |
|------|-------------|---------|
| `get_account_info()` | Account balances and status | `get_account_info()` |
| `get_positions()` | All current positions with P&L | `get_positions()` |
| `get_open_position(symbol)` | Specific position details | `get_open_position("AAPL")` |
| `close_position(symbol, percentage)` | Close position | `close_position("AAPL", percentage="50")` |
| `close_all_positions()` | Close all positions | `close_all_positions(cancel_orders=True)` |

---

## Market Data & Quotes

| Tool | Description | Example |
|------|-------------|---------|
| `get_stock_quote(symbol)` | Real-time bid/ask prices | `get_stock_quote("AAPL")` |
| `get_stock_snapshots(symbols)` | Multi-stock market data | `get_stock_snapshots("AAPL,MSFT,NVDA")` |
| `get_stock_bars(symbol, days)` | Historical daily bars | `get_stock_bars("AAPL", days=10)` |
| `get_stock_bars_intraday(symbol, timeframe)` | Intraday analysis | `get_stock_bars_intraday("AAPL", "5Min")` |
| `get_stock_latest_trade(symbol)` | Most recent trade | `get_stock_latest_trade("AAPL")` |
| `get_stock_latest_bar(symbol)` | Latest minute bar | `get_stock_latest_bar("AAPL")` |

---

## Order Management

| Tool | Description | Example |
|------|-------------|---------|
| `place_stock_order(symbol, side, quantity, order_type, limit_price)` | Place orders | `place_stock_order("AAPL", "buy", 10, "limit", limit_price=150.00)` |
| `get_orders(status, limit)` | View orders | `get_orders("open", limit=20)` |
| `cancel_order_by_id(order_id)` | Cancel specific order | `cancel_order_by_id("12345")` |
| `cancel_all_orders()` | Cancel all orders | `cancel_all_orders()` |

---

## Streaming Data (Real-time)

| Tool | Description | Example |
|------|-------------|---------|
| `start_global_stock_stream(symbols, data_types)` | Start live data | `start_global_stock_stream(["AAPL"], ["trades", "quotes"])` |
| `get_stock_stream_data(symbol, data_type, recent_seconds)` | Get streaming data | `get_stock_stream_data("AAPL", "trades", recent_seconds=60)` |
| `stop_global_stock_stream()` | Stop all streams | `stop_global_stock_stream()` |
| `list_active_stock_streams()` | View active streams | `list_active_stock_streams()` |

---

## Options Trading

| Tool | Description | Example |
|------|-------------|---------|
| `get_option_contracts(underlying_symbol, type)` | Find option contracts | `get_option_contracts("AAPL", type="call")` |
| `get_option_latest_quote(symbol)` | Option bid/ask + Greeks | `get_option_latest_quote("AAPL230616C00150000")` |
| `place_option_market_order(legs)` | Place option order | `place_option_market_order([{"symbol": "...", "side": "buy"}])` |

---

## Market Information

| Tool | Description | Example |
|------|-------------|---------|
| `get_market_clock()` | Market open/closed status | `get_market_clock()` |
| `get_extended_market_clock()` | Extended hours info | `get_extended_market_clock()` |
| `get_market_calendar(start_date, end_date)` | Trading calendar | `get_market_calendar("2023-06-01", "2023-06-30")` |

---

## Day Trading Workflow

**1. Market Check & Analysis:**
```
get_market_clock()
get_stock_snapshots("CGTL,HCTI,KLTO")
get_stock_peak_trough_analysis("CGTL", timeframe="1Min")
```

**2. Live Data Setup:**
```
start_global_stock_stream(["CGTL"], ["trades", "quotes"])
```

**3. Order Execution (LIMIT ORDERS ONLY):**
```
place_stock_order("CGTL", "buy", 1000, "limit", limit_price=1.25)
```

**4. Real-time Monitoring:**
```
get_stock_stream_data("CGTL", "trades", recent_seconds=30)
get_positions()
```

**5. Exit Management:**
```
close_position("CGTL", percentage="100")
```

---

## Trading Lessons Integration

- **"SCAN LONGER before entry"** → `get_stock_peak_trough_analysis()` for precise levels
- **"Use limit orders exclusively"** → Always use `order_type="limit"`
- **"React within 2-3 seconds"** → Have streaming data ready
- **"Monitor every 1-3 seconds"** → Use `get_stock_stream_data()`
- **"Capture profits aggressively"** → Monitor positions and close at resistance

---

## Additional Categories

**Watchlists:** `create_watchlist()`, `get_watchlists()`, `update_watchlist()`
**Assets:** `get_all_assets()`, `get_asset_info()`
**Extended Hours:** `place_extended_hours_order()`, `validate_extended_hours_order()`
**System Health:** `health_check()`, `resource_*()` functions

**Total Tools Available: ~45+ tools across all categories**

For detailed documentation, see: `MCP_TOOLS_REFERENCE.md`
"""

    return tools_reference
