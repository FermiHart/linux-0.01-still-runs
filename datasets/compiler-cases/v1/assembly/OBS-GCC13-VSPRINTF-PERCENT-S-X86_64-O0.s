	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O0 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.section	.rodata
.LC0:
	.string	"(null)"
	.text
	.type	mini_vsprintf, @function
mini_vsprintf:
.LFB0:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
	subq	$80, %rsp	#,
	movq	%rdi, -56(%rbp)	# buf, buf
	movq	%rsi, -64(%rbp)	# fmt, fmt
	movq	%rdx, -72(%rbp)	# args, args
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movq	-56(%rbp), %rax	# buf, tmp121
	movq	%rax, -24(%rbp)	# tmp121, str
# sources/vsprintf_percent_s.c:25:     int flags = 0;
	movl	$0, -36(%rbp)	#, flags
# sources/vsprintf_percent_s.c:26:     int field_width = 0;
	movl	$0, -32(%rbp)	#, field_width
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movq	-64(%rbp), %rax	# fmt, tmp122
	movq	%rax, -8(%rbp)	# tmp122, p
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	jmp	.L2	#
.L24:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	movq	-8(%rbp), %rax	# p, tmp123
	movzbl	(%rax), %eax	# *p_55, _1
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %al	#, _1
	je	.L3	#,
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movq	-24(%rbp), %rax	# str, str.0_2
	leaq	1(%rax), %rdx	#, tmp124
	movq	%rdx, -24(%rbp)	# tmp124, str
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movq	-8(%rbp), %rdx	# p, tmp125
	movzbl	(%rdx), %edx	# *p_55, _3
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%dl, (%rax)	# _3, *str.0_2
# sources/vsprintf_percent_s.c:32:             continue;
	jmp	.L4	#
.L3:
# sources/vsprintf_percent_s.c:34:         ++p;
	addq	$1, -8(%rbp)	#, p
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	movq	-8(%rbp), %rax	# p, tmp126
	movzbl	(%rax), %eax	# *p_73, _4
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, %al	#, _4
	jne	.L5	#,
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	orl	$16, -36(%rbp)	#, flags
# sources/vsprintf_percent_s.c:37:             ++p;
	addq	$1, -8(%rbp)	#, p
.L5:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movq	-8(%rbp), %rax	# p, tmp127
	movzbl	(%rax), %eax	# *p_50, _5
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$47, %al	#, _5
	jle	.L6	#,
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movq	-8(%rbp), %rax	# p, tmp128
	movzbl	(%rax), %eax	# *p_50, _6
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$57, %al	#, _6
	jg	.L6	#,
# sources/vsprintf_percent_s.c:40:             field_width = 0;
	movl	$0, -32(%rbp)	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	jmp	.L7	#
.L8:
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movl	-32(%rbp), %edx	# field_width, tmp129
	movl	%edx, %eax	# tmp129, tmp130
	sall	$2, %eax	#, tmp130
	addl	%edx, %eax	# tmp129, tmp130
	addl	%eax, %eax	# tmp131
	movl	%eax, %ecx	# tmp130, _7
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movq	-8(%rbp), %rax	# p, p.1_8
	leaq	1(%rax), %rdx	#, tmp132
	movq	%rdx, -8(%rbp)	# tmp132, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movzbl	(%rax), %eax	# *p.1_8, _9
	movsbl	%al, %eax	# _9, _10
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addl	%ecx, %eax	# _7, _11
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	subl	$48, %eax	#, tmp133
	movl	%eax, -32(%rbp)	# tmp133, field_width
.L7:
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movq	-8(%rbp), %rax	# p, tmp134
	movzbl	(%rax), %eax	# *p_51, _12
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	cmpb	$47, %al	#, _12
	jle	.L6	#,
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movq	-8(%rbp), %rax	# p, tmp135
	movzbl	(%rax), %eax	# *p_51, _13
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	cmpb	$57, %al	#, _13
	jle	.L8	#,
.L6:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movq	-8(%rbp), %rax	# p, tmp136
	movzbl	(%rax), %eax	# *p_52, _14
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$108, %al	#, _14
	je	.L9	#,
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movq	-8(%rbp), %rax	# p, tmp137
	movzbl	(%rax), %eax	# *p_52, _15
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$76, %al	#, _15
	jne	.L10	#,
.L9:
# sources/vsprintf_percent_s.c:45:             ++p;
	addq	$1, -8(%rbp)	#, p
