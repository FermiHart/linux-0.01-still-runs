	.file	"vsprintf_percent_s.c"
# GNU C89 (Ubuntu 13.3.0-6ubuntu2~24.04.1) version 13.3.0 (x86_64-linux-gnu)
#	compiled by GNU C version 13.3.0, GMP version 6.3.0, MPFR version 4.2.1, MPC version 1.3.1, isl version isl-0.26-GMP

# GGC heuristics: --param ggc-min-expand=100 --param ggc-min-heapsize=131072
# options passed: -mtune=generic -march=x86-64 -O1 -std=gnu90 -fasynchronous-unwind-tables -fstack-protector-strong -fstack-clash-protection -fcf-protection
	.text
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	"(null)"
	.text
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
	pushq	%r12	#
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp	#
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx	#
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	subq	$104, %rsp	#,
	.cfi_def_cfa_offset 160
	movq	%rdi, 8(%rsp)	# buf, %sfp
	movq	%rdx, 64(%rsp)	#,
	movq	%rcx, 72(%rsp)	#,
	movq	%r8, 80(%rsp)	#,
	movq	%r9, 88(%rsp)	#,
# sources/vsprintf_percent_s.c:74: {
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp173
	movq	%rax, 40(%rsp)	# tmp173, D.3833
	xorl	%eax, %eax	# tmp173
# sources/vsprintf_percent_s.c:76:     va_start(args, fmtstr);
	movl	$16, 16(%rsp)	#, MEM[(struct [1] *)&args].gp_offset
	leaq	160(%rsp), %rax	#, tmp176
	movq	%rax, 24(%rsp)	# tmp176, MEM[(struct [1] *)&args].overflow_arg_area
	leaq	48(%rsp), %rax	#, tmp177
	movq	%rax, 32(%rsp)	# tmp177, MEM[(struct [1] *)&args].reg_save_area
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	(%rsi), %eax	# *fmtstr_4(D), _9
	testb	%al, %al	# _9
	je	.L25	#,
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movq	%rdi, %rbp	# buf, str
	movl	$0, %r13d	#, field_width
	jmp	.L22	#
.L37:
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	movb	%al, 0(%rbp)	# _9, *str_113
# sources/vsprintf_percent_s.c:32:             continue;
	movq	%rsi, %rbx	# fmtstr, p
# sources/vsprintf_percent_s.c:31:             *str++ = *p;
	leaq	1(%rbp), %rbp	#, str
.L4:
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	leaq	1(%rbx), %rsi	#, fmtstr
# sources/vsprintf_percent_s.c:29:     for (p = fmt; *p; ++p) {
	movzbl	1(%rbx), %eax	# MEM[(const char *)p_63 + 1B], _9
	testb	%al, %al	# _9
	je	.L2	#,
.L22:
# sources/vsprintf_percent_s.c:30:         if (*p != '%') {
	cmpb	$37, %al	#, _9
	jne	.L37	#,
# sources/vsprintf_percent_s.c:35:         if (*p == '-') {
	cmpb	$45, 1(%rsi)	#, MEM[(const char *)p_115 + 1B]
	je	.L5	#,
# sources/vsprintf_percent_s.c:34:         ++p;
	leaq	1(%rsi), %rbx	#, p
	movl	%r13d, %r15d	# field_width, flags
.L6:
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	movzbl	(%rbx), %eax	# *p_16, _24
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	leal	-48(%rax), %edx	#, tmp139
	movl	%r13d, %r12d	# field_width, field_width
# sources/vsprintf_percent_s.c:39:         if (*p >= '0' && *p <= '9') {
	cmpb	$9, %dl	#, tmp139
	jbe	.L8	#,
.L7:
# sources/vsprintf_percent_s.c:44:         if (*p == 'l' || *p == 'L')
	movzbl	(%rbx), %eax	# *p_30, tmp146
	andl	$-33, %eax	#, tmp146
