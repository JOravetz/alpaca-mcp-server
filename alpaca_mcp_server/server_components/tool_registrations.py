"""Tool registration module for MCP server."""

from ..resources import help_system, server_health, session_status
from ..tools import (
    account_tools,
    asset_tools,
    corporate_action_tools,
    fastapi_monitoring_tools,
    market_data_tools,
    market_info_tools,
    monitoring_tools,
    options_tools,
    order_tools,
    position_tools,
    streaming_tools,
    volume_bars_tool,
    watchlist_tools,
)
from ..tools.cleanup_tool import cleanup_server
from ..tools.peak_trough_analysis_tool import (
    analyze_peaks_and_troughs_with_plot_py as peak_trough_analysis,
)
from ..tools.c_peak_trough_wrapper import (
    analyze_peaks_troughs_fast as c_peak_trough_fast,
    compare_implementations as c_compare_implementations,
)
# C analyzer imports moved to function level to avoid naming conflicts


def register_account_tools(mcp):
    """Register account and position management tools."""

    @mcp.tool()
    async def get_account_info() -> str:
        """Get current account information including balances and status."""
        return await account_tools.get_account_info()

    @mcp.tool()
    async def get_positions() -> str:
        """Get all current positions in the portfolio."""
        return await account_tools.get_positions()

    @mcp.tool()
    async def get_open_position(symbol: str) -> str:
        """Get details for a specific open position."""
        return await account_tools.get_open_position(symbol)

    @mcp.tool()
    async def close_position(symbol: str, qty: str = None, percentage: str = None) -> str:
        """Close a specific position."""
        return await position_tools.close_position(symbol, qty, percentage)

    @mcp.tool()
    async def close_all_positions(cancel_orders: bool = False) -> str:
        """Close all open positions."""
        return await position_tools.close_all_positions(cancel_orders)


def register_market_data_tools(mcp):
    """Register market data tools."""

    def get_safe_help_system():
        """Get help system, initializing if needed."""
        try:
            return help_system.get_help_system()
        except RuntimeError:
            # Help system not initialized, initialize it now
            help_system.initialize_help_system(mcp)
            return help_system.get_help_system()

    @mcp.tool()
    async def get_stock_quote(symbol: str, help: str = None) -> str:
        """Get latest quote for a stock."""
        if help == "--help" or help == "help":
            return get_safe_help_system().get_tool_help("get_stock_quote")
        return await market_data_tools.get_stock_quote(symbol)

    @mcp.tool()
    async def get_stock_snapshots(symbols: str) -> str:
        """Get comprehensive market snapshots."""
        return await market_data_tools.get_stock_snapshots(symbols)

    @mcp.tool()
    async def get_stock_bars(symbol: str, days: int = 5) -> str:
        """Get historical price bars."""
        return await market_data_tools.get_stock_bars(symbol, days)

    @mcp.tool()
    async def get_stock_bars_intraday(
        symbol: str,
        timeframe: str = "1Min",
        start_date: str = None,
        end_date: str = None,
        limit: int = 10000,
    ) -> str:
        """Get intraday historical bars with analysis."""
        return await market_data_tools.get_stock_bars_intraday(
            symbol, timeframe, start_date, end_date, limit
        )

    @mcp.tool()
    async def get_stock_trades(symbol: str, days: int = 5, limit: int = None) -> str:
        """Get recent trades for a stock."""
        return await market_data_tools.get_stock_trades(symbol, days, limit)

    @mcp.tool()
    async def get_stock_latest_trade(symbol: str) -> str:
        """Get the latest trade for a stock."""
        return await market_data_tools.get_stock_latest_trade(symbol)

    @mcp.tool()
    async def get_stock_latest_bar(symbol: str) -> str:
        """Get the latest minute bar for a stock."""
        return await market_data_tools.get_stock_latest_bar(symbol)


def register_market_info_tools(mcp):
    """Register market info tools."""

    @mcp.tool()
    async def get_market_clock() -> str:
        """Get current market status and next open/close times."""
        return await market_info_tools.get_market_clock()

    @mcp.tool()
    async def get_market_calendar(start_date: str, end_date: str) -> str:
        """Get market calendar for specified date range."""
        return await market_info_tools.get_market_calendar(start_date, end_date)


def register_options_tools(mcp):
    """Register options trading tools."""

    @mcp.tool()
    async def get_option_contracts(
        underlying_symbol: str,
        expiration_date: str = None,
        strike_price_gte: str = None,
        strike_price_lte: str = None,
        type: str = None,
        limit: int = None,
    ) -> str:
        """Get option contracts for underlying symbol."""
        from datetime import datetime

        # Convert string date to date object if provided
        parsed_expiration_date = None
        if expiration_date:
            try:
                parsed_expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
            except ValueError:
                return f"Error: Invalid date format '{expiration_date}'. Use YYYY-MM-DD format."

        return await options_tools.get_option_contracts(
            underlying_symbol,
            parsed_expiration_date,
            strike_price_gte,
            strike_price_lte,
            type,
            None,
            None,
            limit,
        )

    @mcp.tool()
    async def get_option_latest_quote(symbol: str) -> str:
        """Get latest quote for an option contract."""
        return await options_tools.get_option_latest_quote(symbol)

    @mcp.tool()
    async def get_option_snapshot(symbol: str) -> str:
        """Get comprehensive option snapshot with Greeks."""
        return await options_tools.get_option_snapshot(symbol)


