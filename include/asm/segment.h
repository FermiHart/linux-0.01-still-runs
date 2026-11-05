extern inline unsigned char get_fs_byte(const char * addr)
{
	register unsigned char _v;

	__asm__ volatile ("movb %%fs:%1,%0":"=q" (_v):"m" (*addr));
	return _v;
}

extern inline unsigned short get_fs_word(const unsigned short *addr)
{
	unsigned short _v;

	__asm__ volatile ("movw %%fs:%1,%0":"=r" (_v):"m" (*addr));
	return _v;
}

extern inline unsigned long get_fs_long(const unsigned long *addr)
{
	unsigned long _v;

	__asm__ volatile ("movl %%fs:%1,%0":"=r" (_v):"m" (*addr));
	return _v;
}

extern inline void put_fs_byte(char val,char *addr)
{
	__asm__ volatile ("movb %1,%%fs:%0":"=m" (*addr):"q" (val):"memory");
}

extern inline void put_fs_word(short val,short * addr)
{
	__asm__ volatile ("movw %1,%%fs:%0":"=m" (*addr):"r" (val):"memory");
}

extern inline void put_fs_long(unsigned long val,unsigned long * addr)
{
	__asm__ volatile ("movl %1,%%fs:%0":"=m" (*addr):"r" (val):"memory");
}
