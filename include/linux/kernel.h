/*
 * 'kernel.h' contains some often-used function prototypes etc
 */
int verify_area(void * addr,int count);
__attribute__((noreturn)) void panic(const char * str);
int printf(const char * fmt, ...);
int printk(const char * fmt, ...);
int tty_write(unsigned ch,char * buf,int count);