def register_technical_analysis_tools(mcp, DEFAULT_WINDOW_LEN):
    """Register technical analysis tools."""

    @mcp.tool()
    async def get_stock_peak_trough_analysis(
        symbols: str = "AUTO",
        timeframe: str = "1Min",
        days: int = 1,
        limit: int = 1000,
        window_len: int = DEFAULT_WINDOW_LEN,
        lookahead: int = 1,
        delta: float = 0.0,
        min_peak_distance: int = 5,
    ) -> str:
        """
        Get stock peak and trough analysis for day trading signals using zero-phase Hanning filtering.

        This professional technical analysis tool:
        1. Fetches intraday bar data for specified symbols
        2. Applies zero-phase low-pass Hanning filtering to remove noise
        3. Detects peaks/troughs using advanced algorithms
        4. Returns precise entry/exit levels for day trading

        Perfect for identifying support/resistance levels and timing entries based on
        yesterday's trading lessons: "SCAN LONGER before entry" - this tool provides
        the technical analysis to find optimal entry points.

        Args:
            symbols: "AUTO" for current scanner results, or manual symbols (e.g., "AAPL,MSFT,NVDA")
            timeframe: "1Min", "5Min", "15Min", "30Min", "1Hour" (default: "1Min")
            days: Historical days to analyze (1-30, default: 1)
            limit: Max bars to fetch (1-10000, default: 1000)
            window_len: Hanning filter smoothing (3-101, uses global config value from technical_analysis.hanning_window_samples)
            lookahead: Peak detection sensitivity (1-50, uses global config value from technical_analysis.peak_trough_lookahead)
            delta: Minimum peak amplitude (default: 0.0 for penny stocks)
            min_peak_distance: Min bars between peaks (default: 5)

        Returns detailed analysis with BUY/LONG and SELL/SHORT signals.
        """
        return await peak_trough_analysis(
            symbols, timeframe, days, window_len, lookahead, delta, min_peak_distance
        )

    @mcp.tool()
    async def analyze_peaks_troughs_fast(
        symbols: str,
        timeframe: str = "1Min",
        days: int = 1,
        window_len: int = None,
        filter_key: str = "close",
        feed: str = "sip",
    ) -> str:
        """
        Ultra-fast peak/trough analysis using C implementation (5-10x faster).
        
        This high-performance version uses a compiled C program for speed,
        making it ideal for real-time scanning and high-frequency analysis.
        
        Args:
            symbols: Comma-separated symbols or "AUTO" for scanner results
            timeframe: Bar timeframe (1Min, 5Min, 15Min, 1Hour, 1Day)
            days: Number of trading days to analyze (1-30)
            window_len: Hanning filter window length (3-101, odd, uses global config if None)
            filter_key: Data field to filter (close, open, high, low, vwap)
            feed: Data feed source (sip, iex, otc)
        
        Returns:
            Formatted analysis with trading signals
        """
        return await c_peak_trough_fast(
            symbols, timeframe, days, window_len, filter_key, feed
        )
    
    @mcp.tool()
    async def compare_peak_trough_implementations(
        symbol: str,
        timeframe: str = "1Min",
        days: int = 1,
    ) -> str:
        """
        Compare performance between C and Python peak/trough implementations.
        
        Useful for benchmarking and verifying the speedup of the C version.
        
        Args:
            symbol: Stock symbol to analyze
            timeframe: Bar timeframe
            days: Number of days to analyze
        
        Returns:
            Performance comparison report
        """
        return await c_compare_implementations(symbol, timeframe, days)

    @mcp.tool()
    async def get_volume_bars_from_history(
        symbol: str,
        volume_threshold: float = None,
        days: int = 1,
        auto_calculate_threshold: bool = True,
        target_bars_per_day: int = 50,
        use_bars: bool = True,
        bar_timeframe: str = "1Min",
    ) -> str:
        """
        Generate volume bars from historical data using López de Prado's methodology.

        Volume bars sample by volume rather than time, providing better statistical properties
        for machine learning and more responsive market microstructure analysis.

        Args:
            symbol: Stock symbol
            volume_threshold: Volume per bar (if None, auto-calculates)
            days: Number of days of history to process
            auto_calculate_threshold: Whether to auto-calculate optimal threshold
            target_bars_per_day: Target number of bars per day for auto-calculation
            use_bars: If True, uses bar data with pre-computed VWAP; if False, uses trade data
            bar_timeframe: Timeframe for bars ("1Min", "5Min", etc.) when use_bars=True

        Returns:
            Formatted volume bars analysis with statistical properties
        """
        return await volume_bars_tool.get_volume_bars_from_history(
            symbol,
            volume_threshold,
            days,
            auto_calculate_threshold,
            target_bars_per_day,
            use_bars,
            bar_timeframe,
        )

    @mcp.tool()
    async def compare_bar_types(
        symbol: str, days: int = 1, time_bars_minutes: int = 5, volume_threshold: float = None
    ) -> str:
        """
        Compare statistical properties of time bars vs volume bars.

        This comparison helps understand the benefits of volume bars over
        traditional time-based sampling as described in López de Prado's book.

        Args:
            symbol: Stock symbol to analyze
            days: Number of days to analyze
            time_bars_minutes: Minute interval for time bars
            volume_threshold: Volume threshold for volume bars

        Returns:
            Comparative analysis of both bar types including autocorrelation,
            kurtosis, and suitability for machine learning
        """
        return await volume_bars_tool.compare_bar_types(
            symbol, days, time_bars_minutes, volume_threshold
        )

    @mcp.tool()
    async def start_volume_bar_streaming(
        symbols: str,
        volume_thresholds: str = None,
        auto_calculate: bool = True,
        target_bars_per_day: int = 50,
    ) -> str:
        """
        Start real-time volume bar aggregation using existing stream.

        Integrates with the global stock stream to aggregate trades into volume bars.

        Args:
            symbols: Comma-separated symbols to track
            volume_thresholds: Comma-separated thresholds or single value for all
            auto_calculate: Auto-calculate thresholds based on ADV
            target_bars_per_day: Target bars per day for auto-calculation

        Returns:
            Status message
        """
        return await volume_bars_tool.start_volume_bar_streaming(
            symbols, volume_thresholds, auto_calculate, target_bars_per_day
        )

    @mcp.tool()
    async def get_volume_bar_stats(symbol: str = None) -> str:
        """
        Get current volume bar statistics and recent bars.

        Args:
            symbol: Specific symbol or None for all

        Returns:
            Formatted statistics and recent bars
        """
        return await volume_bars_tool.get_volume_bar_stats(symbol)


