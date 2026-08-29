/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "trace_clock.h"

#include <stdlib.h>

void trace_clock_reset(struct trace_clock *tc)
{
    const char *env = getenv("SOURCE_DATE_EPOCH");
    tc->boot_ns = 0;
    if (env) {
        char *end = NULL;
        unsigned long long epoch = strtoull(env, &end, 10);
        if (end && *end == '\0' && epoch <= UINT64_MAX / 1000000000ULL)
            tc->boot_ns = epoch * 1000000000ULL;
    }
    tc->event_seq = 0;
    tc->logical_ns = tc->boot_ns;
}

void trace_clock_tick(struct trace_clock *tc)
{
    tc->event_seq++;
    tc->logical_ns = tc->boot_ns + tc->event_seq * TRACE_CLOCK_QUANTUM_NS;
}

uint64_t trace_clock_now(const struct trace_clock *tc)
{
    return tc->logical_ns;
}

uint64_t trace_clock_seq(const struct trace_clock *tc)
{
    return tc->event_seq;
}
