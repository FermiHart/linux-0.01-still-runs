#include "irq.h"

#include <string.h>

static void trace_action(struct bemu_irq_bridge *bridge, unsigned irq,
                         const char *action)
{
    if (bridge->trace)
        bridge->trace(bridge->opaque, irq, action);
}

static void forward_level(struct bemu_irq_bridge *bridge, unsigned irq,
                          int level)
{
    bridge->set_line(bridge->opaque, irq, level);
    trace_action(bridge, irq, level ? "raise" : "lower");
}

void bemu_irq_init(struct bemu_irq_bridge *bridge, void *opaque,
                   bemu_irq_set_line_fn set_line,
                   bemu_irq_is_quiescent_fn is_quiescent,
                   bemu_irq_trace_fn trace)
{
    memset(bridge, 0, sizeof *bridge);
    bridge->opaque = opaque;
    bridge->set_line = set_line;
    bridge->is_quiescent = is_quiescent;
    bridge->trace = trace;
}

void bemu_irq_reset(struct bemu_irq_bridge *bridge)
{
    bridge->fault_kind = BEMU_IRQ_FAULT_NONE;
    bridge->fault_irq = 0;
    bridge->replay_after_run = 0;
    bridge->fault_armed = 0;
    bridge->suppressed_assertion = 0;
    bridge->duplicate_pending = 0;
}

int bemu_irq_inject_fault(struct bemu_irq_bridge *bridge,
                          enum bemu_irq_fault_kind kind, unsigned irq)
{
    if (!bridge || irq >= BEMU_IRQ_COUNT ||
        (kind != BEMU_IRQ_FAULT_DROP_ONCE &&
         kind != BEMU_IRQ_FAULT_DUPLICATE_ONCE))
        return -1;
    if (bridge->fault_armed || bridge->suppressed_assertion ||
        bridge->duplicate_pending)
        return -1;
    bridge->fault_kind = kind;
    bridge->fault_irq = irq;
    bridge->fault_armed = 1;
    return 0;
}

int bemu_irq_level(struct bemu_irq_bridge *bridge, unsigned irq, int level)
{
    uint16_t mask;
    int was_high;

    if (!bridge || !bridge->set_line || irq >= BEMU_IRQ_COUNT)
        return -1;
    level = !!level;
    mask = (uint16_t)(1u << irq);
    was_high = (bridge->requested_levels & mask) != 0;
    if (level)
        bridge->requested_levels |= mask;
    else
        bridge->requested_levels &= (uint16_t)~mask;

    if (bridge->suppressed_assertion && irq == bridge->fault_irq) {
        if (!level) {
            bridge->suppressed_assertion = 0;
            bridge->fault_kind = BEMU_IRQ_FAULT_NONE;
        }
        return 0;
    }

    if (bridge->fault_armed && irq == bridge->fault_irq &&
        level && !was_high) {
        bridge->fault_armed = 0;
        if (bridge->fault_kind == BEMU_IRQ_FAULT_DROP_ONCE) {
            bridge->suppressed_assertion = 1;
            trace_action(bridge, irq, "fault_drop");
            return 0;
        }
        bridge->duplicate_pending = 1;
        bridge->replay_after_run = bridge->completed_runs + 1;
        trace_action(bridge, irq, "fault_duplicate_queued");
    }

    forward_level(bridge, irq, level);
    return 0;
}

int bemu_irq_pulse(struct bemu_irq_bridge *bridge, unsigned irq)
{
    if (bemu_irq_level(bridge, irq, 1) < 0)
        return -1;
    return bemu_irq_level(bridge, irq, 0);
}

int bemu_irq_run_completed(struct bemu_irq_bridge *bridge)
{
    uint16_t mask;
    int quiescent;
    unsigned irq;

    if (!bridge)
        return -1;
    bridge->completed_runs++;
    if (!bridge->duplicate_pending ||
        bridge->completed_runs < bridge->replay_after_run)
        return 0;

    irq = bridge->fault_irq;
    mask = (uint16_t)(1u << irq);
    if (bridge->requested_levels & mask)
        return 0;
    if (!bridge->is_quiescent)
        return -1;
    quiescent = bridge->is_quiescent(bridge->opaque, irq);
    if (quiescent < 0)
        return -1;
    if (!quiescent)
        return 0;

    forward_level(bridge, irq, 1);
    forward_level(bridge, irq, 0);
    bridge->duplicate_pending = 0;
    bridge->fault_kind = BEMU_IRQ_FAULT_NONE;
    trace_action(bridge, irq, "fault_duplicate_replayed");
    return 0;
}

int bemu_irq_pic_quiescent(unsigned irq,
                           uint8_t master_irr, uint8_t master_isr,
                           uint8_t slave_irr, uint8_t slave_isr)
{
    uint8_t mask;

    if (irq >= BEMU_IRQ_COUNT)
        return 0;
    if (irq < 8) {
        mask = (uint8_t)(1u << irq);
        return ((master_irr | master_isr) & mask) == 0;
    }
    mask = (uint8_t)(1u << (irq - 8));
    if ((slave_irr | slave_isr) & mask)
        return 0;
    return ((master_irr | master_isr) & (1u << 2)) == 0;
}
