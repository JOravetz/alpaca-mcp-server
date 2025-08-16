# /ANALYZE COMMAND - COMPREHENSIVE STOCK ANALYSIS

## COMMAND STRUCTURE

```
/analyze [symbols|momentum|file.lis]
```

## EXECUTION FLOW

### 1. PARALLEL DATA FETCHING (ALL STOCKS SIMULTANEOUSLY)

#### Market Data (Alpaca MCP)
- `get_stock_snapshots(ALL_SYMBOLS)` - Single API call for 20+ symbols
- `get_stock_bars_intraday(symbol, '1Min', days=1)` - Per symbol
- `get_stock_bars_intraday(symbol, '5Min', days=5)` - Per symbol
- `analyze_peaks_troughs_fast(batch_5_symbols)` - C tool, batches of 5

#### Fundamental Data (SEC EDGAR MCP)
- `get_company_info(symbol)` - Company details
- `get_recent_filings(symbol, days=30)` - Recent 8-K, 10-Q, etc
- `get_financials(symbol, 'all')` - Income, balance, cash flow
- `get_insider_transactions(symbol, days=30)` - Form 4 trades

#### News Data (External Tool)
- `Bash: ./external_tools/news_scrapers/yf_rss.py SYMBOL`

### 2. PARALLEL EXECUTION PATTERN

```python
# Execute ALL operations in parallel for ALL stocks
tasks = []

# Single call for all snapshots
tasks.append(get_stock_snapshots(','.join(ALL_SYMBOLS)))

# Per-symbol parallel operations
for symbol in ALL_SYMBOLS:
    tasks.extend([
        get_stock_bars_intraday(symbol, '1Min', 1),
        get_stock_bars_intraday(symbol, '5Min', 5),
        get_company_info(symbol),
        get_recent_filings(symbol),
        get_financials(symbol),
        get_insider_transactions(symbol),
        get_news(symbol)
    ])

# Batch peak/trough analysis (5 symbols at a time)
for batch in chunks(ALL_SYMBOLS, 5):
    tasks.append(analyze_peaks_troughs_fast(','.join(batch)))

# Execute all tasks simultaneously
results = await parallel_execute(tasks)
```

### 3. ANALYSIS OUTPUT STRUCTURE

```
═══════════════════════════════════════════════════════════════════
                    COMPREHENSIVE STOCK ANALYSIS
═══════════════════════════════════════════════════════════════════

📊 SYMBOL: [STOCK_NAME]
───────────────────────────────────────────────────────────────────

MARKET DATA
• Current: $XXX.XX | Change: ±X.XX%
• Volume: XXM | Avg Volume: XXM
• Range: $XXX.XX - $XXX.XX
• 52-Week: $XXX.XX - $XXX.XX

TECHNICAL SIGNALS
• Support: $XXX.XX (trough detected)
• Resistance: $XXX.XX (peak detected)
• Trend: BULLISH/BEARISH/NEUTRAL
• RSI: XX | MACD: X.XX

FUNDAMENTALS (Latest Filing)
• Revenue: $XXB | Growth: ±XX% YoY
• Net Income: $XXB | Margin: XX%
• EPS: $X.XX | P/E: XX.X
• Cash: $XXB | Debt: $XXB

INSIDER ACTIVITY (30 Days)
• Buys: X transactions | $XXM
• Sells: X transactions | $XXM
• Net: BUYING/SELLING pressure

RECENT NEWS
• [Date] Headline - Sentiment
• [Date] Headline - Sentiment

TRADING RECOMMENDATION
• Signal: BUY/HOLD/SELL
• Entry: $XXX.XX
• Target: $XXX.XX
• Stop: $XXX.XX
• Risk/Reward: X:X

═══════════════════════════════════════════════════════════════════
```

## IMPLEMENTATION USING MCP TOOLS

### Step 1: Get ALL Stock Data in Parallel

```python
# ALL 52 stocks from momentum.lis analyzed simultaneously
symbols = read_momentum_list()

# Single snapshot call for all
snapshots = mcp.get_stock_snapshots(','.join(symbols[:20]))
snapshots2 = mcp.get_stock_snapshots(','.join(symbols[20:40]))
snapshots3 = mcp.get_stock_snapshots(','.join(symbols[40:]))

# Parallel bars for each symbol
bars_1min = parallel([mcp.get_bars(s, '1Min', 1) for s in symbols])
bars_5min = parallel([mcp.get_bars(s, '5Min', 5) for s in symbols])

# Fast C peak/trough analysis
peaks = parallel([mcp.analyze_peaks_fast(batch) for batch in batches(symbols, 5)])

# SEC data for all
fundamentals = parallel([mcp.get_financials(s) for s in symbols])
insiders = parallel([mcp.get_insider_trades(s) for s in symbols])

# News for all
news = parallel([bash(f'./external_tools/news_scrapers/yf_rss.py {s}') for s in symbols])
```

### Step 2: Process Results

```python
for symbol in symbols:
    analyze_single_stock(
        snapshot=snapshots[symbol],
        bars_1min=bars_1min[symbol],
        bars_5min=bars_5min[symbol],
        peaks=peaks[symbol],
        fundamentals=fundamentals[symbol],
        insiders=insiders[symbol],
        news=news[symbol]
    )
```

## HOOKS FOR SUB-AGENTS

Yes, hooks can assist! Configure in settings:

```json
{
  "hooks": {
    "pre-analyze": "validate_symbols.sh",
    "post-fetch": "process_raw_data.py",
    "on-complete": "generate_report.py"
  }
}
```

## USAGE EXAMPLES

```bash
# Analyze all momentum stocks
/analyze momentum

# Analyze specific stocks
/analyze NVDA,MSTR,PLTR,HOOD,RKLB

# Analyze from file
/analyze ~/autotrade/momentum.lis

# With specific options
/analyze momentum --timeframes=1Min,5Min,1Hour --days=10
```

## PERFORMANCE OPTIMIZATIONS

1. **Batch API Calls**: Snapshots support 20+ symbols per call
2. **C Implementation**: Peak/trough uses compiled C for 10x speed
3. **Parallel Execution**: ALL operations run simultaneously
4. **Smart Caching**: Recent data cached for 5 minutes
5. **Batch Processing**: Group symbols for API efficiency

## ERROR HANDLING

- Retry failed API calls with exponential backoff
- Continue analysis even if some data missing
- Mark failed fetches in output
- Provide partial analysis when possible

## COMPLETE TOOL LIST USED

1. **mcp__alpaca-trading__get_stock_snapshots**
2. **mcp__alpaca-trading__get_stock_bars_intraday**
3. **mcp__alpaca-trading__analyze_peaks_troughs_fast**
4. **mcp__alpaca-trading__get_stock_stream_data** (if streaming active)
5. **mcp__sec-edgar__get_company_info**
6. **mcp__sec-edgar__get_recent_filings**
7. **mcp__sec-edgar__get_financials**
8. **mcp__sec-edgar__get_insider_transactions**
9. **Bash: ./external_tools/news_scrapers/yf_rss.py**

Total operations per stock: ~8
Total for 52 stocks: ~416 parallel operations!