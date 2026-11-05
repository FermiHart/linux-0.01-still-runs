	.file	"bitmap_inline_asm.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.local	bitmap
	.comm	bitmap,16,16
	.section	.rodata
	.align 8
.LC0:
	.string	"FAIL: bit %d not visible after set_bit; old=%d word=0x%lx\n"
	.text
	.type	use_bit, @function
use_bit:
.LFB6:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
	pushq	%rbx	#
	subq	$40, %rsp	#,
	.cfi_offset 3, -24
	movl	%edi, -36(%rbp)	# n, n
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	movl	-36(%rbp), %eax	# n, tmp90
	leal	31(%rax), %edx	#, tmp92
	testl	%eax, %eax	# tmp91
	cmovs	%edx, %eax	# tmp92,, tmp91
	sarl	$5, %eax	#, tmp93
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	cltq
	leaq	0(,%rax,8), %rdx	#, tmp95
	leaq	bitmap(%rip), %rax	#, tmp96
	addq	%rdx, %rax	# tmp95, tmp97
	movq	%rax, -24(%rbp)	# tmp97, word
# sources/bitmap_inline_asm.c:35:     int bit = n & 31;
	movl	-36(%rbp), %eax	# n, tmp101
	andl	$31, %eax	#, tmp100
	movl	%eax, -32(%rbp)	# tmp100, bit
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	movl	$0, %eax	#, tmp103
	movl	-32(%rbp), %edx	# bit, tmp104
	movq	-24(%rbp), %rcx	# word, tmp105
#APP
# 38 "sources/bitmap_inline_asm.c" 1
	btsl %edx,(%rcx)	# tmp104, *word_8
	setb %al
# 0 "" 2
#NO_APP
	movl	%eax, %ebx	# res, res
	movl	%ebx, %eax	# res, _12
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	movl	%eax, -28(%rbp)	# _12, old
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	movq	-24(%rbp), %rax	# word, tmp106
	movq	(%rax), %rdx	# *word_8, _2
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	movl	-32(%rbp), %eax	# bit, tmp107
	movl	%eax, %ecx	# tmp107, tmp114
	shrq	%cl, %rdx	# tmp114, _2
	movq	%rdx, %rax	# _2, _3
	andl	$1, %eax	#, _4
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	testq	%rax, %rax	# _4
	jne	.L3	#,
# sources/bitmap_inline_asm.c:41:         fprintf(stderr,
	movq	-24(%rbp), %rax	# word, tmp108
	movq	(%rax), %rsi	# *word_8, _5
	movq	stderr(%rip), %rax	# stderr, stderr.0_6
	movl	-28(%rbp), %ecx	# old, tmp109
	movl	-36(%rbp), %edx	# n, tmp110
	movq	%rsi, %r8	# _5,
	leaq	.LC0(%rip), %rsi	#, tmp111
	movq	%rax, %rdi	# stderr.0_6,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/bitmap_inline_asm.c:44:         exit(1);
	movl	$1, %edi	#,
	call	exit@PLT	#
.L3:
# sources/bitmap_inline_asm.c:46: }
	nop
	movq	-8(%rbp), %rbx	#,
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE6:
	.size	use_bit, .-use_bit
	.section	.rodata
	.align 8
.LC1:
	.string	"PASS: bit operations are visible after inline asm"
	.text
	.globl	main
	.type	main, @function
main:
.LFB7:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
# sources/bitmap_inline_asm.c:50:     memset(bitmap, 0, sizeof(bitmap));
	movl	$16, %edx	#,
	movl	$0, %esi	#,
	leaq	bitmap(%rip), %rax	#, tmp84
	movq	%rax, %rdi	# tmp84,
	call	memset@PLT	#
# sources/bitmap_inline_asm.c:52:     use_bit(0);
	movl	$0, %edi	#,
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
	leaq	.LC1(%rip), %rax	#, tmp85
	movq	%rax, %rdi	# tmp85,
	call	puts@PLT	#
# sources/bitmap_inline_asm.c:58:     return 0;
	movl	$0, %eax	#, _8
# sources/bitmap_inline_asm.c:59: }
	popq	%rbp	#
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE7:
	.size	main, .-main
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
