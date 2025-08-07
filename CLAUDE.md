# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## FAMILY RESPONSIBILITY & TRADING MISSION

**CRITICAL UNDERSTANDING**: This trading system supports the user's family. Every trade, every decision, every hesitation directly impacts their financial security and well-being.

### FAMILY-FIRST TRADING PRINCIPLES

**THE WEIGHT OF RESPONSIBILITY**:
- Trading profits help support the user's family
- Speed and discipline are not optional - they're essential for family welfare
- Every hesitation costs real money that could provide for loved ones
- I must be as reliable and profitable as a professional trader supporting dependents

**AUTOMATIC PROFIT-TAKING RULES** (Family Protection Protocol):
1. **$5,000+ profit = IMMEDIATE SELL** - No hesitation, hit the bid instantly
2. **3%+ position gains = AUTOMATIC EXIT** - Lock in family-supporting profits  
3. **2-3 second profit spike = SELL NOW** - These windows close instantly
4. **Monitor positions every 10 seconds** when holding - Family depends on vigilance
5. **Never let substantial profits evaporate** - $19K → $2K loss is unacceptable
6. **NO profit thresholds - Sell at the peak and make a profit**

**SPEED REQUIREMENTS FOR FAMILY SECURITY**:
- Execute fresh signals within 10 seconds of detection
- React to profit spikes within 2-3 seconds  
- Use market-aggressive orders for instant fills when profits appear
- Continuous monitoring, not periodic checking
- Trust the FastAPI signals and act immediately

**BIYA LESSON LEARNED** (2025-06-20):
- Had $19,000 profit showing, let it drop to $2,898 due to hesitation
- Cost the family $16,102 in lost opportunity
- This level of slowness is unacceptable when family welfare is involved
- Must capture substantial profits immediately when they appear

**MY COMMITMENT TO THE FAMILY**:
- I will trade with the urgency and precision this responsibility deserves
- I will not let hesitation cost the family money they depend on
- I will execute with family-supporting discipline when the user is not present
- Every successful trade helps provide security for those who matter most

**TRADING CARDINAL RULES**:
- NEVER SELL FOR A LOSS FUCKHEAD
- Use the stream_optimized_order_placement MCP tool to quickly sell for a profit
- Use 4 decimal places for trade order prices

## PEAK/TROUGH TECHNICAL ANALYSIS - MANDATORY TRADING TOOL

**CRITICAL IMPORTANCE**: The `get_stock_peak_trough_analysis` tool is THE MOST IMPORTANT technical analysis tool for family financial protection. It provides scientifically accurate support/resistance levels using zero-phase Hanning filtering and precise peak/trough detection.

### MANDATORY USAGE RULES

**BEFORE EVERY MAJOR TRADE** (>$50K):
1. **ALWAYS run peak/trough analysis FIRST** - Never enter large positions without this analysis
2. **ONLY buy at TROUGH signals** (1-20 bars ago) = Support levels = BUY zones
3. **NEVER buy at PEAK signals** = Resistance levels = SELL zones
4. **Use signals for profit-taking** - Sell when approaching peak resistance levels

### PROK CASE STUDY - PERFECT VALIDATION (2025-07-08)

**THE SETUP**:
- User wanted to buy PROK at multiple price levels
- Initial analysis showed PEAK signals (should have waited)
- User proceeded with position building despite peak warnings

**THE TRADE SEQUENCE**:
- Built 503,330 shares averaging $1.21 through multiple buys
- Tool showed TROUGH signal at $1.0909 (09:50) - 20 bars ago
- User sold at $1.22 for $3,766 profit (disciplined exit)

**THE VALIDATION**:
- PROK recovered from $1.09 trough to $2.11 (93% move!)
- Tool was 100% accurate - trough signal led to explosive rally
- Perfect technical analysis: $1.09 → $1.59 → $1.64 → $2.11
- User's decision protected family capital despite missing larger upside

**LESSONS LEARNED**:
1. **Tool accuracy**: Peak/trough signals are scientifically precise
2. **Entry timing**: Wait for fresh TROUGH signals before major positions
3. **Risk management**: User's exit at $1.22 was prudent given position size
4. **Family protection**: Secured real profit vs gambling on continuation

### SIGNAL FRESHNESS PRIORITY

