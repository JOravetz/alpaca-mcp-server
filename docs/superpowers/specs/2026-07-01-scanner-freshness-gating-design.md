# Scanner Freshness Gating — Design

**Date:** 2026-07-01
**Status:** Approved

## Problem

The explosive stock scanners rank symbols by percent change computed from each
symbol's Alpaca snapshot without ever checking how old the `latestTrade` print
is. A halted stock keeps its last pre-halt trade in the snapshot indefinitely,
so it surfaces as a top mover weeks after it stopped trading.

Observed failure: INHD was halted by Nasdaq (code T12) post-market on
2026-06-08. On 2026-07-01, `scan_explosive_stocks_fast` ranked it #1 at
+3579.05% using the frozen June 8 print — an untradeable, three-week-stale
result presented as the strongest opportunity.

Current state:

- `c_progs/stock_analyzer_json.c` extracts `latestTrade.t` and emits it in its
  JSON output (`timestamp` field) but never filters on it.
- `alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py` ignores the
  `timestamp` field entirely — it is neither displayed nor filtered.
- `alpaca_mcp_server/tools/day_trading_scanner.py` appends a
  "(Data: Xm old)" warning when the minute bar is >60 minutes old but still
  includes and ranks the stale symbol.

## Decision

Drop stale symbols from scanner results entirely, and show the last-trade
timestamp/age on every surviving result. Filter in the C binary (before
ranking/top-N selection) with the cutoff computed in Python from the Alpaca
market calendar.

## Freshness rule (shared by all scanners)

A symbol is **fresh** iff its `latestTrade` timestamp is at or after
**04:00 ET (pre-market start) of the previous trading day**, where "previous
trading day" is the most recent completed session date from Alpaca's market
calendar (weekends and holidays therefore need no special-casing).

- Monday night scan → cutoff is Friday 04:00 ET.
- A stock that traded in the current or prior session passes.
- A halted/delisted symbol whose print predates the prior session is dropped.
- Intraday activity requirements remain the job of the existing trades/min and
  percent-change filters; this gate only removes dead prints.

## Components

### 1. C binary — `c_progs/stock_analyzer_json.c`

- New option `-T EPOCH`: minimum `latestTrade` timestamp as Unix seconds
  (UTC). Default `0` = disabled, so existing callers see no behavior change.
- In `get_stock_snapshots()`, after extracting `timestamp_json`, parse the
  ISO-8601 string (`YYYY-MM-DDTHH:MM:SS[.fraction]Z`) to epoch seconds using
  `strptime` + `timegm`; fractional seconds are ignored.
- When a cutoff is active (`> 0`) and the symbol is not in `-a` all-symbols
  mode: skip the symbol if its trade epoch is older than the cutoff.
  **Fail closed:** a missing or unparseable timestamp is treated as stale and
  skipped.
- The skip happens before results are stored, so stale symbols never consume
  top-N output slots.
- Help text documents `-T`. Build must be warning-free
  (`cd c_progs && make stock_analyzer_json`).

### 2. Python wrapper — `alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py`

- New module-level helper `_freshness_cutoff() -> tuple[int, str]` returning
  `(epoch_seconds, source)`:
  - Fetch the market calendar via the existing TradingClient pattern (as in
    `tools/enhanced_market_clock.py`): request the last ~10 calendar days,
    take the most recent session date strictly before today's ET date —
    that is the "previous trading day" — and set cutoff = that date at
    04:00 ET converted to epoch. `source = "calendar"`.
  - Cache the computed cutoff for 15 minutes (module-level timestamped cache)
    so repeated scans don't re-hit the API.
  - On any exception: fallback `cutoff = now - 96h`, `source = "fallback"`;
    the formatter appends a note that the calendar was unavailable.
- `CStockAnalyzer.analyze()` gains `min_trade_ts: int | None = None`; when
  set and `> 0`, appends `-T <value>` to the command.
- `scan_explosive_stocks_fast` and `analyze_market_activity_fast` gain
  `require_fresh: bool = True`. When true they compute the cutoff and pass it
  through; `require_fresh=False` is the escape hatch that restores old
  behavior.
- Formatters parse each result's `timestamp` field and append a line per
  stock: `• Last trade: 2026-07-01 19:59 ET (1h 26m ago)`. Scanner-settings
  header states the active freshness cutoff.

### 3. Python scanner — `alpaca_mcp_server/tools/day_trading_scanner.py`

- Import the shared `_freshness_cutoff()` helper.
- Drop (not warn) any symbol whose `latestTrade.t` is older than the cutoff;
  count them and print one summary line, e.g. `Filtered 3 stale symbols
  (last trade before 2026-06-30 04:00 ET)`.
- Keep the existing "(Data: Xm old)" minute-bar age tag on surviving rows.

## Error handling

| Failure | Behavior |
|---:|---|
| Calendar API unavailable | 96-hour fallback cutoff + note in output |
| `latestTrade.t` missing/unparseable (cutoff active) | Symbol skipped (fail closed) |
| `-T 0` or `require_fresh=False` | Filter fully disabled (pre-change behavior) |

## Testing

1. C: `make stock_analyzer_json` completes with zero warnings; extend
   `test_stock_analyzer.c` to cover ISO→epoch parsing (with/without
   fractional seconds, malformed input) and cutoff skip logic.
2. Python: unit test `_freshness_cutoff()` calendar path (mocked client) and
   96h fallback path; unit test that `analyze()` appends `-T` only when set.
3. Live verification: run `scan_explosive_stocks_fast` — INHD (halted
   2026-06-08) must be absent; fresh movers still appear, each showing a
   last-trade age; `require_fresh=False` still surfaces INHD (escape hatch
   works).

## Out of scope

- Streaming/monitoring tools and other non-scanner consumers of snapshots.
- Halt detection via Nasdaq/SEC feeds (freshness gating is the proxy).
- Changing existing trades/min or percent-change thresholds.
