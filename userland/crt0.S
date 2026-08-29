/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/* crt0.S — Minimal C runtime for linux-0.01 userland programs.
 *
 * This is the entry point for C programs compiled as flat binaries.
 * The kernel's execve() sets up a stack with argc and argv;
 * we zero BSS, call main(), and exit with the return code.
 *
 * Assembled with x86_64-elf-as (GAS), linked at VMA 0.
 * CFLAGS include -fleading-underscore so C symbols are _main, _exit, etc.
 */

.code32
.section .text.startup
.globl _entry

_entry:
    /* Zero BSS */
    cld
    movl    $__bss_start, %edi
    movl    $_end, %ecx
    subl    %edi, %ecx
    xorl    %eax, %eax
    rep     stosb

    /* The a.out wrapper reserves enough BSS; expose only the linked extent. */
    movl    $_end, %ebx
    movl    $45, %eax               /* __NR_brk */
    int     $0x80

    /* The kernel's execve() builds: argc, argv, envp on the stack. */
    popl    %eax                    /* argc */
    popl    %ebx                    /* argv */
    popl    %ecx                    /* envp */
    pushl   %ecx
    pushl   %ebx
    pushl   %eax
    call    _main

    /* _exit(eax) */
    pushl   %eax
    movl    $1, %eax                /* __NR_exit */
    int     $0x80

    /* Should never reach here */
1:  hlt
    jmp     1b
