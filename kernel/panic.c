/*
 * This function is used through-out the kernel (includeinh mm and fs)
 * to indicate a major problem.
 */
#include <linux/kernel.h>
#include <asm/system.h>

__attribute__((noreturn)) void panic(const char * s)
{
	printk("\033[31mKernel panic:\033[0m %s\n\r",s);
	cli();
	for(;;)
		__asm__("hlt");
}
