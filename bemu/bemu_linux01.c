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

#define RAM_SIZE       (8ULL << 20)
#define GDT_GPA        0x90000ULL
#define VGA_GPA        0xB8000ULL
#define KERNEL_MAX     (512U << 10)
#define SERIAL_LOG_MAX (1U << 20)
#define KEY_QUEUE_MAX  8192

#define IDE_HEADS      5
#define IDE_SECTORS    17
#define IDE_CYLINDERS  977
#define IDE_SECTOR_LEN 512

#define IDE_DATA       0x1F0
#define IDE_ERROR      0x1F1
#define IDE_NSECTOR    0x1F2
#define IDE_SECTOR     0x1F3
#define IDE_LCYL       0x1F4
#define IDE_HCYL       0x1F5
#define IDE_CURRENT    0x1F6
#define IDE_STATUS     0x1F7
#define IDE_CONTROL    0x3F6

#define IDE_ERR        0x01
#define IDE_DRQ        0x08
#define IDE_SEEK       0x10
#define IDE_READY      0x40
#define IDE_BUSY       0x80

static const uint8_t bootstrap_gdt[24] = {
    0,0,0,0,0,0,0,0,
    0xff,0xff,0,0,0,0x9a,0xcf,0,
    0xff,0xff,0,0,0,0x92,0xcf,0,
};

struct ide_state {
    uint8_t *disk;
    size_t disk_size;
    uint8_t error, count, sector, lcyl, hcyl, current, status, control;
    uint32_t lba;
    unsigned remaining, data_pos;
    int writing, irq_pending;
};

struct uart_state {
    uint8_t ier, lcr, mcr, dll, dlm, scratch;
};

