# Stock Market Scrapers - Technical Architecture

This document provides deep technical details about the scraper implementations, research findings, and the technology decisions made during development.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Technology Stack](#technology-stack)
4. [Individual Scraper Details](#individual-scraper-details)
5. [API Discovery & Reverse Engineering](#api-discovery--reverse-engineering)
6. [Test Results](#test-results)
7. [Performance Benchmarks](#performance-benchmarks)
8. [Future Improvements](#future-improvements)

---

## Overview

This suite of CLI scrapers was built for **aggressive day-trading research**. The goal is to aggregate data from multiple financial sources quickly, without requiring paid subscriptions or complex authentication.

### Design Principles

1. **Speed First**: Most scrapers complete in 1-3 seconds
2. **No Browser When Possible**: Use REST APIs and HTML scraping to avoid heavy browser automation
3. **Zero External Dependencies**: Fast scrapers use Python's `urllib` stdlib only
4. **JSON + Pretty Output**: All scrapers support `--json` for automation and pretty terminal output for humans
5. **Composable**: Outputs can be piped together with `jq` for complex workflows

---

## Architecture Patterns

### Bash Wrapper + Embedded Python Pattern

All scrapers follow this architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     Bash Wrapper Script                      │
│  - Argument parsing (getopts)                               │
│  - Creates temporary Python script                          │
│  - Handles output formatting                                │
│  - Cleanup on exit                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Embedded Python Script                     │
│  - HTTP requests (urllib.request)                           │
│  - Data parsing (regex, json)                               │
│  - Business logic                                           │
│  - JSON output to stdout                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python Formatter                          │
│  - Reads JSON from stdin                                    │
│  - ANSI color-coded terminal output                         │
│  - Human-readable tables and summaries                      │
└─────────────────────────────────────────────────────────────┘
```

### Why This Pattern?

1. **Self-contained**: Single file deployment, no package installation
2. **Fast startup**: No Python environment activation needed
3. **Portable**: Works on any system with Python 3 and bash
4. **Debuggable**: `--json` bypasses formatter for raw data inspection

---

## Technology Stack

### Fast Scrapers (No Browser)

| Scraper | Technology | Why |
|---------|------------|-----|
| `stocktwits-sentiment` | urllib + JSON API | Free unauthenticated REST API |
| `barchart-options` | urllib + Session Cookies | Internal API with XSRF token |
| `shortsqueeze-scanner` | urllib + HTML regex | Simple HTML table structure |
| `finviz-premarket` | requests + BeautifulSoup | Complex HTML needs proper parsing |

### Browser-Based Scrapers (Cloudflare Bypass)

| Scraper | Technology | Why |
|---------|------------|-----|
| `pplx-stock` | undetected-chromedriver | Cloudflare + heavy JavaScript |
| `pplx-stock-fast` | DrissionPage + REST API | Hybrid: browser for auth, API for data |
| `pplx-stock-drission` | DrissionPage | Alternative driver for comparison |

### Cloudflare Bypass Techniques

Perplexity Finance uses aggressive bot detection. Our solution:

```python
# 1. Headed mode (not headless) - headless is easily detected
options.headless = False

# 2. Virtual display instead of headless
Xvfb :99 -screen 0 1920x1080x24

# 3. Force X11 on Wayland systems
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11

# 4. Chrome options to appear human
options.add_argument('--ozone-platform=x11')
options.add_argument('--disable-blink-features=AutomationControlled')

# 5. Patched ChromeDriver (undetected-chromedriver)
# Modifies Chrome binary to remove automation fingerprints
```

---

## Individual Scraper Details

### Stocktwits Sentiment Scanner

**API Discovery:**
```
GET https://api.stocktwits.com/api/2/trending/symbols.json
GET https://api.stocktwits.com/api/2/streams/symbol/{TICKER}.json
```

**Authentication:** None required (free public API)

**Rate Limits:** ~200 requests/hour

**Data Flow:**
```
User Input → Stocktwits API → JSON Response → Sentiment Calculation → Output
```

**Sentiment Calculation:**
```python
bullish_pct = bullish / (bullish + bearish) * 100
sentiment_score = bullish_pct - bearish_pct  # Range: -100 to +100
```

**Test Results (2025-12-06):**
```
$ stocktwits-sentiment --trending
✓ Successfully fetched 30 trending symbols
✓ Top trending: TGL (score: 9.55), CVNA (score: 9.01)
✓ Response time: ~1.2 seconds

$ stocktwits-sentiment -s NVDA
✓ Fetched 15 messages with sentiment tags
✓ Sentiment breakdown: 60% Bullish, 0% Bearish, 40% Neutral
✓ Watchlist count: 635,000 traders
✓ Response time: ~1.4 seconds
```

---

### Barchart Options Flow Scanner

**API Discovery Process:**

1. Opened Chrome DevTools on barchart.com/options/unusual-activity
2. Observed XHR requests to internal API
3. Identified authentication mechanism: Session cookies + XSRF token
4. Reverse-engineered API parameters

**Authentication Flow:**
```
1. GET /options/unusual-activity → Set-Cookie: XSRF-TOKEN=...
2. Extract XSRF token from cookies
3. Include X-XSRF-TOKEN header in API requests
4. API now returns data (no login required)
```

**API Endpoints:**
```
GET /proxies/core-api/v1/options/get?list=options.mostActive.us&...
GET /proxies/core-api/v1/options/get?list=options.unusual.us&...
```

**Key Parameters:**
```
fields=baseSymbol,baseLastPrice,symbolType,strikePrice,expirationDate,
       daysToExpiration,bidPrice,askPrice,lastPrice,volume,openInterest,
       volumeOpenInterestRatio
orderBy=volume|volumeOpenInterestRatio
orderDir=desc
raw=1  # Returns raw numeric values
limit=30
```

**Test Results (2025-12-06):**
```
$ barchart-options --unusual
✓ Fetched 30 options with unusual Vol/OI ratios
✓ Highest Vol/OI: 119.9 (AAL Put $13 May 2026)
✓ Put/Call ratio: 0.23 (Bullish)
✓ Response time: ~2.3 seconds

$ barchart-options -s NVDA
✓ Fetched 30 NVDA options sorted by volume
✓ Most active: $185 Call (155.9K volume)
✓ Response time: ~2.1 seconds
```

**Note:** Pre-market, the `--unusual` mode returns 0 results (no options trading yet). Use `--active` for general market data.

---

### Short Squeeze Scanner

**Data Source:** highshortinterest.com

**Scraping Approach:** Simple HTML table parsing with regex

**HTML Structure:**
```html
<tr>
  <td><a href="...">HTZ</a></td>
  <td>Hertz Global Holdings Inc</td>
  <td>Nasdaq</td>
  <td>43.50%</td>
  <td>126.27M</td>
  <td>311.59M</td>
  <td>Passenger Transportation</td>
</tr>
```

**Regex Pattern:**
```python
row_pattern = re.compile(
    r'<tr>\s*<td[^>]*>\s*<a[^>]*>([A-Z]+)</a>\s*</td>\s*'
    r'<td[^>]*>([^<]*)</td>\s*'  # Company
    r'<td[^>]*>([^<]*)</td>\s*'  # Exchange
    r'<td[^>]*>([^<]*)</td>\s*'  # Short Interest %
    r'<td[^>]*>([^<]*)</td>\s*'  # Float
    r'<td[^>]*>([^<]*)</td>\s*'  # Outstanding
    r'<td[^>]*>([^<]*)</td>',    # Industry
    re.IGNORECASE | re.DOTALL
)
```

**Test Results (2025-12-06):**
```
$ shortsqueeze-scanner
✓ Fetched 49 stocks with >20% short interest
✓ Data last updated: November 26, 2025
✓ Highest SI: HTZ (43.5%), AIRS (42.3%), GRPN (38.8%)
✓ Response time: ~1.5 seconds

$ shortsqueeze-scanner --min-si 35
✓ Filtered to 5 extreme squeeze candidates
✓ All with >35% short interest
✓ Response time: ~1.4 seconds

$ shortsqueeze-scanner --nasdaq --min-si 30 --json | jq '.stocks[:3]'
✓ JSON output properly formatted
✓ Exchange filter working correctly
```

---

### Finviz Premarket Scanner

**Technology:** requests + BeautifulSoup (HTML too complex for regex)

**Endpoints:**
```
https://finviz.com/screener.ashx?v=111&s=ta_topgainers
https://finviz.com/screener.ashx?v=111&s=ta_toplosers
https://finviz.com/screener.ashx?v=111&s=ta_mostvolatile
https://finviz.com/screener.ashx?v=111&s=ta_mostactive
https://finviz.com/quote.ashx?t=NVDA
```

**Test Results (2025-12-06 07:08):**
```
$ finviz-premarket --gainers
✓ Fetched top 20 gainers
✓ Top movers: TGL (+276%), SMX (+135%), WHLR (+98%)
✓ Response time: ~2.1 seconds

$ finviz-premarket --quote NVDA --json
✓ Fetched all fundamentals (P/E, Market Cap, etc.)
✓ Fetched 10 recent news headlines
✓ Fetched analyst ratings and targets
✓ Response time: ~2.8 seconds
```

---

### Perplexity Finance Scrapers

**REST API Discovery:**

Through browser DevTools, we discovered Perplexity's internal APIs:

```
GET /rest/finance/quote/{ticker}      # Real-time quote data
GET /rest/finance/profile/{ticker}    # Company profile
GET /rest/finance/earnings/{ticker}   # Earnings data
GET /rest/finance/financials/{ticker} # Financial statements
GET /rest/finance/movers              # Top movers
```

**`pplx-stock-fast` Hybrid Approach:**

1. Launch browser with DrissionPage (for Cloudflare bypass)
2. Navigate to finance page (establishes session)
3. Call REST APIs directly (fast, structured data)
4. Return JSON without HTML parsing

**Test Results:**
```
$ pplx-stock-fast NVDA
✓ Real-time quote: $182.35
✓ After-hours: $182.50 (+0.08%)
✓ Day range, 52W range, market cap
✓ Response time: ~8 seconds

$ pplx-stock NVDA
✓ Full HTML page with AI summaries
✓ Bull/bear cases from analysts
✓ Latest news headlines
✓ Response time: ~18 seconds
```

---

## API Discovery & Reverse Engineering

### Methodology

1. **Browser DevTools Network Tab**: Monitor XHR/Fetch requests
2. **Request Analysis**: Identify headers, cookies, authentication
3. **Parameter Testing**: Vary query params to understand API capabilities
4. **Error Handling**: Test edge cases and error responses
5. **Documentation**: Record findings for maintainability

### Key Findings

| Site | API Type | Auth Method | Rate Limits |
|------|----------|-------------|-------------|
| Stocktwits | Public REST | None | ~200/hour |
| Barchart | Internal REST | Session + XSRF | Unknown (no issues) |
| Finviz | HTML scraping | None | ~60/min recommended |
| Highshortinterest | HTML scraping | None | Unknown (simple table) |
| Perplexity | Internal REST | Cloudflare session | Unknown |
| Benzinga | Internal REST | **Requires login** | N/A |

### Benzinga Assessment

**Status:** Not implemented (requires authentication)

**Research Findings:**
- Next.js application with heavy JavaScript rendering
- Data API exists at `data-api-next.benzinga.com`
- API returns `{"message":"no Route matched"}` without auth
- Would require browser automation + login credentials
- **Decision:** Deprioritized - other sources provide similar data

---

## Performance Benchmarks

Tested on Ubuntu 22.04, Python 3.12, 100Mbps connection:

| Scraper | Avg Time | Memory | CPU | Dependencies |
|---------|----------|--------|-----|--------------|
| `stocktwits-sentiment` | 1.2s | 15MB | Low | urllib only |
| `shortsqueeze-scanner` | 1.5s | 15MB | Low | urllib only |
| `barchart-options` | 2.2s | 18MB | Low | urllib only |
| `finviz-premarket` | 2.5s | 45MB | Low | requests, bs4 |
| `pplx-stock-fast` | 8s | 350MB | Medium | DrissionPage |
| `pplx-stock` | 18s | 400MB | High | undetected-chromedriver |

### Why Browser Scrapers Are Slower

```
Browser-based:
1. Launch Chrome process (~2s)
2. Navigate to URL (~1s)
3. Wait for Cloudflare challenge (~3s)
4. Wait for JavaScript rendering (~2s)
5. Parse page content (~0.5s)
Total: ~8-18s

API-based:
1. HTTP request (~0.5s)
2. Parse JSON (~0.01s)
Total: ~1-2s
```

---

## Test Results Summary

### All Scrapers Tested (2025-12-06 Pre-Market)

| Scraper | Status | Notes |
|---------|--------|-------|
| `stocktwits-sentiment --trending` | ✅ Working | 30 symbols, 1.2s |
| `stocktwits-sentiment -s NVDA` | ✅ Working | Sentiment + messages |
| `barchart-options --active` | ✅ Working | 30 options, 2.2s |
| `barchart-options --unusual` | ⚠️ Empty pre-market | Works during market hours |
| `barchart-options -s NVDA` | ✅ Working | NVDA options chain |
| `shortsqueeze-scanner` | ✅ Working | 49 stocks >20% SI |
| `shortsqueeze-scanner --min-si 35` | ✅ Working | 5 extreme candidates |
| `shortsqueeze-scanner --nasdaq` | ✅ Working | Exchange filter works |
| `finviz-premarket --gainers` | ✅ Working | Top 20 gainers |
| `finviz-premarket --quote NVDA` | ✅ Working | Full fundamentals |
| `pplx-stock-fast NVDA` | ✅ Working | Fast quote data |
| `pplx-stock NVDA` | ✅ Working | Full AI analysis |

---

## Future Improvements

### Planned Enhancements

1. **Caching Layer**: Cache API responses to reduce rate limit hits
2. **Parallel Execution**: Fetch from multiple sources simultaneously
3. **WebSocket Support**: Real-time streaming for Stocktwits
4. **MCP Integration**: Expose scrapers as MCP tools for Claude Code
5. **Error Recovery**: Automatic retry with exponential backoff

### Potential New Sources

| Source | Difficulty | Data Type | Priority |
|--------|------------|-----------|----------|
| Yahoo Finance | Easy | Quotes, fundamentals | Medium |
| TradingView | Hard | Technical analysis | Low |
| SEC EDGAR | Medium | Filings, insiders | Medium |
| Unusual Whales | Hard | Options flow (paid) | Low |

### Code Quality Improvements

1. Add unit tests for parsers
2. Type hints throughout
3. Proper logging with `--verbose` flag
4. Configuration file for API endpoints
5. Docker container for reproducible environment

---

## Conclusion

This scraper suite provides **comprehensive day-trading research capabilities** using a combination of:

- **Public REST APIs** (Stocktwits) - Fast, reliable, free
- **Reverse-engineered internal APIs** (Barchart) - Professional-grade data
- **HTML scraping** (Finviz, Highshortinterest) - When APIs unavailable
- **Browser automation** (Perplexity) - Last resort for heavy protection

The architecture prioritizes **speed and simplicity**, with most scrapers completing in under 3 seconds using only Python's standard library.
