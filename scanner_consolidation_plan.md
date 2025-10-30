# Scanner Consolidation Plan

## Current State (BLOATED)

We have **4 scanner tools** doing overlapping work:

1. `scan_day_trading_opportunities` - 334 lines, complexity 31
2. `scan_after_hours_opportunities` - 301 lines, complexity 27
3. `scan_explosive_momentum` - 16 lines, complexity 1
4. `scan_explosive_stocks_fast` - 82 lines, complexity 6

**Total:** 733 lines of scanner code with significant duplication

## Problems

1. **Overlapping logic:** All scanners filter by price movement, volume, and trades
2. **Parameter explosion:** Each scanner has slightly different thresholds
3. **Maintenance burden:** Changes need to be replicated across 4 tools
4. **Context window waste:** Claude Code loads metadata for all 4 scanners
5. **Decision paralysis:** Users don't know which scanner to use when

## Proposed Solution: 2 Core Scanners

### Scanner 1: `scan_stock_opportunities` (Universal Scanner)

**Purpose:** One scanner to rule them all, with strategy parameter

```python
async def scan_stock_opportunities(
    strategy: Literal["day_trading", "explosive", "after_hours"] = "day_trading",
    symbols: str = "ALL",
    max_results: int = 10,
    custom_filters: dict | None = None
) -> str:
    """
    Universal stock scanner for day-trading opportunities.

    WHEN TO USE:
    - Finding volatile stocks for same-day trades
    - Identifying momentum plays during/after market hours
    - Scanning for explosive percentage moves

    HOW TO USE:
    - strategy="day_trading": Regular hours, high volume movers (default)
    - strategy="explosive": Extreme % gainers, lower volume tolerance
    - strategy="after_hours": Extended hours with spread analysis

    Examples:
        scan_stock_opportunities("explosive", max_results=5)
        scan_stock_opportunities("after_hours", symbols="AAPL,TSLA,NVDA")
    """
```

**Benefits:**
- Single tool with clear strategy selection
- Unified filtering logic (DRY principle)
- ~150 lines vs 733 lines (80% reduction)
- One docstring for Claude Code to learn

### Scanner 2: `analyze_market_activity_fast` (C-optimized)

**Keep as-is:** This uses C implementation, fundamentally different approach

**Purpose:** Lightning-fast scanning of hundreds of symbols

## Implementation Plan

1. **Phase 1:** Create new `scan_stock_opportunities` tool
2. **Phase 2:** Migrate existing scanner logic into strategy branches
3. **Phase 3:** Deprecate old scanners (mark as deprecated in docstrings)
4. **Phase 4:** Remove old scanners after 1-2 releases

## Code Reuse Strategy

Extract shared logic into private functions:

```python
def _filter_by_momentum(snapshot, thresholds: dict) -> bool:
    """Shared filtering logic across all strategies."""

def _calculate_trade_intensity(snapshot) -> float:
    """Shared metric calculation."""

def _format_opportunity(stock, strategy: str) -> dict:
    """Shared output formatting."""
```

## Migration Path for Users

Old code:
```python
scan_day_trading_opportunities(min_trades_per_minute=1000)
scan_explosive_momentum(min_percent_change=15)
scan_after_hours_opportunities(min_volume=100000)
```

New code:
```python
scan_stock_opportunities("day_trading")
scan_stock_opportunities("explosive")
scan_stock_opportunities("after_hours")
```

**Backward compatibility:** Keep old tools for 2 releases with deprecation warnings

## Expected Outcomes

- ✅ 80% reduction in scanner code (733 → ~150 lines)
- ✅ Single source of truth for filtering logic
- ✅ Easier to maintain and extend
- ✅ Clearer for Claude Code to understand when to use
- ✅ Smaller context window footprint
- ✅ Faster for users (less decision fatigue)
