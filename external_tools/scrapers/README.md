# Stock Market Scrapers

**A comprehensive CLI toolkit for aggressive day-trading research.**

These command-line tools fetch real-time and historical stock data from multiple financial sources, enabling rapid pre-market analysis, sentiment tracking, options flow monitoring, and squeeze candidate identification.

## Why This Toolkit?

Day-trading requires **speed** and **multiple data sources**. This toolkit provides:

- **Sub-3-second data retrieval** from 6+ financial sources
- **No paid subscriptions required** - all free tier or public APIs
- **JSON output** for automation and scripting
- **Beautiful terminal output** with color-coded signals
- **Composable workflows** - pipe outputs together with `jq`

## Quick Start

```bash
# Install dependencies (one-time)
cd /path/to/alpaca-mcp-server-enhanced/external_tools/scrapers
mkdir -p ~/bin
ln -sf $(pwd)/* ~/bin/

# Morning research workflow (run before market open)
shortsqueeze-scanner --min-si 30          # Weekly squeeze watchlist
stocktwits-sentiment --trending            # What's buzzing?
finviz-premarket --gainers                 # Top price movers
finnhub-realtime earnings                  # Upcoming earnings this week
barchart-options --unusual                 # Smart money signals

# Deep-dive on a specific stock
finnhub-realtime quote -s NVDA            # Real-time quote
finnhub-realtime news -s NVDA             # Latest news
stocktwits-sentiment -s NVDA              # Social sentiment
barchart-options -s NVDA                  # Options flow
pplx-cf NVDA                              # COMPREHENSIVE Perplexity analysis (RECOMMENDED)

# Multi-symbol watchlist scan
finnhub-realtime multi -s NVDA,AAPL,TSLA,GME,AMD
```

## Available Scrapers

### Perplexity Finance Scrapers

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `pplx-cf` | **Camoufox** | ~15s | **RECOMMENDED** - Bypasses Cloudflare, fetches ALL data |
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

### Finnhub Real-Time Data

| Script | Technology | Speed | Description |
|--------|-----------|-------|-------------|
| `finnhub-realtime` | REST API (urllib) | ~1-2s | Quotes, news, earnings calendar |
| `finnhub-format.py` | Python | - | JSON formatter with color-coded output |

## Installation

### Prerequisites

```bash
# System packages (for Perplexity scrapers)
sudo apt install xvfb html2text

# Python packages (via uv in project root)
uv add DrissionPage undetected-chromedriver requests beautifulsoup4

# Camoufox (for pplx-cf - RECOMMENDED Perplexity scraper)
uv add camoufox rich
```

### Setup

Option 1: Symlink to ~/bin (recommended):
```bash
mkdir -p ~/bin
ln -sf $(pwd)/pplx-cf ~/bin/
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
ln -sf $(pwd)/finnhub-realtime ~/bin/
ln -sf $(pwd)/finnhub-format.py ~/bin/
```

### Environment Variables

```bash
# Finnhub API key (required for finnhub-realtime)
# Get your free key at: https://finnhub.io
export FINNHUB_API_KEY="your_api_key_here"
```

Option 2: Add this directory to PATH:
```bash
export PATH="$PATH:/path/to/alpaca-mcp-server-enhanced/external_tools/scrapers"
```

---

## Perplexity Finance Scrapers

### Comprehensive Analysis with Camoufox (pplx-cf) - RECOMMENDED

```bash
# Get comprehensive AI-powered analysis (bypasses Cloudflare)
pplx-cf NVDA

# JSON output for programmatic use
pplx-cf NVDA --json

# Market overview (main finance page)
pplx-cf --market

# Finance Discover page (trends, news, topics)
pplx-cf --discover                    # 200 articles (default)
pplx-cf --discover --articles 50      # 50 articles
pplx-cf --discover --articles 500     # 500 articles (max)
```

**Stock Analysis Output includes ALL Perplexity Finance data:**
- Real-time quote with after-hours pricing
- **Latest price movement summaries** (THE GOLD for day trading)
- Recent developments and headlines
- Bullish vs Bearish key issues analysis
- Sector peers with prices and changes
- Earnings history with beat/miss indicators
- Prediction markets data (Polymarket)
- Research reports with analyst sentiment