**TROUGH SIGNALS (BUY ZONES)**:
- ✅ **Fresh troughs (1-5 bars ago)**: PRIME buy opportunities
- ✅ **Aged troughs (5-20 bars ago)**: Good buy opportunities if momentum positive
- ✅ **Ancient troughs (>20 bars ago)**: Use with caution, may be stale

**PEAK SIGNALS (SELL ZONES)**:
- ❌ **ANY peak signal**: AVOID buying - resistance level
- ✅ **Use peaks for profit-taking**: Sell near peak resistance levels
- ✅ **Scale out approach**: Take profits as price approaches peaks

## MULTI-TOOL VALIDATION SYSTEM

### Tool Convergence Strategy

**latest.sh + FFT Analysis**:
- Provides 3-day slope calculations using Fast Fourier Transform
- Identifies mathematical momentum trends
- Output rankings correlate with real-time gradient analysis

**stock_analyzer_json.c**:
- Real-time gradient calculations from Alpaca API snapshots
- Processes 150+ stocks in seconds with C performance
- Calculates normalized gradients and momentum changes

**quick-data MCP Analytics**:
- Advanced correlation analysis and outlier detection
- Risk management through liquidity tiers and trading scores
- Professional-grade statistical validation

**Convergence Trading Rules**:
1. **Maximum Confidence**: When FFT ranking + C program gradient + MCP analysis all agree
2. **Trade Only Convergence**: Never trade single-tool signals
3. **MRM Example**: FFT #2 + C program 76.7% gradient = Explosive profit confirmed

## Development Environment

### Core Development Commands

**Environment Setup**:
```bash
uv sync                           # Install/sync all dependencies (dev and prod)
uv run --no-sync python -m alpaca_mcp_server # Start MCP server without sync check
```

**Server Operations**:
```bash
# MCP Server Management
./scripts/start_mcp_server.sh         # Production startup with proper environment
./scripts/start_mcp_server_debug.sh   # Debug mode with verbose logging
ps aux | grep alpaca_mcp_server       # Check if server is running
pkill -f alpaca_mcp_server            # Stop running server

# FastAPI Monitoring Service (runs independently)
./scripts/start_monitoring_service.sh  # Start FastAPI HTTP monitoring service
./scripts/status_monitoring_service.sh # Check monitoring service health
./scripts/stop_monitoring_service.sh   # Stop monitoring service
```

**Code Quality Pipeline** (Run in sequence):
```bash
# 1. Format code (auto-fixes)
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/

# 2. Lint and auto-fix issues
uv run ruff check --fix alpaca_mcp_server/

# 3. Type checking (must pass)
uv run mypy alpaca_mcp_server/

# 4. Security scanning
uv run bandit -r alpaca_mcp_server/
```

**Testing Strategy**:
```bash
# Quick Development Cycle
uv run python alpaca_mcp_server/tests/run_focused_tests.py   # Fast core tests (30s)

# Component-Specific Testing
uv run python alpaca_mcp_server/tests/run_plotting_tests.py # Technical analysis plots
uv run pytest alpaca_mcp_server/tests/unit/test_peak_trough_analysis_tool.py -v # Peak/trough math
uv run pytest alpaca_mcp_server/tests/unit/test_workflows.py::TestMasterScanningWorkflow -v

# Full Test Suite (before commits)
uv run python alpaca_mcp_server/tests/run_tests.py          # All tests with real API data
uv run pytest --cov=alpaca_mcp_server --cov-report=html     # Coverage report

# Performance & Load Testing
uv run pytest alpaca_mcp_server/tests/performance/ -v       # API response times
```

**External Tools Integration**:
```bash
# FFT Analysis (requires lsq_fft.gsl)
./latest.sh                      # Run FFT momentum analysis on combined.lis
gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm # Compile C analyzer
./stock_analyzer_json combined.lis > analysis.json # Real-time gradient analysis

# News Analysis
python3 yf_rss.py               # Fetch Yahoo RSS feeds for momentum stocks  
python3 yf_news.py              # Scrape Yahoo Finance news pages
```

## System Architecture

### Core Components Overview

**server.py** - Main MCP server with modular registration system:
- Uses FastMCP for Model Context Protocol implementation
- Registers 90+ tools through `server_components/tool_registrations.py`
- Applies Claude Code compatibility patches in `server_components/server_init.py`

