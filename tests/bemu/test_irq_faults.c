#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../bemu/irq.h"

#define EVENT_MAX 64

struct level_event {
    unsigned irq;
    int level;
};

struct trace_event {
    unsigned irq;
    const char *action;
};

struct fixture {
    struct bemu_irq_bridge bridge;
    struct level_event levels[EVENT_MAX];
    struct trace_event traces[EVENT_MAX];
    unsigned level_count;
    unsigned trace_count;
    unsigned quiescent_irq;
    unsigned quiescent_calls;
    int quiescent;
};

static int failures;

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void set_line(void *opaque, unsigned irq, int level)
{
    struct fixture *f = opaque;
    if (f->level_count >= EVENT_MAX)
        return;
    f->levels[f->level_count].irq = irq;
    f->levels[f->level_count].level = level;
    f->level_count++;
}

static int is_quiescent(void *opaque, unsigned irq)
{
    struct fixture *f = opaque;
    f->quiescent_irq = irq;
    f->quiescent_calls++;
    return f->quiescent;
}

static void trace_irq(void *opaque, unsigned irq, const char *action)
{
    struct fixture *f = opaque;
    if (f->trace_count >= EVENT_MAX)
        return;
    f->traces[f->trace_count].irq = irq;
    f->traces[f->trace_count].action = action;
    f->trace_count++;
}

static void setup(struct fixture *f)
{
    memset(f, 0, sizeof *f);
    f->quiescent = 1;
    bemu_irq_init(&f->bridge, f, set_line, is_quiescent, trace_irq);
}

static unsigned trace_count(const struct fixture *f, const char *action)
{
    unsigned count = 0;
    unsigned i;
    for (i = 0; i < f->trace_count; i++)
        if (strcmp(f->traces[i].action, action) == 0)
            count++;
    return count;
}

static void test_passthrough_and_validation(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_pulse(&f.bridge, 0) == 0,
          "unarmed IRQ pulse passes through");
    check(f.level_count == 2 && f.levels[0].irq == 0 &&
          f.levels[0].level == 1 && f.levels[1].level == 0,
          "unarmed IRQ preserves raise/lower order");
    check(trace_count(&f, "raise") == 1 && trace_count(&f, "lower") == 1,
          "unarmed IRQ preserves trace actions");
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_NONE, 0) < 0,
          "none fault is rejected");
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 16) < 0,
          "out-of-range fault IRQ is rejected");
    check(bemu_irq_level(&f.bridge, 16, 1) < 0,
          "out-of-range IRQ transition is rejected");
}

static void test_drop_scope_and_recovery(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 0) == 0,
          "drop fault arms");
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 1) < 0,
          "second armed fault is rejected");
    check(bemu_irq_pulse(&f.bridge, 1) == 0 && f.level_count == 2,
          "nonmatching IRQ passes without consuming fault");
    check(bemu_irq_pulse(&f.bridge, 0) == 0 && f.level_count == 2,
          "matching drop suppresses raise and lower");
    check(trace_count(&f, "fault_drop") == 1,
          "drop decision is traced once");
    check(bemu_irq_pulse(&f.bridge, 0) == 0 && f.level_count == 4,
          "IRQ delivery recovers after one drop");
}

static void test_duplicate_deferral_and_recovery(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 0) == 0,
          "duplicate fault arms");
    check(bemu_irq_pulse(&f.bridge, 0) == 0 && f.level_count == 2,
          "duplicate passes original edge without immediate replay");
    check(trace_count(&f, "fault_duplicate_queued") == 1,
          "duplicate queue decision is traced");
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 0) < 0,
          "new fault is rejected while duplicate is pending");

    f.quiescent = 0;
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 2,
          "pending PIC state defers duplicate replay");
    check(f.quiescent_calls == 1 && f.quiescent_irq == 0,
          "duplicate queries selected IRQ quiescence");

    f.quiescent = 1;
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 4,
          "quiescent PIC receives one duplicate edge");
    check(f.levels[2].irq == 0 && f.levels[2].level == 1 &&
          f.levels[3].irq == 0 && f.levels[3].level == 0,
          "duplicate replay is a complete pulse");
    check(trace_count(&f, "fault_duplicate_replayed") == 1,
          "duplicate replay is traced once");
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 4,
          "later KVM runs do not emit a third edge");
    check(bemu_irq_pulse(&f.bridge, 0) == 0 && f.level_count == 6,
          "IRQ delivery recovers after duplicate replay");
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 0) == 0,
          "new fault can arm after duplicate completion");
}

