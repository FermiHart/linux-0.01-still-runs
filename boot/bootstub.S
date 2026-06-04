/*
 * bootstub.S — Limine multiboot2 entry; relocates Linus' kernel to phys 0.
 *
 * F E R M I ∞ H A R T <contact@fermihart.com>
 *
 * Linus' original linux-0.01 hardcodes pg_dir at physical address 0
 * (see mm/memory.c — every page-table dereference does
 * `(addr>>20) & 0xffc`, treating PA 0 as the base of pg_dir).
 * Limine cannot load below 1MB, so we use the multiboot2 module
 * mechanism: Limine loads kernel.bin as a module somewhere high,
 * and this stub memcpy's it down to physical 0 then far-jumps.
 *
 * Early serial console: we initialize COM1 (0x3F8) and write all
 * boot markers to serial in addition to VGA. This enables QEMU
 * to capture boot progress with -serial stdio or -serial file:.
 *
 * Multiboot2 hand-off state (per spec §3.3):
 *   EAX = 0x36d76289 (magic)
 *   EBX = physical address of multiboot2 info struct
 *   CS  = flat 32-bit code segment, base=0, limit=4GiB
 *   DS/ES/FS/GS/SS = flat 32-bit data segments
 *   Paging OFF
 */

.set MB2_MAGIC,        0xe85250d6
.set MB2_ARCH_I386,    0
.set MB2_BOOT_MAGIC,   0x36d76289

.set TAG_END,          0
.set TAG_MODULES,      3

/* ------------------------------------------------------------------ */
.section .multiboot2, "a"
.align 8
mb2_hdr:
    .long   MB2_MAGIC
    .long   MB2_ARCH_I386
    .long   mb2_hdr_end - mb2_hdr
    .long   -(MB2_MAGIC + MB2_ARCH_I386 + (mb2_hdr_end - mb2_hdr))
    /* end tag */
    .align  8
    .word   0
    .word   0
    .long   8
mb2_hdr_end:

/* ------------------------------------------------------------------ */
.section .bss
.align 16
    .skip 16384
stack_top:

/* ------------------------------------------------------------------ */
.section .text.entry, "ax"
.code32
.globl _start
_start:
    cli
    cld
    movl    $stack_top, %esp

    /* Initialize serial port (COM1 @ 0x3F8) for early console output */
    call    serial_init

    /* Verify multiboot2 magic */
    cmpl    $MB2_BOOT_MAGIC, %eax
    jne     hang
    movl    %ebx, %edi              /* %edi = ptr to mb2 info */

    /* Skip total_size(4) + reserved(4) — first tag is at offset 8 */
    addl    $8, %edi

scan_tags:
    movl    (%edi), %eax            /* tag type */
    movl    4(%edi), %ecx           /* tag size */
    cmpl    $TAG_END, %eax
    je      hang                    /* no module found */
    cmpl    $TAG_MODULES, %eax
    jne     next_tag

    /* Module tag layout:
     *   u32 type=3
     *   u32 size
     *   u32 mod_start
     *   u32 mod_end
     *   u8  string[]
     * We take the first module unconditionally.
     */
    movl    8(%edi),  %esi          /* mod_start (src) */
    movl    12(%edi), %edx          /* mod_end */
    subl    %esi, %edx              /* %edx = byte count */
    jmp     do_copy

next_tag:
    /* Tags are 8-byte aligned */
    addl    $7, %ecx
    andl    $-8, %ecx
    addl    %ecx, %edi
    jmp     scan_tags

    /* Marker macro: write CHAR to VGA (attr=0x0B) at OFFSET and to serial.
       VGA text mode word: low byte = char, high byte = attribute.
       So value = (attr << 8) | char = 0x0B00 | char. */
    .macro marker char, offset
    movw    $(0x0B00 | \char), 0xB8000 + \offset
    pushal
    pushf
    movb    $\char, %al
    call    serial_putchar
    popf
    popal
    .endm

do_copy:
    marker 'L', 0

    /* memcpy(0, mod_start, mod_end-mod_start) */
    xorl    %edi, %edi              /* dest = 0 */
    movl    %edx, %ecx
    /* rep movsb is fine — 1MB-ish, not perf-critical */
    rep     movsb

    marker 'I', 2

    /* Install bridge GDT matching Linus' layout */
    lgdt    bridge_gdtr
    ljmp    $0x08, $jump_to_kernel
