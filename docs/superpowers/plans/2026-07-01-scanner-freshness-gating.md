# Scanner Freshness Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop stale prints (e.g. halted stocks like INHD) from all scanner results and show last-trade age on every surviving result.

**Architecture:** The Python side computes a freshness cutoff (04:00 ET of the previous trading day, from the Alpaca market calendar) in a new shared module `alpaca_mcp_server/tools/freshness.py`. The C analyzer gains a `-T <epoch>` flag and filters stale symbols *before* ranking/top-N selection. The Python wrapper passes the cutoff and formats last-trade ages; the pure-Python scanner drops (not warns about) stale symbols using the same cutoff.

**Tech Stack:** C (gcc, `-Wall -Wextra`, json-c, strptime/timegm), Python 3 (pytz, alpaca-py TradingClient, pytest via `uv run pytest`).

**Repo:** `/home/jjoravet/alpaca-mcp-server-enhanced` (branch `feature/enhanced-market-data-streaming`). All paths below are relative to that root. Run all Python commands with `uv run`. **Zero compile warnings/errors are acceptable** (user's hard rule; CFLAGS already include `-Wall -Wextra`).

**Spec:** `docs/superpowers/specs/2026-07-01-scanner-freshness-gating-design.md`

## File structure

| File | Action | Responsibility |
|---|---|---|
| `c_progs/stock_analyzer_json.c` | Modify | `parse_iso8601_to_epoch()`, `-T` flag, freshness skip in `get_stock_snapshots()`, `main()` guarded by `#ifndef STOCK_ANALYZER_NO_MAIN` |
| `c_progs/test_freshness_filter.c` | Create | Unit tests for the ISO→epoch parser (includes the .c with the no-main guard) |
| `c_progs/Makefile` | Modify | Build/run target for the new test binary |
| `alpaca_mcp_server/tools/freshness.py` | Create | Cutoff computation (calendar + cache + 96h fallback), ISO parsing, age/cutoff formatting, `is_stale()` |
| `alpaca_mcp_server/tests/unit/test_freshness.py` | Create | Tests for everything in `freshness.py` |
| `alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py` | Modify | `min_trade_ts` → `-T`; `require_fresh` on both fast scanners; age lines in output |
| `alpaca_mcp_server/tools/day_trading_scanner.py` | Modify | Drop stale symbols; "Filtered N stale" summary |
| `alpaca_mcp_server/server_components/tool_registrations.py` | Modify | Expose `require_fresh` on the two MCP tool wrappers |

Note: the spec placed `_freshness_cutoff()` inside the wrapper module; it lives in `freshness.py` instead so `day_trading_scanner.py` can import it without depending on the C-wrapper module. Same behavior, cleaner boundary.

---

### Task 1: C ISO-8601 parser (TDD)

**Files:**
- Modify: `c_progs/stock_analyzer_json.c` (main guard + new function)
- Create: `c_progs/test_freshness_filter.c`
- Modify: `c_progs/Makefile`

- [ ] **Step 1: Guard `main()` so tests can include the source file**

In `c_progs/stock_analyzer_json.c`, wrap `main()` (currently at line 653, `int main(int argc, char *argv[]) {`) with a preprocessor guard. Add the line directly above `int main`:

```c
#ifndef STOCK_ANALYZER_NO_MAIN
int main(int argc, char *argv[]) {
```

and after the closing brace of `main()` (the final `}` at the end of the file) add:

```c
#endif /* STOCK_ANALYZER_NO_MAIN */
```

Verify nothing broke: `cd c_progs && make stock_analyzer_json` → compiles with zero warnings.

- [ ] **Step 2: Write the failing test file**

Create `c_progs/test_freshness_filter.c`:

```c
/*
 * test_freshness_filter.c - Tests for the freshness-gating additions to
 * stock_analyzer_json.c (parse_iso8601_to_epoch).
 *
 * Includes stock_analyzer_json.c directly with STOCK_ANALYZER_NO_MAIN so the
 * real implementation is tested without duplicating main().
 *
 * Build & run: make run_freshness_tests
 */
#define STOCK_ANALYZER_NO_MAIN
#include "stock_analyzer_json.c"

#include <assert.h>

static int tests_run = 0;

#define RUN_TEST(fn) do { fn(); tests_run++; printf("  PASS: %s\n", #fn); } while (0)

static void test_epoch_zero(void) {
    assert(parse_iso8601_to_epoch("1970-01-01T00:00:00Z") == 0L);
}

static void test_known_timestamp(void) {
    /* date -u -d "2026-06-08T20:00:00Z" +%s */
    assert(parse_iso8601_to_epoch("2026-06-08T20:00:00Z") == 1780948800L);
}

static void test_fractional_seconds_ignored(void) {
    assert(parse_iso8601_to_epoch("2026-06-08T20:00:00.123456789Z") == 1780948800L);
}

static void test_day_boundary(void) {
    /* date -u -d "1970-01-02T00:00:00Z" +%s */
    assert(parse_iso8601_to_epoch("1970-01-02T00:00:00Z") == 86400L);
}

static void test_null_input(void) {
    assert(parse_iso8601_to_epoch(NULL) == -1L);
}

static void test_empty_string(void) {
    assert(parse_iso8601_to_epoch("") == -1L);
}

static void test_too_short(void) {
    assert(parse_iso8601_to_epoch("2026-06-08") == -1L);
}

static void test_garbage(void) {
    assert(parse_iso8601_to_epoch("not-a-timestamp-at-all") == -1L);
}

int main(void) {
    printf("Freshness filter tests:\n");
    RUN_TEST(test_epoch_zero);
    RUN_TEST(test_known_timestamp);
    RUN_TEST(test_fractional_seconds_ignored);
    RUN_TEST(test_day_boundary);
    RUN_TEST(test_null_input);
    RUN_TEST(test_empty_string);
    RUN_TEST(test_too_short);
    RUN_TEST(test_garbage);
    printf("All %d tests passed.\n", tests_run);
    return 0;
}
```

- [ ] **Step 3: Add Makefile targets**

In `c_progs/Makefile`, after the `# --- Program 4 ---` block, add:

```make
# --- Program 5: test_freshness_filter ---
TARGET5 = test_freshness_filter
SRC5 = test_freshness_filter.c
```

After the `$(TARGET4)` rule, add (note: SRC5 `#include`s stock_analyzer_json.c, so only SRC5 is compiled but both are dependencies):

```make
# Rule to build the freshness filter test program
$(TARGET5): $(SRC5) stock_analyzer_json.c
	@echo "Compiling test executable $< -> $@"
	$(CC) $(CFLAGS) -o $@ $(SRC5) $(LDFLAGS)

# Build and run the freshness tests
run_freshness_tests: $(TARGET5)
	./$(TARGET5)
```

Update the `clean:` rule's `rm -f` line to also remove `$(TARGET5)`:

```make
	rm -f $(TARGET1) $(TARGET2) $(TARGET3) $(TARGET4) $(TARGET5) *.o
```

Add `run_freshness_tests` to `.PHONY`:

```make
.PHONY: all clean test_stock_analyzer test run_freshness_tests
```

(Do NOT touch the existing broken `test_stock_analyzer` phony/binary name clash — out of scope.)

- [ ] **Step 4: Run tests, verify they fail**

Run: `cd c_progs && make run_freshness_tests`
Expected: FAIL — compile error `implicit declaration of function 'parse_iso8601_to_epoch'` (the function doesn't exist yet).

- [ ] **Step 5: Implement `parse_iso8601_to_epoch()`**

In `c_progs/stock_analyzer_json.c`, immediately after `load_credentials()` (ends around line 75) and before `get_stock_snapshots()`, add:

```c
// Parse an ISO-8601 UTC timestamp (e.g. "2026-06-08T20:00:00.123456789Z")
// to Unix epoch seconds. Fractional seconds are ignored.
// Returns -1 on NULL, malformed, or too-short input.
long parse_iso8601_to_epoch(const char *ts) {
    if (ts == NULL || strlen(ts) < 19) return -1L;
    struct tm tm_utc;
    memset(&tm_utc, 0, sizeof(tm_utc));
    if (strptime(ts, "%Y-%m-%dT%H:%M:%S", &tm_utc) == NULL) return -1L;
    time_t epoch = timegm(&tm_utc);
    if (epoch == (time_t)-1) return -1L;
    return (long)epoch;
}
```

`<time.h>` and `<string.h>` are already included. `strptime`/`timegm` are available because CFLAGS set no `-std` flag (gcc gnu mode defines `_DEFAULT_SOURCE`). If the compiler nonetheless warns about implicit declarations, add `#define _DEFAULT_SOURCE` as the FIRST line of the file — but only if needed; zero warnings is the acceptance bar either way.

- [ ] **Step 6: Run tests, verify they pass with zero warnings**

Run: `cd c_progs && make run_freshness_tests`
Expected: compiles with no warnings, prints 8 PASS lines and `All 8 tests passed.`

- [ ] **Step 7: Commit**

```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced
git add c_progs/stock_analyzer_json.c c_progs/test_freshness_filter.c c_progs/Makefile
git commit -m "feat(c): add ISO-8601 to epoch parser with unit tests

Groundwork for scanner freshness gating. main() is now guarded by
STOCK_ANALYZER_NO_MAIN so tests can include the source directly.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: C `-T` cutoff flag and stale-symbol skip

**Files:**
- Modify: `c_progs/stock_analyzer_json.c`

- [ ] **Step 1: Add `min_trade_epoch` parameter to `get_stock_snapshots()`**

Change the signature (line ~224):

```c
int get_stock_snapshots(char **symbols, int symbol_count, StockData *results, int *result_count, double max_price, double min_percent_change, int min_trades, int all_symbols, int raw_output, long min_trade_epoch) {
```

- [ ] **Step 2: Add the freshness skip inside the per-symbol loop**

Directly after the existing block that extracts `timestamp_json` and the price/trades values (after line ~333, `int volume = json_object_get_int(volume_json);`), add:

```c
        // Freshness gate: halted/delisted symbols keep their last pre-halt
        // print in the snapshot indefinitely, so anything older than the
        // cutoff is dropped BEFORE ranking. Missing/unparseable timestamps
        // fail closed when a cutoff is active.
        if (!all_symbols && min_trade_epoch > 0) {
            long trade_epoch = -1L;
            if (timestamp_json) {
                trade_epoch = parse_iso8601_to_epoch(json_object_get_string(timestamp_json));
            }
            if (trade_epoch < min_trade_epoch) continue;
        }
```

- [ ] **Step 3: Add `-T` option parsing in `main()`**

In `main()`'s locals (line ~654 area), add:

```c
    long min_trade_epoch = 0;  // 0 = freshness filter disabled
```

In the argument-parsing loop, after the `-t` handler (ends line ~706), add:

```c
        } else if (strcmp(argv[i], "-T") == 0 && i + 1 < argc) {
            char *endptr;
            long val = strtol(argv[++i], &endptr, 10);
            if (*endptr != '\0' || val < 0) {
                fprintf(stderr, "Error: -T requires a non-negative Unix epoch (seconds), got '%s'\n", argv[i]);
                return 1;
            }
            min_trade_epoch = val;
```

- [ ] **Step 4: Update the call site and help text**

The `get_stock_snapshots(...)` call in `main()` (line ~772) gets the new final argument:

```c
    if (get_stock_snapshots(symbols, symbol_count, results, &result_count, max_price, min_percent_change, min_trades, all_symbols, raw_output, min_trade_epoch) != 0) {
```

In `print_help()`, after the `-t TRADES` line, add:

```c
    printf("  -T EPOCH      Minimum latestTrade Unix timestamp in seconds (default: 0 = disabled)\n");
    printf("                Symbols whose last trade is older are skipped (stale/halted filter)\n");
```

- [ ] **Step 5: Rebuild everything warning-free and re-run tests**

Run: `cd c_progs && make clean && make stock_analyzer_json && make run_freshness_tests`
Expected: zero warnings; all 8 tests pass.

- [ ] **Step 6: Manual behavioral check against the live API**

```bash
cd c_progs
# Cutoff in the far future: EVERYTHING is stale, expect empty results array
./stock_analyzer_json -s "AAPL,MSFT" -T 4102444800 -c 0 -t 0 -p 100000
# Cutoff disabled: expect AAPL/MSFT to appear as before
./stock_analyzer_json -s "AAPL,MSFT" -T 0 -c 0 -t 0 -p 100000
```

Expected: first command outputs JSON with `"results_count": 0`; second outputs both symbols.

- [ ] **Step 7: Commit**

```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced
git add c_progs/stock_analyzer_json.c
git commit -m "feat(c): -T epoch cutoff drops stale prints before ranking

Symbols whose latestTrade predates the cutoff never consume top-N
slots. Fail-closed on missing/bad timestamps; -T 0 (default) keeps
pre-change behavior. Not applied in -a all-symbols mode.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Python `freshness.py` module (TDD)

**Files:**
- Create: `alpaca_mcp_server/tools/freshness.py`
- Test: `alpaca_mcp_server/tests/unit/test_freshness.py`

- [ ] **Step 1: Write the failing tests**

Create `alpaca_mcp_server/tests/unit/test_freshness.py`:

```python
"""Tests for scanner freshness-cutoff computation and timestamp helpers."""

import time
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytz

from alpaca_mcp_server.tools import freshness


def _reset_cache():
    freshness._cache["value"] = None
    freshness._cache["expires"] = 0.0


class TestParseIsoEpoch:
    def test_known_value(self):
        # date -u -d "2026-06-08T20:00:00Z" +%s -> 1780948800
        assert freshness.parse_iso_epoch("2026-06-08T20:00:00Z") == 1780948800

    def test_fractional_seconds_ignored(self):
        assert freshness.parse_iso_epoch("2026-06-08T20:00:00.123456789Z") == 1780948800

    def test_malformed_returns_none(self):
        assert freshness.parse_iso_epoch("garbage") is None
        assert freshness.parse_iso_epoch("") is None
        assert freshness.parse_iso_epoch(None) is None


class TestIsStale:
    def test_older_than_cutoff_is_stale(self):
        assert freshness.is_stale("2026-06-08T20:00:00Z", cutoff_epoch=1780948801)

    def test_at_cutoff_is_fresh(self):
        assert not freshness.is_stale("2026-06-08T20:00:00Z", cutoff_epoch=1780948800)

    def test_missing_timestamp_fails_closed(self):
        assert freshness.is_stale(None, cutoff_epoch=1)
        assert freshness.is_stale("garbage", cutoff_epoch=1)

    def test_disabled_cutoff_never_stale(self):
        assert not freshness.is_stale(None, cutoff_epoch=0)


class TestFreshnessCutoff:
    def _client_with_sessions(self, dates):
        client = MagicMock()
        client.get_calendar.return_value = [
            SimpleNamespace(date=d.isoformat()) for d in dates
        ]
        return client

    def test_calendar_cutoff_is_prev_trading_day_0400_et(self):
        _reset_cache()
        eastern = pytz.timezone("America/New_York")
        today = datetime.now(eastern).date()
        prev_day = today - timedelta(days=3)  # pretend a long weekend
        client = self._client_with_sessions(
            [today, prev_day, prev_day - timedelta(days=1)]
        )
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            return_value=client,
        ):
            cutoff, source = freshness.freshness_cutoff()
        expected = int(
            eastern.localize(
                datetime.combine(prev_day, freshness._PREMARKET_START)
            ).timestamp()
        )
        assert source == "calendar"
        assert cutoff == expected

    def test_fallback_when_calendar_unavailable(self):
        _reset_cache()
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            side_effect=RuntimeError("api down"),
        ):
            before = time.time()
            cutoff, source = freshness.freshness_cutoff()
        assert source == "fallback"
        assert abs(cutoff - (before - 96 * 3600)) < 5

    def test_result_is_cached(self):
        _reset_cache()
        client = self._client_with_sessions(
            [date.today() - timedelta(days=1)]
        )
        with patch(
            "alpaca_mcp_server.config.settings.get_trading_client",
            return_value=client,
        ) as mock_get:
            first = freshness.freshness_cutoff()
            second = freshness.freshness_cutoff()
        assert first == second
        assert mock_get.call_count == 1


class TestFormatting:
    def test_format_trade_age_recent(self):
        two_hours_ago = datetime.now(pytz.UTC) - timedelta(hours=2, minutes=5)
        iso = two_hours_ago.strftime("%Y-%m-%dT%H:%M:%S") + ".123Z"
        out = freshness.format_trade_age(iso)
        assert " ET (" in out
        assert out.endswith("ago)")
        assert "2h" in out

    def test_format_trade_age_days(self):
        old = datetime.now(pytz.UTC) - timedelta(days=23, hours=1)
        iso = old.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        assert "23d" in freshness.format_trade_age(iso)

    def test_format_trade_age_malformed(self):
        assert freshness.format_trade_age("garbage") == "unknown"

    def test_format_cutoff(self):
        # 1782806400 == 2026-06-30 04:00 ET (date -u -d "2026-06-30T04:00:00-04:00" +%s)
        assert freshness.format_cutoff(1782806400) == "2026-06-30 04:00 ET"
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd /home/jjoravet/alpaca-mcp-server-enhanced && uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py -v`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'alpaca_mcp_server.tools.freshness'`.

- [ ] **Step 3: Implement `freshness.py`**

Create `alpaca_mcp_server/tools/freshness.py`:

```python
"""Shared freshness-cutoff logic for scanner staleness gating.

A print is *fresh* iff its latestTrade timestamp is at or after 04:00 ET
(pre-market start) of the previous trading day per the Alpaca market
calendar. Halted/delisted symbols keep their last pre-halt print in
snapshots indefinitely; this cutoff is what filters them out of scanner
results (see docs/superpowers/specs/2026-07-01-scanner-freshness-gating-design.md).
"""

import logging
import time as _time
from datetime import date, datetime, time, timedelta

import pytz

logger = logging.getLogger(__name__)

_EASTERN = pytz.timezone("America/New_York")
_PREMARKET_START = time(4, 0)
_CACHE_TTL_SECONDS = 900  # 15 minutes
_FALLBACK_WINDOW_HOURS = 96

_cache: dict = {"value": None, "expires": 0.0}


def freshness_cutoff() -> tuple[int, str]:
    """Return (cutoff_epoch_seconds, source).

    source is "calendar" normally, or "fallback" (now - 96h) when the
    market calendar is unavailable. Results are cached for 15 minutes.
    """
    now = _time.time()
    if _cache["value"] is not None and now < _cache["expires"]:
        return _cache["value"]

    try:
        value = (_calendar_cutoff(), "calendar")
    except Exception as exc:
        logger.warning("Market calendar unavailable, using 96h fallback: %s", exc)
        value = (int(now - _FALLBACK_WINDOW_HOURS * 3600), "fallback")

    _cache["value"] = value
    _cache["expires"] = now + _CACHE_TTL_SECONDS
    return value


def _calendar_cutoff() -> int:
    """Cutoff = 04:00 ET on the most recent trading day before today (ET)."""
    from alpaca.trading.requests import GetCalendarRequest

    from ..config.settings import get_trading_client

    client = get_trading_client()
    today_et = datetime.now(_EASTERN).date()
    calendar = client.get_calendar(
        filters=GetCalendarRequest(
            start=(today_et - timedelta(days=10)).isoformat(),
            end=today_et.isoformat(),
        )
    )
    session_dates = sorted(
        d
        for d in (_session_date(entry) for entry in calendar)
        if d is not None and d < today_et
    )
    if not session_dates:
        raise RuntimeError("no prior trading sessions in calendar response")
    cutoff_dt = _EASTERN.localize(
        datetime.combine(session_dates[-1], _PREMARKET_START)
    )
    return int(cutoff_dt.timestamp())


def _session_date(entry) -> date | None:
    """Calendar entries expose .date as a date or an ISO string."""
    try:
        return date.fromisoformat(str(entry.date)[:10])
    except (AttributeError, ValueError):
        return None


def parse_iso_epoch(iso_timestamp: str | None) -> int | None:
    """ISO-8601 UTC timestamp -> epoch seconds; None if unparseable.

    Fractional seconds of any precision are ignored (Alpaca uses
    nanoseconds, which datetime.fromisoformat cannot digest).
    """
    if not iso_timestamp:
        return None
    try:
        head = iso_timestamp.replace("Z", "+00:00")
        if "." in head:
            base, _, frac = head.partition(".")
            plus = frac.find("+")
            head = base + (frac[plus:] if plus != -1 else "+00:00")
        return int(datetime.fromisoformat(head).timestamp())
    except (ValueError, AttributeError, TypeError):
        return None


def is_stale(iso_timestamp: str | None, cutoff_epoch: int) -> bool:
    """True iff the print predates the cutoff. Fail closed: a missing or
    unparseable timestamp is stale whenever a cutoff is active."""
    if cutoff_epoch <= 0:
        return False
    epoch = parse_iso_epoch(iso_timestamp)
    if epoch is None:
        return True
    return epoch < cutoff_epoch


def format_trade_age(iso_timestamp: str | None) -> str:
    """Render '2026-07-01 19:59 ET (1h 26m ago)' for scanner output."""
    epoch = parse_iso_epoch(iso_timestamp)
    if epoch is None:
        return "unknown"
    dt_et = datetime.fromtimestamp(epoch, _EASTERN)
    age = max(0, int(_time.time()) - epoch)
    days, rem = divmod(age, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        age_str = f"{days}d {hours}h ago"
    elif hours:
        age_str = f"{hours}h {minutes}m ago"
    else:
        age_str = f"{minutes}m ago"
    return f"{dt_et.strftime('%Y-%m-%d %H:%M')} ET ({age_str})"


def format_cutoff(cutoff_epoch: int) -> str:
    """Render the cutoff as '2026-06-30 04:00 ET'."""
    return datetime.fromtimestamp(cutoff_epoch, _EASTERN).strftime(
        "%Y-%m-%d %H:%M ET"
    )
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced
git add alpaca_mcp_server/tools/freshness.py alpaca_mcp_server/tests/unit/test_freshness.py
git commit -m "feat: shared freshness-cutoff module for scanner staleness gating

Cutoff = 04:00 ET of the previous trading day (Alpaca market calendar,
15-min cache, 96h fallback). Includes ISO parsing, is_stale fail-closed
check, and age/cutoff formatting for scanner output.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Wire the C wrapper — `-T` pass-through, `require_fresh`, age display

**Files:**
- Modify: `alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py`
- Test: `alpaca_mcp_server/tests/unit/test_freshness.py` (append a class)

- [ ] **Step 1: Write the failing test**

Append to `alpaca_mcp_server/tests/unit/test_freshness.py`:

```python
class TestAnalyzerCutoffFlag:
    def _run_analyze(self, **kwargs):
        from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import CStockAnalyzer

        captured = {}

        def fake_run(cmd, **_kw):
            captured["cmd"] = cmd
            return SimpleNamespace(
                stdout='{"results_count": 0, "stocks": []}', stderr="", returncode=0
            )

        with patch(
            "alpaca_mcp_server.tools.c_stock_analyzer_wrapper.subprocess.run",
            side_effect=fake_run,
        ):
            CStockAnalyzer().analyze(symbols="AAPL", **kwargs)
        return captured["cmd"]

    def test_min_trade_ts_appends_T_flag(self):
        cmd = self._run_analyze(min_trade_ts=1782806400)
        assert "-T" in cmd
        assert cmd[cmd.index("-T") + 1] == "1782806400"

    def test_no_min_trade_ts_no_T_flag(self):
        cmd = self._run_analyze()
        assert "-T" not in cmd
```

Run: `uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py::TestAnalyzerCutoffFlag -v`
Expected: FAIL — `TypeError: CStockAnalyzer.analyze() got an unexpected keyword argument 'min_trade_ts'`.

- [ ] **Step 2: Add `min_trade_ts` to `CStockAnalyzer.analyze()`**

In `alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py`, add the parameter to the signature (after `raw_data: bool = False,`):

```python
        raw_data: bool = False,
        min_trade_ts: int | None = None,
    ) -> dict:
```

Document it in the docstring Args:

```
            min_trade_ts: Minimum latestTrade Unix timestamp (seconds).
                Symbols with older prints are dropped by the C program (-T).
```

In the command-building section, after the `if raw_data:` block:

```python
        if min_trade_ts and min_trade_ts > 0:
            cmd.extend(["-T", str(min_trade_ts)])
```

Run: `uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py -v` → all PASS.

- [ ] **Step 3: Add `require_fresh` + age display to `scan_explosive_stocks_fast`**

At the top of the module add the import:

```python
from alpaca_mcp_server.tools.freshness import (
    format_cutoff,
    format_trade_age,
    freshness_cutoff,
)
```

Change the signature:

```python
async def scan_explosive_stocks_fast(
    max_results: int = 20,
    min_percent_change: float = 15.0,  # Higher for explosive moves
    max_price: float = 30.0,  # C program default for penny stocks
    require_fresh: bool = True,
) -> str:
```

Add to the docstring Args: `require_fresh: Drop symbols whose last trade predates the freshness cutoff (default True; False restores unfiltered behavior).`

Before `result = analyzer.analyze(`, compute the cutoff:

```python
    cutoff_epoch, cutoff_source = (0, "disabled")
    if require_fresh:
        cutoff_epoch, cutoff_source = freshness_cutoff()
```

Pass it through in the `analyzer.analyze(...)` call by adding:

```python
        min_trade_ts=cutoff_epoch,
```

In the "Scanner Settings" section, after the Min Trades line, add:

```python
    if cutoff_source == "disabled":
        output.append("  • Freshness Filter: DISABLED (stale prints may appear)")
    else:
        note = " — market calendar unavailable, using 96h fallback" if cutoff_source == "fallback" else ""
        output.append(f"  • Freshness Cutoff: last trade ≥ {format_cutoff(cutoff_epoch)}{note}")
```

In the per-stock output loop, after the Trades line (`output.append(f"    • Trades: {trades:,}")`), add:

```python
            output.append(f"    • Last trade: {format_trade_age(stock.get('timestamp'))}")
```

- [ ] **Step 4: Same treatment for `analyze_market_activity_fast`**

Signature gains `require_fresh: bool = True` (after `sort_by`). Same cutoff computation before `analyzer.analyze(...)`, same `min_trade_ts=cutoff_epoch` pass-through, same Freshness line in the "Analysis Summary" section, and the same `Last trade:` line after the Trades line in its stock loop.

- [ ] **Step 5: Run the full unit test file + smoke-check formatting**

```bash
uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py -v
uv run python -c "
import asyncio
from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import scan_explosive_stocks_fast
print(asyncio.run(scan_explosive_stocks_fast(max_results=5, min_percent_change=10, max_price=50)))
"
```

Expected: tests pass; live output shows the `Freshness Cutoff:` header line and a `Last trade: ... ET (... ago)` line per stock; INHD absent.

- [ ] **Step 6: Commit**

```bash
git add alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py alpaca_mcp_server/tests/unit/test_freshness.py
git commit -m "feat: fast scanners drop stale prints and show last-trade age

require_fresh=True (default) passes the calendar cutoff to the C
analyzer via -T; each result now displays its last-trade time and age.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Python scanner drops stale symbols

**Files:**
- Modify: `alpaca_mcp_server/tools/day_trading_scanner.py`

- [ ] **Step 1: Import and compute the cutoff**

Add the import near the top (after `from ..config import ...`):

```python
from .freshness import format_cutoff, freshness_cutoff, is_stale
```

Inside `scan_day_trading_opportunities()`, right before the per-symbol loop (`for symbol in symbol_list:` at line ~184), add:

```python
        # Freshness gate: drop symbols whose latest print predates the cutoff
        cutoff_epoch, cutoff_source = freshness_cutoff()
        stale_filtered = 0
```

- [ ] **Step 2: Drop stale symbols in the loop**

Directly after the `if not latest_trade or not minute_bar: continue` check (line ~195), add:

```python
                # Halted/delisted symbols keep stale prints in snapshots;
                # drop them instead of ranking three-week-old data.
                if is_stale(latest_trade.get("t"), cutoff_epoch):
                    stale_filtered += 1
                    continue
```

- [ ] **Step 3: Report the filtered count in both output paths**

Both f-string templates (the "0 stocks" early return at line ~300 and the main results header at line ~324) contain the line `Total Qualified: ...`. In BOTH, add directly beneath it:

```
Freshness: last trade ≥ {format_cutoff(cutoff_epoch)} ({cutoff_source}); filtered {stale_filtered} stale symbols
```

- [ ] **Step 4: Verify live**

```bash
uv run python -c "
import asyncio
from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities
print(asyncio.run(scan_day_trading_opportunities(symbols='AAPL,MSFT,INHD', min_trades_per_minute=0, min_percent_change=0)))
"
```

Expected: output shows the `Freshness:` line with `filtered 1 stale symbols` (INHD), and INHD does not appear in the table. (If run during a live session INHD may still be halted; if it has resumed trading by execution time, it will legitimately pass — then verify with the future-cutoff C check from Task 2 Step 6 instead.)

- [ ] **Step 5: Run the whole unit suite to catch regressions**

Run: `uv run pytest alpaca_mcp_server/tests/unit/ -x -q`
Expected: no new failures (pre-existing failures, if any, are unrelated — note them).

- [ ] **Step 6: Commit**

```bash
git add alpaca_mcp_server/tools/day_trading_scanner.py
git commit -m "feat: day trading scanner drops stale symbols instead of warning

Uses the shared calendar cutoff; reports the filtered count and active
cutoff in the scan header.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Expose `require_fresh` through MCP tool registration

**Files:**
- Modify: `alpaca_mcp_server/server_components/tool_registrations.py:479-535`

⚠️ This file may carry pre-existing uncommitted user changes (help-system WIP). Commit the whole file anyway and say so in the commit body — it's the user's own WIP feature branch.

- [ ] **Step 1: Add the parameter to both registered tools**

`scan_explosive_stocks_fast` registration (line ~514): add `require_fresh: bool = True,` after `max_price`, document it in the docstring (`require_fresh: Drop symbols whose last trade predates the freshness cutoff (default True)`), and pass it through:

```python
        return await c_scanner_func(max_results, min_percent_change, max_price, require_fresh)
```

`analyze_market_activity_fast` registration (line ~479): same pattern — add `require_fresh: bool = True` as the last parameter, document it, and append it to the `c_analyzer_func(...)` call as a keyword argument (`require_fresh=require_fresh`) since that function has more positional parameters.

- [ ] **Step 2: Verify the server still imports cleanly**

Run: `uv run python -c "from alpaca_mcp_server.server_components import tool_registrations; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add alpaca_mcp_server/server_components/tool_registrations.py
git commit -m "feat: expose require_fresh on fast scanner MCP tools

Note: includes pre-existing uncommitted WIP hunks already present in
this file on the feature branch.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Full rebuild + full test pass**

```bash
cd /home/jjoravet/alpaca-mcp-server-enhanced/c_progs && make clean && make && make run_freshness_tests
cd /home/jjoravet/alpaca-mcp-server-enhanced && uv run pytest alpaca_mcp_server/tests/unit/test_freshness.py -v
```

Expected: zero compile warnings; all pytest tests pass.

- [ ] **Step 2: The INHD regression check (the original bug)**

```bash
uv run python -c "
import asyncio
from alpaca_mcp_server.tools.c_stock_analyzer_wrapper import scan_explosive_stocks_fast

fresh = asyncio.run(scan_explosive_stocks_fast(max_results=15, min_percent_change=10, max_price=50))
print(fresh)
assert 'INHD' not in fresh, 'stale halted symbol leaked through!'

unfiltered = asyncio.run(scan_explosive_stocks_fast(max_results=15, min_percent_change=10, max_price=50, require_fresh=False))
assert 'INHD' in unfiltered, 'escape hatch broken (or INHD resumed trading)'
print('INHD filtered when fresh, visible when unfiltered — OK')
"
```

Expected: assertion passes both ways while INHD remains halted. If INHD has resumed trading by execution time, substitute the future-cutoff check: `./c_progs/stock_analyzer_json -s "AAPL" -T 4102444800 -c 0 -t 0 -p 100000` must return 0 results.

- [ ] **Step 3: Confirm every surviving result shows an age**

Inspect the `fresh` output from Step 2: every listed stock must have a `Last trade: YYYY-MM-DD HH:MM ET (... ago)` line, and the header must show the `Freshness Cutoff:` line with source `calendar` (not `fallback`, unless the API was actually down).

- [ ] **Step 4: Lint check (repo uses ruff)**

Run: `uv run ruff check alpaca_mcp_server/tools/freshness.py alpaca_mcp_server/tools/c_stock_analyzer_wrapper.py alpaca_mcp_server/tools/day_trading_scanner.py alpaca_mcp_server/tests/unit/test_freshness.py`
Expected: no errors. Fix anything reported, amend the relevant commit.
