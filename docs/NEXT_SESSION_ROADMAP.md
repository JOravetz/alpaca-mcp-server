# Next Session Roadmap: Real-Time Data Sources

**Created:** December 6, 2024
**Purpose:** Implementation plan for real-time financial data scrapers and APIs
**Priority:** High-value sources for day-trading edge

---

## Quick Start for Next Session

```bash
# 1. Pull latest changes
git fetch origin feature/enhanced-market-data-streaming
git checkout feature/enhanced-market-data-streaming
git pull

# 2. Review current scrapers
ls -la external_tools/scrapers/

# 3. Test existing scrapers work
stocktwits-sentiment --trending
barchart-options --active
shortsqueeze-scanner --min-si 30
finviz-premarket --gainers

# 4. Start implementing from priority list below
```

---

## Current State Summary

### Implemented Scrapers (6 total)

| Scraper | Speed | Data Type | Status |
|---------|-------|-----------|--------|
| `stocktwits-sentiment` | ~1s | Social sentiment | ✅ Working |
| `barchart-options` | ~2s | Options flow | ✅ Working |
| `shortsqueeze-scanner` | ~1.5s | Short interest | ✅ Working |
| `finviz-premarket` | ~2s | Market screener | ✅ Working |
| `pplx-stock-fast` | ~8s | AI analysis | ✅ Working |
| `pplx-stock` | ~18s | Full AI analysis | ✅ Working |

### What's Missing

1. **Real-time news alerts** - News moves stocks instantly
2. **Earnings calendar** - Know when volatility is coming
3. **Dark pool data** - Institutional positioning
4. **SEC filings alerts** - Insider buying/selling in real-time

---

## Priority Implementation List

### Priority 1: Finnhub Real-Time (RECOMMENDED FIRST)

**URL:** https://finnhub.io/

**Why Priority 1:**
- Free tier: 60 API calls/minute (generous)
- Real-time news via WebSocket
- Earnings calendar built-in
- Pre-market data available
- Official REST API (no scraping needed)

**API Endpoints:**
```
GET /api/v1/quote?symbol=AAPL              # Real-time quote
GET /api/v1/company-news?symbol=AAPL       # Company news
GET /api/v1/calendar/earnings              # Earnings calendar
GET /api/v1/stock/insider-transactions     # Insider trading
WS  wss://ws.finnhub.io                    # Real-time WebSocket
```

**Authentication:**
- Free API key required (sign up at finnhub.io)
- Key passed as query param: `?token=YOUR_API_KEY`

**Implementation Plan:**
```bash
# Create finnhub-realtime scraper
external_tools/scrapers/finnhub-realtime    # Main script
external_tools/scrapers/finnhub-format.py   # Formatter

# Features to implement:
# --quote TICKER       Real-time quote
# --news TICKER        Latest news (last 24h)
# --earnings           Upcoming earnings this week
# --insider TICKER     Recent insider transactions
# --stream TICKER      WebSocket real-time updates
```

**Estimated Time:** 2-3 hours

---

### Priority 2: Alpha Vantage (Free Fundamentals)

**URL:** https://www.alphavantage.co/

**Why Priority 2:**
- Free tier: 25 API calls/day (limited but useful)
- Excellent fundamental data
- Technical indicators built-in
- No scraping needed

**API Endpoints:**
```
GET /query?function=GLOBAL_QUOTE&symbol=IBM
GET /query?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min
GET /query?function=NEWS_SENTIMENT&tickers=AAPL
GET /query?function=EARNINGS&symbol=IBM
```

**Authentication:**
- Free API key required
- Key passed as query param: `&apikey=YOUR_KEY`

**Implementation Plan:**
```bash
# Create alphavantage scraper
external_tools/scrapers/alphavantage        # Main script

# Features:
# --quote TICKER       Real-time quote
# --intraday TICKER    5-min bars
# --sentiment TICKER   News sentiment score
# --earnings TICKER    Earnings history
```

**Estimated Time:** 1-2 hours

---

### Priority 3: SEC EDGAR MCP Integration

**URL:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces

**Why Priority 3:**
- Official SEC data (free, unlimited)
- Real-time filing alerts
- Insider transactions (Form 4)
- Already have MCP server available

**Existing MCP Server:**
- Repository: https://github.com/stefanoamorelli/sec-edgar-mcp
- Already integrated in your system as `mcp__sec-edgar__*`

