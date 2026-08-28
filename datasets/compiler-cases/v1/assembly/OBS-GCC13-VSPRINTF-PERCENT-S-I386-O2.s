	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O2 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	"(null)"
	.text
	.p2align 4
	.type	fmt, @function
fmt:
.LFB39:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	pushl	%edi	#
	.cfi_def_cfa_offset 12
	.cfi_offset 7, -12
	pushl	%esi	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	pushl	%ebx	#
	.cfi_def_cfa_offset 20
	.cfi_offset 3, -20
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
	subl	$44, %esp	#,
	.cfi_def_cfa_offset 64
# sources/vsprintf_percent_s.c:74: {
	movl	68(%esp), %ecx	# fmtstr, fmtstr
	movl	64(%esp), %esi	# buf, buf
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	(%ecx), %edx	# *fmtstr_5(D), _10
	testb	%dl, %dl	# _10
	je	.L20	#,
	leal	72(%esp), %eax	#, args
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movl	%esi, %ebp	# buf, str
	jmp	.L16	#
	.p2align 4,,10
	.p2align 3
.L33:
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%dl, 0(%ebp)	# _10, *str_105
# sources/vsprintf_percent_s.c:32:             continue;
	movl	%ecx, %esi	# fmtstr, p
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	addl	$1, %ebp	#, str
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%esi), %edx	# MEM[(const char *)p_63 + 1B], _10
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leal	1(%esi), %ecx	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	testb	%dl, %dl	# _10
	je	.L32	#,
.L16:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %dl	#, _10
	jne	.L33	#,
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	movsbl	1(%ecx), %edx	# MEM[(const char *)p_107 + 1B],
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, %dl	#, prephitmp_70
	je	.L5	#,
# sources/vsprintf_percent_s.c:34:         ++p;
	movl	$0, 12(%esp)	#, %sfp
	leal	1(%ecx), %esi	#, p
.L6:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	leal	-48(%edx), %ecx	#, tmp116
	xorl	%edi, %edi	# field_width
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$9, %cl	#, tmp116
	jbe	.L8	#,
.L7:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movl	%edx, %ecx	# prephitmp_70, tmp123
	andl	$-33, %ecx	#, tmp123
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$76, %cl	#, tmp123
	jne	.L9	#,
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movzbl	1(%esi), %edx	# MEM[(const char *)p_31 + 1B], prephitmp_70
# sources/vsprintf_percent_s.c:45:             ++p;
	addl	$1, %esi	#, p
.L9:
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpb	$115, %dl	#, prephitmp_70
	je	.L34	#,
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%dl, 0(%ebp)	# prephitmp_70, *str_105
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%esi), %edx	# MEM[(const char *)p_63 + 1B], _10
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	addl	$1, %ebp	#, str
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leal	1(%esi), %ecx	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	testb	%dl, %dl	# _10
	jne	.L16	#,
.L32:
	movl	64(%esp), %esi	# buf, buf
.L2:
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movb	$0, 0(%ebp)	#, *str_106
# sources/vsprintf_percent_s.c:70:     return str - buf;
	movl	%ebp, %eax	# str, str
# sources/vsprintf_percent_s.c:80: }
	addl	$44, %esp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 20
	popl	%ebx	#
	.cfi_restore 3
	.cfi_def_cfa_offset 16
# sources/vsprintf_percent_s.c:70:     return str - buf;
	subl	%esi, %eax	# buf, str
# sources/vsprintf_percent_s.c:80: }
	popl	%esi	#
	.cfi_restore 6
	.cfi_def_cfa_offset 12
	popl	%edi	#
	.cfi_restore 7
	.cfi_def_cfa_offset 8
	popl	%ebp	#
	.cfi_restore 5
	.cfi_def_cfa_offset 4
	ret
	.p2align 4,,10
	.p2align 3
.L8:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	(%edi,%edi,4), %ecx	#, tmp119
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addl	$1, %esi	#, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	-48(%edx,%ecx,2), %edi	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movsbl	(%esi), %edx	# MEM[(const char *)p_24],
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	leal	-48(%edx), %ecx	#, tmp122
	cmpb	$9, %cl	#, tmp122
	jbe	.L8	#,
	jmp	.L7	#
	.p2align 4,,10
	.p2align 3
.L5:
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	movl	$16, 12(%esp)	#, %sfp
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movsbl	2(%ecx), %edx	# MEM[(const char *)p_107 + 2B],
# sources/vsprintf_percent_s.c:37:             ++p;
	leal	2(%ecx), %esi	#, p
	jmp	.L6	#
.L34:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	(%eax), %edx	# MEM[(char * *)args_77], s
	leal	4(%eax), %ecx	#, D.3219
	movl	%ecx, 20(%esp)	# D.3219, %sfp