def register_scanner_tools(mcp):
    """Register market scanner tools."""

    @mcp.tool()
    async def scan_day_trading_opportunities(
        symbols: str = "ALL",
        min_trades_per_minute: int = None,
        min_percent_change: float = None,
        max_symbols: int = None,
        sort_by: str = None,
    ) -> str:
        """
        Scan for EXPLOSIVE UP-ONLY day-trading opportunities with extreme volatility.

        UPDATED FILTER CRITERIA:
        1. ONLY UP STOCKS - No negative movers ever
        2. Minimum gain threshold from global config (min_percent_change_threshold)
        3. Minimum trades/minute from global config (trades_per_minute_threshold)
        4. EXPLOSIVE VOLATILITY FOCUS - Penny stocks and rocket ships preferred

        Args:
            symbols: Comma-separated symbols to scan (default: ALL tradeable assets)
            min_trades_per_minute: IGNORED - Always uses global config value
            min_percent_change: IGNORED - Always uses global config value
            max_symbols: Maximum results to return (default: from global config)
            sort_by: Sort results by "trades", "percent_change", or "volume" (default: from global config)

        Returns:
            Formatted analysis with EXPLOSIVE UP-ONLY trading opportunities.
        """
        from ..tools.day_trading_scanner import scan_day_trading_opportunities as scanner_func

        return await scanner_func(
            symbols, min_trades_per_minute, min_percent_change, max_symbols, sort_by
        )

    @mcp.tool()
    async def scan_explosive_momentum(
        symbols: str = "CVAC,CGTL,GNLN,NEHC,SOUN,RIOT,MARA,COIN,HOOD,RBLX",
        min_percent_change: float = 15.0,
    ) -> str:
        """
        Quick scanner for explosive momentum moves like NEHC.

        Optimized for finding extreme percentage movers with high activity.
        Lower trade threshold but higher % change requirement for explosive stocks.

        Args:
            symbols: Comma-separated symbols (default: volatile/momentum stocks)
            min_percent_change: Minimum absolute % change (default: 15.0% for explosive moves)

        Returns:
            Top explosive momentum opportunities sorted by % change.
        """
        from ..tools.day_trading_scanner import scan_explosive_momentum as explosive_func

        return await explosive_func(symbols, min_percent_change)

    @mcp.tool()
    async def scan_after_hours_opportunities(
        symbols: str = "AAPL,MSFT,NVDA,TSLA,GOOGL,AMZN,META,NFLX,COIN,HOOD,AMC,GME,PLTR,SOFI,RIVN,LCID",
        min_volume: int = 100000,
        min_percent_change: float = 2.0,
        max_symbols: int = 15,
        sort_by: str = "percent_change",
    ) -> str:
        """
        Scan for after-hours trading opportunities with enhanced analytics.

        Focuses on:
        1. Extended hours price movements
        2. Volume analysis relative to average
        3. News-driven momentum detection
        4. Liquidity assessment for safe entry/exit

        Args:
            symbols: Comma-separated symbols for after-hours scanning
            min_volume: Minimum after-hours volume threshold
            min_percent_change: Minimum % change from regular session close
            max_symbols: Maximum results to return
            sort_by: Sort results by "percent_change", "volume", or "price"

        Returns:
            Formatted analysis of after-hours opportunities
        """
        from ..tools.after_hours_scanner import scan_after_hours_opportunities as scanner_func

        return await scanner_func(symbols, min_volume, min_percent_change, max_symbols, sort_by)

    @mcp.tool()
    async def analyze_market_activity_fast(
        symbols: str = None,
        max_results: int = 10,
        max_price: float = 50.0,
        min_percent_change: float = 5.0,
        min_trades: int = 500,
        sort_by: str = "trades,percent_change",
    ) -> str:
        """
        Ultra-fast market activity analysis using C implementation (10x+ faster).
        
        Analyzes real-time stock snapshots to find high-activity stocks with
        momentum. Calculates gradients, volume changes, and trade intensity.
        
        Perfect for rapid scanning of hundreds of symbols to find day trading
        opportunities. The C implementation provides industrial-grade performance.
        
        Args:
            symbols: Optional comma-separated symbols (None = use default list)
            max_results: Maximum number of results to return
            max_price: Maximum stock price filter (focus on penny stocks)
            min_percent_change: Minimum percent change threshold
            min_trades: Minimum trades threshold
            sort_by: Sort keys (trades, percent_change, volume, gradient_change)
        
        Returns:
            Formatted analysis with high-activity trading opportunities
        """
        from ..tools.c_stock_analyzer_wrapper import analyze_market_activity_fast as c_analyzer_func
        return await c_analyzer_func(
            symbols, max_results, max_price, min_percent_change, min_trades, sort_by
        )
    
    @mcp.tool()
    async def scan_explosive_stocks_fast(
        max_results: int = 20,
        min_percent_change: float = 10.0,
        max_price: float = 30.0,
    ) -> str:
        """
        Lightning-fast scan for explosive penny stocks using C analyzer.
        
        Optimized for finding extreme percentage movers with high activity.
        This is the fastest way to find volatile day trading opportunities.
        
        Args:
            max_results: Maximum number of results
            min_percent_change: Minimum percent change for explosive moves
            max_price: Maximum price (focus on penny stocks)
        
        Returns:
            Formatted list of explosive trading opportunities
        """
        from ..tools.c_stock_analyzer_wrapper import scan_explosive_stocks_fast as c_scanner_func
        return await c_scanner_func(max_results, min_percent_change, max_price)
    
    @mcp.tool()
    async def compare_analyzer_performance(
        test_symbols: str = "AAPL,MSFT,NVDA,SPY,TSLA",
    ) -> str:
        """
        Compare performance between C analyzer and Python scanners.
        
        Useful for demonstrating the speed advantage of the C implementation.
        
        Args:
            test_symbols: Symbols to test with
        
        Returns:
            Performance comparison report
        """
        from ..tools.c_stock_analyzer_wrapper import compare_analyzer_performance as c_compare_func
        return await c_compare_func(test_symbols)

    @mcp.tool()
    async def get_enhanced_streaming_analytics(
        symbol: str, analysis_minutes: int = 15, include_orderbook: bool = True
    ) -> str:
        """
        Enhanced streaming analytics with real-time calculations.

        Provides:
        1. Real-time momentum analysis
        2. Volume-weighted average price (VWAP)
        3. Order flow analysis
        4. Support/resistance detection
        5. Volatility measurements

        Args:
            symbol: Stock symbol to analyze
            analysis_minutes: Minutes of historical data to include
            include_orderbook: Include bid/ask analysis

        Returns:
            Comprehensive real-time analytics
        """
        from ..tools.after_hours_scanner import get_enhanced_streaming_analytics as analytics_func

        return await analytics_func(symbol, analysis_minutes, include_orderbook)

    @mcp.tool()
    async def get_single_day_pnl(
        date: str,
        symbol_filter: str = None,
        min_trade_value: float = 0.0,
    ) -> str:
        """
        Calculate P&L for a SINGLE specific trading day only.

        This tool correctly filters trades to show ONLY activity on the specified date,
        unlike the intraday_pnl resource which shows cumulative data over multiple days.

        Args:
            date: Date to analyze in YYYY-MM-DD format (e.g., "2025-07-08")
            symbol_filter: Optional symbol to filter trades (e.g., "AAPL")
            min_trade_value: Minimum trade value to include (default: 0)

        Returns:
            Formatted P&L report for that specific day only with per-symbol breakdown

        Example:
            get_single_day_pnl("2025-07-08")  # Get P&L for July 8, 2025 only
            get_single_day_pnl("2025-08-07", "FOXO")  # Get FOXO P&L for Aug 7 only
        """
        from ..tools.single_day_pnl import get_single_day_pnl as pnl_func

        return await pnl_func(date, symbol_filter, min_trade_value)


def register_watchlist_tools(mcp):
    """Register watchlist management tools."""

    @mcp.tool()
    async def create_watchlist(name: str, symbols: list) -> str:
        """Create a new watchlist with specified symbols."""
        return await watchlist_tools.create_watchlist(name, symbols)

    @mcp.tool()
    async def get_watchlists() -> str:
        """Get all watchlists for the account."""
        return await watchlist_tools.get_watchlists()

    @mcp.tool()
    async def update_watchlist(watchlist_id: str, name: str = None, symbols: list = None) -> str:
        """Update an existing watchlist."""
        return await watchlist_tools.update_watchlist(watchlist_id, name, symbols)


def register_asset_tools(mcp):
    """Register asset information tools."""

    @mcp.tool()
    async def get_all_assets(
        status: str = None,
        asset_class: str = None,
        exchange: str = None,
        attributes: str = None,
        tradable_only: bool = True,
        max_symbol_length: int = 4,
    ) -> str:
        """Get all available assets with optional filtering."""
        return await asset_tools.get_all_assets(
            status, asset_class, exchange, attributes, tradable_only, max_symbol_length
        )

    @mcp.tool()
    async def get_asset_info(symbol: str) -> str:
        """Get detailed information about a specific asset."""
        return await asset_tools.get_asset_info(symbol)


def register_corporate_action_tools(mcp):
    """Register corporate action tools."""

    @mcp.tool()
    async def get_corporate_announcements(
        ca_types: list,
        since: str,
        until: str,
        symbol: str | None = None,
        cusip: str = None,
        date_type: str = None,
    ) -> str:
        """Get corporate action announcements for specified criteria."""
        return await corporate_action_tools.get_corporate_announcements(
            ca_types, since, until, symbol, cusip, date_type
        )


def register_streaming_tools(mcp):
    """Register real-time streaming tools."""

    @mcp.tool()
    async def start_global_stock_stream(
        symbols: list,
        data_types: list = None,
        feed: str = "sip",
        duration_seconds: int = None,
        buffer_size_per_symbol: int = None,
        replace_existing: bool = False,
    ) -> str:
        """Start global real-time stock data stream for day trading."""
        if data_types is None:
            data_types = ["trades", "quotes"]
        return await streaming_tools.start_global_stock_stream(
            symbols,
            data_types,
            feed,
            duration_seconds,
            buffer_size_per_symbol,
            replace_existing,
        )

    @mcp.tool()
    async def stop_global_stock_stream() -> str:
        """Stop the global stock streaming session."""
        return await streaming_tools.stop_global_stock_stream()

    @mcp.tool()
    async def add_symbols_to_stock_stream(symbols: list, data_types: list = None) -> str:
        """Add symbols to existing stock stream."""
        return await streaming_tools.add_symbols_to_stock_stream(symbols, data_types)

    @mcp.tool()
    async def get_stock_stream_data(
        symbol: str, data_type: str, recent_seconds: int = None, limit: int = None
    ) -> str:
        """Get streaming data for analysis."""
        return await streaming_tools.get_stock_stream_data(symbol, data_type, recent_seconds, limit)

    @mcp.tool()
    async def list_active_stock_streams() -> str:
        """List all active streaming subscriptions."""
        return await streaming_tools.list_active_stock_streams()

    @mcp.tool()
    async def get_stock_stream_buffer_stats() -> str:
        """Get detailed streaming buffer statistics."""
        return await streaming_tools.get_stock_stream_buffer_stats()

    @mcp.tool()
    async def clear_stock_stream_buffers() -> str:
        """Clear streaming buffers to free memory."""
        return await streaming_tools.clear_stock_stream_buffers()

    @mcp.tool()
    async def stream_aware_price_monitor(symbol: str, analysis_seconds: int = 10) -> str:
        """Enhanced real-time price monitoring using shared stream with concurrent analysis."""
        return await streaming_tools.stream_aware_price_monitor(symbol, analysis_seconds)

    @mcp.tool()
    async def stream_optimized_order_placement(
        symbol: str, side: str, quantity: float, order_type: str = "limit"
    ) -> str:
        """Place order using optimal pricing from active stream."""
        return await streaming_tools.stream_optimized_order_placement(
            symbol, side, quantity, order_type
        )


