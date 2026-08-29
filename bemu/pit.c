/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "pit.h"

void pit_reset(struct pit_state *pit)
{
    pit->latch[0] = 0;
    pit->latch[1] = 0;
    pit->bytes = 0;
    pit->enabled = 0;
}

uint8_t pit_read(struct pit_state *pit, uint16_t port)
{
    (void)pit;
    (void)port;
    return 0;
}

void pit_write(struct pit_state *pit, uint16_t port, uint8_t value)
{
    if (port == 0x40) {
        if (pit->bytes < 2)
            pit->latch[pit->bytes++] = value;
        if (pit->bytes == 2)
            pit->enabled = 1;
    } else if (port == 0x43) {
        pit->bytes = 0;
        pit->enabled = 0;
    }
}

int pit_is_enabled(const struct pit_state *pit)
{
    return pit->enabled;
}
