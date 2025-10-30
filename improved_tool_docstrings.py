#!/usr/bin/env python3
"""
IMPROVED TOOL DOCSTRINGS - Before/After Examples

This file demonstrates how to write excellent, actionable tool docstrings
that tell Claude Code EXACTLY when and how to use each tool.

Core principles:
1. ONE-LINE SUMMARY at top
2. WHEN TO USE section (specific scenarios)
3. HOW IT WORKS section (step-by-step)
4. WHY THIS TOOL section (what makes it distinct)
5. EXAMPLES section (copy-paste ready)
6. Clear Args/Returns
"""

# ============================================================================
# EXAMPLE 1: Market Data Fetching
# ============================================================================

# BEFORE (WEAK):
async def get_stock_quote_BEFORE(symbol: str) -> str:
    """Get latest quote for a stock."""
    pass

# AFTER (STRONG):
async def get_stock_quote_AFTER(symbol: str) -> str:
    """
    Get real-time bid/ask quote with spread analysis for immediate trading decisions.

    WHEN TO USE:
    - Checking current price before placing an order
    - Verifying spread before market/limit order decision
    - Confirming liquidity via bid/ask sizes
    - Real-time price monitoring during active trades

    HOW IT WORKS:
    1. Fetches latest quote from Alpaca market data API
    2. Returns bid price, ask price, spread, and sizes
    3. Includes timestamp for quote age verification

    WHY THIS TOOL:
    Use for IMMEDIATE price checks (last few seconds).
    For historical prices, use get_stock_bars() instead.
    For continuous monitoring, use start_global_stock_stream() instead.

    Examples:
        # Quick price check
        get_stock_quote("AAPL")

        # Verify spread before large order
        get_stock_quote("TSLA")  # Check if spread <0.5% before market order

    Args:
        symbol: Stock ticker symbol (e.g., "AAPL", "MSFT", "NVDA")

    Returns:
        Formatted quote with:
        - Bid: $X.XX x SIZE
        - Ask: $X.XX x SIZE
        - Spread: $X.XX (X.XX%)
        - Timestamp: YYYY-MM-DD HH:MM:SS ET
    """
    pass


# ============================================================================
# EXAMPLE 2: Scanning
# ============================================================================

# BEFORE (WEAK):
async def scan_day_trading_opportunities_BEFORE(
    symbols: str = "ALL"
) -> str:
    """Scan for day trading stocks."""
    pass

# AFTER (STRONG):
async def scan_day_trading_opportunities_AFTER(
    symbols: str = "ALL",
    min_trades_per_minute: int | None = None,
    min_percent_change: float | None = None,
    max_symbols: int = 10
) -> str:
    """
    Find explosive intraday movers with high volume for same-day scalping.

    WHEN TO USE:
    - Start of trading day to build watchlist
    - Need to find high-momentum stocks quickly
    - Want stocks with >1000 trades/minute (liquid)
    - Looking for >5% moves (volatile enough to profit)

    HOW IT WORKS:
    1. Scans all tradeable stocks (or specified list)
    2. Filters by trade intensity (trades per minute)
    3. Filters by percentage change from previous close
    4. Ranks by trade activity (most active first)
    5. Returns top N stocks meeting criteria

    WHY THIS TOOL:
    This is your PRIMARY scanner for day trading.
    - Focused on INTRADAY volatility (not after-hours)
    - Optimized for high-frequency trading (needs liquidity)
    - Only returns UPWARD movers (no negative % changes)

    For after-hours trading, use scan_after_hours_opportunities() instead.
    For extreme movers only, use scan_explosive_momentum() instead.

    Examples:
        # Quick morning scan
        scan_day_trading_opportunities()

        # More aggressive filtering
        scan_day_trading_opportunities(
            min_trades_per_minute=2000,
            min_percent_change=10.0,
            max_symbols=5
        )

        # Scan specific watchlist
        scan_day_trading_opportunities("AAPL,TSLA,NVDA,AMD,COIN")

    Args:
        symbols: "ALL" for full market scan, or comma-separated tickers
        min_trades_per_minute: Override global threshold (default: 1000 from config)
        min_percent_change: Override global threshold (default: 5.0% from config)
        max_symbols: Maximum results to return (default: 10)

    Returns:
        Ranked table:
        Rank | Symbol | Trades/Min | % Change | Price | Volume
        Shows top opportunities sorted by trade intensity
    """
    pass


# ============================================================================
# EXAMPLE 3: Technical Analysis
# ============================================================================

