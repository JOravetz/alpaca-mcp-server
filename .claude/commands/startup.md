# Day Trading Startup: Parallel Execution Command

**COMMAND:** `/startup` - Executes all day trading startup checks in parallel for maximum speed

**TRADING TYPE: Day trading extremely volatile stocks (+20% to +100%+ moves)**  
**TARGET: Penny stocks ($0.01-$5.00) and explosive momentum plays**  
**STRATEGY: Fast execution, limit orders only, never sell for loss**

## CORE DAY TRADING RULES (NON-NEGOTIABLE)

### Order Management Rules
- ❌ **NEVER use market orders** (unless specifically instructed)
- ❌ **NEVER sell for a loss** (unless specifically instructed)  
- ✅ **ALWAYS use limit orders** for precise execution
- ✅ **Use 4 decimal places** for penny stocks ($0.0118 format)
- ✅ **Minimum 1,000 trades/minute** for liquidity requirements

### Speed Requirements
- ⚡ **React within 1-2 seconds** when profit appears
- ⚡ **Monitor streaming data** every 1-3 seconds during active trades
- ⚡ **Check order fills immediately** after placement
- ⚡ **Document entry price** immediately after fill verification

### Post-Order Fill Procedure (MANDATORY)
After ANY order fills:
1. `get_orders(status="all", limit=5)` - **Verify actual fill price**
2. `get_positions()` - **Confirm position and entry price**  
3. **Write down and verify fill price** - never rely on memory
4. Start appropriate monitoring (streaming for profits, quotes for losses)

---

## STARTUP EXECUTION: ALL CHECKS IN PARALLEL + SEQUENTIAL NEWS

When `/startup` is executed, Claude will automatically run all these tools concurrently for maximum speed, followed by news analysis:

**PARALLEL BATCH 1: Core System Health (4 tools)**
- `health_check()` - Overall system health
- `resource_server_health()` - Server performance metrics  
- `resource_api_status()` - API connectivity status
- `resource_session_status()` - Current session details

**PARALLEL BATCH 2: Market Status (4 tools)**
- `get_market_clock()` - Basic market status
- `get_extended_market_clock()` - Pre/post market details
- `resource_market_conditions()` - Overall market sentiment
- `resource_market_momentum()` - Market direction analysis

**PARALLEL BATCH 3: Account & Positions (6 tools)**
- `get_account_info()` - Buying power and restrictions
- `resource_account_status()` - Real-time account health
- `get_positions()` - Check for any open positions
- `resource_current_positions()` - Live P&L tracking
- `get_orders(status="open")` - Check for stale orders
- `resource_intraday_pnl()` - Today's performance tracking

**PARALLEL BATCH 4: Data Quality & Streaming (3 tools)**
- `resource_data_quality()` - Feed latency and quality
- `get_stock_stream_buffer_stats()` - Streaming infrastructure
- `list_active_stock_streams()` - Check existing streams
- `clear_stock_stream_buffers()` - Clear old streaming data

**PARALLEL BATCH 5: Trading Scanners (3 tools)**
- `scan_day_trading_opportunities(symbol_file="/home/jjoravet/alpaca-mcp-server-enhanced/data/combined.lis")` - Active stock scanner
- `scan_explosive_momentum()` - High-volatility scanner
- `./stock_analyzer_json` - High-liquidity JSON scanner

**SEQUENTIAL STEP: News Analysis (After C scanner completes)**
- Parse output from `stock_analyzer_json` to extract top symbols
- Run `uv run ./external_tools/news_scrapers/yf_rss.py [SYMBOLS]` on high-liquidity stocks
- Analyze news sentiment and catalysts for identified opportunities

**CLAUDE EXECUTION INSTRUCTIONS:**
When user runs `/startup`, Claude MUST:
1. **Acknowledge startup command** immediately
2. **Execute ALL tools in a SINGLE parallel call** - Use one message with multiple tool invocations:
   ```
   Execute these tools concurrently in ONE message:
   - mcp__alpaca-trading__health_check
   - mcp__alpaca-trading__resource_server_health
   - mcp__alpaca-trading__resource_api_status
   - mcp__alpaca-trading__resource_session_status
   - mcp__alpaca-trading__get_market_clock
   - mcp__alpaca-trading__get_extended_market_clock
   - mcp__alpaca-trading__resource_market_conditions
   - mcp__alpaca-trading__resource_market_momentum
   - mcp__alpaca-trading__get_account_info
   - mcp__alpaca-trading__resource_account_status
   - mcp__alpaca-trading__get_positions
   - mcp__alpaca-trading__resource_current_positions
   - mcp__alpaca-trading__get_orders(status="open")
   - mcp__alpaca-trading__resource_intraday_pnl
   - mcp__alpaca-trading__resource_data_quality
   - mcp__alpaca-trading__get_stock_stream_buffer_stats
   - mcp__alpaca-trading__list_active_stock_streams
   - mcp__alpaca-trading__clear_stock_stream_buffers
   - mcp__alpaca-trading__scan_day_trading_opportunities(symbol_file="/home/jjoravet/alpaca-mcp-server-enhanced/data/combined.lis")
   - mcp__alpaca-trading__scan_explosive_momentum
   - Execute: ./stock_analyzer_json
   ```
