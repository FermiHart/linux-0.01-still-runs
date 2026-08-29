/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_KEYBOARD_H
#define BEMU_KEYBOARD_H

#include <stddef.h>
#include <stdint.h>

struct machine;

enum keyboard_input_end_status {
    KEYBOARD_INPUT_END_OK = 0,
    KEYBOARD_INPUT_END_TRUNCATED,
};

void keyboard_reset(struct machine *m);
void keyboard_queue_text(struct machine *m, const char *text);
void keyboard_queue_input_byte(struct machine *m, unsigned char ch, int *state);
int keyboard_inject_invalid_scancode(struct machine *m, uint8_t code);
enum keyboard_input_end_status keyboard_finish_input(struct machine *m,
                                                      int *state);
void keyboard_pump(struct machine *m);

#endif
