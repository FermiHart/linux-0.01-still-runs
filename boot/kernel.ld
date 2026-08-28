/*
 * kernel.ld — Linus' linux-0.01 kernel image, linked at physical 0.
 *
 * F E R M I ∞ H A R T <contact@fermihart.com>
 *
 * Layout dictated by boot/head.s (DO NOT CHANGE without rewriting head.s):
 *   0x0000  startup_32 code → becomes pg_dir at runtime (.org statements)
 *   0x1000  pg0
 *   0x2000  pg1
 *   0x3000  pg2  (reserved, unused)
 *   0x4000  after_page_tables (rest of kernel)
 *
 * Linked as ELF for symbol/debug ease; objcopy emits build/kernel.raw.
 * The build wraps that PA0 payload with a host-only length trailer in kernel.bin.
 *
 * NOTE: code is built with -fleading-underscore so C symbol `main` lands as
 * `_main`, which is exactly what head.s references.
 */
ENTRY(_startup_32)
OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)

SECTIONS
{
    . = 0;

    .text : {
        /* head.o MUST be first — its .org directives assume base = 0 */
        boot/head.o(.text)
        boot/head.o(.text.*)
        *(.text)
        *(.text.*)
    }

    .rodata : ALIGN(16) {
        *(.rodata)
        *(.rodata.*)
    }

    .data : ALIGN(16) {
        *(.data)
        *(.data.*)
    }

    .bss : ALIGN(16) {
        _bss_start = .;
        *(COMMON)
        *(.bss)
        *(.bss.*)
        . = ALIGN(4);
        _bss_end = .;
    }

    _end = .;
    end  = .;

    /DISCARD/ : {
        *(.eh_frame)
        *(.note.*)
        *(.comment)
        *(.debug*)
    }
}