**Market Overview (`--market`) includes:**
- Market indices (S&P, NASDAQ, Dow futures + VIX)
- Market sentiment (bullish/bearish/upbeat indicator)
- AI-generated market summary
- Top movers (gainers, losers, most active)
- 11 equity sectors with ETF performance
- Prediction markets from Polymarket
- Popular cryptocurrencies
- Standout stocks with z-scores

**Discover Page (`--discover`) includes:**
- Market indices with % changes
- Finance news & analysis (up to 500 articles)
- Trending content and topics
- Trending companies with real-time quotes
- Topic categories

**Sample output:**
```
╭──────────────────────────────────────────────────────────────────────────────╮
│ PERPLEXITY FINANCE - RKLB                                                    │
│ Rocket Lab USA, Inc. - Industrials | Aerospace & Defense                     │
╰──────────────────────────────────────────────────────────────────────────────╯

💰 QUOTE
┌────────────────────────────────────────────────────────────────────────────┐
│ Price: $29.22                                                              │
│ Change: -$0.75 (-2.51%)                                                    │
│ After Hours: $29.40 (+0.62%)                                               │
│ Volume: 24.93M (Volume Ratio: 1.0x)                                        │
│ Day Range: $28.83 - $30.37                                                 │
│ 52W Range: $4.37 - $31.39                                                  │
└────────────────────────────────────────────────────────────────────────────┘

📈 LATEST PRICE MOVEMENT (THE GOLD)
┌────────────────────────────────────────────────────────────────────────────┐
│ Rocket Lab's stock opened lower and fell 2.6%, despite positive news...   │
│ The decline is part of a broader market pullback following the Fed...     │
└────────────────────────────────────────────────────────────────────────────┘

🔥 BULLS VS BEARS
┌─────────────────────────────────────┬──────────────────────────────────────┐
│ BULLISH VIEWS                       │ BEARISH VIEWS                        │
├─────────────────────────────────────┼──────────────────────────────────────┤
│ Strong growth trajectory with...    │ Current valuation concerns as...     │
│ Neutron rocket development on...    │ Competition from SpaceX and...       │
│ Space Systems segment growing...    │ Supply chain risks in satellite...   │
└─────────────────────────────────────┴──────────────────────────────────────┘
```

**Why Camoufox?**
- **Bypasses Cloudflare** - Firefox-based anti-detect browser with deep C++ hooks
- **Fetches ALL APIs** - 12 different REST endpoints in single session
- **More reliable** - Won't get blocked like Chrome-based scrapers
- **~15-20 seconds** - Slightly slower but gets EVERYTHING

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

## Finnhub Real-Time Data

### Setup

```bash
# Get your free API key at https://finnhub.io
export FINNHUB_API_KEY="your_api_key_here"
```

### Usage

```bash
# Real-time quote for a single stock
finnhub-realtime quote -s NVDA

# Multi-quote scanner (sorted by % change)
finnhub-realtime multi -s NVDA,AAPL,TSLA,GME,AMD

# Company-specific news
finnhub-realtime news -s NVDA --limit 10

# General market news
finnhub-realtime market-news --category general

# Earnings calendar (next 7 days)
finnhub-realtime earnings

# Earnings for specific date range
finnhub-realtime earnings --from 2025-12-06 --to 2025-12-20

# JSON output for programmatic use
finnhub-realtime quote -s NVDA --json
finnhub-realtime multi -s NVDA,AAPL --json
```

### Sample Quote Output

```
============================================================
 FINNHUB REAL-TIME QUOTE - NVDA
 2025-12-06 08:18:00
============================================================

 Current Price:
   $182.41
   -0.97 (-0.53%)

 Today's Range:
   Low:  $180.91
   High: $184.66
   Open: $183.89

 Previous Close: $183.38

============================================================
 Source: finnhub.io | Data may be delayed 15 minutes
============================================================
```

### Sample Multi-Quote Output