static void test_quiescence_error_preserves_duplicate(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 0) == 0 &&
          bemu_irq_pulse(&f.bridge, 0) == 0,
          "duplicate queues before quiescence error");
    f.quiescent = -1;
    check(bemu_irq_run_completed(&f.bridge) < 0 && f.level_count == 2,
          "quiescence query error does not replay duplicate");
    f.quiescent = 1;
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 4,
          "duplicate survives quiescence query error");
}

static void test_duplicate_waits_for_low_line(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 1) == 0,
          "level duplicate fault arms");
    check(bemu_irq_level(&f.bridge, 1, 1) == 0,
          "original level assertion passes");
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 1 &&
          f.quiescent_calls == 0,
          "high device line defers replay before PIC query");
    check(bemu_irq_level(&f.bridge, 1, 0) == 0,
          "original level deassertion passes");
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 4,
          "low line allows deferred duplicate pulse");
}

static void test_redundant_high_does_not_consume_fault(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_level(&f.bridge, 3, 1) == 0 &&
          bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 3) == 0,
          "drop fault arms while selected line is high");
    check(bemu_irq_level(&f.bridge, 3, 1) == 0 && f.level_count == 2,
          "redundant high passes without consuming fault");
    check(bemu_irq_level(&f.bridge, 3, 0) == 0 && f.level_count == 3,
          "line can return low before matching edge");
    check(bemu_irq_pulse(&f.bridge, 3) == 0 && f.level_count == 3,
          "next inactive-to-active edge consumes drop");
    check(bemu_irq_pulse(&f.bridge, 3) == 0 && f.level_count == 5,
          "delivery recovers after high-line drop case");
}

static void test_reset_cancels_faults(void)
{
    struct fixture f;
    setup(&f);

    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 0) == 0,
          "fault arms before reset");
    bemu_irq_reset(&f.bridge);
    check(bemu_irq_pulse(&f.bridge, 0) == 0 && f.level_count == 2,
          "reset cancels unconsumed fault");

    setup(&f);
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 0) == 0 &&
          bemu_irq_pulse(&f.bridge, 0) == 0,
          "duplicate queues before reset");
    bemu_irq_reset(&f.bridge);
    check(bemu_irq_run_completed(&f.bridge) == 0 && f.level_count == 2,
          "reset cancels deferred replay");

    setup(&f);
    check(bemu_irq_level(&f.bridge, 3, 1) == 0,
          "line is high before fault reset");
    bemu_irq_reset(&f.bridge);
    check(bemu_irq_inject_fault(&f.bridge, BEMU_IRQ_FAULT_DROP_ONCE, 3) == 0 &&
          bemu_irq_level(&f.bridge, 3, 1) == 0 && f.level_count == 2,
          "reset preserves live line state and redundant high");
    check(bemu_irq_level(&f.bridge, 3, 0) == 0 &&
          bemu_irq_pulse(&f.bridge, 3) == 0 && f.level_count == 3,
          "preserved line must fall before reset fault matches");
}

static void test_pic_quiescence(void)
{
    check(bemu_irq_pic_quiescent(0, 0, 0, 0, 0),
          "idle master PIC is quiescent");
    check(!bemu_irq_pic_quiescent(0, 0x01, 0, 0, 0),
          "master IRR blocks duplicate");
    check(!bemu_irq_pic_quiescent(0, 0, 0x01, 0, 0),
          "master ISR blocks duplicate");
    check(bemu_irq_pic_quiescent(0, 0x02, 0x02, 0, 0),
          "unrelated master state does not block duplicate");
    check(!bemu_irq_pic_quiescent(14, 0, 0, 0x40, 0),
          "slave IRR blocks duplicate");
    check(!bemu_irq_pic_quiescent(14, 0, 0, 0, 0x40),
          "slave ISR blocks duplicate");
    check(!bemu_irq_pic_quiescent(14, 0x04, 0, 0, 0),
          "master cascade IRR blocks slave duplicate");
    check(!bemu_irq_pic_quiescent(14, 0, 0x04, 0, 0),
          "master cascade ISR blocks slave duplicate");
    check(bemu_irq_pic_quiescent(14, 0x01, 0x01, 0x01, 0x01),
          "unrelated PIC state permits slave duplicate");
}

int main(void)
{
    test_passthrough_and_validation();
    test_drop_scope_and_recovery();
    test_duplicate_deferral_and_recovery();
    test_quiescence_error_preserves_duplicate();
    test_duplicate_waits_for_low_line();
    test_redundant_high_does_not_consume_fault();
    test_reset_cancels_faults();
    test_pic_quiescence();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall IRQ fault-injection tests passed\n");
    return 0;
}
