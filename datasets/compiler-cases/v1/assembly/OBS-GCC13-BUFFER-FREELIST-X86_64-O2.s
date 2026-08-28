	.file	"buffer_freelist.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O2 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.p2align 4
	.type	get_node_original, @function
get_node_original:
.LFB40:
	.cfi_startproc
# sources/buffer_freelist.c:55: 	struct node *tmp = free_list;
	movq	free_list(%rip), %rdx	# free_list, tmp
	movq	%rdx, %rax	# tmp, <retval>
	jmp	.L3	#
	.p2align 4,,10
	.p2align 3
.L7:
# sources/buffer_freelist.c:60: 		tmp = tmp->next;
	movq	8(%rax), %rax	# tmp_2->next, <retval>
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpq	%rax, %rdx	# <retval>, tmp
	je	.L6	#,
.L3:
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	movl	(%rax), %ecx	# tmp_2->used,
	testl	%ecx, %ecx	#
	jne	.L7	#,
# sources/buffer_freelist.c:63: }
	ret
.L6:
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	xorl	%eax, %eax	# <retval>
# sources/buffer_freelist.c:63: }
	ret
	.cfi_endproc
.LFE40:
	.size	get_node_original, .-get_node_original
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC0:
	.string	"FAIL: expected NULL for a fully-used list, got %p\n"
	.align 8
.LC1:
	.string	"FAIL: expected node n1 (%p), got %p\n"
	.align 8
.LC2:
	.string	"PASS: free-list loop behaves as intended"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB42:
	.cfi_startproc
	endbr64
	subq	$8, %rsp	#,
	.cfi_def_cfa_offset 16
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	leaq	n0(%rip), %rax	#, tmp87
	leaq	n1(%rip), %rsi	#, tmp88
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	leaq	n2(%rip), %rcx	#, tmp106
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	movq	%rsi, 8+n0(%rip)	# tmp88, n0.next
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	movq	%rcx, 8+n1(%rip)	# tmp106, n1.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	movq	%rax, 8+n2(%rip)	# tmp87, n2.next
# sources/buffer_freelist.c:70: 	free_list = &n0;
	movq	%rax, free_list(%rip)	# tmp87, free_list
# sources/buffer_freelist.c:78: 	got = get_node_original();
	call	get_node_original	#
# sources/buffer_freelist.c:79: 	if (got != NULL) {
	testq	%rax, %rax	# got
	je	.L9	#,
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	stderr(%rip), %rdi	# stderr,
	movq	%rax, %rcx	# got,
	movl	$2, %esi	#,
	xorl	%eax, %eax	#
	leaq	.LC0(%rip), %rdx	#, tmp95
	call	__fprintf_chk@PLT	#
.L10:
# sources/buffer_freelist.c:83: 		return 1;
	movl	$1, %eax	#, <retval>
.L8:
# sources/buffer_freelist.c:98: }
	addq	$8, %rsp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 8
	ret
.L9:
	.cfi_restore_state
# sources/buffer_freelist.c:87: 	n1.used = 0;
	xorl	%eax, %eax	#
	movl	%eax, n1(%rip)	#, n1.used
# sources/buffer_freelist.c:88: 	got = get_node_original();
	call	get_node_original	#
	movq	%rax, %r8	# tmp104, got
# sources/buffer_freelist.c:89: 	if (got != &n1) {
	cmpq	%rsi, %rax	# tmp88, got
	je	.L11	#,
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	stderr(%rip), %rdi	# stderr,
	movq	%rsi, %rcx	# tmp88,
	leaq	.LC1(%rip), %rdx	#, tmp100
	xorl	%eax, %eax	#
	movl	$2, %esi	#,
	call	__fprintf_chk@PLT	#
# sources/buffer_freelist.c:93: 		return 1;
	jmp	.L10	#
.L11:
# sources/buffer_freelist.c:96: 	puts("PASS: free-list loop behaves as intended");
	leaq	.LC2(%rip), %rdi	#, tmp101
	call	puts@PLT	#
# sources/buffer_freelist.c:97: 	return 0;
	xorl	%eax, %eax	# <retval>
	jmp	.L8	#
	.cfi_endproc
.LFE42:
	.size	main, .-main
	.local	free_list
	.comm	free_list,8,8
	.data
	.align 16
	.type	n2, @object
	.size	n2, 16
n2:
# used:
	.long	1
# next:
	.zero	4
	.quad	0
	.align 16
	.type	n1, @object
	.size	n1, 16
n1:
# used:
	.long	1
# next:
	.zero	4
	.quad	0
	.align 16
	.type	n0, @object
	.size	n0, 16
n0:
# used:
	.long	1
# next:
	.zero	4
	.quad	0
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
