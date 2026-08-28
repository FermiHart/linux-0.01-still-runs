	.file	"buffer_freelist.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.data
	.align 4
	.type	n0, @object
	.size	n0, 8
n0:
# used:
	.long	1
# next:
	.long	0
	.align 4
	.type	n1, @object
	.size	n1, 8
n1:
# used:
	.long	1
# next:
	.long	0
	.align 4
	.type	n2, @object
	.size	n2, 8
n2:
# used:
	.long	1
# next:
	.long	0
	.local	free_list
	.comm	free_list,4,4
	.text
	.type	get_node_original, @function
get_node_original:
.LFB6:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	movl	%esp, %ebp	#,
	.cfi_def_cfa_register 5
	subl	$16, %esp	#,
	call	__x86.get_pc_thunk.ax	#
	addl	$_GLOBAL_OFFSET_TABLE_, %eax	# tmp82,
# sources/buffer_freelist.c:55: 	struct node *tmp = free_list;
	movl	free_list@GOTOFF(%eax), %edx	# free_list, tmp87
	movl	%edx, -4(%ebp)	# tmp87, tmp
.L4:
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	movl	-4(%ebp), %edx	# tmp, tmp88
	movl	(%edx), %edx	# tmp_3->used, _1
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	testl	%edx, %edx	# _1
	je	.L7	#,
# sources/buffer_freelist.c:60: 		tmp = tmp->next;
	movl	-4(%ebp), %edx	# tmp, tmp89
	movl	4(%edx), %edx	# tmp_3->next, tmp90
	movl	%edx, -4(%ebp)	# tmp90, tmp
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	movl	free_list@GOTOFF(%eax), %edx	# free_list, free_list.0_2
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpl	%edx, -4(%ebp)	# free_list.0_2, tmp
	jne	.L4	#,
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	movl	$0, -4(%ebp)	#, tmp
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpl	$0, -4(%ebp)	#, tmp
	jne	.L4	#,
	jmp	.L3	#
.L7:
# sources/buffer_freelist.c:59: 			break;
	nop
.L3:
# sources/buffer_freelist.c:62: 	return tmp;
	movl	-4(%ebp), %eax	# tmp, _9
# sources/buffer_freelist.c:63: }
	leave
	.cfi_restore 5
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE6:
	.size	get_node_original, .-get_node_original
	.type	setup, @function
setup:
.LFB7:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	movl	%esp, %ebp	#,
	.cfi_def_cfa_register 5
	call	__x86.get_pc_thunk.ax	#
	addl	$_GLOBAL_OFFSET_TABLE_, %eax	# tmp82,
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	leal	n1@GOTOFF(%eax), %edx	#, tmp83
	movl	%edx, 4+n0@GOTOFF(%eax)	# tmp83, n0.next
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	leal	n2@GOTOFF(%eax), %edx	#, tmp84
	movl	%edx, 4+n1@GOTOFF(%eax)	# tmp84, n1.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	leal	n0@GOTOFF(%eax), %edx	#, tmp85
	movl	%edx, 4+n2@GOTOFF(%eax)	# tmp85, n2.next
# sources/buffer_freelist.c:70: 	free_list = &n0;
	leal	n0@GOTOFF(%eax), %edx	#, tmp86
	movl	%edx, free_list@GOTOFF(%eax)	# tmp86, free_list
# sources/buffer_freelist.c:71: }
	nop
	popl	%ebp	#
	.cfi_restore 5
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE7:
	.size	setup, .-setup
	.section	.rodata
	.align 4
.LC0:
	.string	"FAIL: expected NULL for a fully-used list, got %p\n"
	.align 4
.LC1:
	.string	"FAIL: expected node n1 (%p), got %p\n"
	.align 4
.LC2:
	.string	"PASS: free-list loop behaves as intended"
	.text
	.globl	main
	.type	main, @function
main:
.LFB8:
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
	subl	$16, %esp	#,
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/buffer_freelist.c:77: 	setup();
	call	setup	#
# sources/buffer_freelist.c:78: 	got = get_node_original();
	call	get_node_original	#
	movl	%eax, -12(%ebp)	# tmp87, got
# sources/buffer_freelist.c:79: 	if (got != NULL) {
	cmpl	$0, -12(%ebp)	#, got
	je	.L10	#,
# sources/buffer_freelist.c:80: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp88
	movl	(%eax), %eax	# stderr, stderr.1_1
	subl	$4, %esp	#,
	pushl	-12(%ebp)	# got
	leal	.LC0@GOTOFF(%ebx), %edx	#, tmp89
	pushl	%edx	# tmp89
	pushl	%eax	# stderr.1_1
	call	fprintf@PLT	#
	addl	$16, %esp	#,
# sources/buffer_freelist.c:83: 		return 1;
	movl	$1, %eax	#, _3
	jmp	.L11	#
.L10:
# sources/buffer_freelist.c:87: 	n1.used = 0;
	movl	$0, n1@GOTOFF(%ebx)	#, n1.used
# sources/buffer_freelist.c:88: 	got = get_node_original();
	call	get_node_original	#
	movl	%eax, -12(%ebp)	# tmp90, got
# sources/buffer_freelist.c:89: 	if (got != &n1) {
	leal	n1@GOTOFF(%ebx), %eax	#, tmp91
	cmpl	%eax, -12(%ebp)	# tmp91, got
	je	.L12	#,
# sources/buffer_freelist.c:90: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp92
	movl	(%eax), %eax	# stderr, stderr.2_2
	pushl	-12(%ebp)	# got
	leal	n1@GOTOFF(%ebx), %edx	#, tmp93
	pushl	%edx	# tmp93
	leal	.LC1@GOTOFF(%ebx), %edx	#, tmp94
	pushl	%edx	# tmp94
	pushl	%eax	# stderr.2_2
	call	fprintf@PLT	#
	addl	$16, %esp	#,
# sources/buffer_freelist.c:93: 		return 1;
	movl	$1, %eax	#, _3
	jmp	.L11	#
.L12:
# sources/buffer_freelist.c:96: 	puts("PASS: free-list loop behaves as intended");
	subl	$12, %esp	#,
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp95
	pushl	%eax	# tmp95
	call	puts@PLT	#
	addl	$16, %esp	#,
# sources/buffer_freelist.c:97: 	return 0;
	movl	$0, %eax	#, _3
.L11:
# sources/buffer_freelist.c:98: }
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
.LFE8:
	.size	main, .-main
	.section	.text.__x86.get_pc_thunk.ax,"axG",@progbits,__x86.get_pc_thunk.ax,comdat
	.globl	__x86.get_pc_thunk.ax
	.hidden	__x86.get_pc_thunk.ax
	.type	__x86.get_pc_thunk.ax, @function
__x86.get_pc_thunk.ax:
.LFB9:
	.cfi_startproc
	movl	(%esp), %eax	#,
	ret
	.cfi_endproc
.LFE9:
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB10:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE10:
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
