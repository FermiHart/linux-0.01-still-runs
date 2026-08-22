#include "machine.h"

#include "console.h"
#include "keyboard.h"
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

void irq_level(struct machine *m, unsigned irq, int level)
{
    struct kvm_irq_level line;
    memset(&line, 0, sizeof line);
    line.irq = irq;
    line.level = level;
    if (ioctl(m->vm, KVM_IRQ_LINE, &line) < 0)
        die("KVM_IRQ_LINE");
}

void irq_pulse(struct machine *m, unsigned irq)
{
    irq_level(m, irq, 1);
    irq_level(m, irq, 0);
}

int machine_create(struct machine *m)
{
    memset(m, 0, sizeof *m);
    m->vm = -1;
    m->vcpu = -1;
    pic_reset(&m->pic);
    pit_reset(&m->pit);
    uart_reset(&m->uart);
    console_reset(m);
    keyboard_reset(m);
    return 0;
}

void machine_destroy(struct machine *m)
{
    if (m->run && m->run != MAP_FAILED && m->run_size) {
        munmap(m->run, m->run_size);
        m->run = NULL;
        m->run_size = 0;
    }
    if (m->ram && m->ram != MAP_FAILED) {
        munmap(m->ram, RAM_SIZE);
        m->ram = NULL;
    }
    if (m->vcpu >= 0) {
        close(m->vcpu);
        m->vcpu = -1;
    }
    if (m->vm >= 0) {
        close(m->vm);
        m->vm = -1;
    }
}
