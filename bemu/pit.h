/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_PIT_H
#define BEMU_PIT_H

#include <stdint.h>

struct pit_state {
    uint8_t latch[2];
    int bytes;
    int enabled;
};

void pit_reset(struct pit_state *pit);
uint8_t pit_read(struct pit_state *pit, uint16_t port);
void pit_write(struct pit_state *pit, uint16_t port, uint8_t value);
int pit_is_enabled(const struct pit_state *pit);

#endif
