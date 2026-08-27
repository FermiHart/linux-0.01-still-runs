	.file	"bitmap_inline_asm.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O2 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC0:
	.string	"FAIL: bit %d not visible after set_bit; old=%d word=0x%lx\n"
	.text
	.p2align 4
	.type	use_bit, @function
use_bit:
.LFB54:
	.cfi_startproc
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	movl	%edi, %edx	# n, _1
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	leaq	bitmap(%rip), %rsi	#, tmp96
# sources/bitmap_inline_asm.c:35:     int bit = n & 31;
	movl	%edi, %ecx	# n, bit
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	xorl	%eax, %eax	# res
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	sarl	$5, %edx	#, _1
# sources/bitmap_inline_asm.c:35:     int bit = n & 31;
	andl	$31, %ecx	#, bit
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	movslq	%edx, %rdx	# _1, _1
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	movq	(%rsi,%rdx,8), %r9	# MEM <long unsigned int[2]> [(long unsigned int *)&bitmap][_1], _2
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
#APP
# 38 "sources/bitmap_inline_asm.c" 1
	btsl %ecx,(%rsi,%rdx,8)	# bit, *word_7
	setb %al
# 0 "" 2
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
#NO_APP
	btq	%rcx, %r9	# bit, _2
	jnc	.L7	#,
	ret
.L7:
# sources/bitmap_inline_asm.c:33: {
	pushq	%rdx	#
	.cfi_def_cfa_offset 16
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movl	%edi, %ecx	# n,
	movq	stderr(%rip), %rdi	# stderr,
	movl	%eax, %r8d	# res,
	leaq	.LC0(%rip), %rdx	#, tmp102
	movl	$2, %esi	#,
	xorl	%eax, %eax	#
	call	__fprintf_chk@PLT	#
# sources/bitmap_inline_asm.c:44:         exit(1);
	movl	$1, %edi	#,
	call	exit@PLT	#
	.cfi_endproc
.LFE54:
	.size	use_bit, .-use_bit
	.section	.rodata.str1.8
	.align 8
.LC1:
	.string	"PASS: bit operations are visible after inline asm"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB55:
	.cfi_startproc
	endbr64
	subq	$8, %rsp	#,
	.cfi_def_cfa_offset 16
# /usr/include/x86_64-linux-gnu/bits/string_fortified.h:59:   return __builtin___memset_chk (__dest, __ch, __len,
	pxor	%xmm0, %xmm0	# tmp84
# sources/bitmap_inline_asm.c:52:     use_bit(0);
	xorl	%edi, %edi	#
# /usr/include/x86_64-linux-gnu/bits/string_fortified.h:59:   return __builtin___memset_chk (__dest, __ch, __len,
	movaps	%xmm0, bitmap(%rip)	# tmp84, MEM <char[1:16]> [(void *)&bitmap]
# sources/bitmap_inline_asm.c:52:     use_bit(0);
	call	use_bit	#
# sources/bitmap_inline_asm.c:53:     use_bit(31);
	movl	$31, %edi	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:54:     use_bit(32);
	movl	$32, %edi	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:55:     use_bit(63);
	movl	$63, %edi	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:57:     puts("PASS: bit operations are visible after inline asm");
	leaq	.LC1(%rip), %rdi	#, tmp85
	call	puts@PLT	#
# sources/bitmap_inline_asm.c:59: }
	xorl	%eax, %eax	#
	addq	$8, %rsp	#,
	.cfi_def_cfa_offset 8
	ret
	.cfi_endproc
.LFE55:
	.size	main, .-main
	.local	bitmap
	.comm	bitmap,16,16
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	1f - 0f
	.long	4f - 1f
	.long	5
0:
	.string	"GNU"
1:
	.align 8
	.long	0xc0000002
	.long	3f - 2f
2:
	.long	0x3
3:
	.align 8
4:
