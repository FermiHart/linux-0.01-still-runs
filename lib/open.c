#define __LIBRARY__
#include <unistd.h>
#include <stdarg.h>
#include <fcntl.h>

int open(const char * filename, int flag, ...)
{
	register int res;
	va_list arg;
	int mode = 0;

	va_start(arg,flag);
	if (flag & O_CREAT) {
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Warray-bounds"
		mode = va_arg(arg,int);
#pragma GCC diagnostic pop
	}
	va_end(arg);
	__asm__("int $0x80"
		:"=a" (res)
		:"0" (__NR_open),"b" (filename),"c" (flag),
		"d" (mode));
	if (res>=0)
		return res;
	errno = -res;
	return -1;
}