.code32
jump_to_kernel:
    marker 'N', 4

    /* Reload data segments to flat data selector */
    movw    $0x10, %ax
    movw    %ax, %ds
    movw    %ax, %es
    movw    %ax, %fs
    movw    %ax, %gs
    movw    %ax, %ss
    movl    $stack_top, %esp

    marker 'U', 6

    /*
     * Re-program the 8259 PICs so IRQ 0..15 land at vectors 0x20..0x2F
     * (Linus' original boot.s did this; we replaced boot.s so we redo it).
     * Without this, Limine leaves IRQ0 = vector 0x08 (= #DF in IDT later),
     * which triple-faults the kernel as soon as sti() runs.
     */
    movb    $0x11, %al              /* ICW1: cascade, ICW4 needed */
    outb    %al, $0x20
    .word   0x00eb, 0x00eb
    outb    %al, $0xA0
    .word   0x00eb, 0x00eb
    movb    $0x20, %al              /* ICW2 PIC1: vec base 0x20 */
    outb    %al, $0x21
    .word   0x00eb, 0x00eb
    movb    $0x28, %al              /* ICW2 PIC2: vec base 0x28 */
    outb    %al, $0xA1
    .word   0x00eb, 0x00eb
    movb    $0x04, %al              /* ICW3 PIC1: slave on IRQ2 */
    outb    %al, $0x21
    .word   0x00eb, 0x00eb
    movb    $0x02, %al              /* ICW3 PIC2: cascade ident */
    outb    %al, $0xA1
    .word   0x00eb, 0x00eb
    movb    $0x01, %al              /* ICW4: 8086 mode */
    outb    %al, $0x21
    .word   0x00eb, 0x00eb
    outb    %al, $0xA1
    .word   0x00eb, 0x00eb
    movb    $0xFF, %al              /* mask off ALL IRQs initially */
    outb    %al, $0x21
    .word   0x00eb, 0x00eb
    outb    %al, $0xA1

    marker 'P', 8

    /* Final serial newline before jumping to kernel */
    movb    $0x0D, %al
    call    serial_putchar
    movb    $0x0A, %al
    call    serial_putchar

    /* Far-jump to physical 0 — that's where _pg_dir / startup_32 lives */
    ljmp    $0x08, $0x00000000

hang:
    cli
1:  hlt
    jmp     1b

/* ------------------------------------------------------------------ */
/* Serial port functions                                              */
/* COM1 at I/O base 0x3F8, IRQ 4. 16550 UART.                        */
/* ------------------------------------------------------------------ */

/* Use DX for port I/O (COM1 = 0x3F8 is above 0xFF, needs DX form) */
serial_out:
    .word   0x00eb, 0x00eb
    outb    %al, %dx
    .word   0x00eb, 0x00eb
    addl    $1, %edx
    ret

serial_init:
    pushal
    movl    $0x3F8, %edx
    addl    $1, %edx                /* IER = 0x3F9 */
    movb    $0x00, %al              /* DLAB=0, disable interrupts */
    call    serial_out
    movl    $0x3F8, %edx
    addl    $3, %edx                /* LCR = 0x3FB */
    movb    $0x80, %al              /* DLAB=1 (set divisor) */
    call    serial_out
    movl    $0x3F8, %edx            /* DLL = 0x3F8 */
    movb    $0x01, %al              /* divisor = 1 → 115200 baud */
    call    serial_out
    movl    $0x3F8, %edx
    addl    $1, %edx                /* DLM = 0x3F9 */
    movb    $0x00, %al              /* divisor high byte */
    call    serial_out
    movl    $0x3F8, %edx
    addl    $3, %edx                /* LCR = 0x3FB */
    movb    $0x03, %al              /* 8N1, DLAB=0 */
    call    serial_out
    movl    $0x3F8, %edx
    addl    $2, %edx                /* FCR = 0x3FA */
    movb    $0x0C, %al              /* FIFO enable, 14-byte threshold */
    call    serial_out
    movl    $0x3F8, %edx
    addl    $4, %edx                /* MCR = 0x3FC */
    movb    $0x07, %al              /* RTS/DTR */
    call    serial_out
    popal
    ret

/* Transmit one character in AL via COM1. Waits for THR empty. */
serial_putchar:
    pushal
    pushf
    movl    $0x3F8, %edx
    movb    %al, %bh                /* preserve character in BH */
    /* Wait for THR empty (LSR bit 5 at 0x3FD) */
1:  movl    $0x3F8, %edx
    addl    $5, %edx                /* LSR = 0x3FD */
    inb     %dx, %al
    .word   0x00eb, 0x00eb
    testb   $0x20, %al              /* THR empty? */
    jz      1b
    movl    $0x3F8, %edx            /* THR = 0x3F8 */
    movb    %bh, %al                /* restore character */
    outb    %al, %dx
    .word   0x00eb, 0x00eb
    cmpb    $0x0A, %al              /* if newline, send CR too */
    jne     2f
    movb    $0x0D, %al
    outb    %al, %dx
    .word   0x00eb, 0x00eb
2:  popf
    popal
    ret

/* ------------------------------------------------------------------ */
.section .data
.align 16
bridge_gdt:
    .quad   0x0000000000000000      /* 0x00 NULL */
    .quad   0x00cf9a000000ffff      /* 0x08 flat 4G code R/X DPL=0 */
    .quad   0x00cf92000000ffff      /* 0x10 flat 4G data R/W DPL=0 */
bridge_gdt_end:

bridge_gdtr:
    .word   bridge_gdt_end - bridge_gdt - 1
    .long   bridge_gdt
