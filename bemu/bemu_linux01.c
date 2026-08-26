/*
 * bemu_linux01.c - firmware-free KVM runner for linux-0.01-still-runs.
 *
 * Adapted from bEMU-NANO in OS/Nanokernel.org/BasmOS/bemu/bemu_nano.c.
 * The original bEMU contract loads a guest directly into KVM without BIOS or
 * a bootloader. This port keeps that contract and adds only the legacy devices
 * Linux 0.01 uses: PIC/PIT, COM1, CMOS, VGA registers, keyboard and CHS IDE.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 * Copyright (c) 2026, F E R M I INFINITY H A R T <contact@fermihart.com>
 */

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <linux/kvm.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#include <bbp/bbp.h>
#include <bbp/bbp_crc64.h>
#include "../bbp/bbp_build.h"
#include "../bbp/linux01_handoff.h"
#include "machine.h"
#include "ide.h"
#include "loader.h"
#include "memory.h"
#include "cli.h"
#include "kvm.h"
#include "pic.h"
#include "pit.h"
#include "rtc.h"
#include "uart.h"
#include "console.h"
#include "trace_clock.h"
#include "trace.h"
#include "keyboard.h"
#include "error.h"

#define STOP_SIGNAL_COUNT 4

struct host_input_state {
    int stdin_flags, flags_saved;
    int stdin_is_tty, stdin_eof;
    struct termios tio;
    int tio_changed;
    struct sigaction old_alarm;
    int alarm_handler_changed;
    struct sigaction old_stop[STOP_SIGNAL_COUNT];
    int stop_handler_changed[STOP_SIGNAL_COUNT];
    struct itimerval old_timer;
    int timer_changed;
};

static const int stop_signals[STOP_SIGNAL_COUNT] = {
    SIGHUP, SIGQUIT, SIGTERM, SIGINT,
};
static struct kvm_run *signal_run;
static volatile sig_atomic_t poll_due;
static volatile sig_atomic_t stop_requested;
static struct host_input_state host_input;

static void cleanup_error(const char *what)
{
    int error = errno;
    fprintf(stderr, "[bemu-linux01] cleanup: %s: %s\n", what, strerror(error));
    errno = error;
}

static int restore_host_input(void)
{
    struct itimerval disarmed;
    sigset_t set, old_mask;
    int failed = 0, mask_changed = 0;
    unsigned i;

    sigemptyset(&set);
    sigaddset(&set, SIGALRM);
    for (i = 0; i < STOP_SIGNAL_COUNT; i++)
        sigaddset(&set, stop_signals[i]);
    if (sigprocmask(SIG_BLOCK, &set, &old_mask) < 0) {
        cleanup_error("sigprocmask block");
        failed = 1;
    } else {
        mask_changed = 1;
    }

    signal_run = NULL;
    if (host_input.timer_changed) {
        memset(&disarmed, 0, sizeof disarmed);
        if (setitimer(ITIMER_REAL, &disarmed, NULL) < 0) {
            cleanup_error("disarm timer");
            failed = 1;
        }
    }
    if (host_input.tio_changed) {
        if (tcsetattr(STDIN_FILENO, TCSANOW, &host_input.tio) < 0) {
            cleanup_error("restore terminal");
            failed = 1;
        } else {
            host_input.tio_changed = 0;
        }
    }
    if (host_input.flags_saved) {
        if (fcntl(STDIN_FILENO, F_SETFL, host_input.stdin_flags) < 0) {
            cleanup_error("restore stdin flags");
            failed = 1;
        } else {
            host_input.flags_saved = 0;
        }
    }
    for (i = STOP_SIGNAL_COUNT; i > 0; i--) {
        if (!host_input.stop_handler_changed[i - 1])
            continue;
        if (sigaction(stop_signals[i - 1], &host_input.old_stop[i - 1], NULL) < 0) {
            cleanup_error("restore signal handler");
            failed = 1;
        } else {
            host_input.stop_handler_changed[i - 1] = 0;
        }
    }
    if (host_input.alarm_handler_changed) {
        if (sigaction(SIGALRM, &host_input.old_alarm, NULL) < 0) {
            cleanup_error("restore SIGALRM handler");
            failed = 1;
        } else {
            host_input.alarm_handler_changed = 0;
        }
    }
    if (host_input.timer_changed && !host_input.alarm_handler_changed) {
        if (setitimer(ITIMER_REAL, &host_input.old_timer, NULL) < 0) {
            cleanup_error("restore timer");
            failed = 1;
        } else {
            host_input.timer_changed = 0;
        }
    }
    if (mask_changed && sigprocmask(SIG_SETMASK, &old_mask, NULL) < 0) {
        cleanup_error("restore signal mask");
        failed = 1;
    }
    return failed ? -1 : 0;
}

