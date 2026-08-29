/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_TRACE_CLOCK_H
#define BEMU_TRACE_CLOCK_H

#include <stdint.h>

/*
 * Deterministic logical clock for bEMU observability.
 *
 * The trace clock is intentionally not wall-clock based.  Every observable
 * event advances the clock by a fixed quantum, so two runs that execute the
 * same guest path produce identical timestamps.  This is the foundation for
 * record/replay comparison.
 *
 * The clock exposes a boot timestamp plus a monotonic event counter.  The
 * boot timestamp is taken from SOURCE_DATE_EPOCH when available, otherwise
 * zero, keeping the trace stable across clean builds.
 */

#define TRACE_CLOCK_QUANTUM_NS 1

struct trace_clock {
    uint64_t boot_ns;      /* deterministic epoch */
    uint64_t event_seq;    /* number of clock ticks since boot */
    uint64_t logical_ns;   /* boot_ns + event_seq * TRACE_CLOCK_QUANTUM_NS */
};

void trace_clock_reset(struct trace_clock *tc);
void trace_clock_tick(struct trace_clock *tc);
uint64_t trace_clock_now(const struct trace_clock *tc);
uint64_t trace_clock_seq(const struct trace_clock *tc);

#endif
