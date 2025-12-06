# Perplexity Finance Scrapers

Headless web scrapers for fetching AI-powered stock analysis from Perplexity Finance.

## Scripts

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `pplx-stock` | undetected-chromedriver | ~18s | Full HTML with AI summaries, news |
| `pplx-stock-fast` | DrissionPage + REST API | ~8s | Quick structured JSON quotes |
| `pplx-stock-drission` | DrissionPage | ~17s | Alternative to pplx-stock |
| `pplx-format.py` | Python | - | JSON formatter for pplx-stock-fast |

## Installation

### Prerequisites

```bash
# System packages
sudo apt install xvfb html2text

# Python packages (via uv in project root)
uv add DrissionPage undetected-chromedriver
```

### Setup

Option 1: Symlink to ~/bin (recommended):
```bash
mkdir -p ~/bin
ln -sf $(pwd)/pplx-stock ~/bin/
ln -sf $(pwd)/pplx-stock-fast ~/bin/
ln -sf $(pwd)/pplx-stock-drission ~/bin/
ln -sf $(pwd)/pplx-format.py ~/bin/
```

Option 2: Add this directory to PATH:
```bash
export PATH="$PATH:/path/to/alpaca-mcp-server-enhanced/external_tools/scrapers"
```

## Usage

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

## How It Works

These scrapers bypass Cloudflare protection by:

1. **Running Chrome in "headed" mode** - Headless browsers are easily detected
2. **Using Xvfb virtual display** - Chrome renders to invisible framebuffer
3. **Forcing X11 over Wayland** - Modern Linux uses Wayland; we force X11 for Xvfb compatibility
4. **Patched ChromeDriver** - undetected-chromedriver/DrissionPage evade bot detection

### Key Configuration

```bash
# Environment variables
export DISPLAY=:99
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11

# Chrome flags
--ozone-platform=x11
--no-sandbox
--disable-dev-shm-usage
```

## REST API Discovery

`pplx-stock-fast` uses Perplexity's internal REST APIs for faster data retrieval:

```
/rest/finance/quote/{ticker}     # Real-time quotes
/rest/finance/profile/{ticker}   # Company profile
/rest/finance/earnings/{ticker}  # Earnings data
/rest/finance/financials/{ticker} # Financial statements
```

These APIs require an authenticated browser session (handled automatically).

## Documentation

- [PPLX_STOCK_SCRAPER.md](../../docs/PPLX_STOCK_SCRAPER.md) - Detailed usage guide
- [PPLX_SCRAPER_RESEARCH.md](../../docs/PPLX_SCRAPER_RESEARCH.md) - Technology comparison

## Troubleshooting

### Chrome Version Mismatch
Update `version_main` in the scripts to match your Chrome version:
```bash
google-chrome --version  # Check your version
```

### Window Still Appearing
Ensure X11 forcing is complete:
- `XDG_SESSION_TYPE=x11`
- `GDK_BACKEND=x11`
- `--ozone-platform=x11` in Chrome options

### Rate Limiting
Add delays between requests when batch processing:
```bash
for ticker in NVDA AMD AAPL; do
    pplx-stock-fast $ticker
    sleep 5
done
```