# BEFORE (WEAK):
async def get_stock_peak_trough_analysis_BEFORE(symbols: str) -> str:
    """Analyze peaks and troughs."""
    pass

# AFTER (STRONG):
async def get_stock_peak_trough_analysis_AFTER(
    symbols: str = "AUTO",
    timeframe: str = "1Min",
    days: int = 1,
    window_len: int | None = None,
    lookahead: int | None = None
) -> str:
    """
    Identify precise support/resistance levels using zero-phase Hanning filtering.

    WHEN TO USE:
    - Need entry/exit prices for day trading
    - Want to identify support (buy zone) and resistance (sell zone)
    - Planning limit orders at technical levels
    - Confirming reversal points for scalping

    HOW IT WORKS:
    1. Fetches intraday price bars (1min default)
    2. Applies zero-phase Hanning filter to remove noise
    3. Detects peaks (resistance) and troughs (support)
    4. Reports ORIGINAL prices at peak/trough locations
    5. Generates BUY/SELL signals based on current price position

    WHY THIS TOOL:
    Professional technical analysis for day trading:
    - Uses advanced signal processing (zero-phase filter preserves timing)
    - Returns ORIGINAL prices (not filtered) for actual trading
    - Shows sample indices for verification
    - Interprets signals automatically (no manual analysis needed)

    For plotting visual charts, use generate_stock_plot() instead.
    For quick analysis without filtering, use get_stock_bars() and analyze manually.

    Examples:
        # Auto-analyze current hot stocks
        get_stock_peak_trough_analysis("AUTO")

        # Analyze specific stock with 5-minute bars
        get_stock_peak_trough_analysis("AAPL", timeframe="5Min", days=2)

        # More smoothing for cleaner signals
        get_stock_peak_trough_analysis("NVDA", window_len=21, lookahead=3)

    Args:
        symbols: "AUTO" for scanner results, or comma-separated tickers
        timeframe: Bar interval - "1Min", "5Min", "15Min", "30Min", "1Hour"
        days: Historical days to analyze (1-30 for intraday)
        window_len: Smoothing window size (default: 11 from config, must be odd)
        lookahead: Peak detection sensitivity (default: 1 from config)

    Returns:
        For each symbol:
        - Technical summary (price range, bar count)
        - Recent peaks with prices and distances
        - Recent troughs with prices and distances
        - Trading signals: BUY at trough, SELL at peak
        - Distance analysis to latest signals
    """
    pass


# ============================================================================
# EXAMPLE 4: Order Placement
# ============================================================================

# BEFORE (WEAK):
async def place_stock_order_BEFORE(
    symbol: str,
    side: str,
    quantity: float
) -> str:
    """Place a stock order."""
    pass

# AFTER (STRONG):
async def place_stock_order_AFTER(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "market",
    limit_price: float | None = None,
    time_in_force: str = "day",
    extended_hours: bool = False
) -> str:
    """
    Execute stock order with automatic validation and confirmation.

    WHEN TO USE:
    - Ready to enter/exit a position
    - Have analyzed stock and determined entry/exit price
    - Need to execute trade during regular or extended hours

    HOW IT WORKS:
    1. Validates order parameters (symbol exists, quantity > 0, etc.)
    2. Checks account buying power for buys
    3. Submits order to Alpaca trading API
    4. Returns order confirmation with order ID
    5. Order is tracked in your positions immediately

    WHY THIS TOOL:
    This is your MAIN order execution tool for stocks.
    - Handles market and limit orders
    - Supports extended hours trading
    - Automatic parameter validation
    - Returns order ID for tracking

    For options, use place_option_market_order() instead.
    For automatic spread orders, use place_debit_spread() instead.

    Examples:
        # Quick market buy
        place_stock_order("AAPL", "buy", 100)

        # Limit order at specific price
        place_stock_order(
            "TSLA",
            "buy",
            50,
            order_type="limit",
            limit_price=225.50
        )

        # Extended hours sell
        place_stock_order(
            "NVDA",
            "sell",
            25,
            order_type="limit",
            limit_price=145.00,
            extended_hours=True
        )

    Args:
        symbol: Stock ticker (e.g., "AAPL")
        side: "buy" or "sell"
        quantity: Number of shares (must be > 0)
        order_type: "market" or "limit" (default: "market")
        limit_price: Required if order_type="limit"
        time_in_force: "day", "gtc", "ioc", "fok" (default: "day")
        extended_hours: True for pre/post-market (default: False)

    Returns:
        Order confirmation:
        - Order ID
        - Symbol, Side, Quantity
        - Order Type, Status
        - Limit Price (if applicable)
        - Submitted timestamp
    """
    pass


