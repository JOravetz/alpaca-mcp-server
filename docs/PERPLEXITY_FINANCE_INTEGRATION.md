# Perplexity Finance Integration

This document describes the integration of Perplexity Finance data into the Alpaca MCP Server for enhanced day-trading research and real-time market intelligence.

## Overview

Perplexity Finance provides AI-powered stock analysis, real-time quotes, news, and market insights. We've integrated two access methods:

1. **REST API (cloudscraper)** - Fast ~2 second access for real-time quotes
2. **Browser (undetected-chromedriver)** - Full AI analysis with news, bull/bear cases (~60 seconds)

## Components

### 1. MCP Tools (Fast Access)

Located in `alpaca_mcp_server/tools/perplexity_tools.py`

#### `get_perplexity_quote(symbols)`
Get real-time stock quotes from Perplexity Finance.

```python
# Example usage
get_perplexity_quote("NVDA,AAPL,SMX")
```

Returns:
- Current price and % change
- After-hours price and % change
- Day range and 52-week range
- Volume and volume ratio (with HIGH VOLUME alerts)
- 50-day moving average context

#### `get_perplexity_movers()`
Get today's top gaining stocks for day-trading opportunities.

```python
# Example usage
get_perplexity_movers()
```

Returns top gainers with:
- Price and % change
- Volume ratio
- 🔥 alerts for high-volume plays

### 2. Slash Command (Deep Analysis)

Located in `.claude/commands/pplx.md`

```bash
/pplx NVDA
```

Fetches comprehensive AI-powered analysis including:
- Latest news headlines
- Price movement history with AI summaries
- Bull/Bear key issues analysis
- Peer comparisons
- Support/resistance identification

Best used for **pre-market research** due to ~60 second fetch time.

### 3. Shell Script

Located in `~/bin/pplx-stock`

```bash
# Basic usage
~/bin/pplx-stock NVDA

# Pipe to Claude for analysis
~/bin/pplx-stock NVDA | claude -p "Day trading analysis: key levels, momentum"

# Multiple tickers
for t in NVDA AAPL TSLA; do
  echo "=== $t ==="
  ~/bin/pplx-stock $t | head -100
done
```

### 4. Python Module

Located in `external_tools/perplexity_finance.py`

```bash
# Quick quotes (REST API)
uv run python external_tools/perplexity_finance.py NVDA SMX --quiet

# Full report with profile
uv run python external_tools/perplexity_finance.py NVDA --full

# JSON output
uv run python external_tools/perplexity_finance.py NVDA --json

# Browser-based AI analysis
uv run python external_tools/perplexity_finance.py NVDA --browser
```

## Technical Implementation

### Cloudflare Bypass

Perplexity Finance uses Cloudflare protection. We bypass it using:

1. **cloudscraper** - For REST API access (quote, profile, earnings endpoints)
2. **undetected-chromedriver** - For full page scraping with AI content

### REST API Endpoints

```
https://www.perplexity.ai/rest/finance/quote/{symbol}
https://www.perplexity.ai/rest/finance/profile/{symbol}
https://www.perplexity.ai/rest/finance/earnings/{symbol}
https://www.perplexity.ai/rest/finance/financials/{symbol}
```

### Browser Method

Uses `xvfb-run` with `undetected-chromedriver` to render the full stock page:

```python
xvfb-run uv run --with undetected-chromedriver python3 -c "
import undetected_chromedriver as uc
driver = uc.Chrome(version_main=142)
driver.get('https://www.perplexity.ai/finance/NVDA')
..."
```

## Day-Trading Workflow

### Pre-Market (7:00-9:30 AM)

```bash
# Deep research on potential plays
/pplx NVDA

# Or via shell
~/bin/pplx-stock NVDA | claude -p "Identify key support/resistance for day trading"
```

### Market Open (9:30 AM)

```python
# Find today's explosive movers
get_perplexity_movers()

# Quick quotes on interesting symbols
get_perplexity_quote("SMX,PMI,SNCR")
```

### Active Trading

Combine Perplexity data with Alpaca tools:

```python
# Get Perplexity quote for context
perplexity_data = get_perplexity_quote("SMX")

# Run technical analysis with Alpaca
peak_trough = get_stock_peak_trough_analysis("SMX")

# Place order at support/resistance
place_stock_order("SMX", "buy", 100, limit_price=support_level)
```

## Dependencies

### Required Packages

```bash
# For REST API access
uv pip install cloudscraper

# For browser access (optional)
sudo apt install xvfb html2text
# undetected-chromedriver installed on-demand via uv run --with
```

### Chrome Version

The browser method requires matching Chrome/ChromeDriver versions. Currently configured for Chrome 142:

```python
driver = uc.Chrome(version_main=142)
```

Update this if Chrome is upgraded.

## Data Available

### From REST API (Fast)

| Field | Description |
|-------|-------------|
| price | Current stock price |
| changesPercentage | Daily % change |
| afterHoursPrice | After-hours price |
| afterHoursPercentChange | After-hours % change |
| volume | Daily volume |
| avgVolume | Average volume |
| dayLow / dayHigh | Day range |
| yearLow / yearHigh | 52-week range |
| priceAvg50 / priceAvg200 | Moving averages |
| marketCap | Market capitalization |
| pe | P/E ratio |
| eps | Earnings per share |

### From Browser (Comprehensive)

All REST API data plus:
- Latest news headlines with sources
- AI-generated price movement summaries
- Bull/Bear analysis with citations
- Key issues and risks
- Peer comparisons
- Company profile and description

## Troubleshooting

### "cloudscraper not installed"

```bash
uv pip install cloudscraper
```

### Browser timeout or Cloudflare block

1. Increase timeout: `fetch_with_browser(symbol, timeout=20)`
2. Check Chrome version matches: `chromium-browser --version`
3. Update version_main in script if needed

### Empty response from REST API

Some small-cap stocks may not have data. Fall back to browser method:

```bash
uv run python external_tools/perplexity_finance.py TICKER --browser
```

## Files Modified/Created

- `alpaca_mcp_server/tools/perplexity_tools.py` - MCP tool implementations
- `alpaca_mcp_server/server_components/tool_registrations.py` - Tool registration
- `external_tools/perplexity_finance.py` - Standalone Python module
- `.claude/commands/pplx.md` - Slash command definition
- `~/bin/pplx-stock` - Shell script for CLI access
- `docs/PERPLEXITY_FINANCE_INTEGRATION.md` - This documentation

## Future Enhancements

- [ ] Cache REST API responses (5-minute TTL)
- [ ] Add earnings calendar integration
- [ ] Create combined scanner (Alpaca + Perplexity movers)
- [ ] WebSocket for real-time Perplexity updates
- [ ] Integrate with monitoring service for alerts
