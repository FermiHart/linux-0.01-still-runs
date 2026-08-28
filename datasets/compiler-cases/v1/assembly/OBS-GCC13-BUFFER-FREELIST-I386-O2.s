	.file	"buffer_freelist.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O2 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.p2align 4
	.type	get_node_original, @function
get_node_original:
.LFB40:
	.cfi_startproc
	call	__x86.get_pc_thunk.ax	#
	addl	$_GLOBAL_OFFSET_TABLE_, %eax	# tmp82,
# sources/buffer_freelist.c:55: 	struct node *tmp = free_list;
	movl	free_list@GOTOFF(%eax), %edx	# free_list, tmp
	movl	%edx, %eax	# tmp, <retval>
	jmp	.L3	#
	.p2align 4,,10
	.p2align 3
.L7:
# sources/buffer_freelist.c:60: 		tmp = tmp->next;
	movl	4(%eax), %eax	# tmp_2->next, <retval>
# sources/buffer_freelist.c:61: 	} while (tmp != free_list || (tmp = NULL));
	cmpl	%eax, %edx	# <retval>, tmp
	je	.L6	#,
.L3:
# sources/buffer_freelist.c:58: 		if (!tmp->used)
	movl	(%eax), %ecx	# tmp_2->used,
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
	.section	.text.startup,"ax",@progbits
	.p2align 4
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
	pushl	%esi	#
	pushl	%ebx	#
	.cfi_escape 0x10,0x6,0x2,0x75,0x7c
	.cfi_escape 0x10,0x3,0x2,0x75,0x78
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
	pushl	%ecx	#
	.cfi_escape 0xf,0x3,0x75,0x74,0x6
	subl	$12, %esp	#,
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	leal	n2@GOTOFF(%ebx), %eax	#, tmp91
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	leal	n1@GOTOFF(%ebx), %esi	#, tmp89
# sources/buffer_freelist.c:68: 	n1.next = &n2;
	movl	%eax, 4+n1@GOTOFF(%ebx)	# tmp91, n1.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	leal	n0@GOTOFF(%ebx), %eax	#, tmp93
# sources/buffer_freelist.c:67: 	n0.next = &n1;
	movl	%esi, 4+n0@GOTOFF(%ebx)	# tmp89, n0.next
# sources/buffer_freelist.c:69: 	n2.next = &n0;
	movl	%eax, 4+n2@GOTOFF(%ebx)	# tmp93, n2.next
# sources/buffer_freelist.c:70: 	free_list = &n0;
	movl	%eax, free_list@GOTOFF(%ebx)	# tmp93, free_list
# sources/buffer_freelist.c:78: 	got = get_node_original();
	call	get_node_original	#
# sources/buffer_freelist.c:79: 	if (got != NULL) {
	testl	%eax, %eax	# got
	je	.L9	#,
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%eax	# got
	leal	.LC0@GOTOFF(%ebx), %eax	#, tmp95
	pushl	%eax	# tmp95
# sources/buffer_freelist.c:80: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp96
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	$2	#
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/buffer_freelist.c:83: 		return 1;
	addl	$16, %esp	#,
.L10:
	movl	$1, %eax	#, <retval>
.L8:
# sources/buffer_freelist.c:98: }
	leal	-12(%ebp), %esp	#,
	popl	%ecx	#
	.cfi_remember_state
	.cfi_restore 1
	.cfi_def_cfa 1, 0
	popl	%ebx	#
	.cfi_restore 3
	popl	%esi	#
	.cfi_restore 6
	popl	%ebp	#
	.cfi_restore 5
	leal	-4(%ecx), %esp	#,
	.cfi_def_cfa 4, 4
	ret
.L9:
	.cfi_restore_state
# sources/buffer_freelist.c:87: 	n1.used = 0;
	xorl	%eax, %eax	#
	movl	%eax, n1@GOTOFF(%ebx)	#, n1.used
# sources/buffer_freelist.c:88: 	got = get_node_original();
	call	get_node_original	#
# sources/buffer_freelist.c:89: 	if (got != &n1) {
	cmpl	%esi, %eax	# tmp89, got
	je	.L11	#,
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	subl	$12, %esp	#,
	pushl	%eax	# got
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp100
	pushl	%esi	# tmp89
	pushl	%eax	# tmp100
# sources/buffer_freelist.c:90: 		fprintf(stderr,
	movl	stderr@GOT(%ebx), %eax	#, tmp101
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	$2	#
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/buffer_freelist.c:93: 		return 1;
	addl	$32, %esp	#,
	jmp	.L10	#
.L11:
# sources/buffer_freelist.c:96: 	puts("PASS: free-list loop behaves as intended");
	subl	$12, %esp	#,
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp102
	pushl	%eax	# tmp102
	call	puts@PLT	#
# sources/buffer_freelist.c:97: 	return 0;
	addl	$16, %esp	#,
	xorl	%eax, %eax	# <retval>
	jmp	.L8	#
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
