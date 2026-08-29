/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "machine.h"

#include "console.h"
#include "keyboard.h"
#include "memory.h"
#include "uart.h"

#include <linux/kvm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

void die(const char *what)
{
    perror(what);
    exit(1);
}

void fail(const char *what)
{
    fprintf(stderr, "[bemu-linux01] %s\n", what);
    exit(1);
}

static void machine_set_irq_line(void *opaque, unsigned irq, int level)
{
    struct machine *m = opaque;
    struct kvm_irq_level line;
    memset(&line, 0, sizeof line);
    line.irq = irq;
    line.level = level;
    if (ioctl(m->vm, KVM_IRQ_LINE, &line) < 0)
        die("KVM_IRQ_LINE");
}

static int machine_irq_quiescent(void *opaque, unsigned irq)
{
    struct machine *m = opaque;
    struct kvm_irqchip master;
    struct kvm_irqchip slave;

    memset(&master, 0, sizeof master);
    master.chip_id = KVM_IRQCHIP_PIC_MASTER;
    if (ioctl(m->vm, KVM_GET_IRQCHIP, &master) < 0)
        die("KVM_GET_IRQCHIP master PIC");
    memset(&slave, 0, sizeof slave);
    if (irq >= 8) {
        slave.chip_id = KVM_IRQCHIP_PIC_SLAVE;
        if (ioctl(m->vm, KVM_GET_IRQCHIP, &slave) < 0)
            die("KVM_GET_IRQCHIP slave PIC");
    }
    return bemu_irq_pic_quiescent(irq,
                                  master.chip.pic.irr,
                                  master.chip.pic.isr,
                                  slave.chip.pic.irr,
                                  slave.chip.pic.isr);
}

static void machine_trace_irq(void *opaque, unsigned irq, const char *action)
{
    struct machine *m = opaque;
    trace_event_irq(&m->trace, irq, action);
}

void irq_level(struct machine *m, unsigned irq, int level)
{
    if (bemu_irq_level(&m->irq, irq, level) < 0)
        fail("invalid IRQ bridge transition");
}

void irq_pulse(struct machine *m, unsigned irq)
{
    if (bemu_irq_pulse(&m->irq, irq) < 0)
        fail("invalid IRQ bridge pulse");
}

int irq_inject_fault(struct machine *m, enum bemu_irq_fault_kind kind,
                     unsigned irq)
{
    return bemu_irq_inject_fault(&m->irq, kind, irq);
}

void irq_run_completed(struct machine *m)
{
    if (bemu_irq_run_completed(&m->irq) < 0)
        fail("could not service deferred IRQ fault");
}

int machine_create(struct machine *m)
{
    memset(m, 0, sizeof *m);
    m->vm = -1;
    m->vcpu = -1;
    memset(&m->trace, 0, sizeof m->trace);
    trace_clock_reset(&m->clock);
    bemu_irq_init(&m->irq, m, machine_set_irq_line,
                  machine_irq_quiescent, machine_trace_irq);
    pic_reset(&m->pic);
    pit_reset(&m->pit);
    uart_reset(&m->uart);
    console_reset(m);
    keyboard_reset(m);
    return 0;
}

void machine_destroy(struct machine *m)
{
    trace_close(&m->trace);
    (void)ide_unmap_disk(&m->ide);
    if (m->run && m->run != MAP_FAILED && m->run_size) {
        munmap(m->run, m->run_size);
        m->run = NULL;
        m->run_size = 0;
    }
    bemu_memory_unmap_ram(m);
    if (m->vcpu >= 0) {
        close(m->vcpu);
        m->vcpu = -1;
    }
    if (m->vm >= 0) {
        close(m->vm);
        m->vm = -1;
    }
}
