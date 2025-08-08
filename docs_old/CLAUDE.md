# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **dual-MCP server integration** that combines:
1. **Alpaca Trading MCP Server** - Professional trading operations and market data
2. **Quick-Data MCP Server** - Statistical analysis and data visualization

Together, they create a **quantitative trading research platform** with institutional-grade capabilities for market analysis, signal processing, and statistical validation.

## Common Development Commands

### Environment Setup
```bash
# Install dependencies with UV (preferred)
uv sync

# Or use pip if UV unavailable
pip install -r requirements.txt

# Activate virtual environment
source .venv/bin/activate
```

### Running Dual-MCP Server Configuration
```bash
# Alpaca Trading MCP Server
uv run python -m alpaca_mcp_server

# Both servers should be configured in Claude Code's .mcp.json:
# - alpaca-trading: Advanced trading operations
# - quick-data: Statistical analysis engine

# Test both server connections
mcp list  # Should show both servers connected
```

### Integrated Trading & Analysis Workflows
```bash
# === ALPACA TRADING SERVER COMMANDS ===
# Professional agentic workflows
/alpaca-trading/startup()                 # Complete session initialization
/alpaca-trading/master-scanning-workflow  # Comprehensive market scanning
/alpaca-trading/pro-technical-workflow SYMBOL  # Advanced technical analysis

# Advanced technical analysis with zero-phase filtering
/alpaca-trading/generate-advanced-technical-plots AAPL,MSFT,TSLA

# === QUICK-DATA SERVER COMMANDS ===
# Statistical analysis capabilities  
/quick-data/load-dataset dataset.csv     # Load data for analysis
/quick-data/correlation-investigation    # Statistical correlation analysis
/quick-data/pattern-discovery-session   # AI-powered pattern recognition

# === CROSS-SERVER INTEGRATION ===
# Export trading data → Statistical validation → Enhanced decisions
1. Generate data with Alpaca scanning
2. Export to CSV/JSON format
3. Load into Quick-Data for statistical analysis
4. Apply insights back to trading decisions
```

### Development Tools
```bash
# Code formatting and linting (use UV for dependency management)
uv run ruff format .
uv run ruff check . --fix
uv run mypy alpaca_mcp_server --ignore-missing-imports

# Advanced technical analysis plotting
uv run python peak_trough_detection_plot.py

# Shell script trading scanner
./trades_per_minute.sh -f combined.lis -t 500
```

## Dual-MCP Architecture

### **Alpaca Trading Server** - Market Operations & Real-time Data
🥇 **AGENTIC WORKFLOWS** (`prompts/`) - Professional multi-tool orchestration
- `master_scanning_workflow.py` - Comprehensive market opportunity discovery
- `pro_technical_workflow.py` - Advanced algorithmic analysis with peak/trough detection
- `day_trading_workflow.py` - Complete setup analysis for any symbol
- `market_session_workflow.py` - Session-specific timing strategies

🥈 **REAL-TIME RESOURCES** (`resources/`) - Live market analysis engines  
- `market_momentum.py` - Technical indicators with configurable SMAs
- `data_quality.py` - Feed quality and latency monitoring
- `streaming_resources.py` - Real-time data buffer management
- `intraday_pnl.py` - Live position tracking and P&L analysis

🥉 **TRADING TOOLS** (`tools/`) - 50+ specialized operations
- Advanced plotting with zero-phase Hanning filtering
- Multiple scanner engines (momentum, explosive, differential)
- Real-time streaming data management
- Professional order execution and risk management

### **Quick-Data Server** - Statistical Analysis & Validation
- **Machine Learning Analytics** - Correlation detection, pattern recognition
- **Data Visualization** - Professional plotting and dashboard generation  
- **Statistical Validation** - Hypothesis testing, outlier detection
- **Cross-Dataset Analysis** - Multi-timeframe and cross-asset studies

### **Cross-Server Integration Capabilities**
🔄 **Quantitative Research Pipeline:**
1. **Data Generation** (Alpaca) → Market scanning and technical analysis
2. **Signal Processing** (Alpaca) → Zero-phase filtering and peak/trough detection  
3. **Statistical Validation** (Quick-Data) → Correlation analysis and pattern recognition
4. **Enhanced Decision Making** → Data-driven trading with statistical confidence

🚀 **Professional Research Workflows:**
- **Market Microstructure Studies** using high-frequency Alpaca data + statistical analysis
- **Cross-Asset Correlation Analysis** combining multiple symbols with ML validation
- **Quantitative Strategy Development** with proper backtesting and statistical rigor
- **Risk Model Validation** through historical data analysis and stress testing

### Key Architectural Patterns

**FastMCP Registration Pattern:**
1. Create function in appropriate module (e.g., `prompts/new_prompt.py`)
2. Add to module `__init__.py` exports
3. Import in `server.py`
4. Register with `@mcp.prompt()` decorator in `server.py`

**Client Factory Pattern:**
- All Alpaca API clients initialized in `config/clients.py`
- Supports multiple client types: TradingClient, StockHistoricalDataClient, etc.
- Environment-aware (paper vs live trading)

**Error Handling Strategy:**
- Tools return formatted strings optimized for LLM consumption
- Context-aware error messages with suggested actions
- Graceful degradation when APIs unavailable

## Professional Trading & Research Guidelines

### **Advanced Technical Analysis Standards**
- **Zero-phase filtering** eliminates look-ahead bias in signal processing
- **Peak/trough detection** provides precise support/resistance levels
- **Multi-timeframe coherence** across 1Min to 1Day analysis
- **Statistical validation** required for all trading signals
- **Publication-quality outputs** with professional visualization standards

### **Quantitative Research Protocol**
1. **Data Collection** → Use Alpaca's institutional-grade market data
2. **Signal Processing** → Apply zero-phase Hanning windowing for noise reduction
3. **Statistical Validation** → Cross-validate with Quick-Data correlation analysis
4. **Risk Assessment** → Quantify confidence intervals and drawdown scenarios
5. **Execution** → Implement with proper position sizing and risk management

### **Market Scanning Hierarchy** (Priority Order)
🥇 **Advanced Technical Plots** → `generate_advanced_technical_plots()` for precise entry/exit levels
🥈 **Master Scanner Workflow** → `master_scanning_workflow()` for comprehensive market analysis  
🥉 **Shell Script Scanner** → `./trades_per_minute.sh` for basic liquidity filtering
🏅 **Individual Scanners** → Momentum, explosive, differential scanners for specific strategies

### **Data Quality & Precision Standards**
- **Sub-second latency** for real-time decision making
- **4+ decimal precision** for accurate calculations ($0.0118 format)
- **1,000+ trades/minute** minimum liquidity requirement
- **EDT timezone consistency** for all analysis timestamps
- **Statistical significance** testing for all correlation findings

## Environment Configuration

Required environment variables:
- `APCA_API_KEY_ID` - Alpaca API key
- `APCA_API_SECRET_KEY` - Alpaca secret key  
- `PAPER="true"` - Paper trading flag (defaults to true for safety)

The server defaults to paper trading and requires Python 3.12+.

## Development Principles

- **Solve real problems, never mock** - Implement actual trading functionality
- **Use MCP tools, not direct API calls** - Always prefer existing MCP tools
- **Fix tools before proceeding** - If MCP tools malfunction, stop and fix them
- **Multi-symbol efficiency** - Use `get_stock_bars_intraday` for multiple symbols
- **All times in EDT** - Reference all analysis to NYC/Eastern timezone

## Integration Points

### Prompt Development
Prompts orchestrate multiple tools to provide comprehensive analysis. Example structure:
```python
async def analysis_prompt() -> str:
    # Gather data from multiple sources
    account = await get_account_info()
    positions = await get_positions()
    market = await get_market_momentum()
    
    # Intelligent synthesis and recommendations
    return formatted_professional_analysis()
```

### Resource Real-time Computation
Resources provide live analysis during market hours with configurable parameters:
```python
# Market momentum with custom parameters
await get_market_momentum(
    symbol="SPY",
    timeframe_minutes=1,
    analysis_hours=2,
    sma_short=5,
    sma_long=20
)
```

### Tool Composition Patterns
Tools follow consistent patterns for error handling, parameter validation, and LLM-optimized output formatting. They can be composed by prompts for complex workflows.

## Production Considerations

- Server defaults to paper trading for safety
- All trading actions logged for audit trail
- Performance monitoring for latency and data quality
- Graceful degradation when external services unavailable
- Memory management for high-velocity streaming data