struct machine {
    int vm, vcpu, trace, no_timer, sanitize_console;
    uint8_t *ram;
    struct kvm_run *run;
    struct ide_state ide;
    struct uart_state uart;
    uint8_t cmos_index, port61;
    uint8_t pit_latch[2];
    int pit_bytes, pit_enabled;
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

enum console_state {
    CONSOLE_TEXT,
    CONSOLE_ESC,
    CONSOLE_CSI,
    CONSOLE_OSC,
    CONSOLE_OSC_ESC,
    CONSOLE_STRING,
    CONSOLE_STRING_ESC,
};

#define STOP_SIGNAL_COUNT 4

struct host_input_state {
    int stdin_flags, flags_saved;
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

static void die(const char *what)
{
    perror(what);
    exit(1);
}

static void fail(const char *what)
{
    fprintf(stderr, "[bemu-linux01] %s\n", what);
    exit(1);
}

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

static void read_full(int fd, void *buffer, size_t size, const char *name)
{
    uint8_t *p = buffer;
    while (size) {
        ssize_t got = read(fd, p, size);
        if (got < 0) {
            if (errno == EINTR)
                continue;
            die(name);
        }
        if (!got)
            fail("short input file");
        p += got;
        size -= (size_t)got;
    }
}

static size_t load_kernel(const char *path, uint8_t *ram)
{
    struct stat st;
    int fd = open(path, O_RDONLY);
    if (fd < 0)
        die(path);
    if (fstat(fd, &st) < 0)
        die("fstat kernel");
    if (st.st_size <= 0 || st.st_size > KERNEL_MAX)
        fail("kernel.bin has an invalid size");
    read_full(fd, ram, (size_t)st.st_size, path);
    close(fd);
    return (size_t)st.st_size;
}

static uint64_t monotonic_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) < 0)
        die("clock_gettime");
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static void build_bbp_handoff(struct machine *m, size_t kernel_size)
{
    struct bbp_info *info = (struct bbp_info *)(m->ram + BBP_L01_HANDOFF_PHYS);
    uint8_t *arena = (uint8_t *)(info + 1);
    size_t capacity = BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS - sizeof(*info);
    struct bbp_builder b;
    struct bbp_tag_hhdm *hhdm;
    struct bbp_tag_memory_map *mmap;
    struct bbp_memory_entry *entries;
    struct bbp_tag_kernel_address *kernel;
    struct bbp_tag_cmdline *cmdline;
    struct bbp_tag_hypervisor *hypervisor;
    bbp_phys_t command_phys;
    uint32_t command_len;
    uint64_t now = monotonic_ns();

    memset(info, 0, BBP_L01_HANDOFF_END - BBP_L01_HANDOFF_PHYS);
    bbp_builder_init(&b, arena, BBP_L01_HANDOFF_PHYS + sizeof(*info), capacity);

    command_phys = bbp_arena_strdup(&b, BBP_L01_ROOT_CMDLINE, &command_len);

    hhdm = bbp_alloc_tag(&b, BBP_TAG_HHDM, 1, sizeof(*hhdm));
    if (hhdm)
        hhdm->offset = 0;

    mmap = bbp_alloc_tag(&b, BBP_TAG_MEMORY_MAP, 1,
                         sizeof(*mmap) + 3 * sizeof(*entries));
    if (mmap) {
        mmap->entry_count = 3;
        mmap->entry_size = sizeof(*entries);
        entries = (struct bbp_memory_entry *)(mmap + 1);
        entries[0].base = 0;
        entries[0].length = 0xA0000;
        entries[0].type = BBP_MEM_USABLE;
        entries[0].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                                BBP_MEM_ATTR_CACHED;
        entries[1].base = 0xA0000;
        entries[1].length = 0x60000;
        entries[1].type = BBP_MEM_RESERVED;
        entries[1].attributes = BBP_MEM_ATTR_READABLE;
        entries[2].base = 0x100000;
        entries[2].length = RAM_SIZE - 0x100000;
        entries[2].type = BBP_MEM_USABLE;
        entries[2].attributes = BBP_MEM_ATTR_READABLE | BBP_MEM_ATTR_WRITABLE |
                                BBP_MEM_ATTR_CACHED;
    }

    kernel = bbp_alloc_tag(&b, BBP_TAG_KERNEL_ADDRESS, 1, sizeof(*kernel));
    if (kernel) {
        kernel->physical_base = 0;
        kernel->virtual_base = 0;
    }

    cmdline = bbp_alloc_tag(&b, BBP_TAG_CMDLINE, 1, sizeof(*cmdline));
    if (cmdline) {
        cmdline->string = command_phys;
        cmdline->length = command_len;
        cmdline->string_crc = bbp_crc64(BBP_L01_ROOT_CMDLINE, command_len);
    }

    hypervisor = bbp_alloc_tag(&b, BBP_TAG_HYPERVISOR, 1, sizeof(*hypervisor));
    if (hypervisor) {
        hypervisor->present = 1;
        memcpy(hypervisor->vendor, "bEMU", 4);
    }

    if (!command_phys || b.overflow)
        fail("BBP handoff exceeds its reserved window");

    memcpy(info->bootloader_name, "bEMU-NANO", 9);
    memcpy(info->bootloader_version, "linux01-1", 9);
    info->bootloader_uuid[0] = 0x4f4e414e2d554d45ULL;
    info->bootloader_uuid[1] = 0x31302d58554e494cULL;
    info->bootloader_start_ts = now;
    info->kernel_load_ts = now;
    info->handoff_ts = monotonic_ns();
    info->architecture = BBP_ARCH_X86_32;
    info->cpu_count = 1;
    bbp_builder_finalize(&b, info, BBP_L01_HANDOFF_PHYS);

    fprintf(stderr,
            "[bemu-linux01] BBP @ %#lx: %u tags, kernel=%zu bytes, %s\n",
            (unsigned long)BBP_L01_HANDOFF_PHYS, info->tag_count,
            kernel_size, BBP_L01_ROOT_CMDLINE);
}

static void map_disk(struct ide_state *ide, const char *path)
{
    struct stat st;
    int fd = open(path, O_RDONLY);
    size_t expected = (size_t)IDE_CYLINDERS * IDE_HEADS * IDE_SECTORS * IDE_SECTOR_LEN;
    if (fd < 0)
        die(path);
    if (fstat(fd, &st) < 0)
        die("fstat root image");
    if ((size_t)st.st_size != expected)
        fail("root image does not match 977/5/17 CHS geometry");
    ide->disk = mmap(NULL, expected, PROT_READ | PROT_WRITE, MAP_PRIVATE, fd, 0);
    if (ide->disk == MAP_FAILED) {
        int error = errno;
        (void)close(fd);
        errno = error;
        die("mmap root image");
    }
    if (close(fd) < 0)
        die("close root image");
    ide->disk_size = expected;
    ide->error = 1;
    ide->status = IDE_READY | IDE_SEEK;
    ide->sector = 1;
    ide->current = 0xa0;
}

static void irq_level(struct machine *m, unsigned irq, int level)
{
    struct kvm_irq_level line;
    memset(&line, 0, sizeof line);
    line.irq = irq;
    line.level = level;
    if (ioctl(m->vm, KVM_IRQ_LINE, &line) < 0)
        die("KVM_IRQ_LINE");
}

static void irq_pulse(struct machine *m, unsigned irq)
{
    irq_level(m, irq, 1);
    irq_level(m, irq, 0);
}

static void ide_set_irq(struct machine *m)
{
    struct ide_state *d = &m->ide;
    d->irq_pending = 1;
    if (!(d->control & 2))
        irq_level(m, 14, 1);
}

static void ide_clear_irq(struct machine *m)
{
    m->ide.irq_pending = 0;
    irq_level(m, 14, 0);
}

static int ide_address(struct ide_state *d, uint32_t *lba)
{
    unsigned cyl = d->lcyl | ((unsigned)d->hcyl << 8);
    unsigned head = d->current & 15;
    if ((d->current & 0x10) || cyl >= IDE_CYLINDERS || head >= IDE_HEADS ||
        d->sector < 1 || d->sector > IDE_SECTORS)
        return -1;
    *lba = ((cyl * IDE_HEADS + head) * IDE_SECTORS) + d->sector - 1;
    return ((uint64_t)*lba * IDE_SECTOR_LEN < d->disk_size) ? 0 : -1;
}

static void ide_abort(struct machine *m)
{
    m->ide.error = 4;
    m->ide.status = IDE_READY | IDE_SEEK | IDE_ERR;
    m->ide.remaining = 0;
    m->ide.data_pos = 0;
    ide_set_irq(m);
}

static void ide_command(struct machine *m, uint8_t command)
{
    struct ide_state *d = &m->ide;
    uint32_t lba;
    ide_clear_irq(m);
    if (command == 0x20 || command == 0x30) {
        if (ide_address(d, &lba) < 0) {
            ide_abort(m);
            return;
        }
        d->lba = lba;
        d->remaining = d->count ? d->count : 256;
        d->data_pos = 0;
        d->writing = command == 0x30;
        d->error = 0;
        d->status = IDE_READY | IDE_SEEK | IDE_DRQ;
        if (!d->writing)
            ide_set_irq(m);
        return;
    }
    if (command == 0x10 || command == 0x91) {
        d->error = 0;
        d->status = IDE_READY | IDE_SEEK;
        ide_set_irq(m);
        return;
    }
    ide_abort(m);
}

static void ide_sector_done(struct machine *m)
{
    struct ide_state *d = &m->ide;
    d->data_pos = 0;
    d->lba++;
    if (d->remaining)
        d->remaining--;
    if (d->remaining) {
        if ((uint64_t)d->lba * IDE_SECTOR_LEN >= d->disk_size) {
            ide_abort(m);
            return;
        }
        d->status = IDE_READY | IDE_SEEK | IDE_DRQ;
        ide_set_irq(m);
    } else {
        d->status = IDE_READY | IDE_SEEK;
        if (d->writing)
            ide_set_irq(m);
    }
}

static uint32_t ide_data_read(struct machine *m, unsigned size)
{
    struct ide_state *d = &m->ide;
    uint32_t value = 0;
    unsigned i;
    if (d->writing || !(d->status & IDE_DRQ) || !d->remaining)
        return 0;
    for (i = 0; i < size; i++) {
        size_t at = (size_t)d->lba * IDE_SECTOR_LEN + d->data_pos;
        value |= (uint32_t)d->disk[at] << (i * 8);
        d->data_pos++;
        if (d->data_pos == IDE_SECTOR_LEN) {
            ide_sector_done(m);
            break;
        }
    }
    return value;
}

static void ide_data_write(struct machine *m, uint32_t value, unsigned size)
{
    struct ide_state *d = &m->ide;
    unsigned i;
    if (!d->writing || !(d->status & IDE_DRQ) || !d->remaining)
        return;
    for (i = 0; i < size; i++) {
        size_t at = (size_t)d->lba * IDE_SECTOR_LEN + d->data_pos;
        d->disk[at] = (uint8_t)(value >> (i * 8));
        d->data_pos++;
        if (d->data_pos == IDE_SECTOR_LEN) {
            ide_sector_done(m);
            break;
        }
    }
}

static void ide_control(struct machine *m, uint8_t value)
{
    struct ide_state *d = &m->ide;
    uint8_t old = d->control;
    d->control = value;
    if (value & 2)
        irq_level(m, 14, 0);
    if ((value & 4) && !(old & 4)) {
        ide_clear_irq(m);
        d->status = IDE_BUSY;
        d->remaining = d->data_pos = 0;
    } else if (!(value & 4) && (old & 4)) {
        d->error = 1;
        d->status = IDE_READY | IDE_SEEK;
    }
    if (!(value & 2) && (old & 2) && d->irq_pending)
        irq_level(m, 14, 1);
}

