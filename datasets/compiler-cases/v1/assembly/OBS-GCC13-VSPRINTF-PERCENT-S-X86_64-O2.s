	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O2 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
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
	pushq	%r15	#
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14	#
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13	#
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	movq	%rdi, %r13	# tmp147, buf
	pushq	%r12	#
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp	#
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movq	%rdi, %rbp	# buf, str
# sources/vsprintf_percent_s.c:74: {
	pushq	%rbx	#
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$120, %rsp	#,
	.cfi_def_cfa_offset 176
# sources/vsprintf_percent_s.c:74: {
	movq	%rdx, 80(%rsp)	#,
	movq	%rcx, 88(%rsp)	#,
	movq	%r8, 96(%rsp)	#,
	movq	%r9, 104(%rsp)	#,
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp150
	movq	%rax, 56(%rsp)	# tmp150, D.3821
	xorl	%eax, %eax	# tmp150
# sources/vsprintf_percent_s.c:76:     va_start(args, fmtstr);
	leaq	176(%rsp), %rax	#, tmp153
	movl	$16, 32(%rsp)	#, MEM[(struct [1] *)&args].gp_offset
	movq	%rax, 40(%rsp)	# tmp153, MEM[(struct [1] *)&args].overflow_arg_area
	leaq	64(%rsp), %rax	#, tmp154
	movq	%rax, 48(%rsp)	# tmp154, MEM[(struct [1] *)&args].reg_save_area
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	(%rsi), %eax	# *fmtstr_4(D), _9
	testb	%al, %al	# _9
	jne	.L18	#,
	jmp	.L2	#
	.p2align 4,,10
	.p2align 3
.L35:
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%al, 0(%rbp)	# _9, *str_113
# sources/vsprintf_percent_s.c:32:             continue;
	movq	%rsi, %rbx	# fmtstr, p
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	addq	$1, %rbp	#, str
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%rbx), %eax	# MEM[(const char *)p_62 + 1B], _9
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leaq	1(%rbx), %rsi	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	testb	%al, %al	# _9
	je	.L2	#,
.L18:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %al	#, _9
	jne	.L35	#,
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	movsbl	1(%rsi), %eax	# MEM[(const char *)p_115 + 1B],
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, %al	#, prephitmp_20
	je	.L5	#,
# sources/vsprintf_percent_s.c:34:         ++p;
	leaq	1(%rsi), %rbx	#, p
	xorl	%r14d, %r14d	# flags
.L6:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	leal	-48(%rax), %edx	#, tmp125
	xorl	%r12d, %r12d	# field_width
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$9, %dl	#, tmp125
	jbe	.L8	#,
.L7:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movl	%eax, %edx	# prephitmp_20, tmp132
	andl	$-33, %edx	#, tmp132
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	cmpb	$76, %dl	#, tmp132
	jne	.L9	#,
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movzbl	1(%rbx), %eax	# MEM[(const char *)p_30 + 1B], prephitmp_20
# sources/vsprintf_percent_s.c:45:             ++p;
	addq	$1, %rbx	#, p
.L9:
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpb	$115, %al	#, prephitmp_20
	je	.L36	#,
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%al, 0(%rbp)	# prephitmp_20, *str_113
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%rbx), %eax	# MEM[(const char *)p_62 + 1B], _9
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	addq	$1, %rbp	#, str
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leaq	1(%rbx), %rsi	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	testb	%al, %al	# _9
	jne	.L18	#,
.L2:
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movb	$0, 0(%rbp)	#, *str_114
# sources/vsprintf_percent_s.c:70:     return str - buf;
	movl	%ebp, %eax	# str, tmp143
	subl	%r13d, %eax	# buf, tmp143
# sources/vsprintf_percent_s.c:80: }
	movq	56(%rsp), %rdx	# D.3821, tmp151
	subq	%fs:40, %rdx	# MEM[(<address-space-1> long unsigned int *)40B], tmp151
	jne	.L37	#,
	addq	$120, %rsp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx	#
	.cfi_def_cfa_offset 48
	popq	%rbp	#
	.cfi_def_cfa_offset 40
	popq	%r12	#
	.cfi_def_cfa_offset 32
	popq	%r13	#
	.cfi_def_cfa_offset 24
	popq	%r14	#
	.cfi_def_cfa_offset 16
	popq	%r15	#
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L8:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	(%r12,%r12,4), %edx	#, tmp128
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addq	$1, %rbx	#, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	-48(%rax,%rdx,2), %r12d	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movsbl	(%rbx), %eax	# MEM[(const char *)p_23],
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	leal	-48(%rax), %edx	#, tmp131
	cmpb	$9, %dl	#, tmp131
	jbe	.L8	#,
	jmp	.L7	#
	.p2align 4,,10
	.p2align 3
