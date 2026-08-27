	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -m32 -mtune=generic -march=i686 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection
	.text
	.section	.rodata
.LC0:
	.string	"(null)"
	.text
	.type	mini_vsprintf, @function
mini_vsprintf:
.LFB0:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	movl	%esp, %ebp	#,
	.cfi_def_cfa_register 5
	pushl	%ebx	#
	subl	$36, %esp	#,
	.cfi_offset 3, -12
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movl	8(%ebp), %eax	# buf, tmp115
	movl	%eax, -36(%ebp)	# tmp115, str
# sources/vsprintf_percent_s.c:25:     int flags = 0;
	movl	$0, -24(%ebp)	#, flags
# sources/vsprintf_percent_s.c:26:     int field_width = 0;
	movl	$0, -20(%ebp)	#, field_width
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movl	12(%ebp), %eax	# fmt, tmp116
	movl	%eax, -16(%ebp)	# tmp116, p
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	jmp	.L2	#
.L22:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	movl	-16(%ebp), %eax	# p, tmp117
	movzbl	(%eax), %eax	# *p_54, _1
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %al	#, _1
	je	.L3	#,
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movl	-36(%ebp), %eax	# str, str.0_2
	leal	1(%eax), %edx	#, tmp118
	movl	%edx, -36(%ebp)	# tmp118, str
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movl	-16(%ebp), %edx	# p, tmp119
	movzbl	(%edx), %edx	# *p_54, _3
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%dl, (%eax)	# _3, *str.0_2
# sources/vsprintf_percent_s.c:32:             continue;
	jmp	.L4	#
.L3:
# sources/vsprintf_percent_s.c:34:         ++p;
	addl	$1, -16(%ebp)	#, p
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	movl	-16(%ebp), %eax	# p, tmp120
	movzbl	(%eax), %eax	# *p_72, _4
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, %al	#, _4
	jne	.L5	#,
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	orl	$16, -24(%ebp)	#, flags
# sources/vsprintf_percent_s.c:37:             ++p;
	addl	$1, -16(%ebp)	#, p
.L5:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movl	-16(%ebp), %eax	# p, tmp121
	movzbl	(%eax), %eax	# *p_49, _5
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$47, %al	#, _5
	jle	.L6	#,
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movl	-16(%ebp), %eax	# p, tmp122
	movzbl	(%eax), %eax	# *p_49, _6
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$57, %al	#, _6
	jg	.L6	#,
# sources/vsprintf_percent_s.c:40:             field_width = 0;
	movl	$0, -20(%ebp)	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	jmp	.L7	#
.L8:
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movl	-20(%ebp), %edx	# field_width, tmp123
	movl	%edx, %eax	# tmp123, tmp124
	sall	$2, %eax	#, tmp124
	addl	%edx, %eax	# tmp123, tmp124
	addl	%eax, %eax	# tmp125
	movl	%eax, %ecx	# tmp124, _7
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movl	-16(%ebp), %eax	# p, p.1_8
	leal	1(%eax), %edx	#, tmp126
	movl	%edx, -16(%ebp)	# tmp126, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movzbl	(%eax), %eax	# *p.1_8, _9
	movsbl	%al, %eax	# _9, _10
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addl	%ecx, %eax	# _7, _11
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	subl	$48, %eax	#, tmp127
	movl	%eax, -20(%ebp)	# tmp127, field_width
.L7:
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movl	-16(%ebp), %eax	# p, tmp128
	movzbl	(%eax), %eax	# *p_50, _12
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	cmpb	$47, %al	#, _12
	jle	.L6	#,
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movl	-16(%ebp), %eax	# p, tmp129
	movzbl	(%eax), %eax	# *p_50, _13
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	cmpb	$57, %al	#, _13
	jle	.L8	#,
.L6:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movl	-16(%ebp), %eax	# p, tmp130
	movzbl	(%eax), %eax	# *p_51, _14
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$108, %al	#, _14
	je	.L9	#,
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movl	-16(%ebp), %eax	# p, tmp131
	movzbl	(%eax), %eax	# *p_51, _15
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$76, %al	#, _15
	jne	.L10	#,
.L9:
# sources/vsprintf_percent_s.c:45:             ++p;
	addl	$1, -16(%ebp)	#, p