static uint8_t bcd(unsigned value)
{
    return (uint8_t)(((value / 10) << 4) | (value % 10));
}

static uint8_t cmos_read(uint8_t index)
{
    time_t now = time(NULL);
    struct tm tm;
    gmtime_r(&now, &tm);
    switch (index & 0x7f) {
    case 0: return bcd((unsigned)tm.tm_sec);
    case 2: return bcd((unsigned)tm.tm_min);
    case 4: return bcd((unsigned)tm.tm_hour);
    case 7: return bcd((unsigned)tm.tm_mday);
    case 8: return bcd((unsigned)tm.tm_mon + 1);
    case 9: return bcd((unsigned)(tm.tm_year % 100));
    case 10: return 0;
    case 11: return 2;
    default: return 0;
    }
}

static int console_csi_final_allowed(uint8_t value)
{
    static const char allowed[] = "@ABCDEFGHJKLMPSTXZadefgmrsu";
    return strchr(allowed, value) != NULL;
}

static void console_byte(struct machine *m, uint8_t value)
{
    if (!m->sanitize_console) {
        fputc(value, stdout);
        fflush(stdout);
        return;
    }

    switch (m->console_state) {
    case CONSOLE_TEXT:
        if (value == 0x1b) {
            m->console_state = CONSOLE_ESC;
        } else if (value == 0x9b) {
            m->console_state = CONSOLE_CSI;
            m->console_seq_len = 0;
            m->console_csi_valid = 0;
        } else if (value == 0x9d) {
            m->console_state = CONSOLE_OSC;
        } else if (value == 0x90 || value == 0x98 || value == 0x9e || value == 0x9f) {
            m->console_state = CONSOLE_STRING;
        } else if (value == '\b' || value == '\t' || value == '\n' || value == '\r' ||
                   value >= 0xa0 || (value >= 0x20 && value < 0x7f)) {
            fputc(value, stdout);
            fflush(stdout);
        }
        break;
    case CONSOLE_ESC:
        if (value == '[') {
            m->console_seq[0] = 0x1b;
            m->console_seq[1] = '[';
            m->console_seq_len = 2;
            m->console_csi_valid = 1;
            m->console_state = CONSOLE_CSI;
        } else if (value == ']') {
            m->console_state = CONSOLE_OSC;
        } else if (value == 'P' || value == 'X' || value == '^' || value == '_') {
            m->console_state = CONSOLE_STRING;
        } else if (value != 0x1b) {
            m->console_state = CONSOLE_TEXT;
        }
        break;
    case CONSOLE_CSI:
        if (value == 0x1b) {
            m->console_state = CONSOLE_ESC;
        } else if (value >= 0x40 && value <= 0x7e) {
            if (m->console_csi_valid && console_csi_final_allowed(value) &&
                m->console_seq_len < sizeof m->console_seq) {
                m->console_seq[m->console_seq_len++] = value;
                fwrite(m->console_seq, 1, m->console_seq_len, stdout);
                fflush(stdout);
            }
            m->console_state = CONSOLE_TEXT;
        } else if (value >= 0x20) {
            if (!((value >= '0' && value <= '9') || value == ';' || value == ':'))
                m->console_csi_valid = 0;
            if (m->console_seq_len < sizeof m->console_seq)
                m->console_seq[m->console_seq_len++] = value;
            else
                m->console_csi_valid = 0;
        }
        break;
    case CONSOLE_OSC:
        if (value == 0x07 || value == 0x9c)
            m->console_state = CONSOLE_TEXT;
        else if (value == 0x1b)
            m->console_state = CONSOLE_OSC_ESC;
        break;
    case CONSOLE_OSC_ESC:
        if (value == '\\' || value == 0x9c)
            m->console_state = CONSOLE_TEXT;
        else if (value != 0x1b)
            m->console_state = CONSOLE_OSC;
        break;
    case CONSOLE_STRING:
        if (value == 0x9c)
            m->console_state = CONSOLE_TEXT;
        else if (value == 0x1b)
            m->console_state = CONSOLE_STRING_ESC;
        break;
    case CONSOLE_STRING_ESC:
        if (value == '\\' || value == 0x9c)
            m->console_state = CONSOLE_TEXT;
        else if (value != 0x1b)
            m->console_state = CONSOLE_STRING;
        break;
    }
}