def register_order_tools(mcp):
    """Register order management tools."""

    @mcp.tool()
    async def place_stock_order(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        time_in_force: str = "day",
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail_price: float | None = None,
        trail_percent: float | None = None,
        extended_hours: bool = False,
        client_order_id: str | None = None,
    ) -> str:
        """Place a stock order of any type."""
        return await order_tools.place_stock_order(
            symbol,
            side,
            quantity,
            order_type,
            time_in_force,
            limit_price,
            stop_price,
            trail_price,
            trail_percent,
            extended_hours,
            client_order_id,
        )

    @mcp.tool()
    async def get_orders(status: str = "all", limit: int = 10) -> str:
        """Get orders with specified status."""
        return await order_tools.get_orders(status, limit)

    @mcp.tool()
    async def cancel_order_by_id(order_id: str) -> str:
        """Cancel a specific order by ID."""
        return await order_tools.cancel_order_by_id(order_id)

    @mcp.tool()
    async def cancel_all_orders() -> str:
        """Cancel all open orders."""
        return await order_tools.cancel_all_orders()

    @mcp.tool()
    async def place_option_market_order(
        legs: list, order_class: str | None = None, quantity: int = 1
    ) -> str:
        """Place single or multi-leg options market order."""
        return await order_tools.place_option_market_order(legs, order_class, quantity)


def register_monitoring_tools(mcp):
    """Register hybrid monitoring tools."""

    @mcp.tool()
    async def start_hybrid_monitoring(
        check_interval: int = 2,
        signal_confidence_threshold: float = 0.75,
        max_concurrent_positions: int = 5,
        watchlist_size_limit: int = 20,
        enable_auto_alerts: bool = True,
        alert_channels: list = None,
    ) -> dict:
        """Start the hybrid trading monitoring service."""
        return await monitoring_tools.start_hybrid_monitoring(
            check_interval,
            signal_confidence_threshold,
            max_concurrent_positions,
            watchlist_size_limit,
            enable_auto_alerts,
            alert_channels,
        )

    @mcp.tool()
    async def stop_hybrid_monitoring() -> dict:
        """Stop the hybrid trading monitoring service."""
        return await monitoring_tools.stop_hybrid_monitoring()

    @mcp.tool()
    async def get_hybrid_monitoring_status() -> dict:
        """Get current status of the hybrid monitoring service."""
        return await monitoring_tools.get_hybrid_monitoring_status()

    @mcp.tool()
    async def verify_monitoring_active() -> dict:
        """Verify that monitoring is actually running and provide proof."""
        return await monitoring_tools.verify_monitoring_active()

    @mcp.tool()
    async def add_symbols_to_watchlist(symbols: list) -> dict:
        """Add symbols to the monitoring watchlist."""
        return await monitoring_tools.add_symbols_to_watchlist(symbols)

    @mcp.tool()
    async def remove_symbols_from_watchlist(symbols: list) -> dict:
        """Remove symbols from the monitoring watchlist."""
        return await monitoring_tools.remove_symbols_from_watchlist(symbols)

    @mcp.tool()
    async def get_current_watchlist() -> dict:
        """Get the current monitoring watchlist."""
        return await monitoring_tools.get_current_watchlist()

    @mcp.tool()
    async def get_current_trading_signals() -> dict:
        """Get current trading signals detected by the monitoring service."""
        return await monitoring_tools.get_current_trading_signals()

    @mcp.tool()
    async def get_profit_spike_alerts(count: int = 5) -> dict:
        """Get latest profit spike alerts generated by real-time streaming monitoring."""
        return await monitoring_tools.get_profit_spike_alerts(count)

    @mcp.tool()
    async def check_positions_after_order(order_info: dict = None) -> dict:
        """
        Force immediate position check after order execution.
        This ensures real-time feedback on position changes for continuous monitoring.

        Args:
            order_info: Optional dict with order details (symbol, action, etc.)

        Returns:
            Position status with current count and symbols
        """
        return await monitoring_tools.check_positions_after_order(order_info)

    @mcp.tool()
    async def ping_monitoring_service() -> dict:
        """
        Ping the hybrid monitoring service to verify it's alive and responsive.
        Returns comprehensive health metrics including uptime, response time, and monitoring status.

        Use this to verify service health and troubleshoot monitoring issues.

        Returns:
            Service health status with metrics (alive, responsive, uptime, check_count, etc.)
        """
        return await fastapi_monitoring_tools.ping_fastapi_monitoring_service()

    @mcp.tool()
    async def get_monitoring_alerts(count: int = 10) -> dict:
        """Get recent monitoring alerts."""
        return await monitoring_tools.get_monitoring_alerts(count)


