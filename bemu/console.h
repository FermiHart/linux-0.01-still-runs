#ifndef BEMU_CONSOLE_H
#define BEMU_CONSOLE_H

#include <stdint.h>

struct machine;

void console_reset(struct machine *m);
void console_output(struct machine *m, uint8_t value);

#endif
