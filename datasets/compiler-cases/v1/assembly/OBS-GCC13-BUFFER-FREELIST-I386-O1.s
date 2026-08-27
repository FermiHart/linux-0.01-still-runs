	.file	"buffer_freelist.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O1 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.type	get_node_original, @function
get_node_original:
.LFB40:
	.cfi_startproc
	call	__x86.get_pc_thunk.ax	#
	addl	$_GLOBAL_OFFSET_TABLE_, %eax	# tmp82,
# sources/buffer_freelist.c:55: 	struct node *tmp = free_list;
	movl	free_list@GOTOFF(%eax), %edx	# free_list, tmp
	movl	%edx, %eax	# tmp, <retval>
.L3:
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	cmpl	$0, (%eax)	#, tmp_2->used
	je	.L1	#,
# sources/buffer_freelist.c:60: 		tmp = tmp->next;
	movl	4(%eax), %eax	# tmp_2->next, <retval>
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpl	%eax, %edx	# <retval>, tmp
	jne	.L3	#,
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	movl	$0, %eax	#, <retval>
.L1:
# sources/buffer_freelist.c:63: }
	ret
	.cfi_endproc
.LFE40:
	.size	get_node_original, .-get_node_original
	.section	.rodata.str1.4,"aMS",@progbits,1
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
.LFB42:
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
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	leal	n1@GOTOFF(%ebx), %eax	#, tmp89
	movl	%eax, 4+n0@GOTOFF(%ebx)	# tmp89, n0.next
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	leal	n2@GOTOFF(%ebx), %eax	#, tmp91
	movl	%eax, 4+n1@GOTOFF(%ebx)	# tmp91, n1.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	leal	n0@GOTOFF(%ebx), %eax	#, tmp93
	movl	%eax, 4+n2@GOTOFF(%ebx)	# tmp93, n2.next
# sources/buffer_freelist.c:70: 	free_list = &n0;
	movl	%eax, free_list@GOTOFF(%ebx)	# tmp93, free_list
# sources/buffer_freelist.c:78: 	got = get_node_original();
	call	get_node_original	#
# sources/buffer_freelist.c:79: 	if (got != NULL) {
	testl	%eax, %eax	# got
	je	.L6	#,
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%eax	# got
	leal	.LC0@GOTOFF(%ebx), %eax	#, tmp95
	pushl	%eax	# tmp95
	pushl	$2	#
# sources/buffer_freelist.c:80: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp96
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/buffer_freelist.c:83: 		return 1;
	addl	$16, %esp	#,
	movl	$1, %eax	#, <retval>
.L5:
# sources/buffer_freelist.c:98: }
	leal	-8(%ebp), %esp	#,
	popl	%ecx	#
	.cfi_remember_state
	.cfi_restore 1
	.cfi_def_cfa 1, 0
	popl	%ebx	#
	.cfi_restore 3
	popl	%ebp	#
	.cfi_restore 5
	leal	-4(%ecx), %esp	#,
	.cfi_def_cfa 4, 4
	ret
.L6:
	.cfi_restore_state
# sources/buffer_freelist.c:87: 	n1.used = 0;
	movl	$0, n1@GOTOFF(%ebx)	#, n1.used
# sources/buffer_freelist.c:88: 	got = get_node_original();
	call	get_node_original	#
# sources/buffer_freelist.c:89: 	if (got != &n1) {
	leal	n1@GOTOFF(%ebx), %edx	#, tmp98
	cmpl	%edx, %eax	# tmp98, got
	je	.L8	#,
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	subl	$12, %esp	#,
	pushl	%eax	# got
	pushl	%edx	# tmp99
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp100
	pushl	%eax	# tmp100
	pushl	$2	#
# sources/buffer_freelist.c:90: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp101
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/buffer_freelist.c:93: 		return 1;
	addl	$32, %esp	#,
	movl	$1, %eax	#, <retval>
	jmp	.L5	#
.L8:
# sources/buffer_freelist.c:96: 	puts("PASS: free-list loop behaves as intended");
	subl	$12, %esp	#,
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp102
	pushl	%eax	# tmp102
	call	puts@PLT	#
# sources/buffer_freelist.c:97: 	return 0;
	addl	$16, %esp	#,
	movl	$0, %eax	#, <retval>
	jmp	.L5	#
	.cfi_endproc
.LFE42:
	.size	main, .-main
	.local	free_list
	.comm	free_list,4,4
	.data
	.align 4
	.type	n2, @object
	.size	n2, 8
n2:
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
	.type	n0, @object
	.size	n0, 8
n0:
# used:
	.long	1
# next:
	.long	0
	.section	.text.__x86.get_pc_thunk.ax,"axG",@progbits,__x86.get_pc_thunk.ax,comdat
	.globl	__x86.get_pc_thunk.ax
	.hidden	__x86.get_pc_thunk.ax
	.type	__x86.get_pc_thunk.ax, @function
__x86.get_pc_thunk.ax:
.LFB43:
	.cfi_startproc
	movl	(%esp), %eax	#,
	ret
	.cfi_endproc
.LFE43:
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB44:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE44:
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
