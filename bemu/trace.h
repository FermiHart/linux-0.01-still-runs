#ifndef BEMU_TRACE_H
#define BEMU_TRACE_H

#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#include "trace_clock.h"

/*
 * JSON Lines trace producer for bEMU observability.
 *
 * The producer is intentionally simple: each event is emitted as one JSON
 * object terminated by a newline.  It is driven by the deterministic logical
 * clock so that traces are comparable across runs.
 */

struct trace {
    struct trace_clock *clock;
    FILE *file;
    int enabled;
    unsigned long exit_count;
};

/* Open a trace file.  If path is NULL or "-", events are written to stderr. */
int trace_open(struct trace *t, struct trace_clock *tc, const char *path);
void trace_close(struct trace *t);

/* Event emitters.  Each call emits one JSON Lines object. */
void trace_event_boot(struct trace *t,
                      const char *kernel,
                      const char *root,
                      unsigned ram_mib,
                      unsigned trace_version);

void trace_event_kvm_exit(struct trace *t,
                          unsigned exit_reason,
                          const char *reason_name);

void trace_event_io_access(struct trace *t,
                           const char *direction,
                           uint16_t port,
                           unsigned size,
                           uint32_t value);

void trace_event_irq(struct trace *t,
                     unsigned irq,
                     const char *action);

void trace_event_timer(struct trace *t,
                       uint16_t port,
                       const char *action);

void trace_event_input(struct trace *t,
                       size_t bytes,
                       const char *source);

/*
 * syscall/interrupt/process events are emitted when the host can observe the
 * guest behaviour.  On this KVM backend syscall vectors and process switches are
 * not directly visible, so these events are recorded explicitly when the
 * instrumentation path provides them (see Wave 073).
 */
void trace_event_syscall(struct trace *t,
                         unsigned number,
                         const uint64_t *args,
                         unsigned nargs);

void trace_event_interrupt(struct trace *t,
                           unsigned vector);

void trace_event_process(struct trace *t,
                         unsigned pid,
                         const char *action,
                         const char *name);

void trace_event_shutdown(struct trace *t,
                          const char *reason,
                          unsigned long exits,
                          int status);

#endif
