# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Professional Alpaca trading system with MCP (Model Context Protocol) integration, providing 90+ trading tools for algorithmic trading, real-time market analysis, and automated position management.

## Critical Trading Rules

**NEVER VIOLATE:**
1. **NEVER use `stream_optimized_order_placement()` for BUYING** - It buys at market, not at support
2. **ALWAYS buy at TROUGH signals only** - Use `get_stock_peak_trough_analysis` first
3. **MONITOR IMMEDIATELY after orders** - Start checking within 1-2 seconds
4. **CAPTURE FIRST PROFIT SPIKE** - Profits appear 0-10 seconds after entry
5. **USE MANUAL LIMIT ORDERS** for entries at exact signal prices

## Essential Commands

### Development & Testing
```bash
# Install/sync dependencies
uv sync

# Run MCP server
uv run python -m alpaca_mcp_server.main

# Code quality pipeline (run in order)
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/
uv run ruff check --fix alpaca_mcp_server/
uv run mypy alpaca_mcp_server/

# Quick tests (30 seconds)
uv run python alpaca_mcp_server/tests/run_focused_tests.py

# Full test suite
uv run pytest --cov=alpaca_mcp_server --cov-report=html
```

### Service Management
```bash
# Start services
./scripts/start_mcp_server.sh           # Main MCP interface
./scripts/start_monitoring_service.sh   # FastAPI monitoring (port 8000)

# Check status
curl http://localhost:8000/health
```

## Architecture & Key Components

### Dual-Service System
1. **MCP Server** (`server.py`) - Claude interface with 90+ tools via FastMCP
2. **FastAPI Service** (`monitoring/fastapi_service.py`) - HTTP/WebSocket monitoring on port 8000

### Critical Files & Patterns

**Core Trading Pipeline:**
- `utils/alpaca_stream.py:150-500` - WebSocket streaming with intelligent buffering
- `tools/peak_trough_analysis_tool.py:200-600` - Zero-phase Hanning filter for support/resistance
- `tools/day_trading_scanner.py:100-400` - High-frequency scanner (1000+ trades/min)
- `tools/order_tools.py` - Order placement with loss prevention

**Configuration:**
- `config/global_config.json` - Trading parameters (DO NOT modify without permission)
- Default thresholds: trades/min=1000, min_change=10%, hanning_window=11

**Tool Registration:**
- `server_components/tool_registrations.py` - Modular tool registration system
- Each tool category registered separately for maintainability

### Trading Workflow Pattern

```python
# Standard trading sequence
1. analysis = get_stock_peak_trough_analysis(symbol)  # Technical signals
2. if analysis["latest_trough"]:                      # Buy at support only
3.     place_stock_order(limit_price=trough_price)   # Manual limit order
4.     while position_open:                          # Monitor immediately
5.         get_stock_stream_data(recent_seconds=2)   # Real-time data
6.         if profit > 0: sell()                      # Capture spikes
```

## External Dependencies

**C/Binary Tools (compile separately):**
- `stock_analyzer_json.c` - Compile: `gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm`
- `lsq_fft.gsl` - Required for `latest.sh` FFT analysis
- `daily_bars.sqlite.latest_bars_class.py` - SQLite bar data processor

## MCP Tool Categories

- **Account Management** - get_account_info, get_positions, close_position
- **Market Data** - get_stock_quote, get_stock_bars, get_stock_snapshots
- **Technical Analysis** - get_stock_peak_trough_analysis, generate_advanced_technical_plots
- **Scanners** - scan_day_trading_opportunities, scan_explosive_momentum
- **Order Management** - place_stock_order, cancel_order_by_id
- **Streaming** - start_global_stock_stream, get_stock_stream_data
- **Options** - get_option_contracts, get_option_snapshot
- **Monitoring** - start_fastapi_monitoring_service, get_profit_spike_alerts

## Testing Philosophy

- **NO MOCK TESTING** - Always use real Alpaca API data
- Integration tests validate actual market connectivity
- Performance benchmarks for latency-critical paths

## Service Behavior Notes

- FastAPI service starts with auto-trading DISABLED
- User must explicitly enable auto-trading
- All trades logged to `monitoring_data/alerts/`
- Browser preference: chromium (not firefox)

## Common Slash Commands

- `/list_trading_capabilities` - Show all available tools
- `/account_analysis` - Portfolio health check
- `/scan` - Quick market scanner
- `/day_trading_workflow` - Intraday momentum setup
- `/master_scanning_workflow` - Comprehensive analysis

## Important Patterns to Follow

1. **Always check peak/trough before large trades** (>$50K positions)
2. **Use 4 decimal places for order prices**
3. **Never use market orders unless explicitly requested**
4. **IOC/FOK orders only work in regular market hours**
5. **Monitor positions every 10 seconds when holding**
6. **Immediate profit-taking at $5K+ or 3%+ gains**

## State & Data Locations

- `monitoring_data/` - Persistent state, alerts, position history
- `config/global_config.json` - Trading parameters
- Logs written to project root and monitoring_data/alerts/