.L10:
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movl	-16(%ebp), %eax	# p, tmp132
	movzbl	(%eax), %eax	# *p_52, _16
	movsbl	%al, %eax	# _16, _17
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpl	$115, %eax	#, _17
	jne	.L11	#,
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	16(%ebp), %eax	# args, D.2897
	leal	4(%eax), %edx	#, D.2898
	movl	%edx, 16(%ebp)	# D.2898, args
	movl	(%eax), %eax	# MEM[(char * *)_103], tmp133
	movl	%eax, -32(%ebp)	# tmp133, s
# sources/vsprintf_percent_s.c:50:             if (!s)
	cmpl	$0, -32(%ebp)	#, s
	jne	.L12	#,
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leal	.LC0@GOTOFF(%ebx), %eax	#, tmp134
	movl	%eax, -32(%ebp)	# tmp134, s
.L12:
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	subl	$12, %esp	#,
	pushl	-32(%ebp)	# s
	call	strlen@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, -12(%ebp)	# _18, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	movl	-24(%ebp), %eax	# flags, tmp135
	andl	$16, %eax	#, _19
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%eax, %eax	# _19
	jne	.L13	#,
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	-20(%ebp), %eax	# field_width, tmp139
	subl	-12(%ebp), %eax	# len, tmp138
	movl	%eax, -28(%ebp)	# tmp138, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	jmp	.L14	#
.L15:
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movl	-36(%ebp), %eax	# str, str.2_20
	leal	1(%eax), %edx	#, tmp140
	movl	%edx, -36(%ebp)	# tmp140, str
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movb	$32, (%eax)	#, *str.2_20
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	subl	$1, -28(%ebp)	#, i
.L14:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	cmpl	$0, -28(%ebp)	#, i
	jg	.L15	#,
.L13:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	$0, -28(%ebp)	#, i
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	jmp	.L16	#
.L17:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movl	-32(%ebp), %edx	# s, s.3_21
	leal	1(%edx), %eax	#, tmp141
	movl	%eax, -32(%ebp)	# tmp141, s
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movl	-36(%ebp), %eax	# str, str.4_22
	leal	1(%eax), %ecx	#, tmp142
	movl	%ecx, -36(%ebp)	# tmp142, str
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%edx), %edx	# *s.3_21, _23
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movb	%dl, (%eax)	# _23, *str.4_22
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addl	$1, -28(%ebp)	#, i
.L16:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	-28(%ebp), %eax	# i, tmp143
	cmpl	-12(%ebp), %eax	# len, tmp143
	jl	.L17	#,
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	movl	-24(%ebp), %eax	# flags, tmp144
	andl	$16, %eax	#, _24
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	testl	%eax, %eax	# _24
	je	.L24	#,
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	movl	-20(%ebp), %eax	# field_width, tmp148
	subl	-12(%ebp), %eax	# len, tmp147
	movl	%eax, -28(%ebp)	# tmp147, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	jmp	.L19	#
.L20:
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movl	-36(%ebp), %eax	# str, str.5_25
	leal	1(%eax), %edx	#, tmp149
	movl	%edx, -36(%ebp)	# tmp149, str
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movb	$32, (%eax)	#, *str.5_25
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	$1, -28(%ebp)	#, i
.L19:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	cmpl	$0, -28(%ebp)	#, i
	jg	.L20	#,
# sources/vsprintf_percent_s.c:61:             break;
	jmp	.L24	#
.L11:
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movl	-36(%ebp), %eax	# str, str.6_26
	leal	1(%eax), %edx	#, tmp150
	movl	%edx, -36(%ebp)	# tmp150, str
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movl	-16(%ebp), %edx	# p, tmp151
	movzbl	(%edx), %edx	# *p_52, _27
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%dl, (%eax)	# _27, *str.6_26
# sources/vsprintf_percent_s.c:64:             break;
	jmp	.L21	#
.L24:
# sources/vsprintf_percent_s.c:61:             break;
	nop
.L21:
# sources/vsprintf_percent_s.c:66:         flags = 0;
	movl	$0, -24(%ebp)	#, flags
# sources/vsprintf_percent_s.c:67:         field_width = 0;
	movl	$0, -20(%ebp)	#, field_width
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	addl	$1, -16(%ebp)	#, p
.L2:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movl	-16(%ebp), %eax	# p, tmp152
	movzbl	(%eax), %eax	# *p_54, _28
	testb	%al, %al	# _28
	jne	.L22	#,
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movl	-36(%ebp), %eax	# str, tmp153
	movb	$0, (%eax)	#, *str_36
# sources/vsprintf_percent_s.c:70:     return str - buf;
	movl	-36(%ebp), %eax	# str, tmp154
	subl	8(%ebp), %eax	# buf, _71