static void restore_host_input_at_exit(void)
{
    (void)restore_host_input();
}

static void stop_signal(int sig)
{
    stop_requested = sig;
    if (signal_run)
        signal_run->immediate_exit = 1;
}

static void poll_signal(int sig)
{
    (void)sig;
    poll_due = 1;
    if (signal_run)
        signal_run->immediate_exit = 1;
}

/* loader implementation moved to bemu/loader.c */

/* IRQ and core machine helpers moved to bemu/machine.c */

/* console/UART output handling moved to bemu/console.c and bemu/uart.c */

/* keyboard/scancode handling moved to bemu/keyboard.c */

static void pump_input(struct machine *m)
{
    if (pit_is_enabled(&m->pit) && !m->no_timer)
        irq_pulse(m, 0);
    if (m->script && !m->script_queued && m->prompt_count) {
        const char *p;
        size_t script_len = 0;
        for (p = m->script; *p; p++) {
            if (*p == '\r' || *p == '\n')
                m->script_prompts_pending++;
            script_len++;
        }
        keyboard_queue_text(m, m->script);
        m->script_queued = 1;
        trace_event_input(&m->trace, (const uint8_t *)m->script, script_len, "script");
    }
    if (m->prompt_count && !host_input.stdin_eof) {
        uint8_t input[128];
        ssize_t got;
        size_t stdin_bytes = 0;
        do {
            got = read(STDIN_FILENO, input + stdin_bytes, sizeof input - stdin_bytes);
            if (got > 0)
                stdin_bytes += (size_t)got;
        } while (got > 0 && stdin_bytes < sizeof input);
        if (stdin_bytes) {
            size_t i;
            for (i = 0; i < stdin_bytes; i++)
                keyboard_queue_input_byte(m, input[i], &m->host_escape_state);
            trace_event_input(&m->trace, input, stdin_bytes, "stdin");
        }
        if (got == 0 && !host_input.stdin_is_tty) {
            if (keyboard_finish_input(m, &m->host_escape_state) ==
                KEYBOARD_INPUT_END_TRUNCATED)
                fprintf(stderr, "[bemu-linux01] discarded truncated stdin escape sequence\n");
            host_input.stdin_eof = 1;
        } else if (got < 0 && errno != EAGAIN && errno != EWOULDBLOCK &&
                   errno != EINTR) {
            die("read stdin");
        }
    }
    keyboard_pump(m);
}

static uint32_t io_read(struct machine *m, uint16_t port, unsigned size)
{
    struct ide_state *d = &m->ide;
    uint32_t value = 0;
    if (port == IDE_DATA)
        return ide_data_read(m, size);
    switch (port) {
    case IDE_ERROR: value=d->error; break;
    case IDE_NSECTOR: value=d->count; break;
    case IDE_SECTOR: value=d->sector; break;
    case IDE_LCYL: value=d->lcyl; break;
    case IDE_HCYL: value=d->hcyl; break;
    case IDE_CURRENT: value=d->current; break;
    case IDE_STATUS: value=d->status; ide_clear_irq(m); break;
    case IDE_CONTROL: value=d->status; break;
    case 0x3f8: case 0x3f9: case 0x3fa: case 0x3fb:
    case 0x3fc: case 0x3fd: case 0x3fe: case 0x3ff:
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fd: case 0x2fe: case 0x2ff:
        value = uart_read(&m->uart, port);
        break;
    case 0x60: value=m->key_ready ? m->key_data : 0; m->key_ready=0; break;
    case 0x61: value=m->port61; break;
    case 0x64: value=m->key_ready ? 1 : 0; break;
    case 0x71: value=rtc_read(&m->rtc, m->cmos_index); break;
    case 0x40: value=pit_read(&m->pit, port); break;
    case 0x20: value=pic_read(&m->pic, 0); break;
    case 0x21: value=pic_read(&m->pic, 1); break;
    case 0xa0: case 0xa1: value=0; break;
    case 0x3c5: value=m->seq[m->seq_index]; break;
    case 0x3cf: value=m->gc[m->gc_index]; break;
    case 0x3d5: value=m->crtc[m->crtc_index]; break;
    case 0x3da: value=0x08; break;
    default: value=0; break;
    }
    return value;
}

