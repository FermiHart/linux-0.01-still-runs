/*
 * bootstub.ld — Limine multiboot2 stub linked at 1 MiB.
 * F E R M I ∞ H A R T <contact@fermihart.com>
 */
ENTRY(_start)
OUTPUT_FORMAT(elf32-i386)
OUTPUT_ARCH(i386)

PHDRS
{
    text   PT_LOAD FLAGS(5);  /* R-X */
    rodata PT_LOAD FLAGS(4);  /* R-- */
    data   PT_LOAD FLAGS(6);  /* RW- */
}

SECTIONS
{
    . = 0x100000;

    .multiboot2 : ALIGN(8) { KEEP(*(.multiboot2)) } :text
    .text       : ALIGN(16) {
        *(.text.entry)
        *(.text .text.*)
    } :text

    .rodata     : ALIGN(16) { *(.rodata .rodata.*) } :rodata

    .data       : ALIGN(16) { *(.data .data.*) } :data
    .bss        : ALIGN(16) {
        *(COMMON)
        *(.bss .bss.*)
    } :data

    /DISCARD/ : { *(.eh_frame) *(.note.*) *(.comment) }
}
