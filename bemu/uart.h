/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_UART_H
#define BEMU_UART_H

#include <stdint.h>

struct uart_state {
    uint8_t ier, lcr, mcr, dll, dlm, scratch;
};

void uart_reset(struct uart_state *u);
uint8_t uart_read(struct uart_state *u, uint16_t port);
void uart_write(struct uart_state *u, uint16_t port, uint8_t value);

#endif
