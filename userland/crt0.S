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
.section .text
.globl _entry

_entry:
    /* Zero BSS */
    movl    $_bss_start, %edi
    movl    $_bss_end, %ecx
    subl    %edi, %ecx
    xorl    %eax, %eax
    rep     stosb

    /* Call main(argc, argv) */
    popl    %eax                    /* argc */
    popl    %ebx                    /* argv */
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

.section .bss
.align 4
_bss_start:
    .skip 65536                     /* 64 KiB BSS */
_bss_end:
