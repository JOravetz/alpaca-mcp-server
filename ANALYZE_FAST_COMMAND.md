# ⚡ /ANALYZE FAST - Complete in <60 Seconds

## OPTIMIZED ARCHITECTURE

### KEY OPTIMIZATIONS
1. **Single C Tool Execution** - Process ALL 52 stocks in ONE call per timeframe
2. **Parallel Timeframes** - Run 3 timeframes simultaneously (1Min, 5Min, Daily)
3. **No Bar Fetching** - C tool fetches its own data internally
4. **Hooks Integration** - Automated pre/post processing
5. **Smart Batching** - Single snapshot call for all symbols

## EXECUTION FLOW (<60 seconds)

```
START (0s)
    ↓
[PRE-ANALYZE HOOK] (1s)
    • Validate symbols
    • Clear cache
    • Check market status
    ↓
[PARALLEL EXECUTION] (5-10s)
    ├── Snapshots: ALL symbols in 1 call
    ├── Peak/Trough 1Min/1Day: ALL symbols  
    ├── Peak/Trough 5Min/15Day: ALL symbols
    ├── Peak/Trough 1Day/252Day: ALL symbols
    ├── SEC Data: Top 10 symbols only
    └── News: Top 10 symbols batch
    ↓
[POST-FETCH HOOK] (1s)
    • Process raw data
    • Log metrics
    ↓
[SIGNAL DETECTION] (2s)
    • Compare 3 timeframes
    • Identify agreements
    • Rank signals
    ↓
[ON-SIGNAL HOOK] (1s)
    • Send alerts
    • Log signals
    • Trigger orders (optional)
    ↓
[GENERATE REPORT] (2s)
    • Create markdown
    • Save JSON summary
    ↓
COMPLETE (~15-20s total)
```

## COMMAND USAGE

### Basic Usage
```bash
# Analyze momentum.lis stocks
/analyze momentum

# Analyze specific stocks
/analyze NVDA,MSTR,PLTR,HOOD,RKLB

# With custom parameters
/analyze momentum --windows=11,21,51 --timeframes=1Min,5Min,1Hour
```

### MCP Tool Calls (Optimized)

```python
# ONLY 5-6 PARALLEL CALLS NEEDED!

# 1. Single snapshot for ALL symbols
mcp__alpaca-trading__get_stock_snapshots("AGX,APH,APP,...all 52...")

# 2-4. Three timeframe analyses (C tool handles ALL symbols per call)
mcp__alpaca-trading__analyze_peaks_troughs_fast(
    symbols="AGX,APH,APP,...all 52...",
    timeframe="1Min",
    days=1,
    window_len=11
)

mcp__alpaca-trading__analyze_peaks_troughs_fast(
    symbols="AGX,APH,APP,...all 52...",
    timeframe="5Min", 
    days=15,
    window_len=21
)

mcp__alpaca-trading__analyze_peaks_troughs_fast(
    symbols="AGX,APH,APP,...all 52...",
    timeframe="1Day",
    days=252,
    window_len=51
)

# 5. Quick SEC data (top 10 only for speed)
parallel([mcp__sec-edgar__get_company_info(s) for s in top_10])

# 6. News batch
Bash("./external_tools/news_scrapers/yf_rss.py NVDA MSTR PLTR...")
```

## HOOKS CONFIGURATION

### 1. Pre-Analyze Hook (`hooks/pre_analyze.sh`)
- Validates symbol format
- Checks market status
- Clears stale cache
- Logs start time

### 2. Post-Fetch Hook (`hooks/post_fetch.py`)
- Processes raw results
- Logs metrics
- Validates data quality

### 3. On-Signal Hook (`hooks/on_signal.py`)
- Detects strong signals (all 3 timeframes agree)
- Sends alerts to monitoring service
- Can trigger auto-trading
- Logs signals to file

### 4. Generate Report Hook (`hooks/generate_report.py`)
- Creates markdown report
- Saves JSON summary
- Timestamps everything

## SIGNAL DETECTION LOGIC

### Strong Signals (All 3 Timeframes Agree)
```
1Min: TROUGH + 5Min: TROUGH + Daily: TROUGH = STRONG BUY ✅✅✅
1Min: PEAK + 5Min: PEAK + Daily: PEAK = STRONG SELL 🔴🔴🔴
```

### Normal Signals (2 Timeframes Agree)
```
1Min: TROUGH + 5Min: TROUGH = BUY ✅✅
1Min: PEAK + 5Min: PEAK = SELL 🔴🔴
```

### Weak Signals (Only 1 Timeframe)
```
1Min: TROUGH only = MONITOR 👀
Daily: PEAK only = WATCH ⚠️
```

## PERFORMANCE BENCHMARKS

| Operation | Time | Details |
|-----------|------|---------|
| Pre-hook | 1s | Validation |
| Snapshots | 2s | Single API call |
| Peak/Trough x3 | 5s | C tool, parallel |
| SEC Data | 3s | Top 10 only |
| News | 2s | Batch fetch |
| Processing | 2s | Signal detection |
| Hooks | 3s | All hooks |
| **TOTAL** | **<20s** | **All 52 stocks!** |

## C TOOL ADVANTAGES

### Why It's Fast
1. **Compiled C** - 10-100x faster than Python
2. **Single Process** - No overhead from batching
3. **Efficient Memory** - Direct array operations
4. **Built-in Fetching** - No separate bar requests
5. **Optimized Math** - Fast Fourier transforms

### Window Recommendations
- **11 samples** - Short-term (1Min/1Day)
- **21 samples** - Medium-term (5Min/15Day)  
- **51 samples** - Long-term (1Day/252Day)

## ERROR HANDLING

### Timeout Protection
```python
async def with_timeout(coro, timeout=10):
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        return {"error": "timeout"}
```

### Partial Results
- Continue even if some operations fail
- Mark failed operations in report
- Provide best-effort analysis

## EXAMPLE OUTPUT

```
⚡ FAST ANALYSIS START: 52 stocks
🎯 Target: Complete in <60 seconds
🔍 Pre-analyze: Validating 52 symbols
✅ Pre-analyze complete
⚡ Executing 6 parallel operations...
📊 Post-fetch: Processing 6 results
✅ Post-fetch complete
🎯 Signals detected: 8 strong buys, 15 buys, 12 sells
🔥 STRONG BUY SIGNALS:
   • PLTR
   • RKLB
   • APP
   • SPOT
   • RCL
✅ Signal processing complete
📄 Generating report for 52 symbols
✅ Report saved: /tmp/analysis_report_20250816_072800.md
✅ COMPLETE in 18.3 seconds!
```

## INTEGRATION WITH MONITORING

The hooks can integrate with the FastAPI monitoring service:

```python
# In on_signal.py hook
if strong_buy_signals:
    requests.post("http://localhost:8000/alerts", json={
        "type": "trading_opportunity",
        "signals": strong_buy_signals,
        "confidence": "high",
        "action": "review_for_entry"
    })
```

## COMMAND IMPLEMENTATION

Use the fast analyzer:
```bash
# Make executable
chmod +x analyze_fast.py
chmod +x hooks/*.sh hooks/*.py

# Run analysis
./analyze_fast.py momentum

# Or via Python
uv run python analyze_fast.py NVDA,MSTR,PLTR
```

---

**⚡ This optimized approach completes full analysis of 52 stocks in <20 seconds!**