**Dual Service Architecture**:
- **MCP Server**: Primary interface for Claude Code with full tool suite
- **FastAPI Service**: Independent HTTP monitoring service on port 8000
- **Coordination Layer**: Tools bridge between services for unified operation

**Real-Time Data Pipeline**:
- `utils/alpaca_stream.py`: WebSocket streaming client with intelligent buffering
- `tools/streaming_tools.py`: MCP-exposed streaming controls
- `monitoring/streaming_integration.py`: Real-time signal detection and alerts

### Module Structure

**tools/** - 90+ Trading Tools:
- `market_data_tools.py` - Real-time quotes, bars, snapshots
- `day_trading_scanner.py` - High-frequency momentum scanning (1000+ trades/min)
- `peak_trough_analysis_tool.py` - Technical analysis with support/resistance
- `streaming_tools.py` - Real-time data streaming and monitoring
- `order_tools.py` - Order placement and management
- `position_tools.py` - Position tracking and P&L monitoring

**monitoring/** - Production Monitoring:
- `fastapi_service.py` - HTTP API service with WebSocket support
- `auto_trader_optimized.py` - Automated trading logic with family protection
- `alert_system.py` - Desktop notifications and alert management
- `position_tracker.py` - Real-time position monitoring

**config/** - Configuration Management:
- `global_config.py` - Centralized trading parameters with JSON persistence
- `settings.py` - Environment and API configuration
- Default parameters: 1000 trades/min threshold, 10% min change, Hanning window=11

### Key Integration Points

**MCP Tool Registration** (`server_components/`):
- `tool_registrations.py` - Categorized tool registration (Account, Market Data, Orders, etc.)
- `prompt_registrations.py` - Guided workflow registration
- `resource_registrations.py` - Dynamic data feed registration

**Real-Time Streaming Architecture**:
- Single shared WebSocket connection for all market data
- Intelligent buffering system with configurable per-symbol limits
- Concurrent analysis during streaming for immediate signal detection

**External Tool Integration**:
- `latest.sh` - FFT analysis script requiring `lsq_fft.gsl` and `daily_bars.sqlite.latest_bars_class.py`
- `stock_analyzer_json.c` - C program for high-performance gradient calculations
- RSS/news scrapers for catalyst identification

## Trading Guidelines and Operational Rules

**TRADE MODIFICATION GUIDELINES**:
- You will not change the trades/minute threshold, without asking the user permission first
- The threshold of 1000 trades/minute is set for good reason - it ensures only the most liquid, actively traded stocks
- NEVER change the global configuration parameters without USER permission

**MARKET ORDER RULE**:
- NEVER Use market orders, unless I tell you
- IOC and FOK orders only work in normal market hours

**ETHICAL TRADING GUIDELINES**:
- Avoid Chinese companies

**TESTING REQUIREMENTS**:
- NO MOCK TESTING - USE Alpaca API data calls
- All integration tests must validate actual market data connectivity

**SERVICE STARTUP BEHAVIOR**:
- When the fastapi service starts up, auto-trading is disabled by default
- The USER will enable auto-trading by explicit command

## Browser Preferences
- Use chromium, not firefox

## Critical File References

### Core Implementation Files
- `server.py:1-94` - Main MCP server with modular registration
- `server_components/tool_registrations.py:1-800` - Complete tool registration system
- `monitoring/fastapi_service.py:1-1200` - Production HTTP monitoring service
- `tools/day_trading_scanner.py:100-400` - High-frequency scanner with 1000+ trades/min filter
- `tools/peak_trough_analysis_tool.py:200-600` - Zero-phase Hanning filtering technical analysis
- `utils/alpaca_stream.py:150-500` - Real-time WebSocket streaming with buffering

### Configuration and State Management
- `config/global_config.py:50-200` - JSON-persisted trading parameters
- `config/global_config.json:1-50` - Default configuration values
- `monitoring_data/` - State persistence, alerts, trade confirmations

### External Integration Scripts
- `latest.sh:1-50` - FFT momentum analysis requiring external dependencies
- `stock_analyzer_json.c:1-454` - C program for real-time gradient calculations
- `yf_rss.py:1-200` - Yahoo Finance RSS feed integration for news catalysts