static void io_write(struct machine *m, uint16_t port, uint32_t value, unsigned size)
{
    struct ide_state *d = &m->ide;
    uint8_t byte = (uint8_t)value;
    if (port == IDE_DATA) {
        ide_data_write(m, value, size);
        return;
    }
    switch (port) {
    case IDE_ERROR: break;
    case IDE_NSECTOR: d->count=byte; break;
    case IDE_SECTOR: d->sector=byte; break;
    case IDE_LCYL: d->lcyl=byte; break;
    case IDE_HCYL: d->hcyl=byte; break;
    case IDE_CURRENT: d->current=byte; break;
    case IDE_STATUS: ide_command(m, byte); break;
    case IDE_CONTROL: ide_control(m, byte); break;
    case 0x3f8:
        if (m->uart.lcr & 0x80)
            uart_write(&m->uart, port, byte);
        else
            console_output(m, byte);
        break;
    case 0x3f9: case 0x3fa: case 0x3fb:
    case 0x3fc: case 0x3fd: case 0x3fe: case 0x3ff:
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fd: case 0x2fe: case 0x2ff:
        uart_write(&m->uart, port, byte);
        break;
    case 0x60: break;
    case 0x61: m->port61=byte; break;
    case 0x64: break;
    case 0x70: m->cmos_index=byte; break;
    case 0x40:
    case 0x43:
        pit_write(&m->pit, port, byte);
        break;
    case 0x20: pic_write(&m->pic, 0, byte); break;
    case 0x21: pic_write(&m->pic, 1, byte); break;
    case 0xa0: case 0xa1: break;
    case 0x3c4: m->seq_index=byte; break;
    case 0x3c5: m->seq[m->seq_index]=byte; break;
    case 0x3ce: m->gc_index=byte; break;
    case 0x3cf: m->gc[m->gc_index]=byte; break;
    case 0x3d4: m->crtc_index=byte; break;
    case 0x3d5: m->crtc[m->crtc_index]=byte; break;
    case 0x3c0: case 0x3c2: case 0x3c6: case 0x3c7: case 0x3c8: case 0x3c9:
        break;
    default: break;
    }
}

static void handle_io(struct machine *m)
{
    struct kvm_run *run = m->run;
    uint8_t *data = (uint8_t *)run + run->io.data_offset;
    uint32_t i;
    for (i=0; i<run->io.count; i++) {
        uint8_t *item = data + i * run->io.size;
        uint32_t value = 0;
        if (run->io.direction == KVM_EXIT_IO_OUT) {
            memcpy(&value, item, run->io.size);
            io_write(m, run->io.port, value, run->io.size);
        } else {
            value = io_read(m, run->io.port, run->io.size);
            memcpy(item, &value, run->io.size);
        }
        if (run->io.port != 0x3f8 && run->io.port != 0x3fd)
            trace_event_io_access(&m->trace,
                                  run->io.direction == KVM_EXIT_IO_OUT ? "out" : "in",
                                  run->io.port, run->io.size, value);
    }
    if (m->io_trace && run->io.port != 0x3f8 && run->io.port != 0x3fd)
        fprintf(stderr, "[io] %s port=%#x size=%u count=%u\n",
                run->io.direction == KVM_EXIT_IO_OUT ? "out" : "in",
                run->io.port, run->io.size, run->io.count);
}

/* KVM setup moved to bemu/kvm.c */

