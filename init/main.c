#define __LIBRARY__
#include <unistd.h>
#include <time.h>

/*
 * we need this inline - forking from kernel space will result
 * in NO COPY ON WRITE (!!!), until an execve is executed. This
 * is no problem, but for the stack. This is handled by not letting
 * main() use the stack at all after fork(). Thus, no function
 * calls - which means inline code for fork too, as otherwise we
 * would use the stack upon exit from 'fork()'.
 *
 * Actually only pause and fork are needed inline, so that there
 * won't be any messing with the stack from main(), but we define
 * some others too.
 */
/*
 * Modern GCC refuses `static` redeclaration after the non-static prototypes
 * unistd.h gives us. The 1991 code expects the wrapper to be local; we keep
 * that intent with `inline` + a per-symbol alias so the linker sees the
 * original name once.
 */
/*
 * Modern GCC refuses `static` redeclaration after the non-static prototypes
 * unistd.h gives us. The 1991 intent was: inline wrappers that don't touch
 * the stack post-fork. We open-code the int $0x80 calls directly.
 */
inline int fork(void)
{
    int __res;
    __asm__ volatile("int $0x80" : "=a" (__res) : "0" (__NR_fork));
    return __res;
}
inline int pause(void)
{
    int __res;
    __asm__ volatile("int $0x80" : "=a" (__res) : "0" (__NR_pause));
    return __res;
}
static inline int setup(void)
{
    int __res;
    __asm__ volatile("int $0x80" : "=a" (__res) : "0" (__NR_setup));
    return __res;
}
inline int sync(void)
{
    int __res;
    __asm__ volatile("int $0x80" : "=a" (__res) : "0" (__NR_sync));
    return __res;
}

#include <linux/tty.h>
#include <linux/sched.h>
#include <linux/head.h>
#include <asm/system.h>
#include <asm/io.h>

#include <stddef.h>
#include <stdarg.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>

#include <linux/fs.h>

#include "../bbp/linux01_bbp.h"   /* Bear Boot Protocol — native linux-0.01 port */

static char printbuf[1024];

extern int vsprintf();
extern void init(void);
extern void hd_init(void);
extern long kernel_mktime(struct tm * tm);
extern long startup_time;

/*
 * Yeah, yeah, it's ugly, but I cannot find how to do this correctly
 * and this seems to work. I anybody has more info on the real-time
 * clock I'd be interested. Most of this was trial and error, and some
 * bios-listing reading. Urghh.
 */

#define CMOS_READ(addr) ({ \
outb_p(0x80|addr,0x70); \
inb_p(0x71); \
})

#define BCD_TO_BIN(val) ((val)=((val)&15) + ((val)>>4)*10)

static void time_init(void)
{
	struct tm time;

	do {
		time.tm_sec = CMOS_READ(0);
		time.tm_min = CMOS_READ(2);
		time.tm_hour = CMOS_READ(4);
		time.tm_mday = CMOS_READ(7);
		time.tm_mon = CMOS_READ(8)-1;
		time.tm_year = CMOS_READ(9);
	} while (time.tm_sec != CMOS_READ(0));
	BCD_TO_BIN(time.tm_sec);
	BCD_TO_BIN(time.tm_min);
	BCD_TO_BIN(time.tm_hour);
	BCD_TO_BIN(time.tm_mday);
	BCD_TO_BIN(time.tm_mon);
	BCD_TO_BIN(time.tm_year);
	/* CMOS returns 2-digit year. Y2K rollover: 00-69 = 20xx, 70-99 = 19xx.
	 * kernel_mktime expects tm_year as years-since-1900 (so 2026 -> 126). */
	if (time.tm_year < 70)
		time.tm_year += 100;
	startup_time = kernel_mktime(&time);
}

extern void vga_set_50_rows(void);

void main(void)		/* This really IS void, no error here. */
{			/* The startup routine assumes (well, ...) this */
/*
 * Interrupts are still disabled. Do necessary setups, then
 * enable them
 */
	vga_set_50_rows();	/* before tty_init -> con_init: bump VGA to
				 * 80x50 by selecting the BIOS 8x8 font, so
				 * con_init initializes with LINES=50. */
	time_init();
	tty_init();
	trap_init();
	sched_init();
	buffer_init();
	hd_init();
	bbp_linux01_init();	/* BBP: synthesize + CRC-validate the boot handoff
				 * tag list from the kernel's RAM model. Additive,
				 * non-fatal — logs "[bbp] linux-0.01 adapter: ok". */
	sti();
	move_to_user_mode();
	if (!fork()) {
		init();
	}
/*
 *   NOTE!!   For any other task 'pause()' would mean we have to get a
 * signal to awaken, but task0 is the sole exception (see 'schedule()')
 * as task 0 gets activated at every idle moment (when no other tasks
 * can run). For task0 'pause()' just means we go check if some other
 * task can run, and if not we return here.
 */
	for(;;) pause();
}

static int printf(const char *fmt, ...)
{
	va_list args;
	int i;

	va_start(args, fmt);
	write(1,printbuf,i=vsprintf(printbuf, fmt, args));
	va_end(args);
	return i;
}

static char * argv[] = { "-",NULL };
static char * envp[] = { "HOME=/home/fermihart", NULL };

void init(void)
{
	int i,j;

	setup();
/*	if (!fork())
		_exit(execve("/bin/update",NULL,NULL));  */
	for (i=0;i<NR_OPEN;i++)
		if (current->filp[i])
			close(i);
	(void) open("/dev/tty0",O_RDWR,0);
	(void) dup(0);
	(void) dup(0);
	printf("\033[36m%d buffers\033[0m = \033[37m%d bytes\033[0m buffer space\n\r",NR_BUFFERS,
		NR_BUFFERS*BLOCK_SIZE);
	printf(" \033[32mOk.\033[0m\n\r");
	if ((i=fork())<0)
		printf("\033[31mFork failed in init\033[0m\r\n");
	else if (!i) {
		close(0);close(1);close(2);
		setsid();
		(void) open("/dev/tty0",O_RDWR,0);
		(void) dup(0);
		(void) dup(0);
		_exit(execve("/bin/shell",argv,envp));
	}
	j=wait(&i);
	printf("child %d died with code %04x\n",j,i);
	sync();
	_exit(0);	/* NOTE! _exit, not exit() */
}
