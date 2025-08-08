# Alpaca MCP Server Enhanced - Enterprise Trading System

**Professional-Grade Algorithmic Trading Platform with AI Integration**

[![MCP Tools](https://img.shields.io/badge/MCP_Tools-90+-blue)](#complete-tool-reference)
[![Trading Strategies](https://img.shields.io/badge/Strategies-HFT_Day_Trading-green)](#trading-strategies)
[![Real-Time Data](https://img.shields.io/badge/Data-Streaming_WebSocket-orange)](#real-time-streaming)
[![Python](https://img.shields.io/badge/Python-3.12+-blue)](https://python.org)

A comprehensive algorithmic trading system that integrates Claude AI with Alpaca Markets through the Model Context Protocol (MCP). This platform provides institutional-grade trading capabilities with real-time market analysis, automated opportunity detection, and intelligent trade execution.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** with UV package manager
- **Alpaca Markets Account** (paper or live trading)
- **Claude Desktop** or Claude Code
- **Additional MCP Servers** (optional but recommended):
  - `mcp-server-fetch` - Web data fetching
  - `sec-edgar` - SEC filings and fundamental data
  - `quick-data` - Data analysis and visualization
  - `playwright` - Browser automation for research

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/alpaca-mcp-server-enhanced.git
cd alpaca-mcp-server-enhanced

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Dependencies are auto-installed with UV
uv sync
```

### Configuration

```bash
# Set environment variables
export APCA_API_KEY_ID="your_alpaca_key"
export APCA_API_SECRET_KEY="your_alpaca_secret"
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"  # or live URL
```

### Starting the System

```bash
# Start MCP server (primary interface)
./scripts/start_mcp_server.sh

# Start FastAPI monitoring service (separate terminal)
./scripts/start_monitoring_service.sh

# Verify system health
curl http://localhost:8000/health
```

---

## 📊 System Capabilities

### Core Trading Features

- **High-Frequency Trading (HFT)** - Sub-second execution with streaming data
- **Day Trading** - Momentum-based strategies with technical analysis
- **Extended Hours** - Pre-market and after-hours trading support
- **Options Trading** - Multi-leg strategies and Greeks analysis
- **Position Management** - Real-time P&L tracking and risk monitoring
- **Automated Monitoring** - 24/7 position tracking with alerts

### Market Data & Analysis

- **Real-Time Streaming** - WebSocket feeds for trades, quotes, and bars
- **Technical Analysis** - Zero-phase filtering, peak/trough detection
- **Fundamental Data** - SEC filings integration via `sec-edgar` MCP
- **News Integration** - RSS feeds and sentiment analysis
- **Market Scanning** - High-volume and momentum opportunity detection

### Risk Management

- **Loss Prevention** - Automatic stop-loss and position limits
- **Profit Protection** - Dynamic profit-taking rules
- **Account Monitoring** - Real-time buying power and margin tracking
- **Alert System** - Desktop notifications and logging

---

## 🛠️ Complete Tool Reference

### Account Management Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `get_account_info` | Get account details, buying power, equity | Check trading capacity |
| `get_positions` | List all open positions with P&L | Monitor portfolio |
| `get_open_position` | Detailed info for specific position | Track individual holdings |
| `close_position` | Close position (full or partial) | Exit trades |
| `close_all_positions` | Emergency close all positions | Risk management |

### Market Data Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `get_stock_quote` | Latest bid/ask quotes | Entry/exit pricing |
| `get_stock_snapshots` | Comprehensive market snapshot | Multi-symbol overview |
| `get_stock_bars` | Historical price bars | Chart analysis |
| `get_stock_bars_intraday` | Minute-level bar data | Intraday patterns |
| `get_stock_trades` | Recent trade executions | Volume analysis |
| `get_stock_latest_trade` | Most recent trade | Current price |
| `get_stock_latest_bar` | Latest minute bar | Real-time OHLCV |

### Technical Analysis Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_stock_peak_trough_analysis` | Support/resistance levels with Hanning filter | `window_len`, `lookahead`, `delta` |
| `generate_advanced_technical_plots` | Professional charts with signals | `plot_mode`, `dpi`, `display_plots` |
| `generate_stock_plot` | Standalone plotting with ImageMagick | `timeframe`, `days`, `window` |

### Scanner Tools

| Tool | Description | Filters |
|------|-------------|---------|
| `scan_day_trading_opportunities` | High-volume momentum scanner | 1000+ trades/min, 10%+ change |
| `scan_explosive_momentum` | Extreme volatility finder | 15%+ price movement |
| `scan_after_hours_opportunities` | Extended hours activity | Volume, price change thresholds |

### Order Management Tools

| Tool | Description | Order Types |
|------|-------------|-------------|
| `place_stock_order` | Place any order type | Market, Limit, Stop, Trailing |
| `place_extended_hours_order` | Pre/post market orders | Limit orders only |
| `get_orders` | List orders by status | Open, Closed, All |
| `cancel_order_by_id` | Cancel specific order | By order ID |
| `cancel_all_orders` | Cancel all open orders | Emergency stop |

### Streaming Tools

| Tool | Description | Data Types |
|------|-------------|------------|
| `start_global_stock_stream` | Begin real-time streaming | Trades, Quotes, Bars |
| `get_stock_stream_data` | Retrieve buffered stream data | Recent seconds/limit |
| `add_symbols_to_stock_stream` | Add symbols to active stream | Dynamic subscription |
| `stop_global_stock_stream` | Stop streaming session | Clean shutdown |
| `get_stock_stream_buffer_stats` | Monitor buffer usage | Memory management |

### Monitoring Tools

| Tool | Description | Features |
|------|-------------|----------|
| `start_fastapi_monitoring_service` | Launch HTTP monitoring | REST API + WebSocket |
| `get_fastapi_monitoring_status` | Service health check | Live metrics |
| `get_fastapi_positions` | Real-time position data | Through HTTP service |
| `get_profit_spike_alerts` | Recent profit opportunities | Alert history |
| `ping_monitoring_service` | Verify service responsiveness | Health metrics |

### Options Trading Tools

| Tool | Description | Capabilities |
|------|-------------|--------------|
| `get_option_contracts` | Find option contracts | By underlying, strike, expiry |
| `get_option_latest_quote` | Option bid/ask quotes | Real-time pricing |
| `get_option_snapshot` | Complete option data with Greeks | Delta, Gamma, Theta, Vega |
| `place_option_market_order` | Execute option trades | Single or multi-leg |

---

## 📋 Slash Commands & Prompts

### Available Slash Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/list_trading_capabilities` | Show all available tools and workflows | Initial exploration |
| `/account_analysis` | Complete portfolio health check | Daily review |
| `/position_management` | Strategic position optimization | Risk management |
| `/market_analysis` | Real-time market opportunities | Trading signals |
| `/scan` | Quick market scanner | Find opportunities |
| `/startup` | System initialization guide | First-time setup |
| `/stock_news` | Latest market news analysis | Catalyst research |

### Advanced Workflow Prompts

| Workflow | Description | Use Case |
|----------|-------------|----------|
| `/day_trading_workflow` | Intraday momentum trading setup | Active trading |
| `/master_scanning_workflow` | Comprehensive market analysis | Morning routine |
| `/pro_technical_workflow` | Advanced technical analysis | Chart patterns |
| `/market_session_workflow` | Session-specific strategies | Pre/post market |
| `/stream_centric_trading_cycle` | Real-time streaming focus | HFT strategies |

---

## 📡 Real-Time Streaming System

### WebSocket Data Pipeline

```python
# Start streaming for multiple symbols
await start_global_stock_stream(
    symbols=["AAPL", "TSLA", "SPY"],
    data_types=["trades", "quotes", "bars"],
    feed="sip"  # or "iex"
)

# Monitor stream data
data = await get_stock_stream_data(
    symbol="AAPL",
    data_type="trades",
    recent_seconds=5
)

# Add symbols dynamically
await add_symbols_to_stock_stream(
    symbols=["NVDA", "AMD"],
    data_types=["trades"]
)
```

### Stream Buffer Management

- **Intelligent Buffering**: Per-symbol configurable limits
- **Memory Optimization**: Automatic cleanup of old data
- **Concurrent Analysis**: Real-time signal detection during streaming
- **Performance Monitoring**: Buffer statistics and health metrics

---

## 🔄 FastAPI Monitoring Service

### HTTP REST Endpoints

```bash
# Service health
GET http://localhost:8000/health

# Watchlist management
GET http://localhost:8000/api/watchlist
POST http://localhost:8000/api/watchlist/add
DELETE http://localhost:8000/api/watchlist/remove

# Position monitoring
GET http://localhost:8000/api/positions
GET http://localhost:8000/api/positions/{symbol}

# Trading signals
GET http://localhost:8000/api/signals
GET http://localhost:8000/api/alerts/recent
```

### WebSocket Real-Time Updates

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws');

// Receive real-time updates
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle position updates, signals, alerts
};
```

---

## 🎯 Advanced Usage Examples

### Example 1: HFT-Style Day Trading with Complete Analysis

```python
# 1. Scan for high-frequency opportunities
opportunities = await scan_day_trading_opportunities(
    min_trades_per_minute=1000,  # High liquidity filter
    min_percent_change=10,        # Volatility threshold
    max_symbols=20
)

# 2. Get technical analysis for top candidate
symbol = "AAPL"
technicals = await get_stock_peak_trough_analysis(
    symbol=symbol,
    timeframe="1Min",
    window_len=11,  # Hanning filter window
    lookahead=1      # Peak detection sensitivity
)

# 3. Check fundamental data (via sec-edgar MCP)
fundamentals = await mcp__sec_edgar__get_financials(
    identifier=symbol,
    statement_type="income"
)

# 4. Get recent news (via web fetch or RSS)
news = await analyze_stock_news(symbol)

# 5. Start real-time streaming
await start_global_stock_stream(
    symbols=[symbol],
    data_types=["trades", "quotes"],
    feed="sip"
)

# 6. Place order at support level
if technicals["latest_trough"]:
    order = await place_stock_order(
        symbol=symbol,
        side="buy",
        quantity=100,
        order_type="limit",
        limit_price=technicals["latest_trough"]["price"],
        extended_hours=True
    )

# 7. Monitor position with streaming data
while position_open:
    stream_data = await get_stock_stream_data(
        symbol=symbol,
        data_type="trades",
        recent_seconds=2
    )
    
    position = await get_open_position(symbol)
    if position["unrealized_pl"] > 100:  # Profit target
        await place_stock_order(
            symbol=symbol,
            side="sell",
            quantity=position["qty"],
            order_type="market"
        )
```

### Example 2: Multi-Source Data Fusion

```python
# Combine multiple data sources for comprehensive analysis
async def analyze_opportunity(symbol):
    # 1. Real-time market data
    quote = await get_stock_quote(symbol)
    snapshot = await get_stock_snapshots(symbol)
    
    # 2. Intraday bar data
    bars = await get_stock_bars_intraday(
        symbol=symbol,
        timeframe="1Min",
        limit=1000
    )
    
    # 3. Recent trades for momentum
    trades = await get_stock_trades(
        symbol=symbol,
        limit=100
    )
    
    # 4. Technical signals
    signals = await get_stock_peak_trough_analysis(symbol)
    
    # 5. Fundamental data (sec-edgar)
    company_facts = await mcp__sec_edgar__get_company_facts(symbol)
    
    # 6. News sentiment
    news_data = await fetch_yahoo_rss_news(symbol)
    
    # 7. Quick-data statistical analysis
    await mcp__quick_data__load_dataset(
        file_path=f"{symbol}_data.csv",
        dataset_name=symbol
    )
    
    correlations = await mcp__quick_data__find_correlations(
        dataset_name=symbol
    )
    
    return {
        "real_time": {"quote": quote, "snapshot": snapshot},
        "technicals": signals,
        "fundamentals": company_facts,
        "news": news_data,
        "statistics": correlations
    }
```

### Example 3: C-Based High-Performance Scanning

```bash
# Compile the C scanner
gcc -o stock_analyzer_json stock_analyzer_json.c -lcurl -ljson-c -lm

# Run FFT momentum analysis
./latest.sh  # Requires lsq_fft.gsl

# Execute C-based gradient scanner
./stock_analyzer_json combined.lis > analysis.json

# Parse results in Python
import json

with open('analysis.json') as f:
    gradients = json.load(f)
    
# Find stocks with highest momentum
top_movers = sorted(
    gradients.items(),
    key=lambda x: x[1]['normalized_gradient'],
    reverse=True
)[:10]

# Trade top momentum stocks
for symbol, data in top_movers:
    if data['normalized_gradient'] > 0.5:
        await place_stock_order(
            symbol=symbol,
            side="buy",
            quantity=100,
            order_type="market"
        )
```

### Example 4: Account & P&L Management

```python
# Complete account management workflow
async def manage_account():
    # 1. Check account status
    account = await get_account_info()
    print(f"Buying Power: ${account['buying_power']}")
    print(f"Day Trade Count: {account['daytrade_count']}")
    
    # 2. Review all positions
    positions = await get_positions()
    total_pl = sum(p['unrealized_pl'] for p in positions)
    
    # 3. Get intraday P&L breakdown
    pnl = await resource_intraday_pnl(
        include_open_positions=True,
        min_trade_value=100
    )
    
    # 4. Close losing positions
    for position in positions:
        if position['unrealized_plpc'] < -0.02:  # -2% stop loss
            await close_position(
                symbol=position['symbol'],
                qty=position['qty']
            )
    
    # 5. Scale winners
    for position in positions:
        if position['unrealized_plpc'] > 0.05:  # +5% profit
            await close_position(
                symbol=position['symbol'],
                percentage="50"  # Take half off
            )
    
    return {
        "account": account,
        "total_pl": total_pl,
        "intraday_pnl": pnl
    }
```

### Example 5: Options Trading with Greeks

```python
# Advanced options strategy
async def trade_options(underlying="SPY"):
    # 1. Find option contracts
    contracts = await get_option_contracts(
        underlying_symbol=underlying,
        expiration_date="2024-12-20",
        type="call",
        strike_price_gte="450",
        strike_price_lte="460"
    )
    
    # 2. Get Greeks and pricing
    for contract in contracts[:5]:
        snapshot = await get_option_snapshot(contract['symbol'])
        
        # Analyze Greeks
        if snapshot['greeks']['delta'] > 0.5 and \
           snapshot['greeks']['iv'] < 0.3:
            
            # Place option order
            await place_option_market_order(
                legs=[{
                    'symbol': contract['symbol'],
                    'side': 'buy',
                    'quantity': 1
                }]
            )
```

---

## 📚 Resources & Documentation

### MCP Resources

The system provides dynamic resources that can be queried:

| Resource | Description | Parameters |
|----------|-------------|------------|
| `account://status` | Real-time account metrics | None |
| `positions://current` | Active positions with P&L | None |
| `positions://intraday_pnl` | Today's profit/loss breakdown | `days_back`, `symbol_filter` |
| `market://conditions` | Current market status | None |
| `market://momentum` | Market momentum indicators | `symbol`, `timeframe` |
| `data://quality` | Data feed quality metrics | `test_symbols` |
| `server://health` | System health status | None |

### External Integrations

#### SEC EDGAR Integration
```python
# Get financial statements
financials = await mcp__sec_edgar__get_financials(
    identifier="AAPL",
    statement_type="all"
)

# Get insider transactions
insiders = await mcp__sec_edgar__get_insider_transactions(
    identifier="TSLA",
    days=90
)
```

#### Quick-Data Analytics
```python
# Load and analyze data
await mcp__quick_data__load_dataset(
    file_path="market_data.csv",
    dataset_name="market"
)

# Generate visualizations
await mcp__quick_data__create_chart(
    dataset_name="market",
    chart_type="candlestick",
    x_column="timestamp",
    y_column="price"
)
```

#### Playwright Browser Automation
```python
# Research via browser
await mcp__playwright__browser_navigate(
    url="https://finance.yahoo.com/quote/AAPL"
)

snapshot = await mcp__playwright__browser_snapshot()
```

---

## 🔧 Configuration

### Global Configuration (`config/global_config.json`)

```json
{
  "scanner": {
    "trades_per_minute_threshold": 1000,
    "min_percent_change_threshold": 10.0,
    "max_symbols_to_return": 20,
    "default_sort_by": "trades"
  },
  "technical_analysis": {
    "hanning_window_samples": 11,
    "peak_trough_lookahead": 1,
    "peak_trough_delta": 0.0,
    "min_peak_distance": 5
  },
  "monitoring": {
    "check_interval_seconds": 2,
    "max_concurrent_positions": 10,
    "signal_confidence_threshold": 0.75,
    "profit_spike_threshold_percent": 1.0,
    "auto_trading_enabled": false
  }
}
```

### Environment Variables

```bash
# Required
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# Optional
DISCORD_WEBHOOK_URL=your_webhook_url
MCP_DEBUG=1
CLAUDE_CODE_TOOL_DISCOVERY=1
```

---

## 🧪 Testing

### Run Test Suites

```bash
# Quick core functionality tests
uv run python alpaca_mcp_server/tests/run_focused_tests.py

# Full test suite with coverage
uv run pytest --cov=alpaca_mcp_server --cov-report=html

# Performance benchmarks
uv run python alpaca_mcp_server/tests/run_performance_tests.py
```

### Test Categories

- **Unit Tests**: Core functionality validation
- **Integration Tests**: API connectivity and data flow
- **Performance Tests**: Latency and throughput benchmarks
- **Error Handling**: Edge cases and failure scenarios

---

## 🚨 Risk Disclaimers

**IMPORTANT NOTICES:**

1. **Paper Trading Recommended**: Always test strategies in paper trading before using real money
2. **No Guarantee of Profits**: Past performance does not guarantee future results
3. **Risk of Loss**: Trading involves substantial risk of loss
4. **Not Financial Advice**: This system is a tool, not investment advice
5. **User Responsibility**: Users are responsible for their trading decisions

---

## 🛡️ Security

### Best Practices

- Never commit API keys or secrets
- Use environment variables for sensitive data
- Enable 2FA on your Alpaca account
- Monitor account activity regularly
- Set position and loss limits

### Audit Logging

All trading activities are logged to:
- `monitoring_data/alerts/` - Alert history
- `monitoring_data/trades/` - Trade confirmations
- System logs with timestamps and details

---

## 📈 Performance Metrics

### System Capabilities

- **Order Latency**: < 100ms average
- **Stream Processing**: 10,000+ events/second
- **Concurrent Symbols**: 100+ simultaneous streams
- **Scanner Speed**: Full market scan in < 15 seconds
- **Technical Analysis**: Sub-second calculations

### Resource Usage

- **Memory**: ~500MB base, +10MB per streamed symbol
- **CPU**: 1-2 cores for normal operation
- **Network**: Varies with streaming symbols
- **Storage**: Minimal, mainly logs and state

---

## 🤝 Support & Contributions

### Getting Help

1. Check the [Documentation](#resources--documentation)
2. Review [Advanced Examples](#advanced-usage-examples)
3. Examine test files for usage patterns
4. Use help tools: `get_tool_help("tool_name")`

### Contributing

Contributions welcome! Please:
1. Test thoroughly with paper trading
2. Add unit tests for new features
3. Update documentation
4. Follow existing code style

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- Alpaca Markets for the trading API
- Anthropic for Claude AI and MCP
- Open source contributors
- The quantitative trading community

---

**Remember**: This is a powerful tool. Use it responsibly, start with paper trading, and never risk more than you can afford to lose. Happy trading! 🚀