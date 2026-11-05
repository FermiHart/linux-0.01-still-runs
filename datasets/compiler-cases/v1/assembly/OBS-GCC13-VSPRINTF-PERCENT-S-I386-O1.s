	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O1 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	"(null)"
	.text
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
	subl	$28, %esp	#,
	.cfi_def_cfa_offset 48
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
	movl	48(%esp), %esi	# buf, buf
	movl	52(%esp), %edx	# fmtstr, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	(%edx), %eax	# *fmtstr_5(D), _10
	testb	%al, %al	# _10
	je	.L22	#,
	leal	56(%esp), %ecx	#, args
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movl	%esi, %ebp	# buf, str
	jmp	.L20	#
.L38:
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%al, 0(%ebp)	# _10, *str_105
# sources/vsprintf_percent_s.c:32:             continue;
	movl	%edx, %esi	# fmtstr, p
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	leal	1(%ebp), %ebp	#, str
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leal	1(%esi), %edx	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%esi), %eax	# MEM[(const char *)p_64 + 1B], _10
	testb	%al, %al	# _10
	je	.L37	#,
.L20:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %al	#, _10
	jne	.L38	#,
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, 1(%edx)	#, MEM[(const char *)p_107 + 1B]
	je	.L5	#,
# sources/vsprintf_percent_s.c:34:         ++p;
	leal	1(%edx), %esi	#, p
	movl	$0, (%esp)	#, %sfp
.L6:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movzbl	(%esi), %eax	# *p_17, _25
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	leal	-48(%eax), %edx	#, tmp120
	movl	$0, %edi	#, field_width
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$9, %dl	#, tmp120
	jbe	.L8	#,
.L7:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movzbl	(%esi), %eax	# *p_31, tmp127
	andl	$-33, %eax	#, tmp127
# sources/vsprintf_percent_s.c:45:             ++p;
	cmpb	$76, %al	#, tmp127
	sete	%al	#, tmp133
	movzbl	%al, %eax	# tmp133, tmp133
	addl	%eax, %esi	# tmp133, p
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movzbl	(%esi), %eax	# *p_37, _38
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpb	$115, %al	#, _38
	je	.L39	#,
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%al, 0(%ebp)	# _38, *str_105
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	leal	1(%ebp), %ebp	#, str
# sources/vsprintf_percent_s.c:64:             break;
	jmp	.L4	#
.L5:
# sources/vsprintf_percent_s.c:37:             ++p;
	leal	2(%edx), %esi	#, p
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	movl	$16, (%esp)	#, %sfp
	jmp	.L6	#
.L8:
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addl	$1, %esi	#, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	(%edi,%edi,4), %edx	#, tmp123
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movsbl	%al, %eax	# _25, _25
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	-48(%eax,%edx,2), %edi	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movzbl	(%esi), %eax	# MEM[(const char *)p_24], _25
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	leal	-48(%eax), %edx	#, tmp126
	cmpb	$9, %dl	#, tmp126
	jbe	.L8	#,
	jmp	.L7	#
.L39:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	leal	4(%ecx), %eax	#, D.3219
	movl	%eax, 8(%esp)	# D.3219, %sfp
	movl	(%ecx), %eax	# MEM[(char * *)args_76], s
	movl	%eax, 4(%esp)	# s, %sfp
# sources/vsprintf_percent_s.c:50:             if (!s)
	testl	%eax, %eax	# s
	je	.L11	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	subl	$12, %esp	#,
	.cfi_def_cfa_offset 60
	pushl	%eax	# s
	.cfi_def_cfa_offset 64
	call	strlen@PLT	#
	addl	$16, %esp	#,
	.cfi_def_cfa_offset 48
	movl	%eax, %ecx	# tmp130, _112
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, %edx	# tmp130, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	cmpl	$0, (%esp)	#, %sfp
	je	.L12	#,
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%eax, %eax	# tmp130
	jle	.L21	#,
