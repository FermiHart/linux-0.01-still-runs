/*
 *  NOTE!!! memcpy(dest,src,n) assumes ds=es=normal data segment. This
 *  goes for all kernel functions (ds=es=kernel space, fs=local data,
 *  gs=null), as well as for all well-behaving user programs (ds=es=
 *  user data space). This is NOT a bug, as any user program that changes
 *  es deserves to die if it isn't careful.
 */
#define memcpy(dest,src,n) ({ \
void * _res = dest; \
unsigned long _dst = (unsigned long)(_res); \
unsigned long _src = (unsigned long)(src); \
unsigned long _cnt = (unsigned long)(n); \
__asm__ volatile ("cld;rep;movsb" \
	:"+D" (_dst),"+S" (_src),"+c" (_cnt) \
	: :"memory","cc"); \
_res; \
})