.L5:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movsbl	2(%rsi), %eax	# MEM[(const char *)p_115 + 2B],
# sources/vsprintf_percent_s.c:37:             ++p;
	leaq	2(%rsi), %rbx	#, p
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	movl	$16, %r14d	#, flags
	jmp	.L6	#
.L36:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	32(%rsp), %eax	# MEM[(struct  *)&args].gp_offset, D.3794
	cmpl	$47, %eax	#, D.3794
	ja	.L11	#,
	movl	%eax, %edx	# D.3794, D.3797
	addl	$8, %eax	#, tmp135
	addq	48(%rsp), %rdx	# MEM[(struct  *)&args].reg_save_area, D.3799
	movl	%eax, 32(%rsp)	# tmp135, MEM[(struct  *)&args].gp_offset
.L12:
	movq	(%rdx), %r15	# MEM[(char * * {ref-all})addr.15_69], s
# sources/vsprintf_percent_s.c:50:             if (!s)
	testq	%r15, %r15	# s
	je	.L13	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movq	%r15, %rdi	# s,
	call	strlen@PLT	#
	movq	%rax, %r8	# tmp149, _40
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, %ecx	# _40, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%r14d, %r14d	# flags
	je	.L21	#,
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%eax, %eax	# _40
	jle	.L20	#,
.L16:
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	xorl	%eax, %eax	# ivtmp.23
	.p2align 4,,10
	.p2align 3
.L17:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%r15,%rax), %edx	# MEM[(char *)s_86 + ivtmp.23_101 * 1], _53
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movb	%dl, 0(%rbp,%rax)	# _53, MEM[(char *)str_100 + ivtmp.23_101 * 1]
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addq	$1, %rax	#, ivtmp.23
	cmpl	%eax, %ecx	# ivtmp.23, len
	jg	.L17	#,
	leal	-1(%r8), %eax	#, tmp141
	leaq	1(%rbp,%rax), %rbp	#, str
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	testl	%r14d, %r14d	# flags
	je	.L4	#,
.L20:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	%ecx, %r12d	# len, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	testl	%r12d, %r12d	# i
	jle	.L4	#,
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movslq	%r12d, %r12	# i, _13
	movq	%rbp, %rdi	# str,
	movl	$32, %esi	#,
	movq	%r12, %rdx	# _13,
	addq	%r12, %rbp	# _13, str
	call	memset@PLT	#
	jmp	.L4	#
.L11:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movq	40(%rsp), %rdx	# MEM[(struct  *)&args].overflow_arg_area, D.3799
	leaq	8(%rdx), %rax	#, tmp136
	movq	%rax, 40(%rsp)	# tmp136, MEM[(struct  *)&args].overflow_arg_area
	jmp	.L12	#
.L13:
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, len
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %r8d	#, _40
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leaq	.LC0(%rip), %r15	#, s
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%r14d, %r14d	# flags
	jne	.L16	#,
.L21:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	%r12d, %eax	# field_width, i
	subl	%ecx, %eax	# len, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	testl	%eax, %eax	# i
	jle	.L15	#,
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movslq	%eax, %rdx	# i, _37
	movq	%rbp, %rdi	# str,
	movl	$32, %esi	#,
	movl	%ecx, 28(%rsp)	# len, %sfp
	movq	%r8, 16(%rsp)	# _40, %sfp
	movq	%rdx, 8(%rsp)	# _37, %sfp
	call	memset@PLT	#
	movq	8(%rsp), %rdx	# %sfp, _37
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	movl	28(%rsp), %ecx	# %sfp, len
	movq	16(%rsp), %r8	# %sfp, _40
	addq	%rdx, %rbp	# _37, str
	testl	%ecx, %ecx	# len
	jg	.L16	#,
	jmp	.L4	#
.L15:
	testl	%ecx, %ecx	# len
	jg	.L16	#,
	jmp	.L4	#
.L37:
# sources/vsprintf_percent_s.c:80: }
	call	__stack_chk_fail@PLT	#
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
	.section	.rodata.str1.8,"aMS",@progbits,1
	.align 8
.LC4:
	.string	"FAIL: got '%s' expected '[hello]'\n"
	.section	.rodata.str1.1
