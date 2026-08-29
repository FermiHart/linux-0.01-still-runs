/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/* Deterministic host-side keyboard fault and truncation tests. */

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../../bemu/keyboard.h"
#include "../../bemu/machine.h"

static int failures;
static unsigned irq_count;
static unsigned last_irq;

void fail(const char *what)
{
    fprintf(stderr, "FAIL: unexpected fatal error: %s\n", what);
    failures++;
}

void irq_pulse(struct machine *m, unsigned irq)
{
    (void)m;
    irq_count++;
    last_irq = irq;
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

static void reset_fixture(struct machine *m)
{
    memset(m, 0, sizeof(*m));
    keyboard_reset(m);
    irq_count = 0;
    last_irq = 0;
}

static int queue_equals(const struct machine *m, const uint8_t *expected,
                        size_t expected_len)
{
    size_t i;

    if (m->key_head != expected_len || m->key_tail != 0)
        return 0;
    for (i = 0; i < expected_len; i++)
        if (m->keys[i] != expected[i])
            return 0;
    return 1;
}

static void test_invalid_scancode_scope(void)
{
    static const uint8_t expected[] = { 0x00, 0xff };
    struct machine m;
    unsigned code;
    int scoped = 1;

    reset_fixture(&m);
    for (code = 0; code <= 0xff; code++) {
        int result = keyboard_inject_invalid_scancode(&m, (uint8_t)code);
        if ((code == 0x00 || code == 0xff) ? result != 0 : result >= 0)
            scoped = 0;
    }
    check(scoped, "keyboard accepts only Set-1 error bytes");
    check(queue_equals(&m, expected, sizeof(expected)),
          "rejected bytes leave only invalid scancodes queued once and in order");

    keyboard_pump(&m);
    check(m.key_ready && m.key_data == 0x00 && irq_count == 1 && last_irq == 1,
          "first invalid scancode requests one IRQ1");
    keyboard_pump(&m);
    check(irq_count == 1 && m.key_data == 0x00,
          "occupied keyboard latch suppresses a second IRQ1");
    m.key_ready = 0;
    keyboard_pump(&m);
    check(m.key_ready && m.key_data == 0xff && irq_count == 2 && last_irq == 1,
          "second invalid scancode requests one IRQ1");
}

static void test_fault_recovery(void)
{
    static const uint8_t expected[] = { 0x00, 0x1e, 0x9e };
    struct machine m;
    int state = 0;

    reset_fixture(&m);
    keyboard_inject_invalid_scancode(&m, 0x00);
    keyboard_queue_input_byte(&m, 'a', &state);
    check(state == 0 && queue_equals(&m, expected, sizeof(expected)),
          "normal input recovers after invalid scancode injection");
    keyboard_pump(&m);
    check(m.key_ready && m.key_data == 0x00 && irq_count == 1,
          "recovery sequence first delivers injected error");
    m.key_ready = 0;
    keyboard_pump(&m);
    check(m.key_ready && m.key_data == 0x1e && irq_count == 2,
          "recovery sequence delivers normal make code");
    m.key_ready = 0;
    keyboard_pump(&m);
    check(m.key_ready && m.key_data == 0x9e && irq_count == 3,
          "recovery sequence delivers normal break code");
}

static void test_split_escape_sequence(void)
{
    static const uint8_t expected[] = { 0xe0, 0x48, 0xe0, 0xc8 };
    struct machine m;
    int state = 0;
    size_t i;

    reset_fixture(&m);
    for (i = 0; i < 127; i++)
        keyboard_queue_input_byte(&m, 0x00, &state);
    keyboard_queue_input_byte(&m, 0x1b, &state);
    check(state == 1 && m.key_head == 0,
          "escape prefix survives a simulated 128-byte input boundary");
    keyboard_queue_input_byte(&m, '[', &state);
    keyboard_queue_input_byte(&m, 'A', &state);
    check(state == 0 && queue_equals(&m, expected, sizeof(expected)),
          "navigation sequence split across input chunks remains complete");
}

static void test_lone_escape_finish(void)
{
    static const uint8_t expected[] = { 0x01, 0x81 };
    struct machine m;
    int state = 0;

    reset_fixture(&m);
    keyboard_queue_input_byte(&m, 0x1b, &state);
    check(keyboard_finish_input(&m, &state) == KEYBOARD_INPUT_END_OK &&
          state == 0 && queue_equals(&m, expected, sizeof(expected)),
          "lone escape at end of input becomes an Escape keystroke");
    check(keyboard_finish_input(&m, &state) == KEYBOARD_INPUT_END_OK &&
          queue_equals(&m, expected, sizeof(expected)),
          "input finalization is idempotent");
}

static void check_truncated(const unsigned char *bytes, size_t count,
                            const char *name)
{
    struct machine m;
    int state = 0;
    size_t i;

    reset_fixture(&m);
    for (i = 0; i < count; i++)
        keyboard_queue_input_byte(&m, bytes[i], &state);
    check(keyboard_finish_input(&m, &state) == KEYBOARD_INPUT_END_TRUNCATED &&
          state == 0 && m.key_head == 0, name);
    check(keyboard_finish_input(&m, &state) == KEYBOARD_INPUT_END_OK &&
          m.key_head == 0, "truncated input finalization is idempotent");
    keyboard_queue_input_byte(&m, 'a', &state);
    check(state == 0 && m.key_head == 2 &&
          m.keys[0] == 0x1e && m.keys[1] == 0x9e,
          "normal input recovers after truncated sequence");
}

static void test_truncated_escape_sequences(void)
{
    static const unsigned char csi[] = { 0x1b, '[' };
    static const unsigned char ss3[] = { 0x1b, 'O' };
    static const unsigned char params[] = { 0x1b, '[', '1', ';' };
    struct machine m;
    int state = 0;

    check_truncated(csi, sizeof(csi), "EOF discards truncated CSI input");
    check_truncated(ss3, sizeof(ss3), "EOF discards truncated SS3 input");
    check_truncated(params, sizeof(params),
                    "EOF discards truncated CSI parameters");

    reset_fixture(&m);
    keyboard_queue_input_byte(&m, 0x1b, &state);
    keyboard_queue_input_byte(&m, '[', &state);
    keyboard_queue_input_byte(&m, 'Z', &state);
    check(state == 0 && m.key_head == 0 &&
          keyboard_finish_input(&m, &state) == KEYBOARD_INPUT_END_OK,
          "complete unsupported escape is not reported as truncated");
}

int main(void)
{
    test_invalid_scancode_scope();
    test_fault_recovery();
    test_split_escape_sequence();
    test_lone_escape_finish();
    test_truncated_escape_sequences();
    if (failures) {
        fprintf(stderr, "\n%d keyboard fault test(s) failed\n", failures);
        return 1;
    }
    printf("\nall keyboard fault-injection tests passed\n");
    return 0;
}
