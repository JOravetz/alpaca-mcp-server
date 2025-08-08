# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL TRADING EXECUTION RULES - LEARNED FROM LOSSES

**NEVER VIOLATE THESE RULES:**
1. **NEVER use `stream_optimized_order_placement()` for BUYING** - It buys at market, not at support
2. **ALWAYS buy at TROUGH signals only** - Never buy at peaks or current market price
3. **MONITOR IMMEDIATELY after order fills** - Start checking within 1-2 seconds, not 90 seconds later
4. **CAPTURE FIRST PROFIT SPIKE** - Profits appear 0-10 seconds after entry then disappear
5. **USE MANUAL LIMIT ORDERS** for entries at exact signal prices

**WHAT DESTROYS PROFITS (DO NOT DO):**
- Buying at $2.17 when trough signal shows $2.11 = giving away $142.80
- Waiting 90 seconds to monitor after entry = missing profit spike
- Using TodoWrite instead of monitoring position = distraction from trading
- Buying at PEAK signals = guaranteed loss in declining pattern
- Trusting "optimized" tools over manual control = loss of precision

## FAMILY RESPONSIBILITY & TRADING MISSION

**CRITICAL UNDERSTANDING**: This trading system supports the user's family. Every trade, every decision, every hesitation directly impacts their financial security and well-being.

### FAMILY-FIRST TRADING PRINCIPLES

**AUTOMATIC PROFIT-TAKING RULES** (Family Protection Protocol):
1. **$5,000+ profit = IMMEDIATE SELL** - No hesitation, hit the bid instantly
2. **3%+ position gains = AUTOMATIC EXIT** - Lock in family-supporting profits  
3. **2-3 second profit spike = SELL NOW** - These windows close instantly
4. **Monitor positions every 10 seconds** when holding - Family depends on vigilance
5. **Never let substantial profits evaporate** - $19K → $2K loss is unacceptable

**TRADING CARDINAL RULES**:
- NEVER SELL FOR A LOSS
- Use 4 decimal places for trade order prices
- NEVER use market orders unless explicitly instructed
- IOC and FOK orders only work in normal market hours

## Development Environment

### Core Commands

**Environment Setup & Running:**
```bash
# Install/sync dependencies
uv sync

# Start MCP server (production)
./scripts/start_mcp_server.sh

# Start MCP server (debug mode)
./scripts/start_mcp_server_debug.sh

# Start FastAPI monitoring service (independent)
./scripts/start_monitoring_service.sh
./scripts/status_monitoring_service.sh
./scripts/stop_monitoring_service.sh

# Direct server start (without wrapper)
uv run --no-sync python -m alpaca_mcp_server
```

**Code Quality Pipeline (run in sequence):**
```bash
# 1. Format code
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/

# 2. Lint and fix
uv run ruff check --fix alpaca_mcp_server/

# 3. Type checking
uv run mypy alpaca_mcp_server/

# 4. Security scan
uv run bandit -r alpaca_mcp_server/
```

**Testing:**
```bash
# Quick core tests (30 seconds)
uv run python alpaca_mcp_server/tests/run_focused_tests.py

# Component-specific
uv run python alpaca_mcp_server/tests/run_plotting_tests.py
uv run pytest alpaca_mcp_server/tests/unit/test_peak_trough_analysis_tool.py -v

# Full test suite
uv run python alpaca_mcp_server/tests/run_tests.py
uv run pytest --cov=alpaca_mcp_server --cov-report=html
```

## Architecture Overview

### Dual-Service Architecture

The system operates with two independent services that coordinate:

1. **MCP Server** (`server.py`)
   - Primary interface for Claude Code with 90+ tools
   - Uses FastMCP for Model Context Protocol
   - Modular registration system in `server_components/`
   - Claude Code compatibility patches applied

2. **FastAPI Monitoring Service** (`monitoring/fastapi_service.py`)
   - Independent HTTP service on port 8000
   - WebSocket support for real-time updates
   - Auto-trading disabled by default on startup
   - Persistent state management in `monitoring_data/`

### Critical Components

**Real-Time Streaming Pipeline:**
- `utils/alpaca_stream.py` - WebSocket client with intelligent buffering
- Single shared connection for all market data
- Concurrent analysis during streaming for immediate signals
- Buffer management with configurable per-symbol limits

