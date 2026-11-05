	.file	"bitmap_inline_asm.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O1 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.section	.rodata.str1.4,"aMS",@progbits,1
	.align 4
.LC0:
	.string	"FAIL: bit %d not visible after set_bit; old=%d word=0x%lx\n"
	.text
	.type	use_bit, @function
use_bit:
.LFB54:
	.cfi_startproc
	pushl	%esi	#
	.cfi_def_cfa_offset 8
	.cfi_offset 6, -8
	pushl	%ebx	#
	.cfi_def_cfa_offset 12
	.cfi_offset 3, -12
	subl	$4, %esp	#,
	.cfi_def_cfa_offset 16
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
	movl	%eax, %edx	# tmp106, n
# sources/bitmap_inline_asm.c:34:     unsigned long *word = &bitmap[n / 32];
	leal	31(%eax), %ecx	#, tmp95
	testl	%eax, %eax	# n
	cmovns	%eax, %ecx	# tmp95,, n, n
	sarl	$5, %ecx	#, tmp96
# sources/bitmap_inline_asm.c:35:     int bit = n & 31;
	movl	%eax, %esi	# n, bit
	andl	$31, %esi	#, bit
# sources/bitmap_inline_asm.c:38:     old = set_bit(bit, word);
	movl	$0, %eax	#, res
#APP
# 38 "sources/bitmap_inline_asm.c" 1
	btsl %esi,bitmap@GOTOFF(%ebx,%ecx,4)	# bit, *word_7
	setb %al
# 0 "" 2
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
#NO_APP
	movl	bitmap@GOTOFF(%ebx,%ecx,4), %ecx	# MEM <long unsigned int[2]> [(long unsigned int *)&bitmap][_1], _2
# sources/bitmap_inline_asm.c:40:     if (!(*word & (1UL << bit))) {
	btl	%esi, %ecx	# bit, _2
	jnc	.L4	#,
# sources/bitmap_inline_asm.c:46: }
	addl	$4, %esp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 12
	popl	%ebx	#
	.cfi_restore 3
	.cfi_def_cfa_offset 8
	popl	%esi	#
	.cfi_restore 6
	.cfi_def_cfa_offset 4
	ret
.L4:
	.cfi_restore_state
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	subl	$8, %esp	#,
	.cfi_def_cfa_offset 24
	pushl	%ecx	# _2
	.cfi_def_cfa_offset 28
	pushl	%eax	# res
	.cfi_def_cfa_offset 32
	pushl	%edx	# n
	.cfi_def_cfa_offset 36
	leal	.LC0@GOTOFF(%ebx), %eax	#, tmp104
	pushl	%eax	# tmp104
	.cfi_def_cfa_offset 40
	pushl	$2	#
	.cfi_def_cfa_offset 44
# sources/bitmap_inline_asm.c:41:         fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp105
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	.cfi_def_cfa_offset 48
	call	__fprintf_chk@PLT	#
# sources/bitmap_inline_asm.c:44:         exit(1);
	addl	$20, %esp	#,
	.cfi_def_cfa_offset 28
	pushl	$1	#
	.cfi_def_cfa_offset 32
	call	exit@PLT	#
	.cfi_endproc
.LFE54:
	.size	use_bit, .-use_bit
	.section	.rodata.str1.4
	.align 4
.LC1:
	.string	"PASS: bit operations are visible after inline asm"
	.text
	.globl	main
	.type	main, @function
main:
.LFB55:
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
# ${MULTILIB_ROOT}/usr/include/bits/string_fortified.h:59:   return __builtin___memset_chk (__dest, __ch, __len,
	movl	$0, bitmap@GOTOFF(%ebx)	#, MEM <char[1:8]> [(void *)&bitmap]
	movl	$0, 4+bitmap@GOTOFF(%ebx)	#, MEM <char[1:8]> [(void *)&bitmap]
# sources/bitmap_inline_asm.c:52:     use_bit(0);
	movl	$0, %eax	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:53:     use_bit(31);
	movl	$31, %eax	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:54:     use_bit(32);
	movl	$32, %eax	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:55:     use_bit(63);
	movl	$63, %eax	#,
	call	use_bit	#
# sources/bitmap_inline_asm.c:57:     puts("PASS: bit operations are visible after inline asm");
	subl	$12, %esp	#,
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp87
	pushl	%eax	# tmp87
	call	puts@PLT	#
# sources/bitmap_inline_asm.c:58:     return 0;
	addl	$16, %esp	#,
# sources/bitmap_inline_asm.c:59: }
	movl	$0, %eax	#,
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
.LFE55:
	.size	main, .-main
	.local	bitmap
	.comm	bitmap,8,4
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB56:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE56:
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
