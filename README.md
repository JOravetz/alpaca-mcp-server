# Alpaca MCP Server Enhanced

A professional-grade **Model Context Protocol (MCP) server** for day-trading with Alpaca Markets API. Designed for aggressive intraday trading with real-time streaming, technical analysis, and AI-powered research tools.

## Features

### Core Trading Capabilities
- **Real-time Market Data** - WebSocket streaming for quotes, trades, and bars
- **Order Management** - Place, modify, and cancel orders with extended hours support
- **Position Tracking** - Live P&L monitoring with profit spike alerts
- **Technical Analysis** - Peak/trough detection with zero-phase Hanning filtering

### High-Performance Scanning
- **C-Optimized Analyzers** - 10x faster market scanning with compiled C programs
- **Explosive Momentum Scanner** - Find volatile stocks with high trade frequency
- **Day Trading Opportunities** - Filter by % change, volume, and activity

### AI-Powered Research
- **Perplexity Finance Integration** - Headless scraper for AI stock analysis
- **SEC EDGAR Tools** - Company filings, insider transactions, financial statements
- **News Aggregation** - Real-time news from multiple sources

### Monitoring & Alerts
- **FastAPI Dashboard** - Web-based position and signal monitoring
- **Desktop Notifications** - System alerts for trading signals
- **Hybrid Monitoring** - Combines streaming data with position tracking

## Quick Start

```bash
# Clone and setup
git clone https://github.com/jjoravet/alpaca-mcp-server-enhanced.git
cd alpaca-mcp-server-enhanced

# Configure environment
cp .env.example .env
# Edit .env with your Alpaca API credentials

# Install dependencies
uv sync

# Start the MCP server
uv run python -m alpaca_mcp_server.main
```

## Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- Alpaca Markets account (paper or live)

## Project Structure

```
alpaca-mcp-server-enhanced/
├── alpaca_mcp_server/
│   ├── tools/           # MCP tools (trading, scanning, analysis)
│   ├── resources/       # Read-only data endpoints
│   ├── prompts/         # Workflow prompts
│   ├── monitoring/      # Position tracking & alerts
│   ├── utils/           # Shared utilities
│   └── config/          # Global configuration
├── c_progs/             # High-performance C analyzers
├── external_tools/      # Perplexity, news scrapers
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Development guide and coding standards |
| [docs/PPLX_STOCK_SCRAPER.md](docs/PPLX_STOCK_SCRAPER.md) | Perplexity Finance headless scraper |
| [docs/PERPLEXITY_FINANCE_INTEGRATION.md](docs/PERPLEXITY_FINANCE_INTEGRATION.md) | AI research integration |

## Key Tools

### Market Data
- `get_stock_quote` - Real-time quotes
- `get_stock_bars` - Historical OHLCV data
- `get_stock_snapshots` - Comprehensive market snapshots
- `start_global_stock_stream` - WebSocket streaming

### Trading
- `place_stock_order` - Execute trades
- `place_extended_hours_order` - Pre/post market orders
- `get_positions` - Current holdings
- `close_position` - Exit positions

### Scanning
- `scan_day_trading_opportunities` - Find active stocks
- `scan_explosive_momentum` - Volatile movers
- `analyze_market_activity_fast` - C-optimized scanner

### Technical Analysis
- `get_stock_peak_trough_analysis` - Support/resistance levels
- `generate_stock_plot` - Technical charts with ImageMagick display
- `get_enhanced_streaming_analytics` - Real-time VWAP, momentum

### Research
- `get_perplexity_quote` - AI-powered stock analysis
- `mcp__sec-edgar__get_financials` - SEC financial statements
- `mcp__sec-edgar__get_insider_transactions` - Insider trading data

## External Tools

### pplx-stock

Headless Perplexity Finance scraper - fetches AI-powered stock analysis without browser windows:

```bash
# Install to ~/bin
chmod +x ~/bin/pplx-stock

# Usage
pplx-stock NVDA          # Get full analysis
pplx-stock AMD --raw     # Raw HTML output
```

Features:
- Bypasses Cloudflare with undetected-chromedriver
- Runs invisibly using Xvfb virtual display
- Captures AI-written price movement summaries
- Extracts bull/bear analyst cases

See [docs/PPLX_STOCK_SCRAPER.md](docs/PPLX_STOCK_SCRAPER.md) for full documentation.

## Configuration

### Environment Variables

```bash
# .env file
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
PAPER=true  # Use paper trading
```

### Global Config

Trading parameters in `config/global_config.json`:

```json
{
  "trades_per_minute_threshold": 1000,
  "min_percent_change_threshold": 10.0,
  "hanning_window_samples": 11,
  "never_sell_for_loss": true
}
```

## Development

```bash
# Run tests
uv run pytest --cov=alpaca_mcp_server

# Linting
uv run ruff check alpaca_mcp_server/

# Type checking
uv run mypy alpaca_mcp_server/

# Format code
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/
```

## Day-Trading Philosophy

This system is built for **intraday trading only**:

- All positions opened and closed same day
- Enter at resistance (shorts) or support (longs)
- Target 3-10% moves within hours
- Mandatory exit by 4:00 PM ET
- Never hold overnight

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This software is for educational and research purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always use paper trading to test strategies before risking real capital.