static void serial_byte(struct machine *m, uint8_t value)
{
    static const char prompt_prefix[] = "fermihart@linux01:";
    size_t line_start;
    int plain_appended = 0;
    if (m->serial_len + 1 < SERIAL_LOG_MAX) {
        m->serial_log[m->serial_len++] = (char)value;
        m->serial_log[m->serial_len] = 0;
    }
    console_byte(m, value);
    if (!m->ansi_state && value == 0x1b)
        m->ansi_state = 1;
    else if (m->ansi_state == 1)
        m->ansi_state = value == '[' ? 2 : 0;
    else if (m->ansi_state == 2) {
        if (value >= 0x40 && value <= 0x7e)
            m->ansi_state = 0;
    } else if (m->plain_len + 1 < SERIAL_LOG_MAX) {
        m->plain_log[m->plain_len++] = (char)value;
        m->plain_log[m->plain_len] = 0;
        plain_appended = 1;
    }
    if (m->expect && !m->expect_seen && strstr(m->serial_log, m->expect))
        m->expect_seen = 1;
    line_start = m->plain_len;
    while (line_start && m->plain_log[line_start - 1] != '\r' &&
           m->plain_log[line_start - 1] != '\n')
        line_start--;
    if (plain_appended && value == '$' &&
        m->plain_len - line_start >= sizeof(prompt_prefix) - 1 &&
        !memcmp(m->plain_log + line_start, prompt_prefix,
                sizeof(prompt_prefix) - 1)) {
        m->prompt_count++;
        if (m->script_queued && m->script_prompts_pending)
            m->script_prompts_pending--;
        if (!m->script || !*m->script) {
            if (m->expect && m->expect_seen)
                m->done = 1;
        } else if (m->script_queued && !m->script_prompts_pending &&
                   (!m->expect || m->expect_seen)) {
            m->done = 1;
        }
    }
}

static void key_push(struct machine *m, uint8_t code)
{
    size_t next = (m->key_head + 1) % KEY_QUEUE_MAX;
    if (next == m->key_tail)
        fail("keyboard queue overflow");
    m->keys[m->key_head] = code;
    m->key_head = next;
}

static int ascii_key(unsigned char ch, uint8_t *code, int *shift)
{
    static const uint8_t letters[26] = {
        0x1e,0x30,0x2e,0x20,0x12,0x21,0x22,0x23,0x17,0x24,0x25,0x26,0x32,
        0x31,0x18,0x19,0x10,0x13,0x1f,0x14,0x16,0x2f,0x11,0x2d,0x15,0x2c
    };
    static const uint8_t digits[10] = {0x0b,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a};
    *shift = 0;
    if (ch >= 'a' && ch <= 'z') { *code = letters[ch-'a']; return 0; }
    if (ch >= 'A' && ch <= 'Z') { *code = letters[ch-'A']; *shift = 1; return 0; }
    if (ch >= '0' && ch <= '9') { *code = digits[ch-'0']; return 0; }
    switch (ch) {
    case 0x1b: *code=0x01; return 0;
    case '\r': case '\n': *code=0x1c; return 0;
    case ' ': *code=0x39; return 0;
    case '/': *code=0x35; return 0;
    case '.': *code=0x34; return 0;
    case '-': *code=0x0c; return 0;
    case '_': *code=0x0c; *shift=1; return 0;
    case '=': *code=0x0d; return 0;
    case '+': *code=0x0d; *shift=1; return 0;
    case ';': *code=0x27; return 0;
    case ':': *code=0x27; *shift=1; return 0;
    case '>': *code=0x34; *shift=1; return 0;
    default: return -1;
    }
}

static void queue_character(struct machine *m, unsigned char ch)
{
    uint8_t code;
    int shift;

    if (ch == 8 || ch == 0x7f) {
        key_push(m, 0x0e);
        key_push(m, 0x8e);
    } else if (ch >= 1 && ch <= 26) {
        if (!ascii_key((unsigned char)('a' + ch - 1), &code, &shift)) {
            key_push(m, 0x1d);
            key_push(m, code);
            key_push(m, code | 0x80);
            key_push(m, 0x9d);
        }
    } else if (ch == '\t') {
        key_push(m, 0x0f);
        key_push(m, 0x8f);
    } else if (!ascii_key(ch, &code, &shift)) {
        if (shift) key_push(m, 0x2a);
        key_push(m, code);
        key_push(m, code | 0x80);
        if (shift) key_push(m, 0xaa);
    }
}

