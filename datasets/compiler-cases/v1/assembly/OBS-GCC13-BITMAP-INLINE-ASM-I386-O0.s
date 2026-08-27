	.file	"bitmap_inline_asm.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.local	bitmap
	.comm	bitmap,8,4
	.section	.rodata
	.align 4
.LC0:
	.string	"FAIL: bit %d not visible after set_bit; old=%d word=0x%lx\n"
	.text
	.type	use_bit, @function
use_bit:
.LFB6:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	movl	%esp, %ebp	#,
	.cfi_def_cfa_register 5
	pushl	%esi	#
	pushl	%ebx	#
	subl	$16, %esp	#,
	.cfi_offset 6, -12
	.cfi_offset 3, -16
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	movl	8(%ebp), %eax	# n, tmp91
	leal	31(%eax), %edx	#, tmp93
	testl	%eax, %eax	# tmp92
	cmovs	%edx, %eax	# tmp93,, tmp92
	sarl	$5, %eax	#, tmp94
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	leal	0(,%eax,4), %edx	#, tmp95
	leal	bitmap@GOTOFF(%ebx), %eax	#, tmp96
	addl	%edx, %eax	# tmp95, tmp97
	movl	%eax, -20(%ebp)	# tmp97, word
# sources/bitmap_inline_asm.c:35:     int bit = n & 31;
	movl	8(%ebp), %eax	# n, tmp101
	andl	$31, %eax	#, tmp100
	movl	%eax, -16(%ebp)	# tmp100, bit
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	movl	$0, %eax	#, tmp103
	movl	-16(%ebp), %edx	# bit, tmp104
	movl	-20(%ebp), %ecx	# word, tmp105
#APP
# 38 "sources/bitmap_inline_asm.c" 1
	btsl %edx,(%ecx)	# tmp104, *word_8
	setb %al
# 0 "" 2
#NO_APP
	movl	%eax, %esi	# res, res
	movl	%esi, %eax	# res, _12
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	movl	%eax, -12(%ebp)	# _12, old
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	movl	-20(%ebp), %eax	# word, tmp106
	movl	(%eax), %edx	# *word_8, _2
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	movl	-16(%ebp), %eax	# bit, tmp107
	movl	%eax, %ecx	# tmp107, tmp113
	shrl	%cl, %edx	# tmp113, _2
	movl	%edx, %eax	# _2, _3
	andl	$1, %eax	#, _4
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	testl	%eax, %eax	# _4
	jne	.L3	#,
# sources/bitmap_inline_asm.c:41:         fprintf(stderr,
	movl	-20(%ebp), %eax	# word, tmp108
	movl	(%eax), %edx	# *word_8, _5
	movl	stderr@GOT(%ebx), %eax	#, tmp109
	movl	(%eax), %eax	# stderr, stderr.0_6
	subl	$12, %esp	#,
	pushl	%edx	# _5
	pushl	-12(%ebp)	# old
	pushl	8(%ebp)	# n
	leal	.LC0@GOTOFF(%ebx), %edx	#, tmp110
	pushl	%edx	# tmp110
	pushl	%eax	# stderr.0_6
	call	fprintf@PLT	#
	addl	$32, %esp	#,
# sources/bitmap_inline_asm.c:44:         exit(1);
	subl	$12, %esp	#,
	pushl	$1	#
	call	exit@PLT	#
.L3:
# sources/bitmap_inline_asm.c:46: }
	nop
	leal	-8(%ebp), %esp	#,
	popl	%ebx	#
	.cfi_restore 3
	popl	%esi	#
	.cfi_restore 6
	popl	%ebp	#
	.cfi_restore 5
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE6:
	.size	use_bit, .-use_bit
	.section	.rodata
	.align 4
.LC1:
	.string	"PASS: bit operations are visible after inline asm"
	.text
	.globl	main
	.type	main, @function
main:
.LFB7:
	.cfi_startproc
	leal	4(%esp), %ecx	#,
	.cfi_def_cfa 1, 0
	andl	$-16, %esp	#,
	pushl	-4(%ecx)	#
	pushl	%ebp	#
	movl	%esp, %ebp	#,
	.cfi_escape 0x10,0x5,0x2,0x75,0
	pushl	%ebx	#
	pushl	%ecx	#
	.cfi_escape 0xf,0x3,0x75,0x78,0x6
	.cfi_escape 0x10,0x3,0x2,0x75,0x7c
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/bitmap_inline_asm.c:50:     memset(bitmap, 0, sizeof(bitmap));
	subl	$4, %esp	#,
	pushl	$8	#
	pushl	$0	#
	leal	bitmap@GOTOFF(%ebx), %eax	#, tmp85
	pushl	%eax	# tmp85
	call	memset@PLT	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:52:     use_bit(0);
	subl	$12, %esp	#,
	pushl	$0	#
	call	use_bit	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:53:     use_bit(31);
	subl	$12, %esp	#,
	pushl	$31	#
	call	use_bit	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:54:     use_bit(32);
	subl	$12, %esp	#,
	pushl	$32	#
	call	use_bit	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:55:     use_bit(63);
	subl	$12, %esp	#,
	pushl	$63	#
	call	use_bit	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:57:     puts("PASS: bit operations are visible after inline asm");
	subl	$12, %esp	#,
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp86
	pushl	%eax	# tmp86
	call	puts@PLT	#
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:58:     return 0;
	movl	$0, %eax	#, _8
# sources/bitmap_inline_asm.c:59: }
	leal	-8(%ebp), %esp	#,
	popl	%ecx	#
	.cfi_restore 1
	.cfi_def_cfa 1, 0
	popl	%ebx	#
	.cfi_restore 3
	popl	%ebp	#
	.cfi_restore 5
	leal	-4(%ecx), %esp	#,
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE7:
	.size	main, .-main
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB8:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE8:
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