**Enhancement Plan:**
```bash
# Create CLI wrapper for SEC EDGAR MCP
external_tools/scrapers/sec-insider         # Insider transactions
external_tools/scrapers/sec-filings         # Recent filings

# Features:
# sec-insider TICKER           Recent insider buys/sells
# sec-insider --buys-only      Filter to purchases only
# sec-filings TICKER           Recent SEC filings
# sec-filings --type 8-K       Filter by filing type
```

**Estimated Time:** 1-2 hours

---

### Priority 4: Polygon.io (Premium Quality)

**URL:** https://polygon.io/

**Why Priority 4:**
- Highest quality data
- Real-time WebSocket
- Options data included
- Free tier: 5 API calls/minute

**API Endpoints:**
```
GET /v2/aggs/ticker/AAPL/prev              # Previous day
GET /v2/snapshot/locale/us/markets/stocks  # Market snapshot
GET /v3/reference/tickers/AAPL             # Ticker details
WS  wss://socket.polygon.io/stocks         # Real-time stream
```

**Authentication:**
- Free API key required
- Key in header: `Authorization: Bearer YOUR_KEY`

**Implementation Plan:**
```bash
# Create polygon scraper
external_tools/scrapers/polygon-realtime    # Main script

# Features:
# --snapshot           Market-wide snapshot
# --ticker AAPL        Single ticker details
# --stream AAPL,TSLA   Real-time WebSocket
```

**Estimated Time:** 2-3 hours

---

### Priority 5: Unusual Whales MCP (Options Flow)

**URL:** https://unusualwhales.com/public-api

**Why Priority 5:**
- Best options flow data available
- MCP server exists: https://lobehub.com/mcp/phields-unusualwhales-mcp
- Requires paid subscription for full access

**Existing MCP Server:**
- Can integrate as MCP tool
- Provides flow alerts, dark pool data

**Implementation Plan:**
```bash
# Install Unusual Whales MCP server
# Add to Claude Code MCP configuration

# Or create CLI wrapper:
external_tools/scrapers/unusualwhales      # If API access available

# Features:
# --flow               Latest options flow
# --darkpool           Dark pool prints
# --alerts             Urgent flow alerts
```

**Estimated Time:** 1 hour (if API access available)

---

### Priority 6: Twelve Data (Backup Real-Time)

**URL:** https://twelvedata.com/stocks

**Why Priority 6:**
- Good backup for real-time data
- Free tier: 800 API calls/day
- WebSocket available

**API Endpoints:**
```
GET /quote?symbol=AAPL
GET /time_series?symbol=AAPL&interval=1min
GET /earnings?symbol=AAPL
WS  wss://ws.twelvedata.com/v1/quotes/price
```

**Estimated Time:** 2 hours

---

## Implementation Architecture

### Recommended File Structure

```
external_tools/scrapers/
├── README.md                    # Updated with new scrapers
├── ARCHITECTURE.md              # Technical details
│
├── # Existing (working)
├── stocktwits-sentiment
├── barchart-options
├── shortsqueeze-scanner
├── finviz-premarket
├── pplx-stock
├── pplx-stock-fast
│
├── # Priority 1 - Finnhub
├── finnhub-realtime
├── finnhub-format.py
│
├── # Priority 2 - Alpha Vantage
├── alphavantage
├── alphavantage-format.py
│
├── # Priority 3 - SEC EDGAR
├── sec-insider
├── sec-filings
├── sec-format.py
│
├── # Priority 4 - Polygon
├── polygon-realtime
├── polygon-format.py
│
├── # Configuration
└── config/
    └── api_keys.env.example     # Template for API keys
```

### API Key Management

```bash
# Create config file (DO NOT COMMIT)
cat > external_tools/scrapers/config/api_keys.env << 'EOF'
# Finnhub (free at finnhub.io)
FINNHUB_API_KEY=your_key_here

# Alpha Vantage (free at alphavantage.co)
ALPHAVANTAGE_API_KEY=your_key_here

# Polygon (free at polygon.io)
POLYGON_API_KEY=your_key_here

# Twelve Data (free at twelvedata.com)
TWELVEDATA_API_KEY=your_key_here
EOF

# Add to .gitignore
echo "external_tools/scrapers/config/api_keys.env" >> .gitignore
```

---

## Day-Trading Workflow Enhancement

### Current Workflow
```
Morning Research (manual, ~5 min):
1. shortsqueeze-scanner → Squeeze candidates
2. stocktwits-sentiment → Social buzz
3. finviz-premarket → Price movers
4. barchart-options → Options flow
```

### Enhanced Workflow (with new scrapers)
```
Real-Time Monitoring (automated):
1. finnhub-realtime --stream → Continuous news alerts
2. sec-insider --watch → Insider buying alerts
3. polygon-realtime --snapshot → Market pulse

Morning Research (faster, ~2 min):
1. finnhub-realtime --earnings → Today's earnings
2. finnhub-realtime --news WATCHLIST → Overnight news
3. Existing scrapers for deep-dive

Pre-Trade Check (instant):
1. finnhub-realtime --quote TICKER → Real-time price
2. sec-insider TICKER → Recent insider activity
3. stocktwits-sentiment -s TICKER → Social sentiment
```

---

## WebSocket Real-Time Architecture

### Finnhub WebSocket Implementation

```python
# finnhub_websocket.py - Real-time news and quote streaming

import asyncio
import websockets
import json
import os

FINNHUB_KEY = os.environ.get('FINNHUB_API_KEY')

async def stream_quotes(symbols: list):
    """Stream real-time quotes for multiple symbols."""
    uri = f"wss://ws.finnhub.io?token={FINNHUB_KEY}"

    async with websockets.connect(uri) as ws:
        # Subscribe to symbols
        for symbol in symbols:
            await ws.send(json.dumps({
                "type": "subscribe",
                "symbol": symbol
            }))

        # Process incoming data
        async for message in ws:
            data = json.loads(message)
            if data.get('type') == 'trade':
                for trade in data.get('data', []):
                    yield {
                        'symbol': trade['s'],
                        'price': trade['p'],
                        'volume': trade['v'],
                        'timestamp': trade['t']
                    }

# Usage in scraper:
# async for quote in stream_quotes(['NVDA', 'TSLA', 'AMD']):
#     print(f"{quote['symbol']}: ${quote['price']}")
```

---

## Testing Checklist for Next Session

### Before Starting Implementation

- [ ] Verify existing scrapers still work
- [ ] Sign up for Finnhub free API key
- [ ] Sign up for Alpha Vantage free API key
- [ ] Create `config/api_keys.env` file
- [ ] Test API keys with curl

### After Each Implementation

- [ ] Test `--help` output
- [ ] Test default mode
- [ ] Test `--json` output
- [ ] Test symbol-specific query
- [ ] Verify formatter colors work
- [ ] Add to README.md
- [ ] Commit with descriptive message

---

## Estimated Total Time

| Priority | Source | Time | Cumulative |
|----------|--------|------|------------|
| P1 | Finnhub | 2-3h | 3h |
| P2 | Alpha Vantage | 1-2h | 5h |
| P3 | SEC EDGAR CLI | 1-2h | 7h |
| P4 | Polygon | 2-3h | 10h |
| P5 | Unusual Whales | 1h | 11h |
| P6 | Twelve Data | 2h | 13h |

**Recommended for single session:** P1 (Finnhub) + P3 (SEC EDGAR) = ~4 hours

---

## Reference Links

### Free APIs (No Payment Required)
- **Finnhub:** https://finnhub.io/ - Real-time quotes, news, earnings
- **Alpha Vantage:** https://www.alphavantage.co/ - Fundamentals, technicals
- **SEC EDGAR:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- **Twelve Data:** https://twelvedata.com/stocks - Real-time market data

### Premium APIs (Paid)
- **Polygon.io:** https://polygon.io/ - Institutional-grade data
- **Unusual Whales:** https://unusualwhales.com/public-api - Options flow
- **FloatAlgo:** https://www.flowalgo.com/ - Dark pool flow
- **WhaleStream:** https://www.whalestream.com - Real-time options
- **Databento:** https://databento.com/stocks - Institutional data

### MCP Integrations
- **SEC EDGAR MCP:** https://github.com/stefanoamorelli/sec-edgar-mcp
- **Unusual Whales MCP:** https://lobehub.com/mcp/phields-unusualwhales-mcp

---

## Questions for Next Session

1. Do you have Finnhub API key? (Free signup)
2. Do you have Alpha Vantage API key? (Free signup)
3. Do you want WebSocket real-time streaming or polling?
4. Priority: News alerts or earnings calendar first?
5. Should we integrate with existing Alpaca MCP server?

---

*Document created for session continuity. All sources verified December 2024.*
