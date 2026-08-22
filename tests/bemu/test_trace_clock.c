/*
 * Unit tests for the deterministic logical trace clock.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../bemu/trace_clock.h"

static int failures = 0;

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void test_reset_zero(void)
{
    struct trace_clock tc;
    trace_clock_reset(&tc);
    check(tc.event_seq == 0, "trace_clock_reset seq is zero");
    check(trace_clock_now(&tc) == 0, "trace_clock_reset logical_ns is zero");
    check(trace_clock_seq(&tc) == 0, "trace_clock_seq after reset");
}

static void test_tick_monotonic(void)
{
    struct trace_clock tc;
    uint64_t before, after;
    trace_clock_reset(&tc);
    before = trace_clock_now(&tc);
    trace_clock_tick(&tc);
    after = trace_clock_now(&tc);
    check(after == before + TRACE_CLOCK_QUANTUM_NS, "tick advances quantum");
    check(trace_clock_seq(&tc) == 1, "seq after one tick");
    trace_clock_tick(&tc);
    check(trace_clock_seq(&tc) == 2, "seq after two ticks");
    check(trace_clock_now(&tc) == before + 2 * TRACE_CLOCK_QUANTUM_NS,
          "logical_ns after two ticks");
}

static void test_source_date_epoch(void)
{
    struct trace_clock tc;
    const char *old = getenv("SOURCE_DATE_EPOCH");
    setenv("SOURCE_DATE_EPOCH", "1700000000", 1);
    trace_clock_reset(&tc);
    check(tc.boot_ns == 1700000000ULL * 1000000000ULL,
          "boot_ns from SOURCE_DATE_EPOCH");
    check(trace_clock_now(&tc) == tc.boot_ns,
          "logical_ns equals boot_ns after reset");
    trace_clock_tick(&tc);
    check(trace_clock_now(&tc) == tc.boot_ns + TRACE_CLOCK_QUANTUM_NS,
          "logical_ns advances from SOURCE_DATE_EPOCH");
    if (old)
        setenv("SOURCE_DATE_EPOCH", old, 1);
    else
        unsetenv("SOURCE_DATE_EPOCH");
}

static void test_determinism(void)
{
    struct trace_clock a, b;
    unsigned i;
    trace_clock_reset(&a);
    trace_clock_reset(&b);
    for (i = 0; i < 1000; i++) {
        trace_clock_tick(&a);
        trace_clock_tick(&b);
    }
    check(trace_clock_seq(&a) == trace_clock_seq(&b),
          "two clocks produce same seq after same ticks");
    check(trace_clock_now(&a) == trace_clock_now(&b),
          "two clocks produce same logical_ns after same ticks");
}

int main(void)
{
    test_reset_zero();
    test_tick_monotonic();
    test_source_date_epoch();
    test_determinism();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall trace-clock tests passed\n");
    return 0;
}