# sources/vsprintf_percent_s.c:50:             if (!s)
	testl	%edx, %edx	# s
	je	.L11	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	subl	$12, %esp	#,
	.cfi_def_cfa_offset 76
	pushl	%edx	# s
	.cfi_def_cfa_offset 80
	movl	%edx, 24(%esp)	# s, %sfp
	call	strlen@PLT	#
	addl	$16, %esp	#,
	.cfi_def_cfa_offset 64
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	movl	8(%esp), %edx	# %sfp, s
	cmpl	$0, 12(%esp)	#, %sfp
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, 16(%esp)	# _41, %sfp
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, %ecx	# _41, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	je	.L19	#,
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	cmpl	$0, 16(%esp)	#, %sfp
	je	.L18	#,
.L14:
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	movl	%ecx, 8(%esp)	# len, %sfp
	xorl	%eax, %eax	# i
	.p2align 4,,10
	.p2align 3
.L15:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%edx,%eax), %ecx	# MEM[(char *)s_94 + _92 * 1], tmp154
	movb	%cl, 0(%ebp,%eax)	# tmp154, MEM[(char *)str_50 + _92 * 1]
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addl	$1, %eax	#, i
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	cmpl	%eax, 8(%esp)	# i, %sfp
	jg	.L15	#,
	movl	16(%esp), %eax	# %sfp, _41
	movl	8(%esp), %ecx	# %sfp, len
	addl	%eax, %ebp	# _41, str
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	cmpl	$0, 12(%esp)	#, %sfp
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	20(%esp), %eax	# %sfp, args
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	je	.L4	#,
.L18:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	%ecx, %edi	# len, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	testl	%edi, %edi	# i
	jle	.L23	#,
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	pushl	%eax	#
	.cfi_def_cfa_offset 68
	pushl	%edi	# i
	.cfi_def_cfa_offset 72
	pushl	$32	#
	.cfi_def_cfa_offset 76
	pushl	%ebp	# str
	.cfi_def_cfa_offset 80
	addl	%edi, %ebp	# i, str
	call	memset@PLT	#
	addl	$16, %esp	#,
	.cfi_def_cfa_offset 64
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	20(%esp), %eax	# %sfp, args
	jmp	.L4	#
.L11:
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	cmpl	$0, 12(%esp)	#, %sfp
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, 16(%esp)	#, %sfp
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, len
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leal	.LC0@GOTOFF(%ebx), %edx	#, s
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	jne	.L14	#,
.L19:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	%edi, %eax	# field_width, i
	subl	%ecx, %eax	# len, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	testl	%eax, %eax	# i
	jle	.L13	#,
	movl	%edx, 24(%esp)	# s, %sfp
	movl	%ecx, 28(%esp)	# len, %sfp
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	pushl	%edx	#
	.cfi_def_cfa_offset 68
	movl	%eax, 12(%esp)	# i, %sfp
	pushl	%eax	#
	.cfi_def_cfa_offset 72
	pushl	$32	#
	.cfi_def_cfa_offset 76
	pushl	%ebp	# str
	.cfi_def_cfa_offset 80
	call	memset@PLT	#
	movl	24(%esp), %eax	# %sfp, i
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	44(%esp), %ecx	# %sfp, len
	addl	$16, %esp	#,
	.cfi_def_cfa_offset 64
	movl	24(%esp), %edx	# %sfp, s
	addl	%eax, %ebp	# i, str
	testl	%ecx, %ecx	# len
	jne	.L14	#,
.L23:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	20(%esp), %eax	# %sfp, args
	jmp	.L4	#
.L20:
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movl	%esi, %ebp	# buf, str
	jmp	.L2	#
.L13:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%ecx, %ecx	# len
	jne	.L14	#,
	jmp	.L23	#
	.cfi_endproc
.LFE39:
	.size	fmt, .-fmt
	.section	.rodata.str1.1
.LC1:
	.string	"hello"
.LC2:
	.string	"[%s]"
.LC3:
	.string	"[hello]"
	.section	.rodata.str1.4,"aMS",@progbits,1
	.align 4
.LC4:
	.string	"FAIL: got '%s' expected '[hello]'\n"
	.section	.rodata.str1.1
.LC5:
	.string	"hi"
.LC6:
	.string	"[%8s]"
.LC7:
	.string	"[      hi]"
	.section	.rodata.str1.4
	.align 4
.LC8:
	.string	"FAIL: got '%s' expected '[      hi]'\n"
	.section	.rodata.str1.1
.LC9:
	.string	"ho"
.LC10:
	.string	"[%-8s]"
.LC11:
	.string	"[ho      ]"
	.section	.rodata.str1.4
	.align 4
.LC12:
	.string	"FAIL: got '%s' expected '[ho      ]'\n"
	.align 4
