/*
 * Minimal unit tests for self-contained bEMU device modules.
 * These tests exercise PIC, PIT and UART state machines without KVM.
 */

#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#include "../../bemu/pic.h"
#include "../../bemu/pit.h"
#include "../../bemu/uart.h"
#include "../../bemu/keyboard.h"
#include "../../bemu/console.h"
#include "../../bemu/machine.h"

static int failures = 0;
static struct machine keyboard_machine;

void fail(const char *what)
{
    fprintf(stderr, "FAIL: %s\n", what);
    failures++;
}

void irq_pulse(struct machine *m, unsigned irq)
{
    (void)m;
    (void)irq;
}

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void test_pic_init(void)
{
    struct pic_state pic;
    pic_reset(&pic);
    check(pic.imr == 0xff, "pic_reset masks all interrupts");
    check(pic.vector_base == 0x08, "pic_reset default vector base");
}

static void test_pic_icw(void)
{
    struct pic_state pic;
    pic_reset(&pic);
    /* ICW1: edge, single, ICW4 needed */
    pic_write(&pic, 0, 0x13);
    /* ICW2: vector base */
    pic_write(&pic, 1, 0x20);
    /* ICW4 (single mode skips ICW3) */
    pic_write(&pic, 1, 0x01);
    check(pic.vector_base == 0x20, "pic vector base after ICW2");
    check(pic.init == 0, "pic init sequence complete");
}

static void test_pic_eoi(void)
{
    struct pic_state pic;
    pic_reset(&pic);
    pic_write(&pic, 0, 0x13);
    pic_write(&pic, 1, 0x08);
    pic_write(&pic, 1, 0x01);
    pic_write(&pic, 1, 0x00); /* unmask all */
    pic_raise_irq(&pic, 2);
    check(pic_get_pending_vector(&pic) == 0x0a, "pic pending vector IRQ2");
    check(pic.isr == 0x04, "pic ISR after accept");
    pic_write(&pic, 0, 0x20); /* EOI */
    check(pic.isr == 0x00, "pic ISR after EOI");
}

static void test_pit_latch(void)
{
    struct pit_state pit;
    pit_reset(&pit);
    check(!pit_is_enabled(&pit), "pit disabled after reset");
    pit_write(&pit, 0x40, 0x34);
    pit_write(&pit, 0x40, 0x12);
    check(pit_is_enabled(&pit), "pit enabled after two latch bytes");
    pit_write(&pit, 0x43, 0x00);
    check(!pit_is_enabled(&pit), "pit disabled after mode port write");
}

static void test_uart_dll_dlm(void)
{
    struct uart_state u;
    uart_reset(&u);
    /* divisor latch access bit */
    uart_write(&u, 0x3fb, 0x80);
    uart_write(&u, 0x3f8, 0x60);
    uart_write(&u, 0x3f9, 0x00);
    check(uart_read(&u, 0x3f8) == 0x60, "uart DLL readback");
    check(uart_read(&u, 0x3f9) == 0x00, "uart DLM readback");
    check(uart_read(&u, 0x3fd) == 0x60, "uart LSR value");
}

static void test_keyboard_shell_operators(void)
{
    static const unsigned char expected[] = {
        0xe0, 0x38, 0x56, 0xd6, 0xe0, 0xb8,
        0x2a, 0x33, 0xb3, 0xaa,
    };
    size_t i;
    int match;

    memset(&keyboard_machine, 0, sizeof(keyboard_machine));
    keyboard_reset(&keyboard_machine);
    keyboard_queue_text(&keyboard_machine, "|<");
    match = keyboard_machine.key_head == sizeof(expected);
    for (i = 0; i < sizeof(expected) && i < keyboard_machine.key_head; i++)
        if (keyboard_machine.keys[i] != expected[i])
            match = 0;
    check(match, "keyboard queues pipe and input redirect scancodes");
}

static void feed_console(struct machine *m, const char *text)
{
    while (*text)
        console_output(m, (unsigned char)*text++);
}

static void test_console_prompt_contract(void)
{
    struct machine m;
    int saved_stdout, null_fd;
    int recognized = 1, ignored_redraw = 1, rejected_malformed = 1;
    int sanitize;

    fflush(stdout);
    saved_stdout = dup(STDOUT_FILENO);
    null_fd = open("/dev/null", O_WRONLY);
    if (saved_stdout < 0 || null_fd < 0 || dup2(null_fd, STDOUT_FILENO) < 0) {
        if (saved_stdout >= 0) close(saved_stdout);
        if (null_fd >= 0) close(null_fd);
        check(0, "console test redirects stdout");
        return;
    }
    close(null_fd);
    for (sanitize = 0; sanitize <= 1; sanitize++) {
        memset(&m, 0, sizeof(m));
        m.sanitize_console = sanitize;
        console_reset(&m);
        feed_console(&m, "\rroot@linux01:/# ");
        recognized = recognized && m.prompt_count == 1;
        feed_console(&m, "\r\033[2Kroot@linux01:/# typed  \rroot@linux01:/# ");
        ignored_redraw = ignored_redraw && m.prompt_count == 1;
        feed_console(&m, "\nroot@linux01:not-a-path# ");
        rejected_malformed = rejected_malformed && m.prompt_count == 1;
    }
    fflush(stdout);
    dup2(saved_stdout, STDOUT_FILENO);
    close(saved_stdout);
    check(recognized, "console recognizes root prompt");
    check(ignored_redraw, "console ignores prompt redraw");
    check(rejected_malformed, "console rejects malformed prompt");
}

int main(void)
{
    test_pic_init();
    test_pic_icw();
    test_pic_eoi();
    test_pit_latch();
    test_uart_dll_dlm();
    test_keyboard_shell_operators();
    test_console_prompt_contract();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall device unit tests passed\n");
    return 0;
}