# sources/vsprintf_percent_s.c:71: }
	movl	-4(%ebp), %ebx	#,
	leave
	.cfi_restore 5
	.cfi_restore 3
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE0:
	.size	mini_vsprintf, .-mini_vsprintf
	.type	fmt, @function
fmt:
.LFB1:
	.cfi_startproc
	pushl	%ebp	#
	.cfi_def_cfa_offset 8
	.cfi_offset 5, -8
	movl	%esp, %ebp	#,
	.cfi_def_cfa_register 5
	subl	$40, %esp	#,
	call	__x86.get_pc_thunk.ax	#
	addl	$_GLOBAL_OFFSET_TABLE_, %eax	# tmp82,
	movl	8(%ebp), %eax	# buf, tmp86
	movl	%eax, -28(%ebp)	# tmp86, buf
	movl	12(%ebp), %eax	# fmtstr, tmp87
	movl	%eax, -32(%ebp)	# tmp87, fmtstr
# sources/vsprintf_percent_s.c:74: {
	movl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp91
	movl	%eax, -12(%ebp)	# tmp91, D.2900
	xorl	%eax, %eax	# tmp91
# sources/vsprintf_percent_s.c:76:     va_start(args, fmtstr);
	leal	16(%ebp), %eax	#, tmp88
	movl	%eax, -20(%ebp)	# tmp88, MEM[(char * *)&args]
# sources/vsprintf_percent_s.c:77:     int n = mini_vsprintf(buf, fmtstr, args);
	movl	-20(%ebp), %eax	# args, args.7_1
	subl	$4, %esp	#,
	pushl	%eax	# args.7_1
	pushl	-32(%ebp)	# fmtstr
	pushl	-28(%ebp)	# buf
	call	mini_vsprintf	#
	addl	$16, %esp	#,
	movl	%eax, -16(%ebp)	# tmp89, n
# sources/vsprintf_percent_s.c:79:     return n;
	movl	-16(%ebp), %eax	# n, _9
# sources/vsprintf_percent_s.c:80: }
	movl	-12(%ebp), %edx	# D.2900, tmp92
	subl	%gs:20, %edx	# MEM[(<address-space-2> unsigned int *)20B], tmp92
	je	.L27	#,
	call	__stack_chk_fail_local	#
.L27:
	leave
	.cfi_restore 5
	.cfi_def_cfa 4, 4
	ret
	.cfi_endproc
.LFE1:
	.size	fmt, .-fmt
	.section	.rodata
.LC1:
	.string	"hello"
.LC2:
	.string	"[%s]"
.LC3:
	.string	"[hello]"
	.align 4
.LC4:
	.string	"FAIL: got '%s' expected '[hello]'\n"
.LC5:
	.string	"hi"
.LC6:
	.string	"[%8s]"
.LC7:
	.string	"[      hi]"
	.align 4
.LC8:
	.string	"FAIL: got '%s' expected '[      hi]'\n"
.LC9:
	.string	"ho"
.LC10:
	.string	"[%-8s]"
.LC11:
	.string	"[ho      ]"
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
.LFB2:
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
	subl	$272, %esp	#,
	call	__x86.get_pc_thunk.bx	#
	addl	$_GLOBAL_OFFSET_TABLE_, %ebx	# tmp82,
# sources/vsprintf_percent_s.c:83: {
	movl	%gs:20, %eax	# MEM[(<address-space-2> unsigned int *)20B], tmp118
	movl	%eax, -12(%ebp)	# tmp118, D.2902
	xorl	%eax, %eax	# tmp118
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	subl	$4, %esp	#,
	leal	.LC1@GOTOFF(%ebx), %eax	#, tmp91
	pushl	%eax	# tmp91
	leal	.LC2@GOTOFF(%ebx), %eax	#, tmp92
	pushl	%eax	# tmp92
	leal	-268(%ebp), %eax	#, tmp93
	pushl	%eax	# tmp93
	call	fmt	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	subl	$8, %esp	#,
	leal	.LC3@GOTOFF(%ebx), %eax	#, tmp94
	pushl	%eax	# tmp94
	leal	-268(%ebp), %eax	#, tmp95
	pushl	%eax	# tmp95
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	testl	%eax, %eax	# _1
	je	.L29	#,
# sources/vsprintf_percent_s.c:88:         fprintf(stderr, "FAIL: got '%s' expected '[hello]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp96
	movl	(%eax), %eax	# stderr, stderr.8_2
	subl	$4, %esp	#,
	leal	-268(%ebp), %edx	#, tmp97
	pushl	%edx	# tmp97
	leal	.LC4@GOTOFF(%ebx), %edx	#, tmp98
	pushl	%edx	# tmp98
	pushl	%eax	# stderr.8_2
	call	fprintf@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:89:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L33	#