.L14:
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	movl	$0, %eax	#, i
	movl	%esi, 12(%esp)	# p, %sfp
	movl	4(%esp), %esi	# %sfp, s
	movl	%ecx, 4(%esp)	# _112, %sfp
.L18:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%esi,%eax), %ecx	# MEM[(char *)s_100 + _86 * 1], tmp172
	movb	%cl, 0(%ebp,%eax)	# tmp172, MEM[(char *)str_51 + _86 * 1]
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addl	$1, %eax	#, i
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	cmpl	%edx, %eax	# len, i
	jl	.L18	#,
	movl	12(%esp), %esi	# %sfp, p
	movl	4(%esp), %ecx	# %sfp, _112
	addl	%ecx, %ebp	# _112, str
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	8(%esp), %ecx	# %sfp, args
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	cmpl	$0, (%esp)	#, %sfp
	je	.L4	#,
.L21:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	%edx, %edi	# len, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	testl	%edi, %edi	# i
	jle	.L26	#,
	leal	0(%ebp,%edi), %eax	#, _91
.L19:
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	addl	$1, %ebp	#, str
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movb	$32, -1(%ebp)	#, MEM[(char *)str_60 + 4294967295B]
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	cmpl	%eax, %ebp	# _91, str
	jne	.L19	#,
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	8(%esp), %ecx	# %sfp, args
	movl	%eax, %ebp	# _91, str
	jmp	.L4	#
.L27:
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %edx	#, len
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, _112
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leal	.LC0@GOTOFF(%ebx), %eax	#, s
	movl	%eax, 4(%esp)	# s, %sfp
.L12:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	%edi, %eax	# field_width, i
	subl	%edx, %eax	# len, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	testl	%eax, %eax	# i
	jle	.L15	#,
	addl	%ebp, %eax	# str, _92
.L16:
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	addl	$1, %ebp	#, str
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movb	$32, -1(%ebp)	#, MEM[(char *)str_48 + 4294967295B]
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	cmpl	%eax, %ebp	# _92, str
	jne	.L16	#,
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	%eax, %ebp	# _92, str
	testl	%edx, %edx	# len
	jg	.L14	#,
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	8(%esp), %ecx	# %sfp, args
	jmp	.L4	#
.L26:
	movl	8(%esp), %ecx	# %sfp, args
	jmp	.L4	#
.L37:
	movl	48(%esp), %esi	# buf, buf
.L2:
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movb	$0, 0(%ebp)	#, *str_106
# sources/vsprintf_percent_s.c:70:     return str - buf;
	movl	%ebp, %eax	# str, str
	subl	%esi, %eax	# buf, str
# sources/vsprintf_percent_s.c:80: }
	addl	$28, %esp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 20
	popl	%ebx	#
	.cfi_restore 3
	.cfi_def_cfa_offset 16
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
.L22:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movl	%esi, %ebp	# buf, str
	jmp	.L2	#
.L15:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%edx, %edx	# len
	jg	.L14	#,
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	8(%esp), %ecx	# %sfp, args
	jmp	.L4	#