def register_fastapi_monitoring_tools(mcp):
    """Register FastAPI monitoring service tools."""

    @mcp.tool()
    async def start_fastapi_monitoring_service() -> dict:
        """
        Start the FastAPI monitoring service.
        Creates a persistent HTTP-based monitoring service with REST endpoints.
        """
        return await fastapi_monitoring_tools.start_fastapi_monitoring_service()

    @mcp.tool()
    async def stop_fastapi_monitoring_service() -> dict:
        """
        Stop the FastAPI monitoring service gracefully.
        """
        return await fastapi_monitoring_tools.stop_fastapi_monitoring_service()

    @mcp.tool()
    async def get_fastapi_monitoring_status() -> dict:
        """
        Get comprehensive status from the FastAPI monitoring service.
        Returns live service health, watchlist, positions, and monitoring metrics.
        """
        return await fastapi_monitoring_tools.get_fastapi_monitoring_status()

    @mcp.tool()
    async def add_symbols_to_fastapi_watchlist(symbols: list) -> dict:
        """
        Add symbols to the FastAPI monitoring service watchlist.

        Args:
            symbols: List of stock symbols to add to monitoring
        """
        return await fastapi_monitoring_tools.add_symbols_to_fastapi_watchlist(symbols)

    @mcp.tool()
    async def remove_symbols_from_fastapi_watchlist(symbols: list) -> dict:
        """
        Remove symbols from the FastAPI monitoring service watchlist.

        Args:
            symbols: List of stock symbols to remove from monitoring
        """
        return await fastapi_monitoring_tools.remove_symbols_from_fastapi_watchlist(symbols)

    @mcp.tool()
    async def get_fastapi_positions() -> dict:
        """
        Get current positions from the FastAPI monitoring service.
        Returns live position data with profit/loss information.
        """
        return await fastapi_monitoring_tools.get_fastapi_positions()

    @mcp.tool()
    async def check_positions_after_order_fastapi(order_info: dict = None) -> dict:
        """
        Check positions immediately after an order using the FastAPI service.

        Args:
            order_info: Optional order information for tracking
        """
        return await fastapi_monitoring_tools.check_positions_after_order_fastapi(order_info)

    @mcp.tool()
    async def get_fastapi_signals() -> dict:
        """
        Get current trading signals from the FastAPI monitoring service.
        Returns active signals detected by the monitoring system.
        """
        return await fastapi_monitoring_tools.get_fastapi_signals()


def register_extended_hours_tools(mcp):
    """Register extended hours trading tools."""

    @mcp.tool()
    async def get_extended_market_clock() -> str:
        """Enhanced market clock with pre/post market sessions."""
        from ..tools.enhanced_market_clock import get_extended_market_clock

        return await get_extended_market_clock()

    @mcp.tool()
    async def validate_extended_hours_order(
        symbol: str, order_type: str, extended_hours: bool | None = None
    ) -> dict:
        """Validate if order can be placed in current market session."""
        from ..tools.extended_hours_orders import validate_extended_hours_order

        return await validate_extended_hours_order(symbol, order_type, extended_hours)

    @mcp.tool()
    async def place_extended_hours_order(
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "limit",
        limit_price: float | None = None,
        extended_hours: bool | None = None,
        time_in_force: str = "day",
    ) -> str:
        """Place order with automatic extended hours detection."""
        from ..tools.extended_hours_orders import place_extended_hours_order

        return await place_extended_hours_order(
            symbol, side, quantity, order_type, limit_price, extended_hours, time_in_force
        )

    @mcp.tool()
    async def get_extended_hours_info() -> str:
        """Get comprehensive information about extended hours trading."""
        from ..tools.extended_hours_orders import get_extended_hours_info

        return await get_extended_hours_info()