# sources/vsprintf_percent_s.c:45:             ++p;
	cmpb	$76, %al	#, tmp146
	sete	%al	#, tmp166
	movzbl	%al, %eax	# tmp166, tmp166
	addq	%rax, %rbx	# tmp166, p
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	movzbl	(%rbx), %eax	# *p_36, _37
# sources/vsprintf_percent_s.c:47:         switch (*p) {
	cmpb	$115, %al	#, _37
	je	.L38	#,
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	movb	%al, 0(%rbp)	# _37, *str_113
# sources/vsprintf_percent_s.c:63:             *str++ = *p;
	leaq	1(%rbp), %rbp	#, str
# sources/vsprintf_percent_s.c:64:             break;
	jmp	.L4	#
.L5:
# sources/vsprintf_percent_s.c:37:             ++p;
	leaq	2(%rsi), %rbx	#, p
# sources/vsprintf_percent_s.c:36:             flags |= LEFT;
	movl	$16, %r15d	#, flags
	jmp	.L6	#
.L8:
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	addq	$1, %rbx	#, p
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	(%r12,%r12,4), %edx	#, tmp142
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	movsbl	%al, %eax	# _24, _24
# sources/vsprintf_percent_s.c:42:                 field_width = field_width * 10 + *p++ - '0';
	leal	-48(%rax,%rdx,2), %r12d	#, field_width
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	movzbl	(%rbx), %eax	# MEM[(const char *)p_23], _24
# sources/vsprintf_percent_s.c:41:             while (*p >= '0' && *p <= '9')
	leal	-48(%rax), %edx	#, tmp145
	cmpb	$9, %dl	#, tmp145
	jbe	.L8	#,
	jmp	.L7	#
.L38:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movl	16(%rsp), %eax	# MEM[(struct  *)&args].gp_offset, D.3794
	cmpl	$47, %eax	#, D.3794
	ja	.L11	#,
	movl	%eax, %edx	# D.3794, D.3797
	addq	32(%rsp), %rdx	# MEM[(struct  *)&args].reg_save_area, D.3799
	addl	$8, %eax	#, tmp150
	movl	%eax, 16(%rsp)	# tmp150, MEM[(struct  *)&args].gp_offset
.L12:
	movq	(%rdx), %r14	# MEM[(char * * {ref-all})addr.15_67], s
# sources/vsprintf_percent_s.c:50:             if (!s)
	testq	%r14, %r14	# s
	je	.L13	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movq	%r14, %rdi	# s,
	call	strlen@PLT	#
	movq	%rax, %rsi	# tmp153, _120
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	%eax, %ecx	# tmp153, len
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%r15d, %r15d	# flags
	je	.L14	#,
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%eax, %eax	# tmp153
	jle	.L23	#,
.L16:
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	movl	$0, %eax	#, ivtmp.30
.L20:
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movzbl	(%r14,%rax), %edx	# MEM[(char *)s_109 + ivtmp.30_104 * 1], _54
# sources/vsprintf_percent_s.c:57:                 *str++ = *s++;
	movb	%dl, 0(%rbp,%rax)	# _54, MEM[(char *)str_73 + ivtmp.30_104 * 1]
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	addq	$1, %rax	#, ivtmp.30
	cmpl	%eax, %ecx	# ivtmp.30, len
	jg	.L20	#,
	leal	-1(%rsi), %eax	#, tmp159
	addq	$1, %rax	#, tmp157
	testl	%ecx, %ecx	# len
	movl	$1, %edx	#, tmp160
	cmovle	%rdx, %rax	# tmp157,, tmp160, tmp157
	addq	%rax, %rbp	# tmp157, str
# sources/vsprintf_percent_s.c:58:             if (flags & LEFT)
	testl	%r15d, %r15d	# flags
	je	.L4	#,
.L23:
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	subl	%ecx, %r12d	# len, i
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	testl	%r12d, %r12d	# i
	jle	.L4	#,
	movl	%r12d, %edx	# i, i
	addq	%rbp, %rdx	# str, _105
	movq	%rbp, %rax	# str, str
.L21:
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	addq	$1, %rax	#, str
# sources/vsprintf_percent_s.c:60:                     *str++ = ' ';
	movb	$32, -1(%rax)	#, MEM[(char *)str_59 + -1B]
