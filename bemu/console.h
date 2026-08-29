/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_CONSOLE_H
#define BEMU_CONSOLE_H

#include <stdint.h>

struct machine;

void console_reset(struct machine *m);
void console_output(struct machine *m, uint8_t value);

#endif
