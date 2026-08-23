#ifndef BEMU_MACHINE_H
#define BEMU_MACHINE_H

#include <linux/kvm.h>
#include <stdint.h>
#include <stddef.h>

#include "ide.h"
#include "pic.h"
#include "pit.h"
#include "uart.h"
#include "trace_clock.h"
#include "trace.h"

#define RAM_SIZE       (8ULL << 20)
#define GDT_GPA        0x90000ULL
#define VGA_GPA        0xB8000ULL
#define KERNEL_MAX     (512U << 10)
#define SERIAL_LOG_MAX (1U << 20)
#define KEY_QUEUE_MAX  8192

enum console_state {
    CONSOLE_TEXT,
    CONSOLE_ESC,
    CONSOLE_CSI,
    CONSOLE_OSC,
    CONSOLE_OSC_ESC,
    CONSOLE_STRING,
    CONSOLE_STRING_ESC,
};

struct machine {
    int vm, vcpu, io_trace, no_timer, sanitize_console;
    size_t run_size;
    uint8_t *ram;
    struct kvm_run *run;
    struct trace_clock clock;
    struct trace trace;
    struct ide_state ide;
    struct pic_state pic;
    struct uart_state uart;
    uint8_t cmos_index, port61;
    struct pit_state pit;
    uint8_t seq_index, gc_index, crtc_index;
    uint8_t seq[256], gc[256], crtc[256];
    uint8_t keys[KEY_QUEUE_MAX];
    size_t key_head, key_tail;
    uint8_t key_data;
    int key_ready;
    const char *script, *expect;
    int script_queued, prompt_count, expect_seen, done;
    size_t script_prompts_pending;
    char serial_log[SERIAL_LOG_MAX];
    size_t serial_len;
    char plain_log[SERIAL_LOG_MAX];
    size_t plain_len;
    int ansi_state;
    int host_escape_state;
    int console_state, console_csi_valid;
    uint8_t console_seq[64];
    size_t console_seq_len;
};

void irq_level(struct machine *m, unsigned irq, int level);
void irq_pulse(struct machine *m, unsigned irq);
void die(const char *what);
void fail(const char *what);
int machine_create(struct machine *m);
void machine_destroy(struct machine *m);

#endif