```
================================================================================
 FINNHUB MULTI-QUOTE SCANNER
 2025-12-06 08:18:09
================================================================================

 Summary
----------------------------------------
   Total: 4 symbols
   Gainers: 2
   Losers: 2

 Real-Time Quotes (sorted by % change)
--------------------------------------------------------------------------------
 SYMBOL      CURRENT     CHANGE    CHANGE%       HIGH        LOW       OPEN
--------------------------------------------------------------------------------
 GME          $23.00      +0.05     +0.22%     $23.07     $22.53     $23.00
 TSLA        $455.00      +0.47     +0.10%    $458.87    $451.66    $453.03
 NVDA        $182.41      -0.97     -0.53%    $184.66    $180.91    $183.89
 AAPL        $278.78      -1.92     -0.68%    $281.14    $278.05    $280.54

================================================================================
```

### Sample Earnings Output

```
====================================================================================================
 FINNHUB EARNINGS CALENDAR
 2025-12-06 08:18:19 | Range: 2025-12-06 to 2025-12-13
====================================================================================================

 Upcoming Earnings (157 companies)
----------------------------------------------------------------------------------------------------
 DATE         SYMBOL   TIME   Q       EPS EST    EPS ACT   SURPRISE      REV EST
----------------------------------------------------------------------------------------------------
 2025-12-08   GME      AMC    Q3        $0.20          -          -       997.2M
 2025-12-10   ADBE     AMC    Q4        $5.50          -          -         6.2B
 2025-12-10   ORCL     AMC    Q2        $1.67          -          -        16.5B
 2025-12-11   AVGO     AMC    Q4        $1.90          -          -        17.8B
 2025-12-11   COST     AMC    Q1        $4.36          -          -        68.5B
 ...

 Legend:
   BMO = Before Market Open (pre-market)
   AMC = After Market Close (after-hours)
   DMH = During Market Hours
====================================================================================================
```

### Data Provided

**Quote Mode:**
- Current price with change and percent change
- Day high, low, open prices
- Previous close

**Multi-Quote Mode:**
- All quote data for multiple symbols
- Sorted by percent change (best performers first)
- Summary of gainers vs losers

**News Mode:**
- Headlines with summaries (truncated for readability)
- Source and publication datetime
- Related ticker symbols
- Full URLs available in JSON output

**Earnings Mode:**
- Company symbol and earnings date
- Timing (BMO/AMC/DMH)
- EPS estimates and actuals (when available)
- Revenue estimates
- Earnings surprise calculations

### Best Use Cases

- **Pre-market scanning**: Quick multi-quote check on watchlist
- **News monitoring**: Real-time news alerts for positions
- **Earnings tracking**: Plan trades around earnings announcements
- **Sentiment confirmation**: Cross-reference news with price action
- **Watchlist building**: Identify stocks with upcoming catalysts

### Important Notes

**Rate Limits:**
- Free tier: 30 API calls/second
- Generous for day-trading research

**Data Characteristics:**
- Quotes may be delayed 15 minutes on free tier
- News is real-time
- Earnings calendar is comprehensive and up-to-date

