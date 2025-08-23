# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Alpaca MCP Server Enhanced - A professional trading system implementing the Model Context Protocol (MCP) for integration with Alpaca's trading APIs. The system focuses on aggressive day trading strategies with real-time market data streaming, technical analysis, and automated monitoring capabilities.

## Key Development Commands

### Running the Server
```bash
# Start the MCP server (primary entry point)
uv run python -m alpaca_mcp_server.main

# Start with monitoring service
./scripts/start_monitoring.sh

# Start FastAPI monitoring dashboard (port 8001)
uv run python -m alpaca_mcp_server.monitoring.fastapi_service
```

### Code Quality & Testing
```bash
# Run full test suite with coverage (80% minimum required)
uv run pytest --cov=alpaca_mcp_server --cov-report=html

# Quick focused tests
uv run python alpaca_mcp_server/tests/run_focused_tests.py

# Run specific test categories
uv run pytest -m unit              # Unit tests only
uv run pytest -m integration       # Integration tests only
uv run pytest -m "not slow"        # Skip slow tests

# Linting and type checking
uv run ruff check alpaca_mcp_server/
uv run mypy alpaca_mcp_server/ --show-error-codes

# Auto-format code (100 char line length)
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/
uv run ruff check --fix alpaca_mcp_server/
```

### Makefile Shortcuts
```bash
make server         # Start MCP server
make test           # Run full test suite
make test-quick     # Run focused tests
make lint           # Run linting checks
make format         # Auto-format all code
make clean          # Clean cache files
make install        # Sync dependencies with uv
make plot ARGS="-s AAPL"  # Generate plots
make scanner        # Run day trading scanner
make news SYMBOLS='AAPL MSFT'  # Fetch stock news
```

## Architecture Overview

### Server Initialization Sequence

1. **Entry Point** (`main.py`) → Handles imports and error handling
2. **Server Setup** (`server.py`) → Creates FastMCP instance with compatibility patches
3. **Component Registration** (`server_components/`):
   - `server_init.py` → Initializes API clients and global state
   - `tool_registrations.py` → Registers all trading tools
   - `resource_registrations.py` → Registers read-only resources
   - `prompt_registrations.py` → Registers workflow prompts

### Core Components

1. **MCP Server (`alpaca_mcp_server/server.py`)**
   - FastMCP-based server implementing Model Context Protocol
   - Registers tools, resources, and prompts for AI integration
   - Entry point manages compatibility patches and initialization

2. **Global Configuration System (`config/global_config.json`)**
   - Centralized trading parameters and thresholds
   - Key settings:
     - `trades_per_minute_threshold`: 1000 (for explosive momentum)
     - `min_percent_change_threshold`: 10.0% (aggressive filtering)
     - `hanning_window_samples`: 11 (technical analysis smoothing)
     - `never_sell_for_loss`: true (core trading principle)

3. **Tool Categories (`alpaca_mcp_server/tools/`)**
   - **Market Data**: Real-time quotes, bars, snapshots, streaming
   - **Trading**: Order placement, position management, extended hours
   - **Technical Analysis**: Peak/trough detection with Hanning filtering
   - **Scanning**: Day trading opportunities, explosive momentum stocks
   - **Monitoring**: FastAPI service, hybrid monitoring, signal detection

4. **Streaming Infrastructure (`alpaca_mcp_server/utils/alpaca_stream.py`)**
   - Global WebSocket connection management
   - Circular buffer storage (5000 items per symbol)
   - Real-time data aggregation for trades, quotes, bars

5. **C-Optimized Analysis (`c_progs/`)**
   - High-performance peak/trough detection (`filter_bars.c`)
   - Stock analyzer for rapid market scanning (`stock_analyzer_json.c`)
   - 10x+ performance improvement over Python implementations

### Monitoring System

The monitoring infrastructure provides real-time visibility:
- **FastAPI Service** (port 8001): REST API and WebSocket endpoints
- **Hybrid Monitoring**: Combines streaming data with position tracking
- **Signal Detection**: Automated alerts for trading opportunities
- **Desktop Notifications**: System-level alerts for critical events

### Trading Workflow Architecture

1. **Prompts** (`alpaca_mcp_server/prompts/`): Pre-configured workflows for complex trading operations
   - `startup_prompt.py` - Comprehensive startup checks (/startup command)
   - `day_trading_workflow.py` - Day trading strategy execution
   - `market_analysis_prompt.py` - Market condition analysis
   - `stream_centric_trading_prompt.py` - Real-time streaming workflows
2. **Resources** (`alpaca_mcp_server/resources/`): Read-only data endpoints for system state
3. **Tools** (`alpaca_mcp_server/tools/`): Executable functions for trading actions

## Critical Trading Logic

### Position Management
- Maximum concurrent positions: 5
- Default position size: $50,000
- Never sell for loss principle enforced
- Automatic profit capture at 3% threshold
- Family protection profit threshold: 10%

