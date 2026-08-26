#ifndef BEMU_IRQ_H
#define BEMU_IRQ_H

#include <stdint.h>

#define BEMU_IRQ_COUNT 16

enum bemu_irq_fault_kind {
    BEMU_IRQ_FAULT_NONE,
    BEMU_IRQ_FAULT_DROP_ONCE,
    BEMU_IRQ_FAULT_DUPLICATE_ONCE,
};

/* Line callbacks either complete the transition or terminate the caller. */
typedef void (*bemu_irq_set_line_fn)(void *opaque, unsigned irq, int level);
/* Return 1 when clear, 0 while pending/in-service, or -1 on query failure. */
typedef int (*bemu_irq_is_quiescent_fn)(void *opaque, unsigned irq);
typedef void (*bemu_irq_trace_fn)(void *opaque, unsigned irq,
                                  const char *action);

struct bemu_irq_bridge {
    void *opaque;
    bemu_irq_set_line_fn set_line;
    bemu_irq_is_quiescent_fn is_quiescent;
    bemu_irq_trace_fn trace;
    uint16_t requested_levels;
    unsigned long completed_runs;
    enum bemu_irq_fault_kind fault_kind;
    unsigned fault_irq;
    unsigned long replay_after_run;
    int fault_armed;
    int suppressed_assertion;
    int duplicate_pending;
};

void bemu_irq_init(struct bemu_irq_bridge *bridge, void *opaque,
                   bemu_irq_set_line_fn set_line,
                   bemu_irq_is_quiescent_fn is_quiescent,
                   bemu_irq_trace_fn trace);
void bemu_irq_reset(struct bemu_irq_bridge *bridge);
int bemu_irq_inject_fault(struct bemu_irq_bridge *bridge,
                          enum bemu_irq_fault_kind kind, unsigned irq);
int bemu_irq_level(struct bemu_irq_bridge *bridge, unsigned irq, int level);
int bemu_irq_pulse(struct bemu_irq_bridge *bridge, unsigned irq);
int bemu_irq_run_completed(struct bemu_irq_bridge *bridge);
int bemu_irq_pic_quiescent(unsigned irq,
                           uint8_t master_irr, uint8_t master_isr,
                           uint8_t slave_irr, uint8_t slave_isr);

#endif