**API Key Required:**
Get your free API key at [finnhub.io](https://finnhub.io) and set the `FINNHUB_API_KEY` environment variable.

---

## Day-Trading Workflow Integration

### Complete Morning Research Script

```bash
#!/bin/bash
# morning_research.sh - Comprehensive pre-market analysis
# Run at 7:00 AM ET before market open

set -e
OUTPUT_DIR="$HOME/trading/$(date +%Y-%m-%d)"
mkdir -p "$OUTPUT_DIR"

echo "=========================================="
echo " DAY-TRADING MORNING RESEARCH"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

# 1. SQUEEZE CANDIDATES (Weekly watchlist)
echo ""
echo ">>> SQUEEZE CANDIDATES (>30% Short Interest)"
shortsqueeze-scanner --min-si 30 | tee "$OUTPUT_DIR/squeeze_candidates.txt"
shortsqueeze-scanner --min-si 30 --json > "$OUTPUT_DIR/squeeze_candidates.json"

# 2. SOCIAL BUZZ
echo ""
echo ">>> STOCKTWITS TRENDING"
stocktwits-sentiment --trending | tee "$OUTPUT_DIR/trending.txt"
stocktwits-sentiment --trending --json > "$OUTPUT_DIR/trending.json"

# 3. TOP MOVERS
echo ""
echo ">>> FINVIZ TOP GAINERS"
finviz-premarket --gainers | tee "$OUTPUT_DIR/gainers.txt"
finviz-premarket --gainers --json > "$OUTPUT_DIR/gainers.json"

# 4. OPTIONS FLOW (Smart Money)
echo ""
echo ">>> BARCHART UNUSUAL OPTIONS"
barchart-options --unusual | tee "$OUTPUT_DIR/unusual_options.txt"
barchart-options --unusual --json > "$OUTPUT_DIR/unusual_options.json"

# 5. DEEP-DIVE ON TOP 3 GAINERS
echo ""
echo ">>> DEEP-DIVE ANALYSIS"
TOP_TICKERS=$(finviz-premarket --json | jq -r '.stocks[:3][].ticker')
for ticker in $TOP_TICKERS; do
    echo ""
    echo "--- $ticker Analysis ---"

    # Sentiment check
    stocktwits-sentiment -s "$ticker" | head -30

    # Options flow
    barchart-options -s "$ticker" | head -20

    # AI analysis (if time permits)
    # pplx-stock-fast "$ticker"

    sleep 1
done

echo ""
echo "=========================================="
echo " Research complete! Files saved to:"
echo " $OUTPUT_DIR"
echo "=========================================="
```

### Squeeze Play Detection Script

```bash
#!/bin/bash
# squeeze_detector.sh - Find squeeze setups with multiple confirmations
# A squeeze needs: High SI% + Bullish sentiment + Unusual options activity

echo "=== SQUEEZE PLAY DETECTOR ==="

# Get squeeze candidates
SQUEEZE_TICKERS=$(shortsqueeze-scanner --min-si 35 --json | jq -r '.stocks[].ticker')

echo "Checking $( echo "$SQUEEZE_TICKERS" | wc -w ) high SI stocks..."
echo ""

for ticker in $SQUEEZE_TICKERS; do
    echo ">>> Analyzing $ticker"

    # Check sentiment
    SENTIMENT=$(stocktwits-sentiment -s "$ticker" --json 2>/dev/null | \
                jq -r '.sentiment_summary.sentiment_score // 0')

    # Check options flow
    OPTIONS=$(barchart-options -s "$ticker" --json 2>/dev/null | \
              jq -r '[.options[] | select(.type == "Call")] | length // 0')

    # Get short interest
    SI=$(shortsqueeze-scanner --json | \
         jq -r --arg t "$ticker" '.stocks[] | select(.ticker == $t) | .short_interest // 0')

    echo "   SI: ${SI}% | Sentiment: ${SENTIMENT} | Call Options: ${OPTIONS}"

    # SQUEEZE ALERT if all conditions met
    if (( $(echo "$SENTIMENT > 20" | bc -l) )) && (( OPTIONS > 5 )); then
        echo "   🚀 POTENTIAL SQUEEZE SETUP! High SI + Bullish + Active Calls"
    fi
    echo ""

    sleep 0.5
done
```

### Real-Time Monitoring Script

```bash
#!/bin/bash
# live_monitor.sh - Continuous monitoring during market hours
# Run in a separate terminal during trading

WATCHLIST="NVDA,TSLA,AMD,AAPL,SPY"
INTERVAL=60  # seconds

while true; do
    clear
    echo "=========================================="
    echo " LIVE WATCHLIST MONITOR - $(date '+%H:%M:%S')"
    echo "=========================================="

    for ticker in ${WATCHLIST//,/ }; do
        echo ""
        echo ">>> $ticker"

        # Quick sentiment check
        SENTIMENT=$(stocktwits-sentiment -s "$ticker" --json 2>/dev/null | \
                    jq -r '"Sentiment: \(.sentiment_summary.sentiment_score | round)%"')
        echo "   $SENTIMENT"

        # Options activity
        TOP_OPTION=$(barchart-options -s "$ticker" --json 2>/dev/null | \
                     jq -r '.options[0] | "\(.type) $\(.strike) - Vol: \(.volume)"')
        echo "   Top Option: $TOP_OPTION"
    done

    echo ""
    echo "Next update in ${INTERVAL}s... (Ctrl+C to exit)"
    sleep $INTERVAL
done
```

### JSON Pipeline Examples

```bash
# Find squeeze candidates that are also trending on Stocktwits
SQUEEZE=$(shortsqueeze-scanner --min-si 30 --json | jq -r '.stocks[].ticker')
TRENDING=$(stocktwits-sentiment --trending --json | jq -r '.symbols[].ticker')
echo "$SQUEEZE" | grep -Ff <(echo "$TRENDING")

# Get options flow for all trending stocks
for ticker in $(stocktwits-sentiment --trending --json | jq -r '.symbols[:5][].ticker'); do
    echo "=== $ticker Options ==="
    barchart-options -s "$ticker" --json | jq '.options[:3]'
done

# Create a combined watchlist from multiple sources
{
    finviz-premarket --gainers --json | jq -r '.stocks[:10][].ticker'
    stocktwits-sentiment --trending --json | jq -r '.symbols[:10][].ticker'
    shortsqueeze-scanner --min-si 30 --json | jq -r '.stocks[:10][].ticker'
} | sort -u > watchlist.txt

# Calculate aggregate sentiment across multiple tickers
for ticker in NVDA AMD AAPL; do
    stocktwits-sentiment -s "$ticker" --json
done | jq -s '[.[].sentiment_summary.sentiment_score] | add / length'

# Export to CSV for spreadsheet analysis
finviz-premarket --gainers --json | \
    jq -r '.stocks[] | [.ticker, .price, .change, .volume] | @csv' > gainers.csv
```

### Integration with Alpaca MCP Server

```bash
# Use scraper data to inform MCP trading decisions
# Example: Check sentiment before placing order

check_before_trade() {
    local TICKER=$1

    echo "Pre-trade check for $TICKER..."

    # Check social sentiment
    SENTIMENT=$(stocktwits-sentiment -s "$TICKER" --json | \
                jq -r '.sentiment_summary.sentiment_score')

    if (( $(echo "$SENTIMENT < -30" | bc -l) )); then
        echo "⚠️  Warning: Bearish sentiment ($SENTIMENT%)"
        echo "Consider waiting for sentiment improvement"
        return 1
    fi

    # Check options flow
    PUT_CALL=$(barchart-options -s "$TICKER" --json | \
               jq -r '.sentiment.put_call_ratio')

    if (( $(echo "$PUT_CALL > 1.5" | bc -l) )); then
        echo "⚠️  Warning: High put/call ratio ($PUT_CALL)"
        echo "Smart money may be bearish"
        return 1
    fi

    echo "✅ Sentiment checks passed - proceed with trade"
    return 0
}

# Usage: check_before_trade NVDA && place_alpaca_order NVDA buy 100
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
| `finnhub-realtime` | **~1s** | ★★★★☆ | Real-time | ✅ |
| `finviz-premarket` | **~2s** | ★★★☆☆ | Delayed | ✅ |
| `barchart-options` | **~2s** | ★★★★☆ | Delayed | ✅ |
| `pplx-stock-fast` | ~8s | ★★★★☆ | Real-time | ❌ |
| `pplx-cf` | ~15s | ★★★★★ | Real-time | ❌ (Camoufox) |
| `pplx-stock` | ~18s | ★★★★★ | Real-time | ❌ |

**Recommendation:**
- Use `stocktwits-sentiment` for instant social sentiment and trending
- Use `shortsqueeze-scanner` for weekly squeeze candidate watchlist
- Use `finnhub-realtime` for real-time quotes, news, and earnings calendar
- Use `finviz-premarket` for fast screener scans and fundamentals
- Use `barchart-options` for options flow and smart money tracking
- Use `pplx-stock-fast` for quick AI-powered quotes
- **Use `pplx-cf` for comprehensive Perplexity data with all 12 APIs (RECOMMENDED)**
- Use `pplx-stock` for comprehensive research with AI analysis (fallback if Camoufox fails)

**Day-Trading Flow:**
1. `shortsqueeze-scanner --min-si 30` → Weekly squeeze watchlist
2. `stocktwits-sentiment --trending` → See what's buzzing
3. `finviz-premarket --gainers` → Top movers by price
4. `finnhub-realtime earnings` → Check for earnings this week
5. `barchart-options --unusual` → Smart money positioning
6. `finnhub-realtime multi -s WATCHLIST` → Quick multi-quote scan
7. `stocktwits-sentiment -s TICKER` → Check sentiment before entry
8. `finnhub-realtime news -s TICKER` → Latest news for the stock
9. `barchart-options -s TICKER` → Options flow for specific stock
10. `pplx-cf TICKER` → **COMPREHENSIVE** analysis with all Perplexity data (bulls/bears, earnings, peers)

---

## How It Works - Technical Deep Dive

### Architecture Pattern

All scrapers follow a consistent **Bash Wrapper + Embedded Python** pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                     Bash Wrapper Script                      │
│  - Argument parsing with getopts                            │
│  - Creates temporary Python script in /tmp                  │
│  - Executes Python with arguments                           │
│  - Routes output to formatter or stdout                     │
│  - Cleanup on exit                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Embedded Python Script                     │
│  - HTTP requests via urllib.request (stdlib)                │
│  - Data parsing (regex for HTML, json for APIs)             │
│  - Business logic and calculations                          │
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

**Why this pattern?**
- **Self-contained**: Single file deployment, no package installation
- **Fast startup**: No Python environment activation overhead
- **Portable**: Works on any system with Python 3 and bash
- **Debuggable**: `--json` bypasses formatter for raw data inspection

### API Discovery Methods

| Source | Discovery Method | Authentication |
|--------|------------------|----------------|
| Stocktwits | Public API docs | None required |
| Barchart | Browser DevTools → Network tab | Session cookies + XSRF |
| Highshortinterest | View page source → HTML table | None required |
| Finviz | HTML structure analysis | None required |
| Perplexity | DevTools → XHR requests | Cloudflare session |

### Barchart XSRF Token Extraction

Barchart uses session-based authentication with XSRF tokens:

```python
# 1. Initial page load sets cookies
req = Request(f'{base_url}/options/unusual-activity', headers=headers)
opener.open(req)

# 2. Extract XSRF token from cookies
for cookie in cookie_jar:
    if cookie.name == 'XSRF-TOKEN':
        xsrf_token = urllib.parse.unquote(cookie.value)

# 3. Include token in API requests
headers['X-XSRF-TOKEN'] = xsrf_token
```

### Cloudflare Bypass (Perplexity)

Perplexity Finance uses Cloudflare bot protection. Our solution:

1. **Headed Mode**: Run Chrome visible (not headless) - headless is detected
2. **Virtual Display**: Use Xvfb to create invisible framebuffer
3. **Force X11**: Modern Linux uses Wayland; force X11 for Xvfb
4. **Patched Driver**: undetected-chromedriver modifies automation fingerprints

```bash
# Environment setup in pplx-stock scripts
export XDG_SESSION_TYPE=x11
export GDK_BACKEND=x11
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

---

## Test Results (December 6, 2025)

All scrapers tested at 07:30 AM ET (pre-market):

### Stocktwits Sentiment Scanner

```
✅ stocktwits-sentiment --trending
   - Fetched 30 trending symbols
   - Top: TGL (9.55), CVNA (9.01), CVKD (7.11)
   - Response time: 1.2 seconds

✅ stocktwits-sentiment -s NVDA
   - Fetched 15 messages with sentiment tags
   - Sentiment: 60% Bullish, 0% Bearish, 40% Neutral
   - Score: +60.0%
   - Watchers: 635,000
   - Response time: 1.4 seconds
```

### Barchart Options Flow Scanner

```
✅ barchart-options --active
   - Fetched 30 most active options
   - Top: NVDA Call $185 (155.9K volume)
   - Put/Call Ratio: 0.23 (Bullish)
   - Response time: 2.3 seconds

✅ barchart-options -s NVDA
   - Fetched 30 NVDA options
   - Highest Vol/OI: 4.1x
   - Response time: 2.1 seconds

⚠️ barchart-options --unusual (pre-market)
   - Returns 0 results before market open
   - Works correctly during market hours
```

### Short Squeeze Scanner

```
✅ shortsqueeze-scanner
   - Fetched 49 stocks with >20% short interest
   - Data updated: November 26, 2025
   - Top: HTZ (43.5%), AIRS (42.3%), GRPN (38.8%)
   - Response time: 1.5 seconds

✅ shortsqueeze-scanner --min-si 35
   - Filtered to 5 extreme candidates
   - Response time: 1.4 seconds

✅ shortsqueeze-scanner --nasdaq --min-si 30 --json
   - Exchange filter working correctly
   - JSON output properly formatted
```

### Finviz Premarket Scanner

```
✅ finviz-premarket --gainers
   - Fetched top 20 gainers
   - Top: TGL (+276%), SMX (+135%), WHLR (+98%)
   - Response time: 2.1 seconds

✅ finviz-premarket --quote NVDA
   - Fetched all fundamentals
   - 10 news headlines
   - Analyst ratings and targets
   - Response time: 2.8 seconds
```

### Finnhub Real-Time Data

```
✅ finnhub-realtime quote -s NVDA
   - Current: $182.41 (-0.53%)
   - Day range: $180.91 - $184.66
   - Response time: ~1.2 seconds

✅ finnhub-realtime multi -s NVDA,AAPL,TSLA,GME
   - 4 symbols fetched successfully
   - Sorted by % change
   - Response time: ~1.5 seconds

✅ finnhub-realtime news -s NVDA --limit 5
   - 5 articles fetched
   - Headlines with summaries
   - Response time: ~1.3 seconds

✅ finnhub-realtime market-news --limit 5
   - General market news
   - Multiple sources (MarketWatch, etc.)
   - Response time: ~1.2 seconds

✅ finnhub-realtime earnings --from 2025-12-06 --to 2025-12-13
   - 157 upcoming earnings found
   - Notable: GME (12/8 AMC), ADBE (12/10), AVGO (12/11)
   - Response time: ~1.4 seconds
```

### Perplexity Finance Scrapers

```
✅ pplx-cf NVDA (RECOMMENDED - Camoufox)
   - Bypasses Cloudflare with Firefox anti-detect browser
   - Fetches ALL 12 Perplexity REST APIs in single session
   - Quote, price movements, bulls/bears, peers, earnings, prediction markets
   - Response time: ~15-20 seconds
   - Tested: RKLB, MIMI, NVDA - all successful

✅ pplx-stock-fast NVDA
   - Real-time quote: $182.35
   - After-hours: $182.50 (+0.08%)
   - Response time: ~8 seconds

✅ pplx-stock NVDA
   - Full HTML with AI summaries
   - Bull/bear analyst cases
   - News headlines
   - Response time: ~18 seconds
```

---

## Sources Not Implemented

### Benzinga (Requires Authentication)

**Research Findings:**
- Next.js application with heavy JavaScript rendering
- Internal API at `data-api-next.benzinga.com`
- API returns 404 without authentication
- Would require login credentials or paid API access

**Decision:** Deprioritized - other sources provide similar data for free.

---

## MCP Server Integration - Slash Commands

The Perplexity Finance scrapers are integrated into the Alpaca MCP Server as slash commands:

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/pplx-finance SYMBOL` | Comprehensive stock analysis | `/pplx-finance NVDA` |
| `/market` | Market overview (indices, movers, sectors) | `/market` |
| `/discover [articles]` | Finance trends and news | `/discover 200` |

### Usage Examples

```bash
# In Claude Code or MCP client:

/pplx-finance RKLB          # Deep-dive on Rocket Lab
/pplx-finance MU            # Micron analysis with bulls/bears

/market                      # Full market overview

/discover                    # 200 articles (default)
/discover 50                 # Quick scan (50 articles)
/discover 500                # Comprehensive (500 articles max)
```

### What Each Command Returns

**`/pplx-finance SYMBOL`:**
- Real-time quote with after-hours
- Latest price movement summaries
- Bulls vs Bears analysis
- Sector peers with prices
- Earnings history
- Research reports

**`/market`:**
- Market indices (S&P, NASDAQ, Dow, VIX)
- Market sentiment indicator
- Top movers (gainers/losers)
- 11 sector performance
- Cryptocurrencies
- Prediction markets

**`/discover [articles]`:**
- Market indices
- Finance news & analysis
- Trending content
- Trending companies with quotes
- Topic categories

---

## Additional Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Deep technical details, API discovery, performance benchmarks
- [PPLX_STOCK_SCRAPER.md](../../docs/PPLX_STOCK_SCRAPER.md) - Perplexity scraper detailed guide
- [PPLX_SCRAPER_RESEARCH.md](../../docs/PPLX_SCRAPER_RESEARCH.md) - Technology comparison research
