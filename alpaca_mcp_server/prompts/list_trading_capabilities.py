"""
Alpaca Trading MCP Server - Enhanced Discovery Prompt
Provides comprehensive overview with guided workflows and next-step suggestions.
Following IndyDevDan's agentic MCP server pattern.
"""


async def list_trading_capabilities() -> str:
    """
    Prime the agent with everything available in the Alpaca Trading MCP server.
    Returns comprehensive overview of tools, resources, and workflows with guided next steps.
    """

    return """
🚀 ALPACA TRADING MCP SERVER - AGENTIC TRADING ASSISTANT

=== QUICK START WORKFLOWS ===
Get started with these guided trading experiences:

🔹 startup() - Initialize complete trading session with market analysis
🔹 scan() - Discover day trading opportunities with momentum analysis
🔹 account_analysis() - Portfolio health check with risk assessment
🔹 market_analysis(["SYMBOL"]) - Deep market analysis for specific stocks
🔹 position_management() - Strategic position review and optimization

=== ADVANCED AGENTIC WORKFLOWS ===
Professional-grade multi-tool orchestration:

🚀 master_scanning_workflow() - Comprehensive market scanning using ALL scanner tools
🔬 pro_technical_workflow(symbol) - Professional algorithmic analysis with peak/trough detection
⏰ market_session_workflow(session) - Complete session strategy with timing analysis
🎯 day_trading_workflow(symbol) - Complete setup analysis for any symbol
📊 Multi-scanner synthesis with actionable opportunities
⚡ Real-time streaming analytics and momentum detection

=== COMPREHENSIVE TOOL CATEGORIES ===

📊 ACCOUNT & PORTFOLIO (9 tools):
  • get_account_info() - Balance, buying power, account status
  • get_positions() - All open positions with live P&L
  • get_open_position(symbol) - Detailed position analysis
  • close_position(symbol, qty, percentage) - Strategic position closing
  • close_all_positions(cancel_orders) - Emergency liquidation
  • resource_account_status() - Real-time account health monitoring
  • resource_current_positions() - Live position tracking
  • resource_intraday_pnl() - Today's trading performance
  • health_check() - Quick server and market status

📈 MARKET DATA & QUOTES (8 tools):
  • get_stock_quote(symbol) - Real-time bid/ask/last prices
  • get_stock_snapshots(symbols) - Comprehensive market snapshots
  • get_stock_bars(symbol, days) - Historical OHLCV analysis
  • get_stock_bars_intraday(symbol, timeframe) - Professional intraday data
  • get_stock_latest_trade(symbol) - Most recent execution
  • get_stock_latest_bar(symbol) - Latest minute bar
  • get_market_clock() - Trading hours and market status
  • get_extended_market_clock() - Pre/post market sessions

🔍 ADVANCED SCANNERS & ANALYSIS (7 tools):
  • scan_day_trading_opportunities() - Find high-activity momentum plays
  • scan_explosive_momentum() - Detect extreme percentage movers
  • get_stock_peak_trough_analysis() - Technical support/resistance levels
  • generate_advanced_technical_plots() - Publication-quality plots with peak/trough detection
  • scan_after_hours_opportunities() - Extended hours momentum
  • start_differential_trade_scanner() - Background continuous monitoring
  • get_enhanced_streaming_analytics() - Real-time VWAP and flow analysis

💰 ORDER EXECUTION (8 tools):
  • place_stock_order() - Any order type (market, limit, stop, trail)
  • place_extended_hours_order() - Pre/post market trading
  • place_option_market_order() - Single and multi-leg strategies
  • get_orders(status, limit) - Order history and tracking
  • cancel_order_by_id(order_id) - Cancel specific orders
  • cancel_all_orders() - Cancel all pending orders
  • validate_extended_hours_order() - Order validation
  • get_extended_hours_info() - Extended trading rules

📡 REAL-TIME STREAMING (7 tools):
  • start_global_stock_stream() - Live quotes, trades, bars
  • add_symbols_to_stock_stream() - Expand streaming coverage
  • get_stock_stream_data() - Extract streaming data for analysis
  • list_active_stock_streams() - Monitor active subscriptions
  • get_stock_stream_buffer_stats() - Performance monitoring
  • stop_global_stock_stream() - Graceful shutdown
  • clear_stock_stream_buffers() - Memory management

📊 OPTIONS TRADING (3 tools):
  • get_option_contracts() - Options chain with strike/expiration filters
  • get_option_latest_quote() - Real-time options quotes
  • get_option_snapshot() - Greeks and volatility analysis

🏢 ASSETS & CORPORATE ACTIONS (4 tools):
  • get_all_assets() - Universe of tradeable symbols
  • get_asset_info(symbol) - Detailed asset information
  • get_corporate_announcements() - Dividends, splits, earnings
  • create_watchlist() / get_watchlists() - Portfolio organization

=== REAL-TIME RESOURCES ===
Dynamic context for intelligent decision making:

📊 account://status - Live account health and capacity
📈 positions://current - Real-time position tracking
🌍 market://conditions - Market status and volatility
💼 portfolio://performance - P&L and performance metrics
⚖️ portfolio://risk - Risk exposure and concentration
📡 streams://status - Streaming data health
📊 market://momentum - SPY momentum indicators

=== GETTING STARTED ===

🎯 FOR NEW TRADERS:
1️⃣ Run startup() to initialize your complete trading environment
2️⃣ Execute account_analysis() to understand your current portfolio
3️⃣ Use scan() to discover trading opportunities
4️⃣ Try market_analysis(["AAPL", "MSFT"]) for specific stock analysis

🎯 FOR ACTIVE DAY TRADERS:
1️⃣ startup() - Complete session initialization with market analysis
2️⃣ scan_day_trading_opportunities() - Find high-activity momentum
3️⃣ get_stock_peak_trough_analysis("SYMBOL") - Technical entry/exit levels
4️⃣ start_global_stock_stream(["SYMBOLS"]) - Live data feeds

🎯 FOR OPTIONS TRADERS:
1️⃣ account_analysis() - Verify account permissions and capital
2️⃣ get_option_contracts("SYMBOL") - Explore available chains
3️⃣ get_option_snapshot("OPTION_SYMBOL") - Greeks and volatility
4️⃣ place_option_market_order() - Execute strategies

=== NEXT STEPS ===
Ready to start trading with AI assistance:

- BEGIN: startup() for complete session initialization
- DISCOVER: scan() for momentum opportunities
- ANALYZE: market_analysis(["YOUR_SYMBOLS"]) for deep insights
- MONITOR: health_check() for quick status updates

=== SAFETY FEATURES ===
✅ Paper trading mode available (set ALPACA_BASE_URL)
✅ Real-time risk monitoring and position tracking
✅ Extended hours validation and protection
✅ Comprehensive order validation and error handling
✅ Live market status awareness

⚠️  IMPORTANT: This assistant can execute real trades. Always validate
recommendations and position sizes before execution.

🎯 Your Alpaca MCP server is ready for agentic trading workflows!
"""


# Export for MCP server registration
__all__ = ["list_trading_capabilities"]
