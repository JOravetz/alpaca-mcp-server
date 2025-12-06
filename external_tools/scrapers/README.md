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

### Stocktwits Sentiment Scrapers

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `stocktwits-sentiment` | REST API (urllib) | ~1-2s | Social sentiment, trending, messages |
| `stocktwits-format.py` | Python | - | JSON formatter with sentiment visualization |

### Barchart Options Flow Scrapers

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `barchart-options` | REST API (urllib) | ~2-3s | Options flow, unusual activity, smart money |
| `barchart-format.py` | Python | - | JSON formatter with Vol/OI highlighting |

### Short Squeeze Scanner

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `shortsqueeze-scanner` | HTML scraping (urllib) | ~1-2s | High short interest stocks (>20% SI) |
| `shortsqueeze-format.py` | Python | - | JSON formatter with squeeze potential highlighting |

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
ln -sf $(pwd)/stocktwits-sentiment ~/bin/
ln -sf $(pwd)/stocktwits-format.py ~/bin/
ln -sf $(pwd)/barchart-options ~/bin/
ln -sf $(pwd)/barchart-format.py ~/bin/
ln -sf $(pwd)/shortsqueeze-scanner ~/bin/
ln -sf $(pwd)/shortsqueeze-format.py ~/bin/
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

## Stocktwits Sentiment Scanner

### Usage

```bash
# Top trending symbols (default)
stocktwits-sentiment

# Sentiment analysis for specific stock
stocktwits-sentiment --symbol NVDA
stocktwits-sentiment -s TSLA

# Get more messages for deeper analysis
stocktwits-sentiment --symbol AMD --messages 30

# JSON output for programmatic use
stocktwits-sentiment --trending --json
stocktwits-sentiment --symbol NVDA --json
```

### Sample Trending Output

```
======================================================================
 STOCKTWITS TRENDING - 2025-12-06 07:16:20
======================================================================

 #   TICKER   COMPANY                                SCORE   WATCHERS
----------------------------------------------------------------------
 1   TGL      TREASURE GLOBAL INC                    9.55      11.5K
 2   CVNA     Carvana Co.                            9.01      40.3K
 3   CVKD     Cadrenal Therapeutics, Inc.            7.11       5.5K
 ...

 Tip: Use --symbol TICKER for detailed sentiment analysis
======================================================================
```

### Sample Symbol Sentiment Output

```
======================================================================
 NVIDIA Corp (NVDA)
======================================================================

 Sentiment Analysis
-----------------------------------
   Overall Mood:   BULLISH
   Sentiment Score: +60.0%

   Bullish:    9 (60.0%)
   Bearish:    0 (0.0%)
   Neutral:    6
   Total:      15 messages analyzed

   [████████████████████████████████████████]

   Watchlist: 635K traders watching

 Recent Messages
-----------------------------------
   ▲  @Richard12_   $BITF $NVDA...
   ▲  @FightingIris $NVDA On December 3rd, Bank of America reiterated...
   ●  @epstok6789   $NVDA Look like the meeting did not end well...

======================================================================
```

### Data Provided

**Trending Symbols:**
- Ticker and company name
- Trending score (higher = more buzz)
- Watchlist count (number of traders tracking)

**Symbol Sentiment:**
- Bullish/Bearish/Neutral message counts
- Sentiment score (-100 to +100)
- Watchlist count
- Recent messages with:
  - User info and follower count
  - Sentiment tag (Bullish/Bearish)
  - Like count
  - Message preview

### Best Use Cases

- **Pre-market sentiment check**: See what retail traders are talking about
- **Momentum confirmation**: High bullish sentiment + price breakout = conviction
- **Contrarian signals**: Extreme sentiment can indicate reversal
- **Social buzz detection**: Trending stocks often have unusual volume
- **Community pulse**: Understand retail trader sentiment before entry

### Important Notes

**Rate Limits:**
- Free API: ~200 requests/hour (be mindful of usage)
- No authentication required

**Data Characteristics:**
- Social sentiment (not professional analysis)
- High noise, but useful for gauging retail interest
- Best combined with technical analysis

---

## Barchart Options Flow Scanner

### Usage

```bash
# Most active options (default)
barchart-options

# Unusual activity - smart money signals (Vol/OI > 1.25)
barchart-options --unusual

# Filter by type
barchart-options --calls            # Active call options
barchart-options --puts             # Active put options

# Options for specific symbol
barchart-options --symbol NVDA
barchart-options -s TSLA

# JSON output for programmatic use
barchart-options --active --json
```

### Sample Output