3. **Parse stock_analyzer_json output** to extract top liquid symbols
4. **Run news scraper** on identified stocks:
   ```
   uv run ./external_tools/news_scrapers/yf_rss.py SYMBOL1 SYMBOL2 SYMBOL3 ...
   ```
5. **Generate comprehensive status report** with all results including news
6. **Identify top trading opportunities** combining liquidity, momentum, and news catalysts
7. **Confirm all systems green for trading**

**CRITICAL:** 
- NEVER execute initial tools sequentially - ALWAYS use parallel execution for maximum speed
- News scraper runs AFTER C scanner completes to analyze identified opportunities

---

## READY TO TRADE VERIFICATION

### All Systems Green Checklist:
- [ ] ✅ Server health: All systems operational
- [ ] ✅ Market status: Trading session confirmed
- [ ] ✅ Account verified: Adequate buying power, no restrictions
- [ ] ✅ Data feeds: Low latency, high quality streaming
- [ ] ✅ Tools tested: Scanners and analysis tools responsive
- [ ] ✅ No stale positions/orders: Clean starting state
- [ ] ✅ High-liquidity stocks identified: JSON scanner results parsed
- [ ] ✅ News catalysts analyzed: RSS feeds checked for momentum drivers
- [ ] ✅ Risk rules reviewed: Position sizing and stop procedures

### Day Trading Flow Ready:
1. **Scanner** → Opportunities identified by scanners during startup
2. **Liquidity** → Verified with `stock_analyzer_json` output (1000+ trades/min)
3. **News Check** → Catalysts confirmed with `yf_rss.py` output
4. **Analysis** → Run `get_stock_peak_trough_analysis("SYMBOL")` for chosen opportunities
5. **Streaming** → Start `start_global_stock_stream()` for real-time monitoring
6. **Execute** → Place limit orders with `place_stock_order()`
7. **Monitor** → Check fills and track with streaming data
8. **Exit** → Take profits aggressively, never sell for loss

---

## EMERGENCY PROCEDURES

**Market Orders Emergency:**
- Only use if specifically instructed
- Speed over price when explicitly told to exit

**Stop All Trading:**
- `cancel_all_orders()` - Cancel all pending orders
- `close_all_positions()` - Emergency position exit
- `stop_global_stock_stream()` - Stop streaming data

**Declining Peaks Emergency:**
- If trapped in falling stock, use averaging down strategy
- Documented in DECLINING_PEAKS_STRATEGY.md

---

## STARTUP OUTPUT FORMAT

After running `/startup`, Claude will provide a structured report:

```
🚀 DAY TRADING STARTUP INITIATED
================================

📊 SYSTEM HEALTH
- API Status: [OPERATIONAL/DEGRADED/DOWN]
- Server Health: [Response Time]
- Session Valid: [YES/NO]
- Data Quality: [Latency/Quality Metrics]

💹 MARKET STATUS
- Market: [OPEN/CLOSED/PRE/POST]
- Trading Hours: [Current Session]
- Market Momentum: [Bullish/Bearish/Neutral]
- Market Conditions: [Volatility/Volume]

💰 ACCOUNT STATUS
- Buying Power: $[Amount]
- Day Trading Power: $[Amount]
- Open Positions: [Count]
- Today's P&L: $[Amount]
- Pattern Day Trader: [YES/NO]

🔥 TOP OPPORTUNITIES (WITH NEWS)
[High-liquidity stocks from stock_analyzer_json + news]
1. [Symbol] - [Trades/Min] - [Price] - [Volume]
   📰 News: [Latest headline/catalyst]
2. [Symbol] - [Trades/Min] - [Price] - [Volume]
   📰 News: [Latest headline/catalyst]
3. [Symbol] - [Trades/Min] - [Price] - [Volume]
   📰 News: [Latest headline/catalyst]

[Scanner Results]
- Momentum Plays: [List top 3 with news status]
- Day Trading Ops: [List top 3 with news status]

📰 NEWS ANALYSIS SUMMARY
- Stocks with positive catalysts: [List]
- Stocks with breaking news: [List]
- Stocks to avoid (negative news): [List]

✅ READY TO TRADE: [YES/NO]
[Any warnings or issues to address]
```

---

**EXECUTION FLOW DIAGRAM:**
```
/startup Command
    ↓
[PARALLEL EXECUTION - 21 system checks + 3 scanners]
    ↓
Parse stock_analyzer_json output → Extract symbols
    ↓
[SEQUENTIAL - News Analysis]
Run uv run ./external_tools/news_scrapers/yf_rss.py on symbols
    ↓
[FINAL REPORT]
Combine all data into comprehensive trading dashboard
```

---

**🚀 ONLY BEGIN DAY TRADING WHEN ALL ITEMS ARE CHECKED ✅**

**Remember: Speed beats perfection. Take profits aggressively. Never sell for loss.**

Use `/startup` to access this complete parallel system check with news analysis before every trading session.