.L29:
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	subl	$4, %esp	#,
	leal	.LC5@GOTOFF(%ebx), %eax	#, tmp99
	pushl	%eax	# tmp99
	leal	.LC6@GOTOFF(%ebx), %eax	#, tmp100
	pushl	%eax	# tmp100
	leal	-268(%ebp), %eax	#, tmp101
	pushl	%eax	# tmp101
	call	fmt	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	subl	$8, %esp	#,
	leal	.LC7@GOTOFF(%ebx), %eax	#, tmp102
	pushl	%eax	# tmp102
	leal	-268(%ebp), %eax	#, tmp103
	pushl	%eax	# tmp103
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# _3
	je	.L31	#,
# sources/vsprintf_percent_s.c:94:         fprintf(stderr, "FAIL: got '%s' expected '[      hi]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp104
	movl	(%eax), %eax	# stderr, stderr.9_4
	subl	$4, %esp	#,
	leal	-268(%ebp), %edx	#, tmp105
	pushl	%edx	# tmp105
	leal	.LC8@GOTOFF(%ebx), %edx	#, tmp106
	pushl	%edx	# tmp106
	pushl	%eax	# stderr.9_4
	call	fprintf@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:95:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L33	#
.L31:
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	subl	$4, %esp	#,
	leal	.LC9@GOTOFF(%ebx), %eax	#, tmp107
	pushl	%eax	# tmp107
	leal	.LC10@GOTOFF(%ebx), %eax	#, tmp108
	pushl	%eax	# tmp108
	leal	-268(%ebp), %eax	#, tmp109
	pushl	%eax	# tmp109
	call	fmt	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	subl	$8, %esp	#,
	leal	.LC11@GOTOFF(%ebx), %eax	#, tmp110
	pushl	%eax	# tmp110
	leal	-268(%ebp), %eax	#, tmp111
	pushl	%eax	# tmp111
	call	strcmp@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# _5
	je	.L32	#,
# sources/vsprintf_percent_s.c:100:         fprintf(stderr, "FAIL: got '%s' expected '[ho      ]'\n", buf);
	movl	stderr@GOT(%ebx), %eax	#, tmp112
	movl	(%eax), %eax	# stderr, stderr.10_6
	subl	$4, %esp	#,
	leal	-268(%ebp), %edx	#, tmp113
	pushl	%edx	# tmp113
	leal	.LC12@GOTOFF(%ebx), %edx	#, tmp114
	pushl	%edx	# tmp114
	pushl	%eax	# stderr.10_6
	call	fprintf@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:101:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L33	#
.L32:
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	subl	$12, %esp	#,
	leal	.LC13@GOTOFF(%ebx), %eax	#, tmp115
	pushl	%eax	# tmp115
	call	puts@PLT	#
	addl	$16, %esp	#,
# sources/vsprintf_percent_s.c:105:     return 0;
	movl	$0, %eax	#, _7
.L33:
# sources/vsprintf_percent_s.c:106: }
	movl	-12(%ebp), %edx	# D.2902, tmp119
	subl	%gs:20, %edx	# MEM[(<address-space-2> unsigned int *)20B], tmp119
	je	.L34	#,
	call	__stack_chk_fail_local	#
.L34:
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
.LFE2:
	.size	main, .-main
	.section	.text.__x86.get_pc_thunk.ax,"axG",@progbits,__x86.get_pc_thunk.ax,comdat
	.globl	__x86.get_pc_thunk.ax
	.hidden	__x86.get_pc_thunk.ax
	.type	__x86.get_pc_thunk.ax, @function
__x86.get_pc_thunk.ax:
.LFB3:
	.cfi_startproc
	movl	(%esp), %eax	#,
	ret
	.cfi_endproc
.LFE3:
	.section	.text.__x86.get_pc_thunk.bx,"axG",@progbits,__x86.get_pc_thunk.bx,comdat
	.globl	__x86.get_pc_thunk.bx
	.hidden	__x86.get_pc_thunk.bx
	.type	__x86.get_pc_thunk.bx, @function
__x86.get_pc_thunk.bx:
.LFB4:
	.cfi_startproc
	movl	(%esp), %ebx	#,
	ret
	.cfi_endproc
.LFE4:
	.hidden	__stack_chk_fail_local
	.ident	"GCC: (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
	.section	.note.GNU-stack,"",@progbits
