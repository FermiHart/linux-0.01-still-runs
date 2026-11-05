/*
 *	serial.c
 *
 * This module implements the rs232 io functions
 *	void rs_write(struct tty_struct * queue);
 *	void rs_init(void);
 *	void serial_console_write(int c);
 * and all interrupts pertaining to serial IO.
 */

#include <linux/tty.h>
#include <linux/sched.h>
#include <asm/system.h>
#include <asm/io.h>

#define WAKEUP_CHARS (TTY_BUF_SIZE/4)

extern void rs1_interrupt(void);
extern void rs2_interrupt(void);

static void init(int port)
{
	outb_p(0x80,port+3);	/* set DLAB of line control reg */
	outb_p(0x01,port);	/* LS of divisor (1 -> 115200 bps).
				 * Original 1991 used 0x30 (2400 bps). At 2400
				 * with polled busy-wait writes and printk going
				 * through both serial_puts AND tty_write paths,
				 * the write_q saturated after ~25 commands and
				 * the shell blocked in puts(prompt). 115200 fits
				 * bEMU's host UART and eliminates the backpressure. */
	outb_p(0x00,port+1);	/* MS of divisor */
	outb_p(0x03,port+3);	/* reset DLAB */
	outb_p(0x0b,port+4);	/* set DTR,RTS, OUT_2 */
	outb_p(0x0d,port+1);	/* enable all intrs but writes */
	(void)inb(port);	/* read data port to reset things (?) */
}

void rs_init(void)
{
	set_intr_gate(0x24,rs1_interrupt);
	set_intr_gate(0x23,rs2_interrupt);
	init(tty_table[1].read_q.data);
	init(tty_table[2].read_q.data);
	outb(inb_p(0x21)&0xE7,0x21);
}

/*
 * This routine gets called when tty_write has put something into
 * the write_queue. It must check wheter the queue is empty, and
 * set the interrupt register accordingly
 *
 *	void _rs_write(struct tty_struct * tty);
 */
void rs_write(struct tty_struct * tty)
{
	cli();
	if (!EMPTY(tty->write_q))
		outb(inb_p(tty->write_q.data+1)|0x02,tty->write_q.data+1);
	sti();
}

/* Polled serial output to COM1 for console echo.
 * Saves/restores interrupt flags so it's safe from any context. */
void serial_console_write(int c)
{
	unsigned long __flags;
	__asm__ __volatile__("pushfl; popl %0" : "=g" (__flags));
	cli();
	while (!(inb_p(0x3FD) & 0x20))
		;
	outb_p(c, 0x3F8);
	if (c == 0x0A) {
		while (!(inb_p(0x3FD) & 0x20))
			;
		outb_p(0x0D, 0x3F8);
	}
	__asm__ __volatile__("pushl %0; popfl" :: "g" (__flags));
}
