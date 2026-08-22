#ifndef BEMU_KEYBOARD_H
#define BEMU_KEYBOARD_H

#include <stddef.h>

struct machine;

void keyboard_reset(struct machine *m);
void keyboard_queue_text(struct machine *m, const char *text);
void keyboard_queue_input_byte(struct machine *m, unsigned char ch, int *state);
void keyboard_pump(struct machine *m);

#endif
