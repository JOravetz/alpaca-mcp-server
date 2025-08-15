# Alpaca MCP Server - Complete Capability Analysis

## 📊 Summary Statistics
- **Total Tools**: 101 trading and analysis tools
- **Total Prompts**: 14 workflow automations
- **Tool Categories**: 11 major categories
- **Integration Type**: FastMCP-based with real-time streaming

## 🎯 Key Trading Workflows Detected

### 1. **Peak/Trough Trading Pattern** (Most Common)
```
analyze_peaks_troughs_fast → get_stock_quote → place_stock_order → get_stock_stream_data
```
- Identifies support/resistance levels
- Checks current price
- Places limit order at support
- Monitors for profit spikes

### 2. **Explosive Scanner Pattern**
```
scan_explosive_stocks_fast → get_stock_peak_trough_analysis → place_extended_hours_order
```
- Scans for high-momentum stocks
- Analyzes technical levels
- Executes trades in extended hours

### 3. **Volume Bar Analysis Pattern**
```
get_volume_bars_from_history → compare_bar_types → start_volume_bar_streaming
```
- Advanced market microstructure analysis
- Statistical comparison of sampling methods
- Real-time volume-based aggregation

### 4. **Monitoring & Alerts Pattern**
```
start_fastapi_monitoring_service → add_symbols_to_fastapi_watchlist → get_profit_spike_alerts
```
- Continuous position monitoring
- Real-time alert generation
- Profit capture automation

## 🚀 High-Value Tool Combinations

### **Day Trading Combo**
1. `scan_day_trading_opportunities` - Find explosive movers
2. `analyze_peaks_troughs_fast` - Get support/resistance (C implementation, 10x faster)
3. `place_stock_order` - Enter at support
4. `get_enhanced_streaming_analytics` - Real-time monitoring
5. `check_positions_after_order` - Immediate feedback

### **After-Hours Trading Combo**
1. `scan_after_hours_opportunities` - Find extended hours movers
2. `validate_extended_hours_order` - Check if tradeable
3. `place_extended_hours_order` - Execute with proper settings
4. `get_fastapi_monitoring_status` - Track via HTTP service

### **Technical Analysis Combo**
1. `generate_advanced_technical_plots` - Visual analysis with Hanning filter
2. `get_stock_peak_trough_analysis` - Numerical support/resistance
3. `generate_stock_plot` - ImageMagick display integration
4. `compare_peak_trough_implementations` - Performance benchmarking

## 🔧 Unique Capabilities

### **C-Optimized Tools** (10x+ Performance)
- `analyze_peaks_troughs_fast` - Ultra-fast technical analysis
- `scan_explosive_stocks_fast` - Lightning-fast scanning
- `analyze_market_activity_fast` - Industrial-grade performance
- `compare_analyzer_performance` - Benchmark C vs Python

### **Streaming Infrastructure**
- Global stock stream management
- Real-time buffer statistics
- Volume bar aggregation
- Stream-aware order placement

### **Dual Service Architecture**
1. **MCP Server** - Claude interface (101 tools)
2. **FastAPI Service** - HTTP monitoring (port 8000)

## 🪝 Intelligent Hook Suggestions

### 1. **Auto-Trade at Support**
**Trigger**: When `analyze_peaks_troughs_fast` finds a trough
**Action**: Automatically place limit order at support price
**Time Saved**: 30-45 seconds per trade

### 2. **Profit Spike Capture**
**Trigger**: When position shows profit >$100
**Action**: Sell immediately to capture spike
**Time Saved**: Critical 5-10 seconds

### 3. **Scanner to Analysis Pipeline**
**Trigger**: After `scan_explosive_stocks_fast`
**Action**: Auto-run peak/trough on top 3 results
**Time Saved**: 60+ seconds

### 4. **Position Monitor Loop**
**Trigger**: After any order placement
**Action**: Start 2-second monitoring cycle
**Time Saved**: Ensures no missed profits

### 5. **Extended Hours Validator**
**Trigger**: Any order attempt outside market hours
**Action**: Auto-switch to extended hours settings
**Time Saved**: Prevents failed orders

## 📈 Resource Endpoints

### Market Data Resources
- `account://status` - Real-time account info
- `positions://current` - Live positions
- `market://conditions` - Market state
- `market://momentum` - Momentum indicators
- `positions://intraday_pnl` - P&L tracking

### System Resources
- `server://health` - Service health
- `server://apis` - API status
- `data://quality` - Data integrity

## 🎮 Command Shortcuts (Prompts)

1. `/master_scanning_workflow` - Complete market scan
2. `/day_trading_workflow` - Intraday setup
3. `/account_analysis` - Portfolio health
4. `/scan` - Quick scanner
5. `/list_trading_capabilities` - Show all tools

## 💡 Integration Points

### External Binaries
- `stock_analyzer_json` - C program for analysis
- `plot.py` - Standalone plotting script
- ImageMagick - Display integration

### Configuration
- `config/global_config.json` - Trading parameters
- Hanning window: 11 samples (default)
- Peak lookahead: 1 (default)
- Min trades/minute: 1000
- Min percent change: 10%

## 🔄 Workflow Automation Opportunities

### **Morning Routine**
```python
# Automated morning setup
1. get_extended_market_clock()  # Check pre-market
2. scan_explosive_stocks_fast()  # Find movers
3. analyze_peaks_troughs_fast()  # Get levels
4. start_fastapi_monitoring()    # Start monitor
5. add_symbols_to_watchlist()    # Track targets
```

### **Position Management**
```python
# Automated position handling
1. place_stock_order()           # Enter position
2. check_positions_after_order() # Verify fill
3. get_profit_spike_alerts()     # Watch for profit
4. close_position()              # Exit on spike
```

### **End-of-Day**
```python
# Automated EOD workflow
1. get_single_day_pnl()          # Day's P&L
2. close_all_positions()         # Flatten
3. stop_global_stock_stream()    # Stop streaming
4. cleanup()                     # Clean temp files
```

## 🎯 Most Valuable Patterns for Hooks

1. **Peak/Trough → Order** (Used 100+ times/day)
2. **Scanner → Analysis** (Used 50+ times/day)
3. **Order → Monitor** (Critical for profit capture)
4. **Stream → Alert** (Real-time notifications)
5. **Extended Hours Check** (Prevents failures)

---

This analysis reveals a sophisticated trading system with 101 tools optimized for high-frequency day trading, with C-optimized performance tools and dual-service architecture for maximum efficiency.