.LC13:
	.string	"PASS: %s formatting reads the correct argument slot"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB40:
	.cfi_startproc
	leal	4(%esp), %ecx	#,
	.cfi_def_cfa 1, 0
	andl	$-16, %esp	#,
	pushl	-4(%ecx)	#
	pushl	%ebp	#
	movl	%esp, %ebp	#,
	.cfi_escape 0x10,0x5,0x2,0x75,0
	pushl	%edi	#
	pushl	%esi	#
	.cfi_escape 0x10,0x7,0x2,0x75,0x7c
	.cfi_escape 0x10,0x6,0x2,0x75,0x78
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	leal	-284(%ebp), %esi	#, tmp127
# sources/vsprintf_percent_s.c:83: {
	pushl	%ebx	#
	.cfi_escape 0x10,0x3,0x2,0x75,0x74
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
	pushl	%ecx	#
	.cfi_escape 0xf,0x3,0x75,0x70,0x6
	subl	$284, %esp	#,
# sources/vsprintf_percent_s.c:83: {
	movl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp130
	movl	%eax, -28(%ebp)	# tmp130, D.3243
	xorl	%eax, %eax	# tmp130
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp90
	pushl	%eax	# tmp90
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp91
	pushl	%eax	# tmp91
	pushl	%esi	# tmp127
	call	fmt	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	addl	$16, %esp	#,
	cmpl	$1818585179, -284(%ebp)	#, MEM <char[1:8]> [(void *)&buf]
	je	.L47	#,
.L36:
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%esi	# tmp127
	leal	.LC4@GOTOFF(%ebx), %eax	#, tmp95
.L46:
	pushl	%eax	# tmp108
# sources/vsprintf_percent_s.c:94:         fprintf(stderr, "FAIL: got '%s' expected '[      hi]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp109
# sources/vsprintf_percent_s.c:89:         return 1;
	movl	$1, %edi	#, <retval>
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	$2	#
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:95:         return 1;
	addl	$16, %esp	#,
.L35:
# sources/vsprintf_percent_s.c:106: }
	movl	-28(%ebp), %eax	# D.3243, tmp131
	subl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp131
	jne	.L48	#,
	leal	-16(%ebp), %esp	#,
	movl	%edi, %eax	# <retval>,
	popl	%ecx	#
	.cfi_remember_state
	.cfi_restore 1
	.cfi_def_cfa 1, 0
	popl	%ebx	#
	.cfi_restore 3
	popl	%esi	#
	.cfi_restore 6
	popl	%edi	#
	.cfi_restore 7
	popl	%ebp	#
	.cfi_restore 5
	leal	-4(%ecx), %esp	#,
	.cfi_def_cfa 4, 4
	ret
.L47:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	cmpl	$6123372, -280(%ebp)	#, MEM <char[1:8]> [(void *)&buf]
	jne	.L36	#,
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	leal	.LC5@GOTOFF(%ebx), %eax	#, tmp97
	pushl	%edi	#
	pushl	%eax	# tmp97
	leal	.LC6@GOTOFF(%ebx), %eax	#, tmp98
	pushl	%eax	# tmp98
	pushl	%esi	# tmp127
	call	fmt	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	popl	%eax	#
	leal	.LC7@GOTOFF(%ebx), %eax	#, tmp103
	popl	%edx	#
	pushl	%eax	# tmp103
	pushl	%esi	# tmp127
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# tmp128
	jne	.L49	#,
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	pushl	%eax	#
	leal	.LC9@GOTOFF(%ebx), %eax	#, tmp110
	pushl	%eax	# tmp110
	leal	.LC10@GOTOFF(%ebx), %eax	#, tmp111
	pushl	%eax	# tmp111
	pushl	%esi	# tmp127
	call	fmt	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	leal	.LC11@GOTOFF(%ebx), %eax	#, tmp116
	popl	%edx	#
	popl	%ecx	#
	pushl	%eax	# tmp116
	pushl	%esi	# tmp127
	call	strcmp@PLT	#
	addl	$16, %esp	#,
	movl	%eax, %edi	# tmp129, <retval>
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# <retval>
	jne	.L50	#,
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	subl	$12, %esp	#,
	leal	.LC13@GOTOFF(%ebx), %eax	#, tmp123
	pushl	%eax	# tmp123
	call	puts@PLT	#
# sources/vsprintf_percent_s.c:105:     return 0;
	addl	$16, %esp	#,
	jmp	.L35	#
.L49:
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%esi	# tmp127
	leal	.LC8@GOTOFF(%ebx), %eax	#, tmp108
	jmp	.L46	#
.L50:
	pushl	%esi	# tmp127
	leal	.LC12@GOTOFF(%ebx), %eax	#, tmp121
	jmp	.L46	#
.L48:
# sources/vsprintf_percent_s.c:106: }
	call	__stack_chk_fail_local	#
	.cfi_endproc
.LFE40:
	.size	main, .-main
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB41:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE41:
	.hidden	__stack_chk_fail_local
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