# ============================================================================
# EXAMPLE 5: Position Management
# ============================================================================

# BEFORE (WEAK):
async def get_positions_BEFORE() -> str:
    """Get current positions."""
    pass

# AFTER (STRONG):
async def get_positions_AFTER() -> str:
    """
    List all open positions with P&L analysis for portfolio review.

    WHEN TO USE:
    - Check current holdings and performance
    - Review unrealized gains/losses before close
    - Verify position sizes and allocations
    - Monitor which positions need attention

    HOW IT WORKS:
    1. Fetches all open positions from Alpaca account
    2. Calculates unrealized P&L for each position
    3. Shows entry price vs current price
    4. Sorts by largest positions first

    WHY THIS TOOL:
    Quick portfolio snapshot tool.
    - Shows ALL positions (stocks and options)
    - Includes unrealized P&L (gain/loss not yet realized)
    - Updates in real-time (reflects current market prices)

    For single position details, use get_open_position(symbol) instead.
    For P&L history, use get_single_day_pnl(date) instead.
    For closing positions, use close_position(symbol) instead.

    Examples:
        # Quick portfolio check
        get_positions()

    Returns:
        Table of positions:
        Symbol | Qty | Entry | Current | Market Value | P&L | P&L %
        ---
        Shows unrealized gains in GREEN, losses in RED (if terminal supports)
        Empty response if no open positions
    """
    pass


# ============================================================================
# EXAMPLE 6: Monitoring
# ============================================================================

# BEFORE (WEAK):
async def start_global_stock_stream_BEFORE(symbols: list[str]) -> str:
    """Start streaming data."""
    pass

# AFTER (STRONG):
async def start_global_stock_stream_AFTER(
    symbols: list[str],
    data_types: list[str] = None,
    feed: str = "sip",
    duration_seconds: int | None = None
) -> str:
    """
    Start real-time WebSocket stream for live market data during active trading.

    WHEN TO USE:
    - Need continuous price updates (not just snapshots)
    - Monitoring multiple positions simultaneously
    - Building real-time trading strategies
    - Want trades, quotes, or bars as they happen

    HOW IT WORKS:
    1. Opens WebSocket connection to Alpaca streaming API
    2. Subscribes to specified symbols and data types
    3. Buffers data in circular buffer (last 5000 items per symbol)
    4. Stream runs continuously until stopped or duration expires
    5. Use get_stock_stream_data() to access buffered data

    WHY THIS TOOL:
    This is for ACTIVE monitoring, not one-time checks.
    - WebSocket connection (low latency, continuous updates)
    - Buffered data accessible via get_stock_stream_data()
    - Multiple symbols and data types simultaneously
    - Automatic reconnection on connection loss

    For one-time price checks, use get_stock_quote() instead.
    To stop stream, use stop_global_stock_stream() instead.

    Examples:
        # Stream trades and quotes for active positions
        start_global_stock_stream(
            ["AAPL", "TSLA", "NVDA"],
            data_types=["trades", "quotes"]
        )

        # Stream with auto-stop after 1 hour
        start_global_stock_stream(
            ["SPY", "QQQ"],
            duration_seconds=3600
        )

    Args:
        symbols: List of tickers to stream (e.g., ["AAPL", "MSFT"])
        data_types: ["trades"], ["quotes"], ["bars"], or ["trades", "quotes"]
                   (default: ["trades", "quotes", "bars"])
        feed: "sip" for all markets, "iex" for IEX only (default: "sip")
        duration_seconds: Auto-stop after N seconds (default: None = run forever)

    Returns:
        Confirmation message:
        - Stream status (started/already running)
        - Subscribed symbols
        - Data types being streamed
        - Buffer size per symbol
        - How to access data (use get_stock_stream_data)
    """
    pass


# ============================================================================
# KEY PATTERNS FOR ALL DOCSTRINGS
# ============================================================================

"""
ALWAYS INCLUDE:
1. ONE-LINE SUMMARY (what it does)
2. WHEN TO USE (3-5 specific scenarios)
3. HOW IT WORKS (numbered steps)
4. WHY THIS TOOL (what makes it distinct, when NOT to use it)
5. EXAMPLES (2-3 realistic, copy-paste ready examples)
6. CLEAR ARGS/RETURNS

AVOID:
- Vague descriptions ("Get data")
- Technical jargon without explanation
- Missing examples
- No guidance on when to use
- Ambiguous return formats
"""
