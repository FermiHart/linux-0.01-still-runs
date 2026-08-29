/*
 * Author: F E R M I INFINITY H A R T <contact@fermihart.com>
 * SPDX-License-Identifier: Unlicense
 */

/*
 *  vga_text50.c
 *
 * Switch VGA from default 80x25 to 80x50 in standard text mode (0xB8000
 * buffer). We carry a PC-compatible 8x8 font as embedded data (see
 * vga_font8x8.h) and write it into
 * plane 2 at offset 0x8000 (font slot 2) at boot. Then we point the
 * Character Map Select at slot 2 and halve the CRTC max scan line.
 *
 * Why embedded and not a firmware font: the direct KVM machine has no BIOS
 * font loaded but not the 8x8 — slot 2 of plane 2 is empty at boot.
 * Earlier attempts at downsampling 8x16 -> 8x8 in software produced
 * either broken glyphs (every-other-row dropped cross-bars) or unreadably
 * thick ones (OR-fold blurred letters together). A properly designed
 * 8x8 font simply renders cleaner.
 *
 * Must run before kernel/console.c con_init() so its geometry is set up
 * for LINES=50.
 *
 * F E R M I ∞ H A R T
 */
#include <asm/io.h>
#include "vga_font8x8.h"

#define PLANE2 ((unsigned char *)0xA0000)

void vga_set_50_rows(void)
{
	unsigned char saved_s2, saved_s4, saved_g4, saved_g5, saved_g6;
	unsigned char msl;
	int c, r;

	/* Stash the sequencer + graphics-controller bits we're about to
	 * stomp on so we can restore the text-mode display afterwards. */
	outb_p(0x02, 0x3C4); saved_s2 = inb_p(0x3C5);
	outb_p(0x04, 0x3C4); saved_s4 = inb_p(0x3C5);
	outb_p(0x04, 0x3CE); saved_g4 = inb_p(0x3CF);
	outb_p(0x05, 0x3CE); saved_g5 = inb_p(0x3CF);
	outb_p(0x06, 0x3CE); saved_g6 = inb_p(0x3CF);

	/* Sequencer: write to plane 2 only; sequential addressing, odd/even
	 * disabled, extended memory enabled. */
	outb_p(0x02, 0x3C4); outb_p(0x04, 0x3C5);
	outb_p(0x04, 0x3C4); outb_p(0x07, 0x3C5);

	/* Graphics controller: read from plane 2; mode 0 read & write, no
	 * odd/even; map 64K window at A0000 in linear graphics layout. */
	outb_p(0x04, 0x3CE); outb_p(0x02, 0x3CF);
	outb_p(0x05, 0x3CE); outb_p(0x00, 0x3CF);
	outb_p(0x06, 0x3CE); outb_p(0x04, 0x3CF);

	/* Write the embedded PC-compatible 8x8 font into slot 2 at offset
	 * 0x8000. Each slot reserves 32 bytes per glyph; we use the first 8
	 * and leave the rest at whatever it was (the CRTC only reads the
	 * first MSL+1 = 8 rows so the tail is invisible). */
	for (c = 0; c < 256; c++) {
		unsigned char *dst = PLANE2 + 0x8000 + (c * 32);
		for (r = 0; r < 8; r++)
			dst[r] = vga_font8x8[c][r];
	}

	/* Restore text-mode access pattern. */
	outb_p(0x04, 0x3CE); outb_p(saved_g4, 0x3CF);
	outb_p(0x05, 0x3CE); outb_p(saved_g5, 0x3CF);
	outb_p(0x06, 0x3CE); outb_p(saved_g6, 0x3CF);
	outb_p(0x02, 0x3C4); outb_p(saved_s2, 0x3C5);
	outb_p(0x04, 0x3C4); outb_p(saved_s4, 0x3C5);

	/* Point both Character Map A and Map B at font slot 2 (offset 0x8000
	 * — our freshly-written 8x8 set). Sequencer reg 3 encoding: bits
	 * 5,3 = Map A; bits 4,1 = Map B; bit pattern for slot 2 = 0x0A. */
	outb_p(0x03, 0x3C4);
	outb_p(0x0A, 0x3C5);

	/* CRTC Max Scan Line: cell height 8 (was 16). Preserve bits 5-7 —
	 * they carry vertical timing. */
	outb_p(0x09, 0x3D4);
	msl = inb_p(0x3D5);
	outb_p((msl & 0xE0) | 0x07, 0x3D5);

	/* Cursor scan start/end inside the new 8-pixel cell. */
	outb_p(0x0A, 0x3D4); outb_p(0x06, 0x3D5);
	outb_p(0x0B, 0x3D4); outb_p(0x07, 0x3D5);

	/* Sequencer reg 1 (Clocking Mode) bit 0: 0 = 9-dot character clock
	 * (default — gives a 1-pixel padding column between glyphs); 1 = 8-dot
	 * (glyphs sit edge-to-edge). Going 8-dot shrinks total screen width
	 * 720 -> 640 pixels and removes the inter-character gap, making the
	 * text feel slightly tighter / smaller. */
	outb_p(0x01, 0x3C4);
	{
		unsigned char clk = inb_p(0x3C5);
		outb_p(clk | 0x01, 0x3C5);
	}
}