# sources/vsprintf_percent_s.c:59:                 for (i = field_width - len; i > 0; --i)
	cmpq	%rdx, %rax	# _105, str
	jne	.L21	#,
	movl	%r12d, %r12d	# i, i
	addq	%r12, %rbp	# i, str
	jmp	.L4	#
.L11:
# sources/vsprintf_percent_s.c:49:             s = va_arg(args, char *);
	movq	24(%rsp), %rdx	# MEM[(struct  *)&args].overflow_arg_area, D.3799
	leaq	8(%rdx), %rax	#, tmp151
	movq	%rax, 24(%rsp)	# tmp151, MEM[(struct  *)&args].overflow_arg_area
	jmp	.L12	#
.L27:
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, len
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %esi	#, _120
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leaq	.LC0(%rip), %r14	#, s
.L14:
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	movl	%r12d, %edi	# field_width, i
	subl	%ecx, %edi	# len, i
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	testl	%edi, %edi	# i
	jle	.L17	#,
	movl	%edi, %edx	# i, i
	addq	%rbp, %rdx	# str, _133
	movq	%rbp, %rax	# str, str
.L18:
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	addq	$1, %rax	#, str
# sources/vsprintf_percent_s.c:55:                     *str++ = ' ';
	movb	$32, -1(%rax)	#, MEM[(char *)str_47 + -1B]
# sources/vsprintf_percent_s.c:54:                 for (i = field_width - len; i > 0; --i)
	cmpq	%rdx, %rax	# _133, str
	jne	.L18	#,
	movl	%edi, %edi	# i, i
	addq	%rdi, %rbp	# i, str
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%ecx, %ecx	# len
	jg	.L16	#,
	jmp	.L4	#
.L25:
# sources/vsprintf_percent_s.c:21:     char *str = buf;
	movq	8(%rsp), %rbp	# %sfp, str
.L2:
# sources/vsprintf_percent_s.c:69:     *str = '\0';
	movb	$0, 0(%rbp)	#, *str_114
# sources/vsprintf_percent_s.c:79:     return n;
	movl	%ebp, %eax	# str, <retval>
	movl	8(%rsp), %edi	# %sfp, tmp181
	subl	%edi, %eax	# tmp181, <retval>
# sources/vsprintf_percent_s.c:80: }
	movq	40(%rsp), %rdx	# D.3833, tmp174
	subq	%fs:40, %rdx	# MEM[(<address-space-1> long unsigned int *)40B], tmp174
	jne	.L39	#,
	addq	$104, %rsp	#,
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
.L17:
	.cfi_restore_state
# sources/vsprintf_percent_s.c:56:             for (i = 0; i < len; ++i)
	testl	%ecx, %ecx	# len
	jg	.L16	#,
	jmp	.L4	#
.L13:
# sources/vsprintf_percent_s.c:53:             if (!(flags & LEFT))
	testl	%r15d, %r15d	# flags
	je	.L27	#,
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %ecx	#, len
# sources/vsprintf_percent_s.c:52:             len = strlen(s);
	movl	$6, %esi	#, _120
# sources/vsprintf_percent_s.c:51:                 s = "(null)";
	leaq	.LC0(%rip), %r14	#, s
	jmp	.L16	#
.L39:
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
	.text
	.globl	main
	.type	main, @function
main:
.LFB40:
	.cfi_startproc
	endbr64
	pushq	%rbx	#
	.cfi_def_cfa_offset 16
	.cfi_offset 3, -16
	subq	$272, %rsp	#,
	.cfi_def_cfa_offset 288
# sources/vsprintf_percent_s.c:83: {
	movq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp125
	movq	%rax, 264(%rsp)	# tmp125, D.3840
	xorl	%eax, %eax	# tmp125