```
=====================================================================================
 BARCHART OPTIONS FLOW - MOST ACTIVE
 2025-12-06 07:26:49
=====================================================================================

 Sentiment Summary
----------------------------------------
   Call Volume:       1.2M
   Put Volume:      276.5K
   Put/Call Ratio: 0.23 (BULLISH (low P/C))

 Options Flow
-------------------------------------------------------------------------------------
 SYM   TYPE   STRIKE        EXP  DTE    LAST     BID     ASK      VOL       OI   V/OI
-------------------------------------------------------------------------------------
 NVDA  Call     $185 2025-12-12    6   $2.52   $2.46   $2.53   155.9K    38.3K  4.1
 NVDA  Call     $190 2025-12-12    6   $0.99   $0.97   $1.00   138.0K    45.0K  3.1
 AAL   Put       $13 2026-05-15  160   $0.91   $0.89   $0.93    86.2K      719 119.9
 ...

 Legend:
   Call = Bullish bet  |  Put = Bearish bet
   V/OI > 1.5 = Unusual activity (potential smart money)
   V/OI > 3.0 = Very unusual (strong signal)
=====================================================================================
```

### Data Provided

**All Modes:**
- Symbol, strike price, expiration date
- Days to expiration (DTE)
- Bid/ask/last prices
- Volume and open interest
- Vol/OI ratio (key unusual activity indicator)
- Underlying stock price

**Sentiment Summary:**
- Total call vs put volume
- Put/call ratio interpretation (bullish/bearish/neutral)

### Vol/OI Ratio Interpretation

| Ratio | Signal | Meaning |
|-------|--------|---------|
| < 1.0 | Normal | Regular trading activity |
| 1.25-1.5 | Elevated | Above-average interest |
| 1.5-3.0 | **Unusual** | Potential smart money positioning |
| > 3.0 | **Very Unusual** | Strong institutional signal |

### Best Use Cases

- **Smart money tracking**: High Vol/OI shows unusual institutional interest
- **Sentiment confirmation**: Call/put ratio validates directional bias
- **Entry timing**: Unusual activity often precedes big moves
- **Strike selection**: See where volume is concentrating
- **Expiration planning**: Identify hot expiration dates

### Important Notes

**Data Delay:**
- Free tier: 25-30 minute delayed quotes
- Premier: Real-time data, more filters, historical reports

**API Authentication:**
- Uses session cookies (no login required)
- XSRF token automatically extracted from page load

---

## Short Squeeze Scanner

### Usage

```bash
# All exchanges with >20% short interest (default)
shortsqueeze-scanner

# Filter by exchange
shortsqueeze-scanner --nasdaq          # Nasdaq stocks only
shortsqueeze-scanner --nyse            # NYSE stocks only
shortsqueeze-scanner --amex            # AMEX stocks only

# Higher short interest threshold
shortsqueeze-scanner --min-si 30       # Only >30% short interest
shortsqueeze-scanner --min-si 40       # Extreme squeeze candidates

# JSON output for programmatic use
shortsqueeze-scanner --json
shortsqueeze-scanner --nasdaq --min-si 35 --json
```

### Sample Output

```
===============================================================================================
 SHORT SQUEEZE CANDIDATES - ALL EXCHANGES
 Data from highshortinterest.com | Updated: November 26, 2025
 Scanned: 2025-12-06 07:32:22 | Min SI: 20.0%
===============================================================================================

 Summary
----------------------------------------
   Stocks found: 49
   Avg Short Interest: 27.0%
   Max Short Interest: 43.5%

 High Short Interest Stocks
-----------------------------------------------------------------------------------------------
 #   TICKER COMPANY                      EXCH       SI%      FLOAT      OUTST INDUSTRY
-----------------------------------------------------------------------------------------------
 1   HTZ    Hertz Global Holdings Inc    Nasdaq   43.5%    126.27M    311.59M Passenger Transporta
 2   AIRS   AirSculpt Technologies, Inc. Nasdaq   42.3%     14.62M     62.44M Health Care Provider
 3   GRPN   Groupon Inc                  Nasdaq   38.8%     23.67M     40.75M Retailers - Discount
 4   SONN   Sonnet Biotherapeutics Holdi Nasdaq   37.6%      6.74M      6.83M Pharmaceuticals
 5   CAPR   Capricor Therapeutics, Inc.  Nasdaq   35.2%     40.19M     45.72M Biotechnology
 ...

 Short Interest Guide:
   40%+ = Extreme squeeze potential (high risk/reward)
   30-40% = High squeeze potential
   25-30% = Moderate squeeze potential
   20-25% = Elevated short interest

 Squeeze Factors:
   - High SI% + Low Float = Maximum squeeze pressure
   - Positive catalyst + High SI% = Squeeze trigger
   - Watch for volume spikes indicating covering
===============================================================================================
```

### Data Provided

- **Ticker**: Stock symbol
- **Company**: Company name
- **Exchange**: Nasdaq, NYSE, or AMEX
- **Short Interest %**: Percentage of float sold short
- **Float**: Shares available for trading
- **Outstanding**: Total shares outstanding
- **Industry**: Business sector

### Short Interest Interpretation

| SI% Range | Signal | Trading Implication |
|-----------|--------|---------------------|
| 40%+ | **Extreme** | Maximum squeeze potential, very high risk/reward |
| 30-40% | **High** | Strong squeeze candidate, watch for catalysts |
| 25-30% | **Moderate** | Elevated interest, potential for squeeze on news |
| 20-25% | **Elevated** | Above normal, worth monitoring |

### Squeeze Setup Factors

**Maximum Squeeze Potential:**
- High SI% (>30%) + Low float (<20M shares)
- Positive catalyst (earnings beat, FDA approval, etc.)
- Increasing volume indicating covering
- Low days-to-cover ratio

**Day-Trading Strategy:**
1. Identify high SI stocks with upcoming catalysts
2. Monitor for volume spikes indicating short covering
3. Enter on breakout confirmation
4. Set tight stops (squeeze plays can reverse violently)
5. Take profits quickly - squeeze momentum fades fast

### Best Use Cases

- **Morning watchlist building**: Identify potential squeeze plays
- **Catalyst tracking**: Monitor high SI stocks for news triggers
- **Risk assessment**: Know what's heavily shorted before trading
- **Contrarian plays**: High SI can mean undervalued if thesis intact

### Important Notes

**Data Characteristics:**
- Updated weekly (not real-time)
- Source: highshortinterest.com
- Short interest data has ~2 week reporting lag
- Float/outstanding may differ from other sources

**NOT Real-Time:**
This data is best for research and watchlist building, not for real-time trading decisions. Combine with live market data from Alpaca MCP tools for execution.

---

## Day-Trading Workflow Integration

### Morning Pre-Market Research

```bash
#!/bin/bash
# morning_research.sh - Run before market open

echo "=== FINVIZ TOP GAINERS ==="
finviz-premarket --gainers

echo ""
echo "=== STOCKTWITS TRENDING ==="
stocktwits-sentiment --trending

echo ""
echo "=== OPTIONS FLOW (Smart Money) ==="
barchart-options --unusual

echo ""
echo "=== AI ANALYSIS FOR TOP PICKS ==="
for ticker in $(finviz-premarket --json | jq -r '.stocks[:3][].ticker'); do
    echo "--- $ticker ---"
    pplx-stock-fast $ticker
    stocktwits-sentiment --symbol $ticker
    sleep 2
done
```

### Combined Analysis Pipeline

```bash
#!/bin/bash
# Get Finviz screener data, then deep-dive with Perplexity AI + sentiment

TICKER="NVDA"

echo "=== FINVIZ DATA ==="
finviz-premarket --quote $TICKER

echo ""
echo "=== STOCKTWITS SENTIMENT ==="
stocktwits-sentiment --symbol $TICKER

echo ""
echo "=== PERPLEXITY AI ANALYSIS ==="
pplx-stock $TICKER
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
| `stocktwits-sentiment` | **~1s** | ★★★☆☆ | Real-time | ✅ |
| `shortsqueeze-scanner` | **~1s** | ★★★☆☆ | Weekly | ✅ |
| `finviz-premarket` | **~2s** | ★★★☆☆ | Delayed | ✅ |
| `barchart-options` | **~2s** | ★★★★☆ | Delayed | ✅ |
| `pplx-stock-fast` | ~8s | ★★★★☆ | Real-time | ❌ |
| `pplx-stock` | ~18s | ★★★★★ | Real-time | ❌ |

**Recommendation:**
- Use `stocktwits-sentiment` for instant social sentiment and trending
- Use `shortsqueeze-scanner` for weekly squeeze candidate watchlist
- Use `finviz-premarket` for fast screener scans and fundamentals
- Use `barchart-options` for options flow and smart money tracking
- Use `pplx-stock-fast` for quick AI-powered quotes
- Use `pplx-stock` for comprehensive research with AI analysis

**Day-Trading Flow:**
1. `shortsqueeze-scanner --min-si 30` → Weekly squeeze watchlist
2. `stocktwits-sentiment --trending` → See what's buzzing
3. `finviz-premarket --gainers` → Top movers by price
4. `barchart-options --unusual` → Smart money positioning
5. `stocktwits-sentiment -s TICKER` → Check sentiment before entry
6. `barchart-options -s TICKER` → Options flow for specific stock
7. `pplx-stock-fast TICKER` → AI analysis for conviction