def register_plotting_tools(mcp):
    """Register technical plotting tools."""

    @mcp.tool()
    async def generate_advanced_technical_plots(
        symbols: str,
        timeframe: str = "1Min",
        days: int = 1,
        window_len: int = None,
        lookahead: int = None,
        plot_mode: str = "single",
        display_plots: bool = False,
        dpi: int = 100,
    ) -> str:
        """
        Generate professional peak/trough analysis plots with zero-phase filtering.

        Creates publication-quality technical analysis plots showing:
        - Original and filtered price data using Hanning window
        - Peak/trough detection with actual price annotations
        - Multiple plotting modes: single, combined, overlay
        - Professional styling with auto-positioned legends
        - Signal summary tables with latest trading levels
        - Precise support/resistance levels for trading

        This tool will use the global config parameters when window_len/lookahead are not specified:
        - window_len defaults to global_config.technical_analysis.hanning_window_samples
        - lookahead defaults to global_config.technical_analysis.peak_trough_lookahead

        Perfect for visual technical analysis and identifying entry/exit levels.
        Integrates seamlessly with other workflow tools for complete analysis.

        Args:
            symbols: Comma-separated symbols (e.g., "AAPL,MSFT,TSLA")
            timeframe: Bar timeframe ("1Min", "5Min", "15Min", "30Min", "1Hour", "1Day")
            days: Number of trading days to analyze (1-30 for intraday, 1-2520 for daily)
            window_len: Hanning filter window length (3-101, must be odd). Uses global config if None.
            lookahead: Peak detection sensitivity (1-50, higher=more sensitive). Uses global config if None.
            plot_mode: "single", "combined", "overlay", or "all"
            display_plots: Show plots via ImageMagick display (default: False)
            dpi: Plot resolution/quality (default: 100)

        Returns:
            Comprehensive analysis with plot locations and trading signals
        """
        # Use fixed version directly
        from ..tools.advanced_plotting_tool import generate_peak_trough_plots_fixed

        return await generate_peak_trough_plots_fixed(
            symbols,
            timeframe,
            days,
            window_len,
            lookahead,
            plot_mode,
            True,  # save_plots
            display_plots,  # display_plots
            dpi,
        )

    @mcp.tool()
    async def generate_stock_plot(
        symbols: str,
        timeframe: str = "1Min",
        days: int = 1,
        window: int = None,
        lookahead: int = None,
        feed: str = "sip",
        no_plot: bool = False,
        verbose: bool = False,
    ) -> str:
        """
        Generate stock analysis plots using the plot.py script with ImageMagick display.

        This tool integrates the standalone plot.py script as an MCP tool, providing
        professional technical analysis plots with automatic ImageMagick display.

        This tool will use the global config parameters when window/lookahead are not specified:
        - window defaults to global_config.technical_analysis.hanning_window_samples
        - lookahead defaults to global_config.technical_analysis.peak_trough_lookahead

        Features:
        - Zero-phase Hanning filtering for noise reduction
        - Peak/trough detection with precise price annotations
        - Real-time market data from Alpaca API
        - Professional styling with NYC/EDT timezone
        - Automatic plot display via ImageMagick
        - Multi-symbol support in single API call

        Args:
            symbols: Comma-separated stock symbols (e.g., "AAPL,MSFT,TSLA")
            timeframe: Bar timeframe - "1Min", "5Min", "15Min", "30Min", "1Hour", "1Day"
            days: Number of trading days to analyze (1-30 for intraday, 1-2520 for daily)
            window: Hanning filter window length (3-101, must be odd). Uses global config if None.
            lookahead: Peak detection sensitivity (1-50, higher = more sensitive). Uses global config if None.
            feed: Data feed - "sip", "iex", or "otc"
            no_plot: Skip plotting and only show analysis (useful for batch processing)
            verbose: Enable detailed logging output

        Returns:
            Comprehensive analysis results with plot locations and trading signals
        """
        from ..tools.plot_py_tool import generate_stock_plot as plot_py_func

        return await plot_py_func(
            symbols, timeframe, days, window, lookahead, feed, no_plot, verbose
        )


def register_help_tools(mcp):
    """Register help system tools."""

    def get_safe_help_system():
        """Get help system, initializing if needed."""
        try:
            return help_system.get_help_system()
        except RuntimeError:
            # Help system not initialized, initialize it now
            help_system.initialize_help_system(mcp)
            return help_system.get_help_system()

    @mcp.tool()
    async def get_tool_help(tool_name: str) -> str:
        """
        Get comprehensive help for a specific tool (like --help in CLI tools).

        Args:
            tool_name: Name of the tool to get help for

        Returns:
            Detailed help including parameters, examples, and related tools

        Examples:
            get_tool_help("get_stock_quote")
            get_tool_help("scan_day_trading_opportunities")
        """
        return get_safe_help_system().get_tool_help(tool_name)

    @mcp.tool()
    async def get_all_tools_help() -> str:
        """
        Get help for all available tools organized by category.

        Returns:
            Comprehensive listing of all tools with descriptions
        """
        return get_safe_help_system().get_all_tools_help()

    @mcp.tool()
    async def get_prompt_help(prompt_name: str) -> str:
        """
        Get comprehensive help for a specific workflow/prompt.

        Args:
            prompt_name: Name of the prompt/workflow to get help for

        Returns:
            Detailed help including parameters and usage examples

        Examples:
            get_prompt_help("master_scanning_workflow")
            get_prompt_help("account_analysis")
        """
        return get_safe_help_system().get_prompt_help(prompt_name)

    @mcp.tool()
    async def get_all_prompts_help() -> str:
        """
        Get help for all available workflows/prompts.

        Returns:
            Comprehensive listing of all workflows with descriptions
        """
        return get_safe_help_system().get_all_prompts_help()

    @mcp.tool()
    async def search_tools(query: str) -> str:
        """
        Search tools by name, description, or category.

        Args:
            query: Search term to find matching tools

        Returns:
            List of tools matching the search query

        Examples:
            search_tools("order")
            search_tools("streaming")
            search_tools("scanner")
        """
        return get_safe_help_system().search_tools(query)

    @mcp.tool()
    async def get_mcp_tool_schema(tool_name: str) -> dict:
        """
        Get MCP-compliant tool schema for a specific tool.

        Args:
            tool_name: Name of the tool to get schema for

        Returns:
            MCP-compliant tool schema with inputSchema and annotations

        Examples:
            get_mcp_tool_schema("get_stock_quote")
            get_mcp_tool_schema("place_stock_order")
        """
        return get_safe_help_system().get_mcp_tool_schema(tool_name) or {}

    @mcp.tool()
    async def export_mcp_tools_list() -> dict:
        """
        Export all tools in MCP tools/list response format.

        Returns:
            Complete MCP tools/list response with all tool schemas

        This provides the exact format that MCP clients expect for tool discovery.
        """
        return get_safe_help_system().export_mcp_tools_list()


