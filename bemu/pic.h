/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#ifndef BEMU_PIC_H
#define BEMU_PIC_H

#include <stdint.h>

struct pic_state {
    uint8_t icw[5];
    uint8_t icw_step;
    uint8_t imr;
    uint8_t isr;
    uint8_t irr;
    uint8_t ocw3;
    uint8_t read_reg;
    uint8_t init;
    uint8_t auto_eoi;
    uint8_t vector_base;
};

void pic_reset(struct pic_state *pic);
uint8_t pic_read(struct pic_state *pic, uint16_t port);
void pic_write(struct pic_state *pic, uint16_t port, uint8_t value);
void pic_raise_irq(struct pic_state *pic, unsigned irq);
void pic_lower_irq(struct pic_state *pic, unsigned irq);
int pic_get_pending_vector(struct pic_state *pic);

#endif
