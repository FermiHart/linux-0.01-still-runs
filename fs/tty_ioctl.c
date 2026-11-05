#include <errno.h>
#include <termios.h>

#include <linux/sched.h>
#include <linux/kernel.h>
#include <linux/tty.h>

#include <asm/segment.h>
#include <asm/system.h>

static void flush(struct tty_queue * queue,int reset_data)
{
	cli();
	queue->head = queue->tail;
	if (reset_data)
		queue->data = 0;
	sti();
}

static void wait_until_sent(struct tty_struct * tty)
{
}

static void send_break(struct tty_struct * tty)
{
}

static int get_termios(struct tty_struct * tty, struct termios * termios)
{
	int i;

	if (verify_area(termios, sizeof (*termios)))
		return -EFAULT;
	for (i=0 ; i< (sizeof (*termios)) ; i++)
		put_fs_byte( ((char *)&tty->termios)[i] , i+(char *)termios );
	return 0;
}

static int set_termios(struct tty_struct * tty, struct termios * termios)
{
	int i;

	if (verify_area(termios, sizeof(*termios)))
		return -EFAULT;
	cli();
	for (i=0 ; i< (sizeof (*termios)) ; i++)
		((char *)&tty->termios)[i]=get_fs_byte(i+(char *)termios);
	sti();
	return 0;
}

static int get_termio(struct tty_struct * tty, struct termio * termio)
{
	int i;
	struct termio tmp_termio;

	if (verify_area(termio, sizeof (*termio)))
		return -EFAULT;
	for (i=0 ; i<sizeof tmp_termio ; i++)
		((char *)&tmp_termio)[i]=0;
	tmp_termio.c_iflag = tty->termios.c_iflag;
	tmp_termio.c_oflag = tty->termios.c_oflag;
	tmp_termio.c_cflag = tty->termios.c_cflag;
	tmp_termio.c_lflag = tty->termios.c_lflag;
	tmp_termio.c_line = tty->termios.c_line;
	for(i=0 ; i < NCC ; i++)
		tmp_termio.c_cc[i] = tty->termios.c_cc[i];
	for (i=0 ; i< (sizeof (*termio)) ; i++)
		put_fs_byte( ((char *)&tmp_termio)[i] , i+(char *)termio );
	return 0;
}

static int set_termio(struct tty_struct * tty, struct termio * termio)
{
	int i;
	struct termio tmp_termio;

	if (verify_area(termio, sizeof(*termio)))
		return -EFAULT;
	for (i=0 ; i< (sizeof (*termio)) ; i++)
		((char *)&tmp_termio)[i]=get_fs_byte(i+(char *)termio);
	cli();
	tty->termios.c_iflag = tmp_termio.c_iflag;
	tty->termios.c_oflag = tmp_termio.c_oflag;
	tty->termios.c_cflag = tmp_termio.c_cflag;
	tty->termios.c_lflag = tmp_termio.c_lflag;
	tty->termios.c_line = tmp_termio.c_line;
	for(i=0 ; i < NCC ; i++)
		tty->termios.c_cc[i] = tmp_termio.c_cc[i];
	sti();
	return 0;
}

int tty_ioctl(int dev, int cmd, int arg)
{
	struct tty_struct * tty;
	if (MAJOR(dev) == 5) {
		dev=current->tty;
		if (dev<0)
			dev=0;
	} else
		dev=MINOR(dev);
	if (dev < 0 || dev >= NR_TTYS)
		return -ENXIO;
	tty = dev + tty_table;
	switch (cmd) {
	case TCGETS:
		return get_termios(tty,(struct termios *) arg);
	case TCSETSF:
		flush(&tty->read_q,0);
		flush(&tty->secondary,1); /* fallthrough */
	case TCSETSW:
		wait_until_sent(tty); /* fallthrough */
	case TCSETS:
		return set_termios(tty,(struct termios *) arg);
	case TCGETA:
		return get_termio(tty,(struct termio *) arg);
	case TCSETAF:
		flush(&tty->read_q,0);
		flush(&tty->secondary,1);
		flush(&tty->write_q,0); /* fallthrough */
	case TCSETAW:
		wait_until_sent(tty); /* fallthrough */
	case TCSETA:
		return set_termio(tty,(struct termio *) arg);
	case TCSBRK:
		if (!arg) {
			wait_until_sent(tty);
			send_break(tty);
		}
		return 0;
	case TCXONC:
		return -EINVAL;
	case TCFLSH:
		if (arg==0) {
			flush(&tty->read_q,0);
			flush(&tty->secondary,1);
		} else if (arg==1)
			flush(&tty->write_q,0);
		else if (arg==2) {
			flush(&tty->read_q,0);
			flush(&tty->secondary,1);
			flush(&tty->write_q,0);
		} else
			return -EINVAL;
		return 0;
	case TIOCEXCL:
		return -EINVAL;
	case TIOCNXCL:
		return -EINVAL;
	case TIOCSCTTY:
		return -EINVAL;
	case TIOCGPGRP:
		if (verify_area((void *) arg,4))
			return -EFAULT;
		put_fs_long(tty->pgrp,(unsigned long *) arg);
		return 0;
	case TIOCSPGRP:
		if (verify_area((void *) arg,4))
			return -EFAULT;
		tty->pgrp=get_fs_long((unsigned long *) arg);
		return 0;
	case TIOCOUTQ:
		if (verify_area((void *) arg,4))
			return -EFAULT;
		put_fs_long(CHARS(tty->write_q),(unsigned long *) arg);
		return 0;
	case TIOCSTI:
		return -EINVAL;
	case TIOCGWINSZ:
		return -EINVAL;
	case TIOCSWINSZ:
		return -EINVAL;
	case TIOCMGET:
		return -EINVAL;
	case TIOCMBIS:
		return -EINVAL;
	case TIOCMBIC:
		return -EINVAL;
	case TIOCMSET:
		return -EINVAL;
	case TIOCGSOFTCAR:
		return -EINVAL;
	case TIOCSSOFTCAR:
		return -EINVAL;
	default:
		return -EINVAL;
	}
}