.L11:
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	cmpl	$0, (%esp)	#, %sfp
	je	.L27	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %edx	#, len
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, _112
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leal	.LC0@GOTOFF(%ebx), %eax	#, s
	movl	%eax, 4(%esp)	# s, %sfp
	jmp	.L14	#
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
	.text
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
	pushl	%esi	#
	pushl	%ebx	#
	pushl	%ecx	#
	.cfi_escape 0xf,0x3,0x75,0x74,0x6
	.cfi_escape 0x10,0x6,0x2,0x75,0x7c
	.cfi_escape 0x10,0x3,0x2,0x75,0x78
	subl	$288, %esp	#,
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/vsprintf_percent_s.c:83: {
	movl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp124
	movl	%eax, -28(%ebp)	# tmp124, D.3251
	xorl	%eax, %eax	# tmp124
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp90
	pushl	%eax	# tmp90
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp91
	pushl	%eax	# tmp91
	leal	-284(%ebp), %esi	#, tmp92
	pushl	%esi	# tmp92
	call	fmt	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	addl	$8, %esp	#,
	leal	.LC3@GOTOFF(%ebx), %eax	#, tmp94
	pushl	%eax	# tmp94
	pushl	%esi	# tmp92
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	testl	%eax, %eax	# tmp121
	jne	.L47	#,
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	subl	$4, %esp	#,
	leal	.LC5@GOTOFF(%ebx), %eax	#, tmp99
	pushl	%eax	# tmp99
	leal	.LC6@GOTOFF(%ebx), %eax	#, tmp100
	pushl	%eax	# tmp100
	leal	-284(%ebp), %esi	#, tmp101
	pushl	%esi	# tmp101
	call	fmt	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	addl	$8, %esp	#,
	leal	.LC7@GOTOFF(%ebx), %eax	#, tmp103
	pushl	%eax	# tmp103
	pushl	%esi	# tmp101
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# tmp122
	jne	.L48	#,
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	subl	$4, %esp	#,
	leal	.LC9@GOTOFF(%ebx), %eax	#, tmp108
	pushl	%eax	# tmp108
	leal	.LC10@GOTOFF(%ebx), %eax	#, tmp109
	pushl	%eax	# tmp109
	leal	-284(%ebp), %esi	#, tmp110
	pushl	%esi	# tmp110
	call	fmt	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	addl	$8, %esp	#,
	leal	.LC11@GOTOFF(%ebx), %eax	#, tmp112
	pushl	%eax	# tmp112
	pushl	%esi	# tmp110
	call	strcmp@PLT	#
	addl	$16, %esp	#,
	movl	%eax, %esi	# tmp123, <retval>
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# <retval>
	jne	.L49	#,
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	subl	$12, %esp	#,
	leal	.LC13@GOTOFF(%ebx), %eax	#, tmp117
	pushl	%eax	# tmp117
	call	puts@PLT	#
# sources/vsprintf_percent_s.c:105:     return 0;
	addl	$16, %esp	#,
	jmp	.L40	#
.L47:
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%esi	# tmp96
	leal	.LC4@GOTOFF(%ebx), %eax	#, tmp97
	pushl	%eax	# tmp97
	pushl	$2	#
# sources/vsprintf_percent_s.c:88:         fprintf(stderr, "FAIL: got '%s' expected '[hello]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp98
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:89:         return 1;
	addl	$16, %esp	#,
	movl	$1, %esi	#, <retval>
.L40:
# sources/vsprintf_percent_s.c:106: }
	movl	-28(%ebp), %eax	# D.3251, tmp125
	subl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp125
	jne	.L50	#,
	movl	%esi, %eax	# <retval>,
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
.L48:
	.cfi_restore_state
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	%esi	# tmp105
	leal	.LC8@GOTOFF(%ebx), %eax	#, tmp106
	pushl	%eax	# tmp106
	pushl	$2	#
# sources/vsprintf_percent_s.c:94:         fprintf(stderr, "FAIL: got '%s' expected '[      hi]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp107
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:95:         return 1;
	addl	$16, %esp	#,
	movl	$1, %esi	#, <retval>
	jmp	.L40	#
.L49:
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	leal	-284(%ebp), %eax	#, tmp114
	pushl	%eax	# tmp114
	leal	.LC12@GOTOFF(%ebx), %eax	#, tmp115
	pushl	%eax	# tmp115
	pushl	$2	#
# sources/vsprintf_percent_s.c:100:         fprintf(stderr, "FAIL: got '%s' expected '[ho      ]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp116
# ${MULTILIB_ROOT}/usr/include/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	pushl	(%eax)	# stderr
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:101:         return 1;
	addl	$16, %esp	#,
	movl	$1, %esi	#, <retval>
	jmp	.L40	#
.L50:
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