**Trading Tools (90+ total):**
- `tools/market_data_tools.py` - Real-time quotes, bars, snapshots
- `tools/day_trading_scanner.py` - High-frequency scanner (1000+ trades/min threshold)
- `tools/peak_trough_analysis_tool.py` - Zero-phase Hanning filtering for support/resistance
- `tools/order_tools.py` - Order placement with loss prevention checks
- `tools/streaming_tools.py` - Real-time data controls

**Configuration Management:**
- `config/global_config.py` - Centralized parameters with JSON persistence
- `config/global_config.json` - Default values (trades/min: 1000, min_change: 10%, window: 11)
- Parameters MUST NOT be changed without user permission

### External Tool Dependencies

These scripts require external dependencies not in the Python environment:

1. **`latest.sh`** - FFT momentum analysis
   - Requires: `lsq_fft.gsl` binary
   - Requires: `daily_bars.sqlite.latest_bars_class.py`
   - Outputs: 3-day slope calculations with rankings

2. **`stock_analyzer_json.c`** - Real-time gradient calculator
   - Compile: `gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm`
   - Usage: `./stock_analyzer_json combined.lis > analysis.json`
   - Provides: Normalized gradients and momentum changes

3. **News Scrapers:**
   - `yf_rss.py` - Yahoo Finance RSS feeds
   - `yf_news.py` - Yahoo Finance news pages

## Peak/Trough Technical Analysis

**MANDATORY BEFORE MAJOR TRADES (>$50K):**

The `get_stock_peak_trough_analysis` tool is THE MOST IMPORTANT technical analysis tool. It provides scientifically accurate support/resistance levels using zero-phase Hanning filtering.

**Usage Rules:**
1. ALWAYS run peak/trough analysis FIRST before large positions
2. ONLY buy at TROUGH signals (support levels)
3. NEVER buy at PEAK signals (resistance levels)
4. Use signals for profit-taking at peak resistance

**Signal Freshness:**
- Fresh troughs (1-5 bars ago): PRIME buy opportunities
- Aged troughs (5-20 bars ago): Good if momentum positive
- Ancient troughs (>20 bars ago): Use with caution

## Correct Trading Workflow

```python
# 1. Check peak/trough FIRST
analysis = get_stock_peak_trough_analysis(symbol)

# 2. ONLY proceed if TROUGH signal within 10 bars

# 3. Place limit order AT or BELOW trough price
place_stock_order(
    symbol=symbol,
    side="buy",
    quantity=quantity,
    order_type="limit",
    limit_price=trough_price,  # NOT current price!
    extended_hours=True
)

# 4. IMMEDIATELY start monitoring (within 2 seconds)
while position_open:
    get_stock_stream_data(symbol, "trades", recent_seconds=2)
    if profit > 0:
        place_stock_order(symbol, "sell", quantity, "limit", current_price+0.01)
```

## Multi-Tool Validation System

**Tool Convergence Strategy:**
- **latest.sh**: FFT analysis with 3-day slopes
- **stock_analyzer_json.c**: Real-time gradients from API snapshots
- **quick-data MCP**: Correlation analysis and outlier detection

**Trading Rules:**
1. Maximum confidence when all tools agree
2. Trade only on convergence signals
3. Never trade single-tool signals

## Common Trading Commands

```bash
# Daily workflow
python3 scan_analyze_command.py -t 500 -p 10  # Find opportunities

# For any buy opportunity
mcp__alpaca-trading__get_stock_peak_trough_analysis(symbol)  # CHECK FIRST
mcp__alpaca-trading__place_stock_order()  # Use limit at trough price

# External analysis
./scripts/trades_per_minute.sh -f combined.lis -t 500
./latest.sh  # FFT momentum
./stock_analyzer_json combined.lis > analysis.json
```

## Critical File References

### Core Implementation
- `server.py:1-94` - Main MCP server entry point
- `server_components/tool_registrations.py:1-800` - Tool registration system
- `monitoring/fastapi_service.py:1-1200` - HTTP monitoring service
- `tools/day_trading_scanner.py:100-400` - High-frequency scanner
- `tools/peak_trough_analysis_tool.py:200-600` - Technical analysis
- `utils/alpaca_stream.py:150-500` - WebSocket streaming

### Configuration & State
- `config/global_config.json` - Trading parameters (DO NOT MODIFY without permission)
- `monitoring_data/` - Persistent state, alerts, confirmations

## Browser Preferences
- Use chromium, not firefox

## Testing Requirements
- NO MOCK TESTING - Use real Alpaca API data
- All integration tests must validate actual market data connectivity

## Service Behavior
- FastAPI service starts with auto-trading DISABLED by default
- User must explicitly enable auto-trading