static int queue_navigation_key(struct machine *m, unsigned char final)
{
    uint8_t code;

    switch (final) {
    case 'A': code=0x48; break;
    case 'B': code=0x50; break;
    case 'C': code=0x4d; break;
    case 'D': code=0x4b; break;
    case 'H': code=0x47; break;
    case 'F': code=0x4f; break;
    default: return 0;
    }
    key_push(m, 0xe0);
    key_push(m, code);
    key_push(m, 0xe0);
    key_push(m, code | 0x80);
    return 1;
}

static void queue_input_byte(struct machine *m, unsigned char ch, int *state)
{
    if (*state == 0) {
        if (ch == 0x1b)
            *state = 1;
        else
            queue_character(m, ch);
        return;
    }
    if (*state == 1) {
        if (ch == '[' || ch == 'O') {
            *state = 2;
        } else {
            queue_character(m, 0x1b);
            *state = 0;
            if (ch == 0x1b)
                *state = 1;
            else
                queue_character(m, ch);
        }
        return;
    }
    if (ch == 0x1b) {
        *state = 1;
    } else if (ch >= 0x40 && ch <= 0x7e) {
        (void)queue_navigation_key(m, ch);
        *state = 0;
    } else if (ch < 0x20 || ch > 0x3f) {
        *state = 0;
    }
}

static void queue_text(struct machine *m, const char *text)
{
    int state = 0;

    while (*text)
        queue_input_byte(m, (unsigned char)*text++, &state);
    if (state == 1)
        queue_character(m, 0x1b);
}

static void pump_input(struct machine *m)
{
    if (m->pit_enabled && !m->no_timer)
        irq_pulse(m, 0);
    if (m->script && !m->script_queued && m->prompt_count) {
        const char *p;
        for (p = m->script; *p; p++)
            if (*p == '\r' || *p == '\n')
                m->script_prompts_pending++;
        queue_text(m, m->script);
        m->script_queued = 1;
    }
    if (m->prompt_count) {
        uint8_t input[128];
        ssize_t got;
        do {
            got = read(STDIN_FILENO, input, sizeof input);
            if (got > 0) {
                ssize_t i;
                for (i=0; i<got; i++)
                    queue_input_byte(m, input[i], &m->host_escape_state);
            }
        } while (got > 0);
    }
    if (!m->key_ready && m->key_tail != m->key_head) {
        m->key_data = m->keys[m->key_tail];
        m->key_tail = (m->key_tail + 1) % KEY_QUEUE_MAX;
        m->key_ready = 1;
        irq_pulse(m, 1);
    }
}

static uint32_t io_read(struct machine *m, uint16_t port, unsigned size)
{
    struct ide_state *d = &m->ide;
    struct uart_state *u = &m->uart;
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
    case 0x3f8: value=(u->lcr & 0x80) ? u->dll : 0; break;
    case 0x3f9: value=(u->lcr & 0x80) ? u->dlm : u->ier; break;
    case 0x3fa: value=1; break;
    case 0x3fb: value=u->lcr; break;
    case 0x3fc: value=u->mcr; break;
    case 0x3fd: value=0x60; break;
    case 0x3fe: value=0xb0; break;
    case 0x3ff: value=u->scratch; break;
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fe: case 0x2ff: value=0; break;
    case 0x2fd: value=0x60; break;
    case 0x60: value=m->key_ready ? m->key_data : 0; m->key_ready=0; break;
    case 0x61: value=m->port61; break;
    case 0x64: value=m->key_ready ? 1 : 0; break;
    case 0x71: value=cmos_read(m->cmos_index); break;
    case 0x40: value=0; break;
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
    struct uart_state *u = &m->uart;
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
        if (u->lcr & 0x80) u->dll=byte;
        else serial_byte(m, byte);
        break;
    case 0x3f9:
        if (u->lcr & 0x80) u->dlm=byte;
        else u->ier=byte;
        break;
    case 0x3fb: u->lcr=byte; break;
    case 0x3fc: u->mcr=byte; break;
    case 0x3ff: u->scratch=byte; break;
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fd: case 0x2fe: case 0x2ff: break;
    case 0x60: break;
    case 0x61: m->port61=byte; break;
    case 0x64: break;
    case 0x70: m->cmos_index=byte; break;
    case 0x40:
        if (m->pit_bytes < 2)
            m->pit_latch[m->pit_bytes++] = byte;
        if (m->pit_bytes == 2)
            m->pit_enabled = 1;
        break;
    case 0x43:
        m->pit_bytes = 0;
        m->pit_enabled = 0;
        break;
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
    }
    if (m->trace && run->io.port != 0x3f8 && run->io.port != 0x3fd)
        fprintf(stderr, "[io] %s port=%#x size=%u count=%u\n",
                run->io.direction == KVM_EXIT_IO_OUT ? "out" : "in",
                run->io.port, run->io.size, run->io.count);
}

