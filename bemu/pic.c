#include "pic.h"

#include <string.h>

void pic_reset(struct pic_state *pic)
{
    memset(pic, 0, sizeof *pic);
    pic->imr = 0xff;
    pic->vector_base = 0x08;
}

static void pic_eoi(struct pic_state *pic)
{
    unsigned i;
    for (i = 0; i < 8; i++) {
        if (pic->isr & (1U << i)) {
            pic->isr &= (uint8_t)~(1U << i);
            break;
        }
    }
}

void pic_write(struct pic_state *pic, uint16_t port, uint8_t value)
{
    if (port == 0) {
        if (value & 0x10) {
            /* ICW1 */
            pic->init = 1;
            pic->icw_step = 1;
            pic->icw[0] = value;
            pic->imr = 0;
            pic->isr = 0;
            pic->irr = 0;
            pic->auto_eoi = (value & 2) ? 1 : 0;
        } else if ((value & 0x18) == 0) {
            /* OCW2 */
            if ((value & 0xe0) == 0x20)
                pic_eoi(pic);
        } else if ((value & 0x18) == 0x08) {
            /* OCW3 */
            pic->ocw3 = value;
            pic->read_reg = (value & 2) ? 1 : 0; /* 0=IRR, 1=ISR if bit 1 set */
        }
    } else {
        if (pic->init) {
            switch (pic->icw_step) {
            case 1:
                pic->icw[1] = value;
                pic->vector_base = value;
                pic->icw_step = (pic->icw[0] & 2) ? 3 : 2;
                break;
            case 2:
                pic->icw[2] = value;
                pic->icw_step = (pic->icw[0] & 1) ? 3 : 4;
                break;
            case 3:
                pic->icw[3] = value;
                pic->icw_step = (pic->icw[0] & 1) ? 4 : 0;
                break;
            case 4:
                pic->icw[4] = value;
                pic->auto_eoi = (value & 2) ? 1 : 0;
                pic->init = 0;
                break;
            default:
                break;
            }
        } else {
            /* OCW1 - IMR */
            pic->imr = value;
        }
    }
}

uint8_t pic_read(struct pic_state *pic, uint16_t port)
{
    if (port == 0) {
        if (pic->ocw3 & 2)
            return pic->read_reg ? pic->isr : pic->irr;
        return 0;
    }
    return pic->imr;
}

void pic_raise_irq(struct pic_state *pic, unsigned irq)
{
    if (irq < 8)
        pic->irr |= (uint8_t)(1U << irq);
}

void pic_lower_irq(struct pic_state *pic, unsigned irq)
{
    if (irq < 8)
        pic->irr &= (uint8_t)~(1U << irq);
}

int pic_get_pending_vector(struct pic_state *pic)
{
    unsigned i;
    uint8_t pending = pic->irr & ~pic->imr;
    for (i = 0; i < 8; i++) {
        if (pending & (1U << i)) {
            pic->irr &= (uint8_t)~(1U << i);
            pic->isr |= (uint8_t)(1U << i);
            return pic->vector_base + (int)i;
        }
    }
    return -1;
}
