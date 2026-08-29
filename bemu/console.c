/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "console.h"
#include "machine.h"

#include <stdio.h>
#include <string.h>

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

void console_reset(struct machine *m)
{
    m->console_state = CONSOLE_TEXT;
    m->console_seq_len = 0;
    m->console_csi_valid = 0;
    m->ansi_state = 0;
    m->console_line_redraw = 0;
    m->console_redraw_state = 0;
}

void console_output(struct machine *m, uint8_t value)
{
    static const char prompt_prefix[] = "root@linux01:";
    size_t line_start, line_len;
    int plain_appended = 0;
    if (m->serial_len + 1 < SERIAL_LOG_MAX) {
        m->serial_log[m->serial_len++] = (char)value;
        m->serial_log[m->serial_len] = 0;
    }
    console_byte(m, value);
    if (value == '\n') {
        m->console_line_redraw = 0;
        m->console_redraw_state = 0;
    } else if (m->console_redraw_state == 0) {
        if (value == 0x1b)
            m->console_redraw_state = 1;
    } else if (m->console_redraw_state == 1) {
        m->console_redraw_state = value == '[' ? 2 : 0;
    } else if (m->console_redraw_state == 2) {
        m->console_redraw_state = value == '2' ? 3 : 0;
    } else {
        if (value == 'K')
            m->console_line_redraw = 1;
        m->console_redraw_state = 0;
    }
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
    line_len = m->plain_len - line_start;
    if (plain_appended && value == ' ' &&
        !m->console_line_redraw &&
        line_len >= sizeof(prompt_prefix) + 2 &&
        !memcmp(m->plain_log + line_start, prompt_prefix,
                sizeof(prompt_prefix) - 1) &&
        m->plain_log[line_start + sizeof(prompt_prefix) - 1] == '/' &&
        m->plain_log[m->plain_len - 2] == '#') {
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