static void set_segment(struct kvm_segment *s, uint16_t selector, int code)
{
    memset(s, 0, sizeof *s);
    s->base = 0;
    s->limit = 0xffffffff;
    s->selector = selector;
    s->type = code ? 0xb : 3;
    s->present = 1;
    s->s = 1;
    s->g = 1;
    s->db = 1;
}

static void setup_kvm(struct machine *m, const char *kernel)
{
    struct kvm_userspace_memory_region region;
    struct kvm_cpuid2 *cpuid;
    struct kvm_sregs sregs;
    struct kvm_regs regs;
    uint64_t identity = 0xfffbc000ULL;
    int kvm, mmap_size;

    kvm = open("/dev/kvm", O_RDWR);
    if (kvm < 0) die("/dev/kvm");
    if (ioctl(kvm, KVM_GET_API_VERSION, 0) != KVM_API_VERSION)
        fail("KVM API version mismatch");
    if (ioctl(kvm, KVM_CHECK_EXTENSION, KVM_CAP_IRQCHIP) <= 0)
        fail("KVM irqchip support is required");
    m->vm = ioctl(kvm, KVM_CREATE_VM, 0);
    if (m->vm < 0) die("KVM_CREATE_VM");
    if (ioctl(m->vm, KVM_SET_TSS_ADDR, 0xfffbd000UL) < 0)
        die("KVM_SET_TSS_ADDR");
    if (ioctl(m->vm, KVM_SET_IDENTITY_MAP_ADDR, &identity) < 0)
        die("KVM_SET_IDENTITY_MAP_ADDR");
    m->ram = mmap(NULL, RAM_SIZE, PROT_READ | PROT_WRITE,
                  MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (m->ram == MAP_FAILED) die("mmap guest RAM");
    memset(&region, 0, sizeof region);
    region.slot = 0;
    region.guest_phys_addr = 0;
    region.memory_size = RAM_SIZE;
    region.userspace_addr = (uint64_t)m->ram;
    if (ioctl(m->vm, KVM_SET_USER_MEMORY_REGION, &region) < 0)
        die("KVM_SET_USER_MEMORY_REGION");
    build_bbp_handoff(m, load_kernel(kernel, m->ram));
    memcpy(m->ram + GDT_GPA, bootstrap_gdt, sizeof bootstrap_gdt);
    if (ioctl(m->vm, KVM_CREATE_IRQCHIP, 0) < 0)
        die("KVM_CREATE_IRQCHIP");
    m->vcpu = ioctl(m->vm, KVM_CREATE_VCPU, 0);
    if (m->vcpu < 0) die("KVM_CREATE_VCPU");

    {
        uint32_t nent = 128;
        for (;;) {
            size_t bytes, entry_bytes;
            uint32_t needed;
            int error;

            if (__builtin_mul_overflow((size_t)nent, sizeof(cpuid->entries[0]),
                                       &entry_bytes) ||
                __builtin_add_overflow(sizeof(*cpuid), entry_bytes, &bytes))
                fail("KVM CPUID entry count is too large");
            cpuid = calloc(1, bytes);
            if (!cpuid)
                die("calloc CPUID");
            cpuid->nent = nent;
            if (ioctl(kvm, KVM_GET_SUPPORTED_CPUID, cpuid) == 0)
                break;
            error = errno;
            needed = cpuid->nent;
            free(cpuid);
            if (error != E2BIG) {
                errno = error;
                die("KVM_GET_SUPPORTED_CPUID");
            }
            if (needed <= nent) {
                if (nent > UINT32_MAX / 2)
                    fail("KVM CPUID entry count overflow");
                needed = nent * 2;
            }
            nent = needed;
        }
    }
    if (ioctl(m->vcpu, KVM_SET_CPUID2, cpuid) < 0)
        die("KVM_SET_CPUID2");
    free(cpuid);
    mmap_size = ioctl(kvm, KVM_GET_VCPU_MMAP_SIZE, 0);
    close(kvm);
    if (mmap_size <= 0) die("KVM_GET_VCPU_MMAP_SIZE");
    m->run = mmap(NULL, (size_t)mmap_size, PROT_READ | PROT_WRITE,
                  MAP_SHARED, m->vcpu, 0);
    if (m->run == MAP_FAILED) die("mmap kvm_run");

    if (ioctl(m->vcpu, KVM_GET_SREGS, &sregs) < 0)
        die("KVM_GET_SREGS");
    sregs.cr0 = 0x11;
    sregs.cr3 = 0;
    sregs.cr4 = 0;
    sregs.efer = 0;
    sregs.gdt.base = GDT_GPA;
    sregs.gdt.limit = sizeof bootstrap_gdt - 1;
    set_segment(&sregs.cs, 0x08, 1);
    set_segment(&sregs.ds, 0x10, 0);
    set_segment(&sregs.es, 0x10, 0);
    set_segment(&sregs.fs, 0x10, 0);
    set_segment(&sregs.gs, 0x10, 0);
    set_segment(&sregs.ss, 0x10, 0);
    if (ioctl(m->vcpu, KVM_SET_SREGS, &sregs) < 0)
        die("KVM_SET_SREGS");
    memset(&regs, 0, sizeof regs);
    regs.rip = 0;
    regs.rflags = 2;
    if (ioctl(m->vcpu, KVM_SET_REGS, &regs) < 0)
        die("KVM_SET_REGS");
}

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
    if (isatty(STDIN_FILENO)) {
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

static int parse_max_exits(const char *text, long *value)
{
    unsigned long parsed = 0;
    unsigned long digit;

    if (!text || !*text)
        return -1;
    while (*text) {
        if (*text < '0' || *text > '9')
            return -1;
        digit = (unsigned long)(*text++ - '0');
        if (parsed > ((unsigned long)LONG_MAX - digit) / 10)
            return -1;
        parsed = parsed * 10 + digit;
    }
    if (!parsed)
        return -1;
    *value = (long)parsed;
    return 0;
}

static void usage(const char *program)
{
    fprintf(stderr, "usage: %s [--kernel FILE] [--root FILE] "
            "[--keys TEXT] [--expect TEXT] [--trace] [--no-timer] "
            "[--raw-console] [--max-exits N]\n", program);
}

int main(int argc, char **argv)
{
    struct machine m;
    const char *kernel = "build/kernel.bin";
    const char *root = "build/root.img";
    long exits = 0, max_exits = 50000000;
    int i, raw_console = 0, status = 1;
    memset(&m, 0, sizeof m);
    for (i=1; i<argc; i++) {
        if (!strcmp(argv[i], "--kernel") && i+1<argc) kernel=argv[++i];
        else if (!strcmp(argv[i], "--root") && i+1<argc) root=argv[++i];
        else if (!strcmp(argv[i], "--keys") && i+1<argc) m.script=argv[++i];
        else if (!strcmp(argv[i], "--expect") && i+1<argc) m.expect=argv[++i];
        else if (!strcmp(argv[i], "--max-exits") && i+1<argc) {
            if (parse_max_exits(argv[++i], &max_exits) < 0) {
                fprintf(stderr, "[bemu-linux01] invalid --max-exits value: %s\n", argv[i]);
                usage(argv[0]);
                return 2;
            }
        }
        else if (!strcmp(argv[i], "--trace")) m.trace=1;
        else if (!strcmp(argv[i], "--no-timer")) m.no_timer=1;
        else if (!strcmp(argv[i], "--raw-console")) raw_console=1;
        else {
            usage(argv[0]);
            return 2;
        }
    }
    if (atexit(restore_host_input_at_exit) != 0)
        fail("could not register host-state cleanup");
    m.sanitize_console = isatty(STDOUT_FILENO) && !raw_console;
    map_disk(&m.ide, root);
    setup_kvm(&m, kernel);
    signal_run = m.run;
    if (setup_host_input() < 0) {
        (void)restore_host_input();
        return 1;
    }
    fprintf(stderr, "[bemu-linux01] direct KVM entry: %s @ PA 0, 8 MiB, no firmware, no bootloader\n",
            kernel);
    while (exits < max_exits && !m.done) {
        if (stop_requested)
            break;
        exits++;
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
        switch (m.run->exit_reason) {
        case KVM_EXIT_IO:
            handle_io(&m);
            break;
        case KVM_EXIT_HLT:
            break;
        case KVM_EXIT_IRQ_WINDOW_OPEN:
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
        status = 128 + stop_requested;
        fprintf(stderr, "\n[bemu-linux01] interrupted by signal %d\n", (int)stop_requested);
    } else if (!m.done) {
        fprintf(stderr, "[bemu-linux01] gave up after %ld KVM exits\n", exits);
    } else {
        fprintf(stderr, "\n[bemu-linux01] RESULT: PASS after %ld KVM exits\n", exits);
        status = 0;
    }
out:
    if (restore_host_input() < 0 && status == 0)
        status = 1;
    return status;
}
