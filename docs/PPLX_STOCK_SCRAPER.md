# Perplexity Finance Scrapers

A suite of command-line tools for fetching AI-powered stock analysis from Perplexity Finance without any browser window interrupting your workflow.

**See also:** [PPLX_SCRAPER_RESEARCH.md](PPLX_SCRAPER_RESEARCH.md) for detailed technology comparison and testing results.

## Overview

`pplx-stock` is a headless web scraper that extracts rich financial data from [Perplexity Finance](https://www.perplexity.ai/finance/) - an AI-powered stock research platform that provides real-time quotes, news analysis, price movement summaries, bull/bear cases, and more.

**Key Innovation:** Runs completely invisibly using a virtual X11 display, so you can fetch data in the background while working on other tasks.

## Available Scrapers

| Scraper | Technology | Speed | Best For |
|---------|-----------|-------|----------|
| `pplx-stock` | undetected-chromedriver | ~18s | Full content, AI summaries, news |
| `pplx-stock-fast` | DrissionPage + REST API | **~8s** | Quick quotes, programmatic access |
| `pplx-stock-drission` | DrissionPage | ~17s | Alternative to undetected-chromedriver |

## Technology Stack

| Component | Purpose |
|-----------|---------|
| **undetected-chromedriver** | Bypasses Cloudflare and bot detection systems |
| **DrissionPage** | Modern browser automation with better Cloudflare bypass |
| **Xvfb (X Virtual Framebuffer)** | Creates invisible virtual display for Chrome |
| **html2text** | Converts HTML to readable terminal output |
| **uv** | Fast Python package management |

### Why These Technologies?

1. **undetected-chromedriver** - Perplexity Finance uses Cloudflare protection. Regular Selenium/requests get blocked. This library patches Chrome to appear as a normal user browser.

2. **DrissionPage** - Modern Python browser automation that combines Selenium and requests. Better Cloudflare bypass and can execute JavaScript to call internal REST APIs for faster data retrieval.

3. **Xvfb + X11 Forcing** - The scraper runs Chrome in "headed" mode (with GUI) because headless mode is easily detected. But we redirect Chrome's display to a virtual framebuffer so no window appears on your screen.

4. **Wayland Bypass** - Modern Linux uses Wayland display server. We force Chrome to use X11 instead (`--ozone-platform=x11`, `XDG_SESSION_TYPE=x11`) so it connects to our virtual Xvfb display rather than your real Wayland desktop.

## Installation

### Prerequisites

```bash
# Install Xvfb and html2text
sudo apt install xvfb html2text

# Ensure uv is installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup

The script is located at `~/bin/pplx-stock`. Ensure it's executable and in your PATH:

```bash
chmod +x ~/bin/pplx-stock
export PATH="$HOME/bin:$PATH"  # Add to ~/.bashrc
```

## Usage

### pplx-stock (Full HTML Scraper)

```bash
# Get full stock analysis with AI summaries
pplx-stock AAPL
pplx-stock TSLA
pplx-stock AMD

# Raw HTML output (for parsing)
pplx-stock NVDA --raw
```

### pplx-stock-fast (Quick REST API Scraper)

```bash
# Get structured quote data (2x faster)
pplx-stock-fast NVDA          # Pretty terminal output
pplx-stock-fast NVDA --json   # Raw JSON for programmatic use

# Sample output:
# ============================================================
#  NVIDIA Corporation (NVDA)
# ============================================================
#  Price:          $182.41
#  Change:         -0.97 (-0.53%)
#  After Hours:    $182.36 (-0.03%)
#  ...
```

### Output Comparison

| Scraper | Output | Best For |
|---------|--------|----------|
| `pplx-stock` | Full text with news, AI analysis | Research, reading |
| `pplx-stock-fast` | Structured JSON/formatted | Scripts, automation |

## What Data You Get

Perplexity Finance provides incredibly rich AI-synthesized data:

### 1. Real-Time Quote Data
- Current price, after-hours price
- Day range, 52-week range
- Market cap, P/E ratio, EPS
- Volume, dividend yield

### 2. Latest Updates (News)
- Recent news headlines with timestamps
- Source attribution (Benzinga, Reuters, etc.)
- Direct links to articles

### 3. Latest Price Movement (AI-Generated)
This is the killer feature - **AI-written daily summaries** explaining why the stock moved:

```
Yesterday ($217.97, +0.92%)
Advanced Micro Devices shares are trading modestly higher after a strong
session, reflecting ongoing optimism around the company's AI and data center
roadmap, including bullish commentary on upcoming Helios rack and MI450
accelerators...
```

### 4. Recent Developments
- Key events affecting the stock
- Earnings reports, analyst actions
- Regulatory news, partnerships

### 5. Key Issues Analysis
- **Bullish view**: Why analysts are optimistic
- **Bearish view**: Risks and concerns
- Multiple source citations

### 6. Company Profile
- Full business description
- CEO, employee count
- Sector, industry classification

### 7. Related Data
- Peer companies with prices
- Top gainers/losers
- Watchlist suggestions

## Creative Use Cases

### 1. Morning Pre-Market Briefing

```bash
#!/bin/bash
# morning_briefing.sh - Run at 6 AM before market open

WATCHLIST="NVDA AMD TSLA AAPL MSFT"
for ticker in $WATCHLIST; do
    echo "===== $ticker ====="
    pplx-stock $ticker | grep -A 20 "Latest Price Movement"
    echo ""
done
```

### 2. Day-Trading Research Pipeline

```bash
# After your scanner finds hot stocks, get AI analysis
for symbol in $(cat todays_hot_picks.txt); do
    pplx-stock $symbol > "research/$symbol_$(date +%Y%m%d).txt"
done
```

### 3. Integration with Claude/AI Analysis

```bash
# Pipe to Claude for trade decision
ANALYSIS=$(pplx-stock NVDA)
echo "Based on this analysis, should I go long or short today?

$ANALYSIS" | claude
```

### 4. Automated Alert System

```bash
#!/bin/bash
# alert_on_news.sh - Check for breaking news

TICKER=$1
OUTPUT=$(pplx-stock $TICKER)

# Check for news in last 2 hours
if echo "$OUTPUT" | grep -q "hours_ago"; then
    notify-send "Breaking: $TICKER News" "New developments detected"
    echo "$OUTPUT" | grep -B2 -A5 "hours_ago"
fi
```

### 5. Bull/Bear Sentiment Extraction

```bash
# Extract just the bull/bear cases for quick sentiment read
pplx-stock TSLA | sed -n '/Bullish view/,/Bearish view/p'
pplx-stock TSLA | sed -n '/Bearish view/,/Key Issues/p'
```

### 6. Competitive Analysis

```bash
# Compare a stock with its peers
pplx-stock AMD | grep -A 30 "Peers"
```

### 7. Weekly Research Digest

```bash
#!/bin/bash
# weekly_digest.sh - Generate weekly research report

PORTFOLIO="NVDA AMD AAPL MSFT GOOGL TSLA"
REPORT="weekly_report_$(date +%Y%m%d).md"

echo "# Weekly Portfolio Research - $(date +%Y-%m-%d)" > $REPORT
echo "" >> $REPORT

for ticker in $PORTFOLIO; do
    echo "## $ticker" >> $REPORT
    echo "" >> $REPORT
    pplx-stock $ticker | head -100 >> $REPORT
    echo "" >> $REPORT
    echo "---" >> $REPORT
    echo "" >> $REPORT
    sleep 5  # Be nice to Perplexity's servers
done

echo "Report saved to $REPORT"
```

### 8. Earnings Watch

```bash
# Get latest earnings data for a stock
pplx-stock NVDA | grep -A 10 "Quarter Revenue"
```

### 9. Price Target Tracking

```bash
# Extract analyst price targets
pplx-stock AMD | grep -i "price target\|fair value\|rating"
```

### 10. Integration with MCP Trading System

```python
# In your trading bot
import subprocess

def get_perplexity_analysis(ticker: str) -> str:
    """Fetch AI-powered stock analysis from Perplexity Finance."""
    result = subprocess.run(
        ['pplx-stock', ticker],
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.stdout

# Use in trading decision
analysis = get_perplexity_analysis("NVDA")
if "bullish" in analysis.lower() and "breaking out" in analysis.lower():
    # Consider long position
    pass
```

## Performance

- **Startup time:** ~5 seconds (Chrome initialization)
- **Page load:** ~8 seconds (waiting for dynamic content)
- **Scrolling:** ~5 seconds (loading lazy content)
- **Total:** ~18-20 seconds per ticker

## Troubleshooting

### Chrome Version Mismatch

If you see errors about Chrome version, update the version number in the script:

```python
driver = uc.Chrome(version_main=142, options=options, headless=False)
#                              ^^^ Update this to match your Chrome version
```

Check your Chrome version:
```bash
google-chrome --version
```

### Window Still Appearing

If a Chrome window still appears on your screen, ensure these environment variables are set:
- `XDG_SESSION_TYPE=x11`
- `GDK_BACKEND=x11`
- Chrome flag: `--ozone-platform=x11`

### Cloudflare Blocks

If you're getting blocked, try:
1. Increasing sleep times
2. Adding random delays
3. Rotating user agents

### Missing Dependencies

```bash
# Install all required packages
sudo apt install xvfb html2text
pip install undetected-chromedriver pyvirtualdisplay
```

## Limitations

1. **Rate Limiting:** Don't hammer Perplexity's servers. Add delays between requests.
2. **Dynamic Content:** Some content may require additional scrolling or waiting.
3. **Format Changes:** If Perplexity updates their site layout, parsing may break.
4. **Chrome Updates:** May need to update `version_main` when Chrome updates.

## How It Works (Technical Deep-Dive)

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Terminal                          │
│                    pplx-stock NVDA                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       xvfb-run                              │
│  Creates virtual X11 display :99 (invisible to you)        │
│  Sets DISPLAY=:99 for all child processes                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Environment Variables Set                       │
│  XDG_SESSION_TYPE=x11  (Force X11, not Wayland)            │
│  GDK_BACKEND=x11       (Force GTK to use X11)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  undetected-chromedriver                    │
│  • Patches Chrome binary to avoid detection                │
│  • Removes navigator.webdriver flag                        │
│  • Uses real browser profile                               │
│  • --ozone-platform=x11 forces X11 rendering              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Chrome (Headed Mode)                       │
│  Renders to virtual display :99 (invisible)                │
│  Loads perplexity.ai/finance/NVDA                          │
│  Executes JavaScript, loads dynamic content                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Page Interaction                          │
│  1. Wait 8 seconds for initial load                        │
│  2. Scroll to bottom (trigger lazy loading)                │
│  3. Wait 3 seconds for content                             │
│  4. Scroll back to top                                     │
│  5. Capture full page HTML                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      html2text                              │
│  Converts HTML → readable plain text                       │
│  Strips tags, formats links, preserves structure           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Your Terminal                           │
│  Clean, readable stock analysis output                     │
└─────────────────────────────────────────────────────────────┘
```

## License

This tool is for personal research use only. Respect Perplexity's terms of service and rate limits.

## See Also

- [Perplexity Finance](https://www.perplexity.ai/finance/) - The data source
- [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) - Bot detection bypass
- [Alpaca MCP Server](../README.md) - Trading system integration
