#define move_to_user_mode() \
__asm__ ("movl %%esp,%%eax\n\t" \
	"pushl $0x17\n\t" \
	"pushl %%eax\n\t" \
	"pushfl\n\t" \
	"pushl $0x0f\n\t" \
	"pushl $1f\n\t" \
	"iret\n" \
	"1:\tmovl $0x17,%%eax\n\t" \
	"movw %%ax,%%ds\n\t" \
	"movw %%ax,%%es\n\t" \
	"movw %%ax,%%fs\n\t" \
	"movw %%ax,%%gs" \
	:::"ax")

#define sti() __asm__ ("sti"::)
#define cli() __asm__ ("cli"::)
#define nop() __asm__ ("nop"::)

#define iret() __asm__ ("iret"::)

/* EAX/EDX and both descriptor words are outputs, not input-only operands. */
#define _set_gate(gate_addr,type,dpl,addr) do { \
unsigned int __low = 0x00080000; \
unsigned int __high = (unsigned long)(addr); \
unsigned int *__gate = (unsigned int *)(gate_addr); \
__asm__ volatile("movw %%dx,%%ax\n\t" \
	"movw %4,%%dx\n\t" \
	"movl %%eax,%2\n\t" \
	"movl %%edx,%3" \
	: "+&a" (__low), "+&d" (__high), "=m" (__gate[0]), "=m" (__gate[1]) \
	: "i" ((short)(0x8000+((dpl)<<13)+((type)<<8)))); \
} while (0)

#define set_intr_gate(n,addr) \
	_set_gate(&idt[n],14,0,addr)

#define set_trap_gate(n,addr) \
	_set_gate(&idt[n],15,0,addr)

#define set_system_gate(n,addr) \
	_set_gate(&idt[n],15,3,addr)

#define _set_seg_desc(gate_addr,type,dpl,base,limit) {\
	*(gate_addr) = ((base) & 0xff000000) | \
		(((base) & 0x00ff0000)>>16) | \
		((limit) & 0xf0000) | \
		((dpl)<<13) | \
		(0x00408000) | \
		((type)<<8); \
	*((gate_addr)+1) = (((base) & 0x0000ffff)<<16) | \
		((limit) & 0x0ffff); }

/* One address register describes the complete eight-byte output. */
#define _set_tssldt_desc(n,addr,type) do { \
unsigned int __base = (unsigned long)(addr); \
char *__desc = (char *)(n); \
__asm__ volatile("movw $104,0(%2)\n\t" \
	"movw %%ax,2(%2)\n\t" \
	"rorl $16,%%eax\n\t" \
	"movb %%al,4(%2)\n\t" \
	"movb $" type ",5(%2)\n\t" \
	"movb $0x00,6(%2)\n\t" \
	"movb %%ah,7(%2)\n\t" \
	"rorl $16,%%eax" \
	: "+&a" (__base), "=m" (*(char (*)[8])__desc) \
	: "r" (__desc) : "cc"); \
} while (0)

#define set_tss_desc(n,addr) _set_tssldt_desc(((char *) (n)),addr,"0x89")
#define set_ldt_desc(n,addr) _set_tssldt_desc(((char *) (n)),addr,"0x82")
