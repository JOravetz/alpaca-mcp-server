# Perplexity Finance Scraper: Research & Technology Comparison

This document details the research, testing, and implementation of various web scraping technologies to extract AI-powered stock analysis from Perplexity Finance.

## The Challenge

**Goal:** Scrape rich financial data from [Perplexity Finance](https://www.perplexity.ai/finance/) - an AI-powered platform that provides:
- Real-time stock quotes with after-hours data
- AI-written daily price movement summaries
- Bull/bear analyst cases
- Company profiles and news

**Obstacles:**
1. Cloudflare protection blocks automated requests
2. Dynamic JavaScript content requires browser rendering
3. Need to run headlessly without interrupting user's desktop

## Technologies Tested

### 1. Playwright with Stealth Plugin

**Technology:** Microsoft's browser automation framework with anti-detection patches.

**Test Result:** ❌ **FAILED - Platform Not Supported**

```
ERROR: Playwright does not support chromium on ubuntu26.04-x64
```

**Analysis:** Playwright has excellent headless support and stealth capabilities, but lacks support for the latest Ubuntu versions. This would be the ideal solution if platform support existed.

**Recommendation:** Monitor for Ubuntu 26.04 support in future Playwright releases.

---

### 2. Browserless.io Cloud API

**Technology:** Cloud-hosted browser infrastructure with built-in Cloudflare bypass.

**Test Result:** ✅ **VIABLE (Paid Service)**

**Analysis:** Browserless offers BrowserQL for solving Cloudflare challenges and CAPTCHAs automatically. Requires subscription.

**Features:**
- Cloudflare bypass built-in
- No local browser management
- Puppeteer/Playwright compatible API
- CAPTCHA solving included

**Pricing:** Subscription-based (see [browserless.io/pricing](https://browserless.io/pricing))

**Recommendation:** Good option for production deployments where reliability is critical and budget allows.

---

### 3. curl-impersonate

**Technology:** Modified curl that mimics Chrome's TLS fingerprint.

**Test Result:** ❌ **FAILED - Cloudflare Blocked**

```bash
$ curl-impersonate-chrome "https://www.perplexity.ai/finance/AAPL"
# Returns: "Just a moment..." Cloudflare challenge page
```

**Analysis:** While curl-impersonate successfully mimics Chrome's TLS handshake, Cloudflare's JavaScript challenge requires actual browser execution. The tool cannot execute JavaScript challenges.

**Use Cases Where It Works:**
- Sites without JavaScript challenges
- Basic bot detection based on TLS fingerprinting only
- Rate limiting based on request patterns

**Recommendation:** Not suitable for Cloudflare-protected sites with JS challenges.

---

### 4. Perplexity Official API

**Technology:** Official REST API from Perplexity.

**Test Result:** ⚠️ **PARTIAL - No Finance-Specific Endpoints**

**Available APIs:**
- Search API - General web search
- Sonar Chat Completions - AI chat interface
- SEC filings search (new in 2025)

**Missing:**
- No dedicated `/finance/quote` endpoint
- No direct access to the Finance platform data
- Finance features only available via web interface

**Discovery:** We found **internal REST APIs** that work from within an authenticated browser session:
```
/rest/finance/quote/{ticker}
/rest/finance/profile/{ticker}
/rest/finance/earnings/{ticker}
/rest/finance/financials/{ticker}
```

**Recommendation:** Use browser automation to establish session, then call REST APIs directly for faster data retrieval.

---

### 5. undetected-chromedriver (Original Solution)

**Technology:** Patched Selenium ChromeDriver that evades bot detection.

**Test Result:** ✅ **WORKS**

**Implementation:** Requires Xvfb virtual display + X11 forcing to run headlessly on Wayland systems.

**Performance:** ~18 seconds per request (full page load + scrolling)

**Key Configuration:**
```python
options.add_argument('--ozone-platform=x11')  # Force X11 over Wayland
os.environ['XDG_SESSION_TYPE'] = 'x11'
os.environ['GDK_BACKEND'] = 'x11'
```

---

### 6. DrissionPage (Best Solution Found)

**Technology:** Modern Python browser automation combining Selenium and requests.

**Test Result:** ✅ **WORKS EXCELLENTLY**

**Performance:** ~8 seconds per request (using REST API approach)

**Why It's Better:**
- Cleaner API than Selenium
- Better Cloudflare bypass capabilities
- Can execute JavaScript to call internal APIs
- Lighter resource footprint

## Final Implementation: Three Scrapers

### Scraper 1: `pplx-stock` (Full HTML)
- **Technology:** undetected-chromedriver + Xvfb
- **Output:** Full page content with news, analysis, price movements
- **Speed:** ~18 seconds
- **Best For:** Comprehensive research, AI summaries, news

### Scraper 2: `pplx-stock-fast` (REST API)
- **Technology:** DrissionPage + internal REST APIs
- **Output:** Structured JSON (quote + profile)
- **Speed:** ~8 seconds
- **Best For:** Quick quotes, programmatic access, batch processing

### Scraper 3: `pplx-stock-drission` (Full HTML via DrissionPage)
- **Technology:** DrissionPage + Xvfb
- **Output:** Full page content
- **Speed:** ~17 seconds
- **Best For:** Alternative to undetected-chromedriver

## Performance Comparison

| Scraper | Technology | Speed | Data Richness | Reliability |
|---------|-----------|-------|---------------|-------------|
| `pplx-stock` | undetected-chromedriver | 18s | ★★★★★ | ★★★★☆ |
| `pplx-stock-fast` | DrissionPage + REST | **8s** | ★★★☆☆ | ★★★★★ |
| `pplx-stock-drission` | DrissionPage | 17s | ★★★★★ | ★★★★★ |

## The Wayland Problem & Solution

Modern Linux systems use Wayland as the display server. Chrome connects directly to Wayland, bypassing our Xvfb virtual display.

**Symptoms:** Chrome window appears on your screen despite Xvfb being active.

**Solution:** Force Chrome to use X11:
```bash
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11
# In Chrome options:
options.add_argument('--ozone-platform=x11')
```

This makes Chrome connect to the X11 display (:99) managed by Xvfb instead of your Wayland desktop.

## REST API Discovery

By inspecting Perplexity's page source, we discovered internal REST endpoints:

```javascript
// Endpoints preloaded in HTML:
/rest/finance/quote/{ticker}?with_history=true&with_ui_hints=true
/rest/finance/profile/{ticker}
/rest/finance/documents/{ticker}
/rest/finance/earnings/{ticker}
/rest/finance/financials/{ticker}
```

**Accessing These APIs:**
1. Cannot call directly (Cloudflare blocks)
2. Must establish browser session first
3. Then use `page.run_js()` to fetch from within browser context

```python
quote = page.run_js('''
    return fetch('/rest/finance/quote/NVDA')
        .then(r => r.json())
''')
```

## Sample REST API Response

```json
{
  "symbol": "NVDA",
  "name": "NVIDIA Corporation",
  "price": 182.41,
  "change": -0.97,
  "changesPercentage": -0.52896,
  "afterHoursPrice": 182.355,
  "afterHoursPercentChange": -0.0302,
  "marketCap": 4441136606729,
  "pe": 45.26,
  "eps": 4.03,
  "dayLow": 180.91,
  "dayHigh": 184.66,
  "yearLow": 86.62,
  "yearHigh": 212.19,
  "volume": 142982463,
  "isMarketOpen": false
}
```

## Creative Use Cases

### 1. Pre-Market Dashboard
```bash
#!/bin/bash
# Run at 6 AM - quick overview of watchlist
for ticker in NVDA AMD TSLA AAPL; do
    echo "=== $ticker ==="
    pplx-stock-fast $ticker --json | jq '{
        symbol, price, changesPercentage,
        afterHoursPrice, afterHoursPercentChange
    }'
done
```

### 2. Batch Research Pipeline
```bash
#!/bin/bash
# Generate research files for scanner results
while read ticker; do
    pplx-stock $ticker > "research/${ticker}_$(date +%Y%m%d).txt" &
    sleep 2  # Rate limiting
done < today_picks.txt
wait
```

### 3. Trading Signal Integration
```python
import subprocess
import json

def get_quote(ticker):
    result = subprocess.run(
        ['pplx-stock-fast', ticker, '--json'],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

# Check for after-hours momentum
data = get_quote('NVDA')
quote = data['quote']
if quote['afterHoursPercentChange'] > 2.0:
    print(f"🚀 {quote['symbol']} up {quote['afterHoursPercentChange']}% after hours!")
```

### 4. Multi-Symbol Comparison
```bash
#!/bin/bash
# Compare semiconductor stocks
echo "Symbol,Price,Change%,PE,MarketCap" > semis.csv
for ticker in NVDA AMD INTC AVGO QCOM; do
    pplx-stock-fast $ticker --json | jq -r '
        [.quote.symbol, .quote.price, .quote.changesPercentage,
         .quote.pe, .quote.marketCap] | @csv
    ' >> semis.csv
done
```

### 5. AI Analysis Pipeline
```bash
# Combine Perplexity data with Claude analysis
ANALYSIS=$(pplx-stock NVDA)
echo "Based on this Perplexity Finance data, provide a day-trading recommendation:

$ANALYSIS" | claude --model claude-sonnet-4-20250514
```

### 6. Earnings Alert System
```python
import subprocess
import json
from datetime import datetime

def check_earnings_move(ticker):
    result = subprocess.run(
        ['pplx-stock-fast', ticker, '--json'],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)

    change = abs(data['quote']['changesPercentage'])
    if change > 5:
        return f"⚠️ {ticker}: {change:.1f}% move - possible earnings reaction"
    return None

# Check watchlist
for ticker in ['NVDA', 'AMD', 'AAPL', 'MSFT']:
    alert = check_earnings_move(ticker)
    if alert:
        print(alert)
```

## Installation

### Prerequisites
```bash
# System packages
sudo apt install xvfb html2text

# Python packages (via uv)
uv add DrissionPage undetected-chromedriver
```

### Script Locations
```
~/bin/pplx-stock          # Full HTML scraper
~/bin/pplx-stock-fast     # Fast REST API scraper
~/bin/pplx-stock-drission # DrissionPage HTML scraper
~/bin/pplx-format.py      # JSON formatter
```

## Troubleshooting

### Chrome Version Mismatch
```python
# Update version_main to match your Chrome
driver = uc.Chrome(version_main=142, ...)

# Check your version:
google-chrome --version
```

### Window Still Appearing
Ensure all X11 forcing is in place:
```bash
export DISPLAY=:99
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11
# Chrome flag: --ozone-platform=x11
```

### Rate Limiting
Add delays between requests:
```bash
for ticker in $TICKERS; do
    pplx-stock-fast $ticker
    sleep 5  # Be respectful
done
```

## Future Improvements

1. **Session Caching:** Keep browser session alive for faster subsequent requests
2. **Parallel Processing:** Run multiple browser instances for batch processing
3. **Webhook Integration:** Push alerts to Discord/Slack on price movements
4. **Playwright Support:** Monitor for Ubuntu 26.04 support
5. **Official API:** Watch for Perplexity Finance API release

## Conclusion

After testing 6 different technologies, **DrissionPage with REST API extraction** emerged as the best solution - providing 2x speed improvement over full HTML scraping while maintaining reliability.

The key insight was discovering Perplexity's internal REST APIs, which provide structured JSON data much faster than parsing HTML.

For comprehensive analysis including AI-written summaries and news, use `pplx-stock`. For quick programmatic access, use `pplx-stock-fast`.
