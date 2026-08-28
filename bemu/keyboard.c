#include "keyboard.h"
#include "machine.h"

#include <stdint.h>
#include <string.h>
#include <unistd.h>

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
    case '\'': *code=0x28; return 0;
    case '"': *code=0x28; *shift=1; return 0;
    case '`': *code=0x2b; return 0;
    case '~': *code=0x2b; *shift=1; return 0;
    case '$': *code=0x05; *shift=1; return 0;
    case '&': *code=0x08; *shift=1; return 0;
    case '*': *code=0x09; *shift=1; return 0;
    case '(': *code=0x0a; *shift=1; return 0;
    case ')': *code=0x0b; *shift=1; return 0;
    case '<': *code=0x33; *shift=1; return 0;
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
    } else if (ch == '|') {
        /* Linux 0.01's Finnish keymap uses AltGr + the ISO < key. */
        key_push(m, 0xe0);
        key_push(m, 0x38);
        key_push(m, 0x56);
        key_push(m, 0xd6);
        key_push(m, 0xe0);
        key_push(m, 0xb8);
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

void keyboard_queue_input_byte(struct machine *m, unsigned char ch, int *state)
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

int keyboard_inject_invalid_scancode(struct machine *m, uint8_t code)
{
    if (code != 0x00 && code != 0xff)
        return -1;
    key_push(m, code);
    return 0;
}

enum keyboard_input_end_status keyboard_finish_input(struct machine *m,
                                                      int *state)
{
    int old_state = *state;

    *state = 0;
    if (old_state == 1) {
        queue_character(m, 0x1b);
        return KEYBOARD_INPUT_END_OK;
    }
    if (old_state == 2)
        return KEYBOARD_INPUT_END_TRUNCATED;
    return KEYBOARD_INPUT_END_OK;
}

void keyboard_queue_text(struct machine *m, const char *text)
{
    int state = 0;

    while (*text)
        keyboard_queue_input_byte(m, (unsigned char)*text++, &state);
    (void)keyboard_finish_input(m, &state);
}

void keyboard_reset(struct machine *m)
{
    m->key_head = 0;
    m->key_tail = 0;
    m->key_data = 0;
    m->key_ready = 0;
}

void keyboard_pump(struct machine *m)
{
    if (!m->key_ready && m->key_tail != m->key_head) {
        m->key_data = m->keys[m->key_tail];
        m->key_tail = (m->key_tail + 1) % KEY_QUEUE_MAX;
        m->key_ready = 1;
        irq_pulse(m, 1);
    }
}