.LC5:
	.string	"hi"
.LC6:
	.string	"[%8s]"
.LC7:
	.string	"[      hi]"
	.section	.rodata.str1.8
	.align 8
.LC8:
	.string	"FAIL: got '%s' expected '[      hi]'\n"
	.section	.rodata.str1.1
.LC9:
	.string	"ho"
.LC10:
	.string	"[%-8s]"
.LC11:
	.string	"[ho      ]"
	.section	.rodata.str1.8
	.align 8
.LC12:
	.string	"FAIL: got '%s' expected '[ho      ]'\n"
	.align 8
.LC13:
	.string	"PASS: %s formatting reads the correct argument slot"
	.section	.text.startup,"ax",@progbits
	.p2align 4
	.globl	main
	.type	main, @function
main:
.LFB40:
	.cfi_startproc
	endbr64
	pushq	%rbp	#
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	leaq	.LC1(%rip), %rdx	#, tmp90
	leaq	.LC2(%rip), %rsi	#, tmp91
# sources/vsprintf_percent_s.c:83: {
	pushq	%rbx	#
	.cfi_def_cfa_offset 24
	.cfi_offset 3, -24
	subq	$280, %rsp	#,
	.cfi_def_cfa_offset 304
# sources/vsprintf_percent_s.c:83: {
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp134
	movq	%rax, 264(%rsp)	# tmp134, D.3830
	xorl	%eax, %eax	# tmp134
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	movq	%rsp, %rbx	#, tmp131
	movq	%rbx, %rdi	# tmp131,
	call	fmt	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	movabsq	$26299684299827291, %rax	#, tmp94
	cmpq	%rax, (%rsp)	# tmp94, MEM <char[1:8]> [(void *)&buf]
	je	.L49	#,
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	stderr(%rip), %rdi	# stderr,
	movq	%rbx, %rcx	# tmp131,
	movl	$2, %esi	#,
	xorl	%eax, %eax	#
	leaq	.LC4(%rip), %rdx	#, tmp97
	call	__fprintf_chk@PLT	#
.L42:
# sources/vsprintf_percent_s.c:89:         return 1;
	movl	$1, %ebp	#, <retval>
.L38:
# sources/vsprintf_percent_s.c:106: }
	movq	264(%rsp), %rax	# D.3830, tmp135
	subq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp135
	jne	.L50	#,
	addq	$280, %rsp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 24
	movl	%ebp, %eax	# <retval>,
	popq	%rbx	#
	.cfi_def_cfa_offset 16
	popq	%rbp	#
	.cfi_def_cfa_offset 8
	ret
.L49:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	leaq	.LC6(%rip), %rsi	#, tmp100
	movq	%rbx, %rdi	# tmp131,
	xorl	%eax, %eax	#
	leaq	.LC5(%rip), %rdx	#, tmp99
	call	fmt	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	leaq	.LC7(%rip), %rsi	#, tmp107
	movq	%rbx, %rdi	# tmp131,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# tmp132
	jne	.L51	#,
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	leaq	.LC9(%rip), %rdx	#, tmp114
	leaq	.LC10(%rip), %rsi	#, tmp115
	movq	%rbx, %rdi	# tmp131,
	xorl	%eax, %eax	#
	call	fmt	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	leaq	.LC11(%rip), %rsi	#, tmp122
	movq	%rbx, %rdi	# tmp131,
	call	strcmp@PLT	#
	movl	%eax, %ebp	# tmp133, <retval>
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# <retval>
	jne	.L52	#,
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	leaq	.LC13(%rip), %rdi	#, tmp128
	call	puts@PLT	#
# sources/vsprintf_percent_s.c:105:     return 0;
	jmp	.L38	#
.L51:
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	stderr(%rip), %rdi	# stderr,
	movq	%rbx, %rcx	# tmp131,
	movl	$2, %esi	#,
	xorl	%eax, %eax	#
	leaq	.LC8(%rip), %rdx	#, tmp112
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:95:         return 1;
	jmp	.L42	#
.L52:
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	stderr(%rip), %rdi	# stderr,
	movq	%rbx, %rcx	# tmp131,
	movl	$2, %esi	#,
	xorl	%eax, %eax	#
	leaq	.LC12(%rip), %rdx	#, tmp127
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:101:         return 1;
	jmp	.L42	#
.L50:
# sources/vsprintf_percent_s.c:106: }
	call	__stack_chk_fail@PLT	#
	.cfi_endproc
.LFE40:
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
