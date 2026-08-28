#include "uart.h"

#include <string.h>

void uart_reset(struct uart_state *u)
{
    memset(u, 0, sizeof *u);
}

uint8_t uart_read(struct uart_state *u, uint16_t port)
{
    switch (port) {
    case 0x3f8: return (u->lcr & 0x80) ? u->dll : 0;
    case 0x3f9: return (u->lcr & 0x80) ? u->dlm : u->ier;
    case 0x3fa: return 1;
    case 0x3fb: return u->lcr;
    case 0x3fc: return u->mcr;
    case 0x3fd: return 0x60;
    case 0x3fe: return 0xb0;
    case 0x3ff: return u->scratch;
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fe: case 0x2ff: return 0;
    case 0x2fd: return 0x60;
    default: return 0;
    }
}

void uart_write(struct uart_state *u, uint16_t port, uint8_t value)
{
    switch (port) {
    case 0x3f8:
        if (u->lcr & 0x80) u->dll = value;
        break;
    case 0x3f9:
        if (u->lcr & 0x80) u->dlm = value;
        else u->ier = value;
        break;
    case 0x3fb: u->lcr = value; break;
    case 0x3fc: u->mcr = value; break;
    case 0x3ff: u->scratch = value; break;
    case 0x2f8: case 0x2f9: case 0x2fa: case 0x2fb:
    case 0x2fc: case 0x2fd: case 0x2fe: case 0x2ff: break;
    default: break;
    }
}
