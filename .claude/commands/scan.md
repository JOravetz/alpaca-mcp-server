---
description: Quick explosive stock scan - fastest way to find day-trading opportunities
arguments:
  - name: min_trades
    description: Minimum trades per minute (default 1000)
    required: false
  - name: min_change
    description: Minimum percent change (default 10)
    required: false
---

# Quick Scan - Find Explosive Stocks NOW

Fast scanner for immediate day-trading opportunities. No fluff, just results.

**Usage:**
- `/scan` - Quick scan with defaults
- `/scan 1000` - Set minimum trades/minute threshold
- `/scan 1000 15` - Trades/min and minimum % change

## Parameters: $ARGUMENTS

Execute these MCP tools IN PARALLEL:

1. **`mcp__alpaca-trading__scan_day_trading_opportunities`**
   - max_symbols: 15
   - sort_by: "percent_change"

2. **`mcp__alpaca-trading__scan_explosive_stocks_fast`**
   - max_results: 15
   - min_percent_change: 10
   - max_price: 50

3. **`mcp__alpaca-trading__get_extended_market_clock`**
   - Check current trading session

## Output Format:

Present results as a SINGLE consolidated table:

```
EXPLOSIVE STOCKS - [TIME]
==========================
#  | Symbol | Price   | Change%  | Trades/Min | Action
---|--------|---------|----------|------------|--------
1  | XXXX   | $XX.XX  | +XXX.X%  |   X,XXX    | BUY
2  | XXXX   | $XX.XX  | +XX.X%   |   X,XXX    | WATCH
...
```

For TOP 3 stocks, add one-liner entry strategy:
- **XXXX**: Entry $X.XX, Stop $X.XX, Target $X.XX

## Decision Rules:
- **BUY**: >20% change AND >1000 trades/min
- **WATCH**: >10% change OR >500 trades/min
- **AVOID**: <10% change AND <500 trades/min

$ARGUMENTS
