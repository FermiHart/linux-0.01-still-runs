	.file	"buffer_freelist.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.data
	.align 16
	.type	n0, @object
	.size	n0, 16
n0:
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
	.type	n2, @object
	.size	n2, 16
n2:
# used:
	.long	1
# next:
	.zero	4
	.quad	0
	.local	free_list
	.comm	free_list,8,8
	.text
	.type	get_node_original, @function
get_node_original:
.LFB6:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
# sources/buffer_freelist.c:55: 	struct node *tmp = free_list;
	movq	free_list(%rip), %rax	# free_list, tmp86
	movq	%rax, -8(%rbp)	# tmp86, tmp
.L4:
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	movq	-8(%rbp), %rax	# tmp, tmp87
	movl	(%rax), %eax	# tmp_3->used, _1
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	testl	%eax, %eax	# _1
	je	.L7	#,
# sources/buffer_freelist.c:60: 		tmp = tmp->next;
	movq	-8(%rbp), %rax	# tmp, tmp88
	movq	8(%rax), %rax	# tmp_3->next, tmp89
	movq	%rax, -8(%rbp)	# tmp89, tmp
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	movq	free_list(%rip), %rax	# free_list, free_list.0_2
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpq	%rax, -8(%rbp)	# free_list.0_2, tmp
	jne	.L4	#,
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	movq	$0, -8(%rbp)	#, tmp
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpq	$0, -8(%rbp)	#, tmp
	jne	.L4	#,
	jmp	.L3	#
.L7:
# sources/buffer_freelist.c:59: 			break;
	nop
.L3:
# sources/buffer_freelist.c:62: 	return tmp;
	movq	-8(%rbp), %rax	# tmp, _9
# sources/buffer_freelist.c:63: }
	popq	%rbp	#
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE6:
	.size	get_node_original, .-get_node_original
	.type	setup, @function
setup:
.LFB7:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	leaq	n1(%rip), %rax	#, tmp82
	movq	%rax, 8+n0(%rip)	# tmp82, n0.next
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	leaq	n2(%rip), %rax	#, tmp83
	movq	%rax, 8+n1(%rip)	# tmp83, n1.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	leaq	n0(%rip), %rax	#, tmp84
	movq	%rax, 8+n2(%rip)	# tmp84, n2.next
# sources/buffer_freelist.c:70: 	free_list = &n0;
	leaq	n0(%rip), %rax	#, tmp85
	movq	%rax, free_list(%rip)	# tmp85, free_list
# sources/buffer_freelist.c:71: }
	nop
	popq	%rbp	#
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE7:
	.size	setup, .-setup
	.section	.rodata
	.align 8
.LC0:
	.string	"FAIL: expected NULL for a fully-used list, got %p\n"
	.align 8
.LC1:
	.string	"FAIL: expected node n1 (%p), got %p\n"
	.align 8
.LC2:
	.string	"PASS: free-list loop behaves as intended"
	.text
	.globl	main
	.type	main, @function
main:
.LFB8:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
	subq	$16, %rsp	#,
# sources/buffer_freelist.c:77: 	setup();
	call	setup	#
# sources/buffer_freelist.c:78: 	got = get_node_original();
	call	get_node_original	#
	movq	%rax, -8(%rbp)	# tmp86, got
# sources/buffer_freelist.c:79: 	if (got != NULL) {
	cmpq	$0, -8(%rbp)	#, got
	je	.L10	#,
# sources/buffer_freelist.c:80: 		fprintf(stderr,
	movq	stderr(%rip), %rax	# stderr, stderr.1_1
	movq	-8(%rbp), %rdx	# got, tmp87
	leaq	.LC0(%rip), %rcx	#, tmp88
	movq	%rcx, %rsi	# tmp88,
	movq	%rax, %rdi	# stderr.1_1,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/buffer_freelist.c:83: 		return 1;
	movl	$1, %eax	#, _3
	jmp	.L11	#
.L10:
# sources/buffer_freelist.c:87: 	n1.used = 0;
	movl	$0, n1(%rip)	#, n1.used
# sources/buffer_freelist.c:88: 	got = get_node_original();
	call	get_node_original	#
	movq	%rax, -8(%rbp)	# tmp89, got
# sources/buffer_freelist.c:89: 	if (got != &n1) {
	leaq	n1(%rip), %rax	#, tmp90
	cmpq	%rax, -8(%rbp)	# tmp90, got
	je	.L12	#,
# sources/buffer_freelist.c:90: 		fprintf(stderr,
	movq	stderr(%rip), %rax	# stderr, stderr.2_2
	movq	-8(%rbp), %rdx	# got, tmp91
	movq	%rdx, %rcx	# tmp91,
	leaq	n1(%rip), %rdx	#, tmp92
	leaq	.LC1(%rip), %rsi	#, tmp93
	movq	%rax, %rdi	# stderr.2_2,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/buffer_freelist.c:93: 		return 1;
	movl	$1, %eax	#, _3
	jmp	.L11	#
.L12:
# sources/buffer_freelist.c:96: 	puts("PASS: free-list loop behaves as intended");
	leaq	.LC2(%rip), %rax	#, tmp94
	movq	%rax, %rdi	# tmp94,
	call	puts@PLT	#
# sources/buffer_freelist.c:97: 	return 0;
	movl	$0, %eax	#, _3
.L11:
# sources/buffer_freelist.c:98: }
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE8:
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