# sources/vsprintf_percent_s.c:86:     fmt(buf, "[%s]", "hello");
	movq	%rsp, %rbx	#, tmp89
	leaq	.LC1(%rip), %rdx	#, tmp90
	leaq	.LC2(%rip), %rsi	#, tmp91
	movq	%rbx, %rdi	# tmp89,
	call	fmt	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	leaq	.LC3(%rip), %rsi	#, tmp95
	movq	%rbx, %rdi	# tmp89,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:87:     if (strcmp(buf, "[hello]") != 0) {
	testl	%eax, %eax	# tmp122
	jne	.L47	#,
# sources/vsprintf_percent_s.c:92:     fmt(buf, "[%8s]", "hi");
	movq	%rsp, %rbx	#, tmp99
	leaq	.LC5(%rip), %rdx	#, tmp100
	leaq	.LC6(%rip), %rsi	#, tmp101
	movq	%rbx, %rdi	# tmp99,
	movl	$0, %eax	#,
	call	fmt	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	leaq	.LC7(%rip), %rsi	#, tmp105
	movq	%rbx, %rdi	# tmp99,
	call	strcmp@PLT	#
# sources/vsprintf_percent_s.c:93:     if (strcmp(buf, "[      hi]") != 0) {
	testl	%eax, %eax	# tmp123
	jne	.L48	#,
# sources/vsprintf_percent_s.c:98:     fmt(buf, "[%-8s]", "ho");
	movq	%rsp, %rbx	#, tmp109
	leaq	.LC9(%rip), %rdx	#, tmp110
	leaq	.LC10(%rip), %rsi	#, tmp111
	movq	%rbx, %rdi	# tmp109,
	movl	$0, %eax	#,
	call	fmt	#
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	leaq	.LC11(%rip), %rsi	#, tmp115
	movq	%rbx, %rdi	# tmp109,
	call	strcmp@PLT	#
	movl	%eax, %ebx	# tmp124, <retval>
# sources/vsprintf_percent_s.c:99:     if (strcmp(buf, "[ho      ]") != 0) {
	testl	%eax, %eax	# <retval>
	jne	.L49	#,
# sources/vsprintf_percent_s.c:104:     puts("PASS: %s formatting reads the correct argument slot");
	leaq	.LC13(%rip), %rdi	#, tmp119
	call	puts@PLT	#
# sources/vsprintf_percent_s.c:105:     return 0;
	jmp	.L40	#
.L47:
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	%rsp, %rcx	#, tmp96
	leaq	.LC4(%rip), %rdx	#, tmp98
	movl	$2, %esi	#,
	movq	stderr(%rip), %rdi	# stderr,
	movl	$0, %eax	#,
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:89:         return 1;
	movl	$1, %ebx	#, <retval>
.L40:
# sources/vsprintf_percent_s.c:106: }
	movq	264(%rsp), %rax	# D.3840, tmp126
	subq	%fs:40, %rax	# MEM[(<address-space-1> long unsigned int *)40B], tmp126
	jne	.L50	#,
	movl	%ebx, %eax	# <retval>,
	addq	$272, %rsp	#,
	.cfi_remember_state
	.cfi_def_cfa_offset 16
	popq	%rbx	#
	.cfi_def_cfa_offset 8
	ret
.L48:
	.cfi_restore_state
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	%rsp, %rcx	#, tmp106
	leaq	.LC8(%rip), %rdx	#, tmp108
	movl	$2, %esi	#,
	movq	stderr(%rip), %rdi	# stderr,
	movl	$0, %eax	#,
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:95:         return 1;
	movl	$1, %ebx	#, <retval>
	jmp	.L40	#
.L49:
# /usr/include/x86_64-linux-gnu/bits/stdio2.h:79:   return __fprintf_chk (__stream, __USE_FORTIFY_LEVEL - 1, __fmt,
	movq	%rsp, %rcx	#, tmp116
	leaq	.LC12(%rip), %rdx	#, tmp118
	movl	$2, %esi	#,
	movq	stderr(%rip), %rdi	# stderr,
	movl	$0, %eax	#,
	call	__fprintf_chk@PLT	#
# sources/vsprintf_percent_s.c:101:         return 1;
	movl	$1, %ebx	#, <retval>
	jmp	.L40	#
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
