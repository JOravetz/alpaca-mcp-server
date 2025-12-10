---
description: Run all explosive stock scanners to find day-trading opportunities like BBGI
arguments:
  - name: max_results
    description: Maximum number of results (default 15)
    required: false
  - name: min_change
    description: Minimum percent change (default 10)
    required: false
---

# Morning Scanner - Find Explosive Stocks Early

This command runs ALL critical MCP scanner tools to catch explosive momentum stocks at market open.

**Usage:**
- `/morning_scanner` - Run full scanner suite with defaults
- `/morning_scanner 20` - Return top 20 results
- `/morning_scanner 10 5` - Top 10 results, min 5% change

## Scanning for: $ARGUMENTS

Execute these MCP tools IN PARALLEL for maximum speed:

### Step 1: Market Status Check
First, verify market is open and check current conditions:
- `mcp__alpaca-trading__get_extended_market_clock` - Check trading session
- `mcp__alpaca-trading__resource_market_conditions` - Overall market health

### Step 2: Run ALL Scanners (PARALLEL)
Execute these simultaneously to find explosive movers:

1. **`scan_day_trading_opportunities`** - Primary scanner
   - Filters: 1000+ trades/min, 10%+ change, UP stocks only
   - Best for: High-activity momentum plays
   - Sort by: percent_change (descending)

2. **`scan_explosive_momentum`** - Quick momentum scanner
   - Filters: 15%+ moves, momentum focus
   - Best for: Catching big % gaps early
   - Lower trade threshold, higher % requirement

3. **`scan_explosive_stocks_fast`** - C-optimized speed scanner
   - Filters: 15%+ change, max price $50
   - Best for: Ultra-fast scanning of all symbols
   - Uses compiled C for 10x performance

4. **`analyze_market_activity_fast`** - Activity analyzer
   - Analyzes: Trade intensity, gradients, volume changes
   - Best for: Finding unusual activity patterns

### Step 3: Consolidate Results
After scanners complete:
- Rank stocks appearing in MULTIPLE scanners (highest priority)
- Sort by % change (biggest movers first)
- Filter for price < $30 (penny stock focus per trading strategy)
- Highlight any stock with 1000+ trades/minute

### Step 4: Technical Analysis on Top 3
For the top 3 candidates, run:
- `get_stock_peak_trough_analysis` - Find support/resistance levels
- `get_stock_snapshots` - Current market data
- `get_perplexity_quote` - Volume ratio and context

### Step 5: Generate Trade Setups
For each qualified stock, provide:

```
SYMBOL: [TICKER]
=================
Current Price: $XX.XX
Change: +XX.X%
Trades/Min: X,XXX
Volume Ratio: XXXx average

KEY LEVELS:
- Resistance: $XX.XX (target for longs)
- Support: $XX.XX (entry for longs)
- Stop Loss: $XX.XX (-X% from entry)

SIGNAL: [BUY/WAIT/AVOID]
Entry Zone: $XX.XX - $XX.XX
Target 1: $XX.XX (+XX%)
Target 2: $XX.XX (+XX%)
Stop: $XX.XX (-X%)

CATALYST: [News/Squeeze/Momentum/Unknown]
RISK: [LOW/MEDIUM/HIGH/EXTREME]
```

### Step 6: Summary Dashboard
Present results in a scannable format:

```
MORNING SCANNER RESULTS - [DATE] [TIME]
========================================
Market Status: [OPEN/CLOSED/PRE/POST]

TOP EXPLOSIVE STOCKS:
Rank | Symbol | Price  | Change% | Trades/Min | Signal
-----|--------|--------|---------|------------|--------
  1  | XXXX   | $XX.XX | +XXX.X% |   X,XXX    | BUY
  2  | XXXX   | $XX.XX | +XX.X%  |   X,XXX    | BUY
  3  | XXXX   | $XX.XX | +XX.X%  |   X,XXX    | WAIT

IMMEDIATE ACTION ITEMS:
1. [Stock] - Entry at $X.XX, target $X.XX
2. [Stock] - Watch for pullback to $X.XX
3. [Stock] - Too extended, wait for consolidation
```

## Key Reminders:
- **Pre-market gaps > 20%** = potential squeeze, act fast
- **1000+ trades/min** = institutional interest
- **Volume > 100x average** = something big is happening
- **No news catalyst + big move** = squeeze mechanics, ride it!
- **Enter at support, exit at resistance** (or vice versa for shorts)
- **Close ALL positions by 3:30 PM** - no overnight holds!

$ARGUMENTS
