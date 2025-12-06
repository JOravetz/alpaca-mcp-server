# Stock Market Scrapers

Command-line tools for fetching stock data from financial websites for day-trading research.

## Available Scrapers

### Perplexity Finance Scrapers

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `pplx-stock` | undetected-chromedriver | ~18s | Full HTML with AI summaries, news |
| `pplx-stock-fast` | DrissionPage + REST API | ~8s | Quick structured JSON quotes |
| `pplx-stock-drission` | DrissionPage | ~17s | Alternative to pplx-stock |
| `pplx-format.py` | Python | - | JSON formatter for pplx-stock-fast |

### Finviz Scrapers

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `finviz-premarket` | requests + BeautifulSoup | ~2-3s | Top gainers/losers/volatile/active + quotes |
| `finviz-format.py` | Python | - | JSON formatter for finviz-premarket |

## Installation

### Prerequisites

```bash
# System packages (for Perplexity scrapers)
sudo apt install xvfb html2text

# Python packages (via uv in project root)
uv add DrissionPage undetected-chromedriver requests beautifulsoup4
```

### Setup

Option 1: Symlink to ~/bin (recommended):
```bash
mkdir -p ~/bin
ln -sf $(pwd)/pplx-stock ~/bin/
ln -sf $(pwd)/pplx-stock-fast ~/bin/
ln -sf $(pwd)/pplx-stock-drission ~/bin/
ln -sf $(pwd)/pplx-format.py ~/bin/
ln -sf $(pwd)/finviz-premarket ~/bin/
ln -sf $(pwd)/finviz-format.py ~/bin/
```

Option 2: Add this directory to PATH:
```bash
export PATH="$PATH:/path/to/alpaca-mcp-server-enhanced/external_tools/scrapers"
```

---

## Perplexity Finance Scrapers

### Full Analysis (pplx-stock)

```bash
# Get comprehensive AI-powered analysis
pplx-stock NVDA

# Raw HTML output
pplx-stock AMD --raw
```

**Output includes:**
- Real-time quotes with after-hours data
- AI-written daily price movement summaries
- Latest news headlines
- Bull/bear analyst cases
- Company profile

### Quick Quotes (pplx-stock-fast)

```bash
# Pretty terminal output
pplx-stock-fast AAPL

# JSON for programmatic use
pplx-stock-fast TSLA --json
```

**Sample output:**
```
============================================================
 Apple Inc. (AAPL)
============================================================

 Price:          $278.78
 Change:         -1.92 (-0.68%)
 After Hours:    $279.00 (+0.08%)

 Day Range:      $278.05 - $281.14
 52W Range:      $169.21 - $288.62
 ...
```

### How It Works

These scrapers bypass Cloudflare protection by:

1. **Running Chrome in "headed" mode** - Headless browsers are easily detected
2. **Using Xvfb virtual display** - Chrome renders to invisible framebuffer
3. **Forcing X11 over Wayland** - Modern Linux uses Wayland; we force X11 for Xvfb compatibility
4. **Patched ChromeDriver** - undetected-chromedriver/DrissionPage evade bot detection

### REST API Discovery

`pplx-stock-fast` uses Perplexity's internal REST APIs for faster data retrieval:

```
/rest/finance/quote/{ticker}     # Real-time quotes
/rest/finance/profile/{ticker}   # Company profile
/rest/finance/earnings/{ticker}  # Earnings data
/rest/finance/financials/{ticker} # Financial statements
```

---

## Finviz Screener

### Usage

```bash
# Top gainers (default)
finviz-premarket

# Other scans
finviz-premarket --losers     # Top losers (for potential shorts)
finviz-premarket --volatile   # Most volatile stocks
finviz-premarket --active     # Most active by volume

# Individual stock quote with news, analyst ratings, insider trading
finviz-premarket --quote NVDA

# JSON output for programmatic use
finviz-premarket --gainers --json
```

### Sample Output

```
======================================================================
 FINVIZ GAINERS - 2025-12-06 07:08:01
======================================================================

 TICKER        PRICE     CHANGE       VOLUME    MKT CAP SECTOR
----------------------------------------------------------------------
 TGL           25.44    276.44%   23,393,213     21.56M Technology
 SMX          331.98    135.45%    3,850,848    348.77M Industrials
 WHLR           6.41     97.84%   87,388,444      4.42M Real Estate
 GURE           8.19     72.78%    8,775,132     11.32M Basic Materials
 DBRG          14.12     45.27%   55,889,121      2.66B Financial
 ...

 Showing 20 of 20 results

 Data is 15-20 min delayed (free tier). Elite subscription required for real-time.
======================================================================
```

### Individual Stock Quote

```bash
finviz-premarket --quote NVDA --json
```

Returns comprehensive data including:
- All fundamentals (P/E, Market Cap, RSI, Beta, etc.)
- Latest news headlines with sources
- Analyst ratings and price targets
- Insider trading activity

### Important Notes

**Data Delay:**
- Free tier: 15-20 minute delayed quotes
- Elite ($24.96/mo): Real-time data, pre-market gaps, CSV export

**Best Use Cases:**
- Morning research and watchlist building
- News aggregation and sentiment analysis
- Sector/industry screening
- End-of-day analysis
- Analyst ratings tracking

**NOT Suitable For:**
- Real-time trading decisions (use Alpaca MCP tools instead)
- Pre-market gap data (requires Elite)

---

## Day-Trading Workflow Integration

### Morning Pre-Market Research

```bash
#!/bin/bash
# morning_research.sh - Run before market open

echo "=== FINVIZ TOP GAINERS ==="
finviz-premarket --gainers

echo ""
echo "=== AI ANALYSIS FOR TOP PICKS ==="
for ticker in $(finviz-premarket --json | jq -r '.stocks[:3][].ticker'); do
    echo "--- $ticker ---"
    pplx-stock-fast $ticker
    sleep 2
done
```

### Combined Analysis Pipeline

```bash
#!/bin/bash
# Get Finviz screener data, then deep-dive with Perplexity AI

TICKER="NVDA"

echo "=== FINVIZ DATA ==="
finviz-premarket --quote $TICKER

echo ""
echo "=== PERPLEXITY AI ANALYSIS ==="
pplx-stock $ticker
```

### Export to JSON for Automation

```bash
# Get top 5 gainers as JSON
finviz-premarket --json | jq '.stocks[:5]'

# Extract just tickers
finviz-premarket --json | jq -r '.stocks[].ticker'

# Filter by sector
finviz-premarket --json | jq '.stocks | map(select(.sector == "Technology"))'
```

---

## Troubleshooting

### Perplexity Scrapers

**Chrome Version Mismatch:**
Update `version_main` in the scripts to match your Chrome version:
```bash
google-chrome --version  # Check your version
```

**Window Still Appearing:**
Ensure X11 forcing is complete:
- `XDG_SESSION_TYPE=x11`
- `GDK_BACKEND=x11`
- `--ozone-platform=x11` in Chrome options

### Finviz Scraper

**Rate Limiting:**
Add delays between requests when batch processing:
```bash
for ticker in NVDA AMD AAPL; do
    finviz-premarket --quote $ticker
    sleep 2
done
```

**No Data Found:**
Finviz occasionally changes their HTML structure. If parsing fails, check for
updates to the scraper.

---

## Documentation

- [PPLX_STOCK_SCRAPER.md](../../docs/PPLX_STOCK_SCRAPER.md) - Perplexity scraper detailed guide
- [PPLX_SCRAPER_RESEARCH.md](../../docs/PPLX_SCRAPER_RESEARCH.md) - Technology comparison

## Performance Comparison

| Tool | Speed | Data Richness | Real-time | No Browser |
|------|-------|---------------|-----------|------------|
| `finviz-premarket` | **~2s** | ★★★☆☆ | Delayed | ✅ |
| `pplx-stock-fast` | ~8s | ★★★★☆ | Real-time | ❌ |
| `pplx-stock` | ~18s | ★★★★★ | Real-time | ❌ |

**Recommendation:**
- Use `finviz-premarket` for fast screener scans
- Use `pplx-stock-fast` for quick AI-powered quotes
- Use `pplx-stock` for comprehensive research with AI analysis
