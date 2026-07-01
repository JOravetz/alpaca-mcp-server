---
description: Find pre-market gaps and extended hours movers for early entry opportunities
arguments:
  - name: threshold
    description: Minimum gap percentage (default 20)
    required: false
  - name: symbols
    description: Comma-separated symbols to scan (optional)
    required: false
---

# Gap Scanner - Catch Big Movers Before They Run

Scans for pre-market gaps and extended hours activity. This is how you catch stocks like BBGI (+49% gap at open that ran to +380%).

**Usage:**
- `/gaps` - Scan for all gaps
- `/gaps 20` - Minimum 20% gap
- `/gaps 20 AAPL,NVDA,TSLA` - Custom symbols with threshold

## Parameters: $ARGUMENTS

### Step 1: Check Market Session
Run `mcp__alpaca-trading__get_extended_market_clock` to determine:
- Pre-market (4:00 AM - 9:30 AM): Focus on gap detection
- Regular hours (9:30 AM - 4:00 PM): Compare open vs previous close
- After-hours (4:00 PM - 8:00 PM): Monitor for tomorrow's gaps

### Step 2: Scan for Gaps (PARALLEL)

1. **`mcp__alpaca-trading__scan_day_trading_opportunities`**
   - Catches stocks already moving with volume

2. **`mcp__alpaca-trading__scan_explosive_stocks_fast`**
   - Fast C-scan for % movers

3. **`mcp__alpaca-trading__scan_after_hours_opportunities`** (if after-hours)
   - Extended hours specific scanning

4. **`mcp__alpaca-trading__get_stock_snapshots`** on top movers
   - Get today's open vs previous close = GAP %

### Step 3: Calculate Gap Metrics

For each stock found:
```
GAP% = ((Today's Open - Previous Close) / Previous Close) * 100
```

**Gap Classifications:**
- **MONSTER GAP**: >50% (like BBGI's +49%)
- **MAJOR GAP**: 20-50%
- **SIGNIFICANT GAP**: 10-20%
- **MINOR GAP**: 5-10%

### Step 4: Gap Analysis Output

```
GAP SCANNER - [DATE] [TIME]
============================
Session: [PRE-MARKET/REGULAR/AFTER-HOURS]

MONSTER GAPS (>50%):
Symbol | Prev Close | Open    | Gap%    | Current | Volume
-------|------------|---------|---------|---------|--------
XXXX   | $X.XX      | $XX.XX  | +XX.X%  | $XX.XX  | XXXx avg

MAJOR GAPS (20-50%):
Symbol | Prev Close | Open    | Gap%    | Current | Volume
-------|------------|---------|---------|---------|--------
XXXX   | $X.XX      | $XX.XX  | +XX.X%  | $XX.XX  | XXXx avg

GAP TRADING STRATEGY:
=====================
For each qualified gap:

1. MONSTER GAPS (>50%):
   - These are SQUEEZE candidates
   - Enter on first pullback to VWAP or opening range low
   - NO FUNDAMENTAL CATALYST = pure momentum, ride it hard
   - Target: +50-100% from entry
   - Stop: Below opening range low

2. MAJOR GAPS (20-50%):
   - Wait for first 5-min candle to close
   - Enter on break of first 5-min high (for longs)
   - Target: Prior resistance levels
   - Stop: Below first 5-min low

3. SIGNIFICANT GAPS (10-20%):
   - More selective - need volume confirmation
   - Enter on pullback to gap fill zone
   - Target: 1.5x the gap amount
   - Stop: Full gap fill
```

### Step 5: Immediate Action Items

For gaps >20%, provide:
```
IMMEDIATE ACTION: [SYMBOL]
- Current: $XX.XX (+XX.X% gap)
- Entry Zone: $XX.XX - $XX.XX
- Stop Loss: $XX.XX
- Target 1: $XX.XX
- Target 2: $XX.XX
- Volume: XXXx average (CONFIRMED INTEREST)
- Catalyst: [News/Squeeze/Unknown]
- RISK: [HIGH/EXTREME]
```

## BBGI Lesson:
On Dec 10, 2025, BBGI gapped +49% ($4.05 → $6.05) at open with NO NEWS.
By EOD it was +380% ($19.50). The gap was the signal - volume confirmed it.

**Rule: Big gap + massive volume + no news = SQUEEZE. Don't be conservative!**

$ARGUMENTS