def register_debug_tools(mcp):
    """Register debug and testing tools."""

    @mcp.tool()
    async def debug_mcp_tools() -> str:
        """Debug function to verify MCP tool registration for Claude Code compatibility."""
        import json

        # Get all registered tools from tool manager
        tool_manager = getattr(mcp, "_tool_manager", None)
        tools_dict = getattr(tool_manager, "_tools", {}) if tool_manager else {}

        tools_info = {
            "total_tools": len(tools_dict),
            "tool_names": (
                list(tools_dict.keys())[:10] if tools_dict else []
            ),  # First 10 for brevity
            "sample_tool_schema": None,
            "claude_code_mode": getattr(mcp, "_claude_code_mode", False),
            "server_name": getattr(mcp, "name", "unknown"),
            "server_version": getattr(mcp, "version", "unknown"),
            "has_tool_manager": tool_manager is not None,
            "tool_manager_type": str(type(tool_manager)) if tool_manager else None,
        }

        # Get a sample tool schema for verification
        if tools_dict:
            sample_name = list(tools_dict.keys())[0]
            sample_tool = tools_dict[sample_name]
            if hasattr(sample_tool, "get_schema"):
                try:
                    tools_info["sample_tool_schema"] = sample_tool.get_schema()
                except Exception as e:
                    tools_info["sample_tool_schema_error"] = str(e)
            else:
                tools_info["sample_tool_info"] = {
                    "name": sample_name,
                    "type": str(type(sample_tool)),
                    "has_schema": hasattr(sample_tool, "get_schema"),
                    "callable": callable(sample_tool),
                }

        return json.dumps(tools_info, indent=2)

    @mcp.tool()
    async def cc_debug_tools() -> str:
        """Claude Code debug: List all registered tools"""
        import json

        tool_manager = getattr(mcp, "_tool_manager", None)
        tools_dict = getattr(tool_manager, "_tools", {}) if tool_manager else {}

        tools_info = {
            "server_name": getattr(mcp, "name", "alpaca-trading"),
            "total_tools": len(tools_dict),
            "tool_names": list(tools_dict.keys()),
            "server_connected": True,
            "claude_code_compatible": True,
            "fastmcp_version": getattr(mcp, "version", "unknown"),
        }

        return json.dumps(tools_info, indent=2)

    @mcp.tool()
    async def cc_force_refresh() -> str:
        """Claude Code: Force tool list refresh"""
        return "Tool list refresh requested - restart Claude Code to see updated tools"

    @mcp.tool()
    async def cc_test_simple() -> str:
        """Simple test tool for Claude Code"""
        return "✅ Claude Code can execute MCP tools successfully!"

    @mcp.tool()
    async def health_check() -> str:
        """Quick server health and status check."""
        try:
            health = await server_health.get_server_health()
            session = await session_status.get_session_status()

            status_emoji = (
                "🟢"
                if health.get("server_status") == "healthy"
                else "🟡" if health.get("server_status") == "degraded" else "🔴"
            )
            market_emoji = "🔔" if session.get("alpaca_market_open") else "🔕"

            return f"""
{status_emoji} Server Status: {health.get("server_status", "unknown").upper()}
{market_emoji} Market: {session.get("session_description", "unknown")}

Quick Stats:
• Memory: {health.get("process_metrics", {}).get("memory_usage_mb", 0):.1f} MB
• CPU: {health.get("process_metrics", {}).get("cpu_usage_percent", 0):.1f}%
• Uptime: {health.get("uptime_formatted", "unknown")}
• APIs: {health.get("connection_health", {}).get("healthy_connections", 0)}/{health.get("connection_health", {}).get("total_connections", 0)}

Market Session:
• Phase: {session.get("session_phase", "unknown")}
• Extended Hours: {session.get("is_extended_hours", False)}
• Next: {session.get("next_event", "unknown")} in {session.get("time_to_next_formatted", "unknown")}

Capabilities: {health.get("capabilities", {}).get("tools", 0)} tools, {health.get("capabilities", {}).get("resources", 0)} resources
            """

        except Exception as e:
            return f"❌ Health check failed: {str(e)}"


def register_cleanup_tools(mcp):
    """Register cleanup and maintenance tools."""

    @mcp.tool()
    async def cleanup(
        remove_logs: bool = True,
        remove_caches: bool = True,
        remove_backups: bool = True,
        dry_run: bool = False,
    ) -> str:
        """
        Clean up unnecessary temporary files from the MCP server.

        This tool removes files that are NOT necessary for MCP server operations:
        - Log files (*.log)
        - Cache directories (.mypy_cache, .pytest_cache, __pycache__)
        - Backup files (*.backup, *.bak, *~)
        - PID files (*.pid)
        - Temporary files (*.tmp, *.temp)

        PRESERVES essential files:
        - State files in monitoring_data/
        - Alert history in monitoring_data/alerts/
        - Configuration files
        - All source code and tools

        Args:
            remove_logs: Remove all log files (default: True)
            remove_caches: Remove cache directories (default: True)
            remove_backups: Remove backup files (default: True)
            dry_run: Only show what would be deleted without actually deleting (default: False)

        Returns:
            Detailed report of cleanup operations
        """
        return await cleanup_server(remove_logs, remove_caches, remove_backups, dry_run)

    @mcp.tool()
    async def list_cleanup_candidates() -> str:
        """
        List all files that would be cleaned up without deleting them.

        This is a safe way to see what the cleanup tool would remove.
        Equivalent to running cleanup(dry_run=True).

        Returns:
            Report of files that can be cleaned up
        """
        return await list_cleanup_candidates()


def register_all_tools(mcp, DEFAULT_WINDOW_LEN):
    """Register all tools with the MCP server."""
    register_account_tools(mcp)
    register_market_data_tools(mcp)
    register_market_info_tools(mcp)
    register_options_tools(mcp)
    register_technical_analysis_tools(mcp, DEFAULT_WINDOW_LEN)
    register_scanner_tools(mcp)
    register_watchlist_tools(mcp)
    register_asset_tools(mcp)
    register_corporate_action_tools(mcp)
    register_streaming_tools(mcp)
    register_order_tools(mcp)
    register_monitoring_tools(mcp)
    register_fastapi_monitoring_tools(mcp)
    register_extended_hours_tools(mcp)
    register_plotting_tools(mcp)
    register_help_tools(mcp)
    register_debug_tools(mcp)
    register_cleanup_tools(mcp)