.L10:
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movq	-8(%rbp), %rax	# p, tmp138
	movzbl	(%rax), %eax	# *p_53, _16
	movsbl	%al, %eax	# _16, _17
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpl	$115, %eax	#, _17
	jne	.L11	#,
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movq	-72(%rbp), %rax	# args, tmp139
	movl	(%rax), %eax	# args_80(D)->gp_offset, D.3473
	cmpl	$47, %eax	#, D.3473
	ja	.L12	#,
	movq	-72(%rbp), %rax	# args, tmp140
	movq	16(%rax), %rdx	# args_80(D)->reg_save_area, D.3475
	movq	-72(%rbp), %rax	# args, tmp141
	movl	(%rax), %eax	# args_80(D)->gp_offset, D.3476
	movl	%eax, %eax	# D.3476, D.3477
	addq	%rdx, %rax	# D.3475, D.3480
	movq	-72(%rbp), %rdx	# args, tmp142
	movl	(%rdx), %edx	# args_80(D)->gp_offset, D.3478
	leal	8(%rdx), %ecx	#, D.3479
	movq	-72(%rbp), %rdx	# args, tmp143
	movl	%ecx, (%rdx)	# D.3479, args_80(D)->gp_offset
	jmp	.L13	#
.L12:
	movq	-72(%rbp), %rax	# args, tmp144
	movq	8(%rax), %rax	# args_80(D)->overflow_arg_area, D.3480
	leaq	8(%rax), %rcx	#, D.3481
	movq	-72(%rbp), %rdx	# args, tmp145
	movq	%rcx, 8(%rdx)	# D.3481, args_80(D)->overflow_arg_area
.L13:
	movq	(%rax), %rax	# MEM[(char * * {ref-all})addr.13_106], tmp146
	movq	%rax, -16(%rbp)	# tmp146, s
# sources/vsprintf_percent_s.c:50:             if (!s)
	cmpq	$0, -16(%rbp)	#, s
	jne	.L14	#,
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leaq	.LC0(%rip), %rax	#, tmp147
	movq	%rax, -16(%rbp)	# tmp147, s
.L14:
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movq	-16(%rbp), %rax	# s, tmp148
	movq	%rax, %rdi	# tmp148,
	call	strlen@PLT	#
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, -28(%rbp)	# _18, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	movl	-36(%rbp), %eax	# flags, tmp149
	andl	$16, %eax	#, _19
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%eax, %eax	# _19
	jne	.L15	#,
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	-32(%rbp), %eax	# field_width, tmp153
	subl	-28(%rbp), %eax	# len, tmp152
	movl	%eax, -40(%rbp)	# tmp152, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	jmp	.L16	#
.L17:
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movq	-24(%rbp), %rax	# str, str.2_20
	leaq	1(%rax), %rdx	#, tmp154
	movq	%rdx, -24(%rbp)	# tmp154, str
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movb	$32, (%rax)	#, *str.2_20
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	subl	$1, -40(%rbp)	#, i
.L16:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	cmpl	$0, -40(%rbp)	#, i
	jg	.L17	#,
.L15:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	$0, -40(%rbp)	#, i
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	jmp	.L18	#
.L19:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movq	-16(%rbp), %rdx	# s, s.3_21
	leaq	1(%rdx), %rax	#, tmp155
	movq	%rax, -16(%rbp)	# tmp155, s
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movq	-24(%rbp), %rax	# str, str.4_22
	leaq	1(%rax), %rcx	#, tmp156
	movq	%rcx, -24(%rbp)	# tmp156, str
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%rdx), %edx	# *s.3_21, _23
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movb	%dl, (%rax)	# _23, *str.4_22
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addl	$1, -40(%rbp)	#, i
.L18:
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	-40(%rbp), %eax	# i, tmp157
	cmpl	-28(%rbp), %eax	# len, tmp157
	jl	.L19	#,
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	movl	-36(%rbp), %eax	# flags, tmp158
	andl	$16, %eax	#, _24
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	testl	%eax, %eax	# _24
	je	.L26	#,
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	movl	-32(%rbp), %eax	# field_width, tmp162
	subl	-28(%rbp), %eax	# len, tmp161
	movl	%eax, -40(%rbp)	# tmp161, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	jmp	.L21	#
.L22:
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movq	-24(%rbp), %rax	# str, str.5_25
	leaq	1(%rax), %rdx	#, tmp163
	movq	%rdx, -24(%rbp)	# tmp163, str
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movb	$32, (%rax)	#, *str.5_25
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	$1, -40(%rbp)	#, i
.L21:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	cmpl	$0, -40(%rbp)	#, i
	jg	.L22	#,
# sources/vsprintf_percent_s.c:61:             break;
	jmp	.L26	#