static int setup_host_input(void)
{
    struct sigaction sa;
    struct itimerval timer;
    unsigned i;

    host_input.stdin_flags = fcntl(STDIN_FILENO, F_GETFL, 0);
    if (host_input.stdin_flags < 0) {
        perror("fcntl stdin F_GETFL");
        return -1;
    }
    host_input.flags_saved = 1;
    if (fcntl(STDIN_FILENO, F_SETFL, host_input.stdin_flags | O_NONBLOCK) < 0) {
        perror("fcntl stdin F_SETFL");
        return -1;
    }
    host_input.stdin_is_tty = isatty(STDIN_FILENO);
    if (host_input.stdin_is_tty) {
        struct termios raw;
        if (tcgetattr(STDIN_FILENO, &host_input.tio) < 0) {
            perror("tcgetattr");
            return -1;
        }
        raw = host_input.tio;
        raw.c_lflag &= (tcflag_t)~(ICANON | ECHO);
        raw.c_cc[VMIN] = 0;
        raw.c_cc[VTIME] = 0;
        if (tcsetattr(STDIN_FILENO, TCSANOW, &raw) < 0) {
            perror("tcsetattr");
            return -1;
        }
        host_input.tio_changed = 1;
    }

    memset(&sa, 0, sizeof sa);
    sa.sa_handler = poll_signal;
    sigemptyset(&sa.sa_mask);
    if (sigaction(SIGALRM, &sa, &host_input.old_alarm) < 0) {
        perror("sigaction SIGALRM");
        return -1;
    }
    host_input.alarm_handler_changed = 1;

    sa.sa_handler = stop_signal;
    for (i = 0; i < STOP_SIGNAL_COUNT; i++) {
        if (sigaction(stop_signals[i], &sa, &host_input.old_stop[i]) < 0) {
            perror("sigaction termination signal");
            return -1;
        }
        host_input.stop_handler_changed[i] = 1;
    }

    memset(&timer, 0, sizeof timer);
    timer.it_interval.tv_usec = 10000;
    timer.it_value.tv_usec = 10000;
    if (setitimer(ITIMER_REAL, &timer, &host_input.old_timer) < 0) {
        perror("setitimer");
        return -1;
    }
    host_input.timer_changed = 1;
    return 0;
}

