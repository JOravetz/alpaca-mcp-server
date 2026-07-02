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

#undef NDEBUG
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

static void test_numeric_offset_rejected(void) {
    /* Offset timestamps must be rejected, not silently misparsed as UTC. */
    assert(parse_iso8601_to_epoch("2026-06-08T16:00:00-04:00") == -1L);
}

static void test_trailing_garbage_rejected(void) {
    assert(parse_iso8601_to_epoch("2026-06-08T20:00:00xyzzy") == -1L);
}

static void test_leap_day(void) {
    /* date -u -d "2024-02-29T12:00:00Z" +%s */
    assert(parse_iso8601_to_epoch("2024-02-29T12:00:00Z") == 1709208000L);
}

static void test_post_2038(void) {
    /* date -u -d "2040-01-01T00:00:00Z" +%s */
    assert(parse_iso8601_to_epoch("2040-01-01T00:00:00Z") == 2208988800L);
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
    RUN_TEST(test_numeric_offset_rejected);
    RUN_TEST(test_trailing_garbage_rejected);
    RUN_TEST(test_leap_day);
    RUN_TEST(test_post_2038);
    printf("All %d tests passed.\n", tests_run);
    return 0;
}