.L11:
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movq	-24(%rbp), %rax	# str, str.6_26
	leaq	1(%rax), %rdx	#, tmp164
	movq	%rdx, -24(%rbp)	# tmp164, str
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movq	-8(%rbp), %rdx	# p, tmp165
	movzbl	(%rdx), %edx	# *p_53, _27
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%dl, (%rax)	# _27, *str.6_26
# sources/vsprintf_percent_s.c:64:             break;
	jmp	.L23	#
.L26:
# sources/vsprintf_percent_s.c:61:             break;
	nop
.L23:
# sources/vsprintf_percent_s.c:66:         flags = 0;
	movl	$0, -36(%rbp)	#, flags
# sources/vsprintf_percent_s.c:67:         field_width = 0;
	movl	$0, -32(%rbp)	#, field_width
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	addq	$1, -8(%rbp)	#, p
.L2:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movq	-8(%rbp), %rax	# p, tmp166
	movzbl	(%rax), %eax	# *p_55, _28
	testb	%al, %al	# _28
	jne	.L24	#,
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movq	-24(%rbp), %rax	# str, tmp167
	movb	$0, (%rax)	#, *str_37
# sources/vsprintf_percent_s.c:70:     return str - buf;
	movq	-24(%rbp), %rax	# str, tmp168
	subq	-56(%rbp), %rax	# buf, _29
# sources/vsprintf_percent_s.c:71: }
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE0:
	.size	mini_vsprintf, .-mini_vsprintf
	.type	fmt, @function
fmt:
.LFB1:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
	subq	$240, %rsp	#,
	movq	%rdi, -232(%rbp)	# buf, buf
	movq	%rsi, -240(%rbp)	# fmtstr, fmtstr
	movq	%rdx, -160(%rbp)	#,
	movq	%rcx, -152(%rbp)	#,
	movq	%r8, -144(%rbp)	#,
	movq	%r9, -136(%rbp)	#,
	testb	%al, %al	#
	je	.L28	#,
	movaps	%xmm0, -128(%rbp)	#,
	movaps	%xmm1, -112(%rbp)	#,
	movaps	%xmm2, -96(%rbp)	#,
	movaps	%xmm3, -80(%rbp)	#,
	movaps	%xmm4, -64(%rbp)	#,
	movaps	%xmm5, -48(%rbp)	#,
	movaps	%xmm6, -32(%rbp)	#,
	movaps	%xmm7, -16(%rbp)	#,
.L28:
# sources/vsprintf_percent_s.c:74: {
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp90
	movq	%rax, -184(%rbp)	# tmp90, D.3483
	xorl	%eax, %eax	# tmp90
# sources/vsprintf_percent_s.c:76:     va_start(args, fmtstr);
	movl	$16, -208(%rbp)	#, MEM[(struct [1] *)&args].gp_offset
	movl	$48, -204(%rbp)	#, MEM[(struct [1] *)&args].fp_offset
	leaq	16(%rbp), %rax	#, tmp93
	movq	%rax, -200(%rbp)	# tmp93, MEM[(struct [1] *)&args].overflow_arg_area
	leaq	-176(%rbp), %rax	#, tmp94
	movq	%rax, -192(%rbp)	# tmp94, MEM[(struct [1] *)&args].reg_save_area
# sources/vsprintf_percent_s.c:77:     int n = mini_vsprintf(buf, fmtstr, args);
	leaq	-208(%rbp), %rdx	#, tmp85
	movq	-240(%rbp), %rcx	# fmtstr, tmp86
	movq	-232(%rbp), %rax	# buf, tmp87
	movq	%rcx, %rsi	# tmp86,
	movq	%rax, %rdi	# tmp87,
	call	mini_vsprintf	#
	movl	%eax, -212(%rbp)	# tmp88, n
# sources/vsprintf_percent_s.c:79:     return n;
	movl	-212(%rbp), %eax	# n, _8
# sources/vsprintf_percent_s.c:80: }
	movq	-184(%rbp), %rdx	# D.3483, tmp91
	subq	%fs:40, %rdx	# MEM[(<address-space-1> long unsigned int *)40B], tmp91
	je	.L30	#,
	call	__stack_chk_fail@PLT	#
.L30:
	leave
	.cfi_def_cfa 7, 8
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
	.align 8
.LC4:
	.string	"FAIL: got '%s' expected '[hello]'\n"
.LC5:
	.string	"hi"
.LC6:
	.string	"[%8s]"
.LC7:
	.string	"[      hi]"
	.align 8
.LC8:
	.string	"FAIL: got '%s' expected '[      hi]'\n"
.LC9:
	.string	"ho"
.LC10:
	.string	"[%-8s]"
.LC11:
	.string	"[ho      ]"
	.align 8
.LC12:
	.string	"FAIL: got '%s' expected '[ho      ]'\n"
	.align 8
.LC13:
	.string	"PASS: %s formatting reads the correct argument slot"
	.text
	.globl	main
	.type	main, @function
main:
.LFB2:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp	#,
	.cfi_def_cfa_register 6
	subq	$272, %rsp	#,
# sources/vsprintf_percent_s.c:83: {
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp113
	movq	%rax, -8(%rbp)	# tmp113, D.3487
	xorl	%eax, %eax	# tmp113
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	leaq	-272(%rbp), %rax	#, tmp90
	leaq	.LC1(%rip), %rdx	#, tmp91
	leaq	.LC2(%rip), %rcx	#, tmp92
	movq	%rcx, %rsi	# tmp92,
	movq	%rax, %rdi	# tmp90,
	movl	$0, %eax	#,
	call	fmt	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	leaq	-272(%rbp), %rax	#, tmp93
	leaq	.LC3(%rip), %rdx	#, tmp94
	movq	%rdx, %rsi	# tmp94,
	movq	%rax, %rdi	# tmp93,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	testl	%eax, %eax	# _1
	je	.L32	#,
# sources/vsprintf_percent_s.c:88:         fprintf(stderr, "FAIL: got '%s' expected '[hello]'\n", buf);
	movq	stderr(%rip), %rax	# stderr, stderr.7_2
	leaq	-272(%rbp), %rdx	#, tmp95
	leaq	.LC4(%rip), %rcx	#, tmp96
	movq	%rcx, %rsi	# tmp96,
	movq	%rax, %rdi	# stderr.7_2,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/vsprintf_percent_s.c:89:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L36	#
.L32:
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	leaq	-272(%rbp), %rax	#, tmp97
	leaq	.LC5(%rip), %rdx	#, tmp98
	leaq	.LC6(%rip), %rcx	#, tmp99
	movq	%rcx, %rsi	# tmp99,
	movq	%rax, %rdi	# tmp97,
	movl	$0, %eax	#,
	call	fmt	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	leaq	-272(%rbp), %rax	#, tmp100
	leaq	.LC7(%rip), %rdx	#, tmp101
	movq	%rdx, %rsi	# tmp101,
	movq	%rax, %rdi	# tmp100,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# _3
	je	.L34	#,
# sources/vsprintf_percent_s.c:94:         fprintf(stderr, "FAIL: got '%s' expected '[      hi]'\n", buf);
	movq	stderr(%rip), %rax	# stderr, stderr.8_4
	leaq	-272(%rbp), %rdx	#, tmp102
	leaq	.LC8(%rip), %rcx	#, tmp103
	movq	%rcx, %rsi	# tmp103,
	movq	%rax, %rdi	# stderr.8_4,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/vsprintf_percent_s.c:95:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L36	#
.L34:
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	leaq	-272(%rbp), %rax	#, tmp104
	leaq	.LC9(%rip), %rdx	#, tmp105
	leaq	.LC10(%rip), %rcx	#, tmp106
	movq	%rcx, %rsi	# tmp106,
	movq	%rax, %rdi	# tmp104,
	movl	$0, %eax	#,
	call	fmt	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	leaq	-272(%rbp), %rax	#, tmp107
	leaq	.LC11(%rip), %rdx	#, tmp108
	movq	%rdx, %rsi	# tmp108,
	movq	%rax, %rdi	# tmp107,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# _5
	je	.L35	#,
# sources/vsprintf_percent_s.c:100:         fprintf(stderr, "FAIL: got '%s' expected '[ho      ]'\n", buf);
	movq	stderr(%rip), %rax	# stderr, stderr.9_6
	leaq	-272(%rbp), %rdx	#, tmp109
	leaq	.LC12(%rip), %rcx	#, tmp110
	movq	%rcx, %rsi	# tmp110,
	movq	%rax, %rdi	# stderr.9_6,
	movl	$0, %eax	#,
	call	fprintf@PLT	#
# sources/vsprintf_percent_s.c:101:         return 1;
	movl	$1, %eax	#, _7
	jmp	.L36	#
.L35:
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	leaq	.LC13(%rip), %rax	#, tmp111
	movq	%rax, %rdi	# tmp111,
	call	puts@PLT	#
# sources/vsprintf_percent_s.c:105:     return 0;
	movl	$0, %eax	#, _7
.L36:
# sources/vsprintf_percent_s.c:106: }
	movq	-8(%rbp), %rdx	# D.3487, tmp114
	subq	%fs:40, %rdx	# MEM[(<address-space-1> long unsigned int *)40B], tmp114
	je	.L37	#,
	call	__stack_chk_fail@PLT	#
.L37:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE2:
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