int main(int argc, char **argv)
{
    struct machine m;
    struct cli_options opts;
    enum bemu_load_status load_status;
    enum bemu_memory_status memory_status;
    size_t kernel_size = 0;
    int load_errno = 0;
    long exits = 0;
    int status = 1;
    machine_create(&m);
    if (cli_parse_args(argc, argv, &opts) < 0) {
        cli_usage(argv[0]);
        return BEMU_EXIT_CLI;
    }
    m.io_trace = opts.trace;
    m.no_timer = opts.no_timer;
    m.experience = opts.experience;
    if (rtc_init_at(&m.rtc, opts.experience, time(NULL)) < 0)
        fail("could not initialize RTC snapshot");
    m.script = opts.script;
    m.expect = opts.expect;
    m.trace_syscalls = opts.trace_syscalls;
    if (opts.trace_file && trace_open(&m.trace, &m.clock, opts.trace_file) < 0)
        fail("could not open trace file");
    if (atexit(restore_host_input_at_exit) != 0)
        fail("could not register host-state cleanup");
    m.sanitize_console = isatty(STDOUT_FILENO) && !opts.raw_console;
    memory_status = bemu_memory_map_ram(&m, RAM_SIZE, NULL, NULL);
    if (memory_status != BEMU_MEMORY_OK) {
        fprintf(stderr, "[bemu-linux01] guest RAM rejected: %s\n",
                bemu_memory_status_string(memory_status));
        goto out;
    }
    load_status = bemu_load_kernel(opts.kernel, m.ram, m.ram_size,
                                   &kernel_size, &load_errno);
    if (load_status != BEMU_LOAD_OK) {
        fprintf(stderr, "[bemu-linux01] kernel load rejected: %s",
                bemu_load_status_string(load_status));
        if (load_errno)
            fprintf(stderr, ": %s", strerror(load_errno));
        fputc('\n', stderr);
        goto out;
    }
    if (build_bbp_handoff(&m, kernel_size) < 0) {
        fprintf(stderr, "[bemu-linux01] BBP handoff rejected: guest RAM layout is invalid\n");
        goto out;
    }
    map_disk(&m.ide, opts.root);
    if (!ide_experience_matches(&m.ide, opts.experience))
        fail("root image does not match selected experience");
    setup_kvm(&m);
    if (m.trace_syscalls) {
        struct kvm_guest_debug dbg;
        memset(&dbg, 0, sizeof dbg);
        dbg.control = KVM_GUESTDBG_ENABLE | KVM_GUESTDBG_SINGLESTEP;
        if (ioctl(m.vcpu, KVM_SET_GUEST_DEBUG, &dbg) < 0)
            die("KVM_SET_GUEST_DEBUG");
    }
    signal_run = m.run;
    if (setup_host_input() < 0) {
        (void)restore_host_input();
        status = BEMU_EXIT_RUNTIME;
        goto out;
    }
    fprintf(stderr, "[bemu-linux01] direct KVM entry: %s @ PA 0, 8 MiB, no firmware, no bootloader\n",
            opts.kernel);
    trace_event_boot(&m.trace, opts.kernel, opts.root, 8, 1);
    while (exits < opts.max_exits && !m.done) {
        if (stop_requested)
            break;
        exits++;
        trace_clock_tick(&m.clock);
        if (poll_due) {
            poll_due = 0;
            m.run->immediate_exit = 0;
            pump_input(&m);
        }
        if (stop_requested)
            break;
        if (ioctl(m.vcpu, KVM_RUN, 0) < 0) {
            if (errno == EINTR)
                continue;
            die("KVM_RUN");
        }
        irq_run_completed(&m);
        switch (m.run->exit_reason) {
        case KVM_EXIT_IO:
            handle_io(&m);
            break;
        case KVM_EXIT_HLT:
            break;
        case KVM_EXIT_IRQ_WINDOW_OPEN:
            break;
        case KVM_EXIT_DEBUG:
            if (m.trace_syscalls) {
                struct kvm_regs regs;
                uint64_t addr;
                if (ioctl(m.vcpu, KVM_GET_REGS, &regs) == 0) {
                    addr = regs.rip;
                    if (addr < m.ram_size && m.ram_size - addr >= 2 &&
                        m.ram[addr] == 0xcd && m.ram[addr + 1] == 0x80) {
                        uint64_t args[6] = { regs.rbx, regs.rcx, regs.rdx,
                                              regs.rsi, regs.rdi, regs.rbp };
                        trace_event_syscall(&m.trace, (unsigned)regs.rax, args, 6);
                    }
                }
            }
            break;
        case KVM_EXIT_SHUTDOWN:
            fail("guest triple fault");
            break;
        case KVM_EXIT_FAIL_ENTRY:
            fprintf(stderr, "[bemu-linux01] KVM fail-entry reason=%llu\n",
                    (unsigned long long)m.run->fail_entry.hardware_entry_failure_reason);
            goto out;
        case KVM_EXIT_INTERNAL_ERROR:
            fprintf(stderr, "[bemu-linux01] KVM internal error suberror=%u\n",
                    m.run->internal.suberror);
            goto out;
        default:
            fprintf(stderr, "[bemu-linux01] unexpected KVM exit %u\n", m.run->exit_reason);
            goto out;
        }
    }
    if (stop_requested) {
        status = BEMU_EXIT_SIGNAL_BASE + stop_requested;
        fprintf(stderr, "\n[bemu-linux01] interrupted by signal %d\n", (int)stop_requested);
    } else if (!m.done) {
        fprintf(stderr, "[bemu-linux01] gave up after %ld KVM exits\n", exits);
        status = BEMU_EXIT_RUNTIME;
    } else {
        fprintf(stderr, "\n[bemu-linux01] RESULT: PASS after %ld KVM exits\n", exits);
        status = BEMU_EXIT_OK;
    }
    trace_event_shutdown(&m.trace,
                         stop_requested ? "signal" :
                         (!m.done ? "max_exits" : "halt"),
                         (unsigned long)exits, status);
out:
    if (restore_host_input() < 0 && status == BEMU_EXIT_OK)
        status = BEMU_EXIT_RUNTIME;
    machine_destroy(&m);
    return status;
}