### Market Hours & Sessions
- Regular hours: 9:30 AM - 4:00 PM ET
- Extended hours: 4:00 AM - 8:00 PM ET
- All timestamps in America/New_York timezone

### Order Execution
- Default order type: limit orders
- Time in force: day orders
- Price precision: 4 decimal places
- Order timeout: 10 seconds

## Testing Strategy

### Test Organization
- Test files in `alpaca_mcp_server/tests/`
- Test markers: `unit`, `integration`, `performance`, `slow`
- Coverage requirement: 80% minimum
- Timeout: 30 seconds per test (configurable)

### Running Specific Test Types
```bash
# Run plotting tests
uv run python alpaca_mcp_server/tests/run_plotting_tests.py

# Run with verbose output
uv run python alpaca_mcp_server/tests/run_tests.py --verbose

# Skip performance tests
uv run python alpaca_mcp_server/tests/run_tests.py --skip-performance

# Run single test file
uv run pytest alpaca_mcp_server/tests/test_specific.py

# Run with specific timeout
uv run pytest --timeout=60 alpaca_mcp_server/tests/
```

## Environment Configuration

Required environment variables (set in `.env`):
- `ALPACA_API_KEY`: Your Alpaca API key
- `ALPACA_SECRET_KEY`: Your Alpaca secret key
- `PAPER`: Set to "true" for paper trading

## Important Implementation Notes

### Stream Management
- Global stock stream must be started before using stream-aware tools
- Buffer size: 5000 items per symbol
- Use `start_global_stock_stream` tool first, then stream-aware operations

### Technical Analysis
- Peak/trough detection uses zero-phase Hanning filtering
- Window length and lookahead parameters from global config
- C implementations available for high-performance scenarios

### Error Recovery
- All tools implement fallback mechanisms
- Streaming reconnection handled automatically
- Position checks after every order execution

### MCP Compatibility
- Claude Code compatibility patches applied automatically
- Tool discovery mode supported via CLAUDE_CODE_TOOL_DISCOVERY env var
- All tools registered with proper MCP schemas

## Development Workflow

1. Always use `uv run` for Python execution to ensure correct environment
2. Check global config before modifying trading parameters
3. Test with paper trading mode before live trading
4. Monitor logs in `logs/` directory for debugging
5. Use monitoring dashboard at http://localhost:8001 for real-time status

## Code Style & Quality

### Requirements
- Python 3.12+ required
- Black formatting (100 char line length)
- Type hints required for all functions
- Ruff for linting (see pyproject.toml for rules)
- MyPy strict mode for type checking

### Pre-commit Checks
```bash
# Run all quality checks before committing
make format && make lint && make test-quick
```

## Dependency Management

Using `uv` for fast, reliable Python environment management:
- Dependencies defined in `pyproject.toml`
- Dev dependencies in `[dependency-groups.dev]`
- Always use `uv run` prefix for Python commands
- Sync dependencies: `uv sync` or `make install`

## Available Scripts

Utility scripts in `scripts/` directory:
- `start_monitoring.sh` - Launch monitoring service with position tracking
- `trades_per_minute.sh` - Analyze trade frequency from symbol lists
- `monitor_signals.sh` - Monitor trading signals in real-time
- `cleanup.sh` - Clean temporary files and logs
- `start_mcp_server_debug.sh` - Debug mode server startup

## C Performance Tools

High-performance C implementations in `c_progs/`:
- `filter_bars` - Zero-phase Hanning filter for peak/trough detection
- `stock_analyzer_json` - Ultra-fast market activity analysis
- Accessed via wrapper tools: `analyze_market_activity_fast`, `scan_explosive_stocks_fast`
- 10x+ performance improvement for scanning operations

## Tool Registration Pattern

All tools follow a consistent registration pattern in `server_components/tool_registrations.py`:
1. Tools are decorated with `@mcp.tool()` for MCP discovery
2. Each tool includes comprehensive docstrings for AI understanding
3. Fallback mechanisms implemented for all external API calls
4. Tools return formatted strings for human readability

## Debugging & Troubleshooting

### Common Issues
```bash
# Check server health
uv run python -c "from alpaca_mcp_server.tools.debug_tools import health_check; print(health_check())"

# Verify API connectivity
uv run python -c "from alpaca_mcp_server.config.settings import get_clients; get_clients()"

# Debug MCP tool registration
CLAUDE_CODE_TOOL_DISCOVERY=1 uv run python -m alpaca_mcp_server.main

# Check logs for errors
tail -f logs/alpaca_mcp_server.log
```

### Performance Monitoring
- Monitor memory usage via `resource_server_health` tool
- Check API latency with `resource_data_quality` tool
- Stream buffer stats: `get_stock_stream_buffer_stats` tool

## Critical Files & Locations

- **Global Config**: `config/global_config.json` - Trading parameters
- **Environment**: `.env` - API credentials (never commit)
- **Logs**: `logs/` directory - Debug output
- **State**: `monitoring_data/` - Persistent monitoring state
- **Symbol Lists**: `data/combined.lis` - Tradable symbols