#!/usr/bin/env python3
"""
bootmon.py — Linux 0.01 Boot Monitor

Decodes the VGA text-mode markers written by the kernel during boot
and monitors QEMU output to track boot progress in real time.

The kernel writes single characters to VGA framebuffer at 0xB8000+offset
as it progresses through initialization. This tool reads either:
1. A QEMU serial log after the fact (offline mode)
2. Live QEMU serial output (monitor mode)

Usage:
    # Offline analysis of captured serial log
    python3 tools/bootmon.py build/serial.log

    # Live monitoring (requires QEMU with -serial file:...)
    python3 tools/bootmon.py --live build/serial.log

    # Annotated boot timeline
    python3 tools/bootmon.py --timeline build/serial.log
"""

import argparse
import os
import re
import sys
import time

# VGA marker map: character → offset → stage description
VGA_MARKERS = {
    'L': (0x00, 'Limine entry — bootstub loaded, about to relocate kernel'),
    'I': (0x02, 'Kernel Installed at physical address 0'),
    'N': (0x04, 'New GDT loaded — flat 4GiB code/data segments'),
    'U': (0x06, 'JUmp to physical 0 — control transferred to startup_32'),
    'P': (0x08, 'PIC reprogrammed IRQ0→0x20 (by bootstub)'),
    # head.s markers
    'S': (0x0A, 'Startup_32 — kernel entry point, setting up page tables'),
    'W': (0x0A, 'Paging enabled — CR0.PG=1, identity map 8 MiB'),
    # main.c markers
    'M': (0x0C, "main() entered — kernel C entry point"),
    'T': (0x0E, 'time_init() — CMOS RTC read, startup_time set'),
    'Y': (0x10, 'tty_init() — console + serial initialized'),
    'R': (0x12, 'trap_init() — IDT populated with real handlers'),
    'C': (0x14, 'sched_init() — scheduler, PIT timer, syscall gate'),
    'B': (0x16, 'buffer_init() — block buffer cache initialized'),
    'H': (0x18, 'hd_init() — ATA hard disk controller initialized'),
    'i': (0x1A, 'sti() — INTERRUPTS ENABLED (IF=1)'),
    'u': (0x1C, 'move_to_user_mode() — transitioned to ring 3'),
    'k': (0x1E, 'fork() — creating init process (task 1)'),
    'f': (0x1E, 'init process running (green "f")'),
    't': (0x20, 'timer_interrupt — first timer tick!'),
}

# Additional kernel printk patterns for timeline
PRINTK_PATTERNS = [
    (r'(\d+)\s+buffers\s*=\s*(\d+)\s+bytes', 'buffer_cache_size'),
    (r'Ok\.', 'root_mounted'),
    (r'child\s+(\d+)\s+died', 'init_exit'),
    (r'panic', 'KERNEL_PANIC'),
    (r'divide error', 'divide_error'),
]


def decode_vga_marker(char):
    """Look up what a VGA marker character means."""
    if char in VGA_MARKERS:
        offset, desc = VGA_MARKERS[char]
        col = offset // 2
        return col, desc
    return None, f"Unknown marker '{char}' (0x{ord(char):02x})"


def parse_vga_markers_from_serial(content):
    """Parse VGA markers from serial content by looking for known chars."""
    markers_found = []
    for line in content.split('\n'):
        for char, (offset, desc) in VGA_MARKERS.items():
            if char in line and desc not in [m[1] for m in markers_found]:
                # Check if it's likely a marker (stands alone)
                markers_found.append((char, offset, desc))
                break
    return markers_found


def parse_vga_markers_from_qemu_log(content):
    """Parse VGA framebuffer dumps from QEMU logs."""
    markers_found = set()
    # Try to find VGA memory writes in log
    for match in re.finditer(r'0xB800[0-9A-Fa-f]{2}\s*=\s*0x[0-9A-Fa-f]{4}', content):
        markers_found.add(match.group())
    return markers_found


def generate_timeline(content):
    """Generate a timeline from serial log content."""
    timeline = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Check for known printk patterns
        for pattern, label in PRINTK_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                timeline.append((i, line.strip(), label))
                break

        # Check for marker chars
        for char, (offset, desc) in VGA_MARKERS.items():
            if char in line and len(line.strip()) < 10:
                timeline.append((i, line.strip(), desc))
                break

    return timeline


def live_monitor(serial_path):
    """Monitor serial log file for new markers in real time."""
    if not os.path.exists(serial_path):
        print(f"  ✗ Serial log not found: {serial_path}")
        print(f"    Start QEMU with: -serial file:{serial_path}")
        sys.exit(1)

    print(f"  ◄ Monitoring {serial_path} (Ctrl-C to stop)")
    print()
    last_size = 0
    seen_markers = set()

    try:
        while True:
            try:
                size = os.path.getsize(serial_path)
                if size > last_size:
                    with open(serial_path, 'r') as f:
                        f.seek(last_size)
                        new_data = f.read()
                        for char in new_data:
                            if char in VGA_MARKERS and char not in seen_markers:
                                col, desc = VGA_MARKERS[char][0], VGA_MARKERS[char][1]
                                status = '✓' if col >= 0x1A else '◄'
                                print(f"  {status} [{char}] col+{col:02x}  {desc}")
                                seen_markers.add(char)
                        last_size = size
                time.sleep(0.1)
            except (IOError, FileNotFoundError):
                time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n  ◄ Monitoring stopped.")
        print(f"  ◄ {len(seen_markers)}/{len(VGA_MARKERS)} markers seen")


def main():
    parser = argparse.ArgumentParser(
        description='Linux 0.01 Boot Monitor — decode VGA boot markers')
    parser.add_argument('logfile', nargs='?', default='build/serial.log',
                        help='Path to QEMU serial log (default: build/serial.log)')
    parser.add_argument('--live', '-l', action='store_true',
                        help='Live monitor mode (tail -f equivalent)')
    parser.add_argument('--timeline', '-t', action='store_true',
                        help='Generate annotated boot timeline')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all raw lines with markers')
    args = parser.parse_args()

    if args.live:
        live_monitor(args.logfile)
        return

    if not os.path.exists(args.logfile):
        print(f"  ✗ File not found: {args.logfile}")
        print(f"    Run 'make run' first to generate boot output.")
        sys.exit(1)

    with open(args.logfile, 'r') as f:
        content = f.read()

    if args.timeline:
        print(f"\n  ╔══════════════════════════════════════════════════════╗")
        print(f"  ║         Linux 0.01 Boot Timeline                    ║")
        print(f"  ╚══════════════════════════════════════════════════════╝\n")
        timeline = generate_timeline(content)
        if not timeline:
            print("  (no patterns matched — boot may not have completed)")
        for line_num, line_text, desc in timeline:
            print(f"  ◄ {desc}")
            if args.verbose:
                print(f"    └─ line {line_num}: {line_text}")
        print()
        return

    # Default: decode mode
    markers_found = []

    # Search for markers in content
    seen = set()
    for char, (offset, desc) in sorted(VGA_MARKERS.items(), key=lambda x: x[1][0]):
        if char in content:
            markers_found.append((char, offset, desc))
            seen.add(char)

    print(f"\n  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║         VGA Boot Marker Decoder                      ║")
    print(f"  ╚══════════════════════════════════════════════════════╝\n")

    # Print decoded markers
    all_markers = [(c, o, d) for c, (o, d) in VGA_MARKERS.items()]
    all_markers.sort(key=lambda x: x[1])

    boot_complete = True
    for char, offset, desc in all_markers:
        found = char in seen
        symbol = '✓' if found else ' '
        if char == 'L' and found:
            symbol = '●'
        elif char in ('f', 't') and found:
            symbol = '◉'
        col = offset // 2
        print(f"  [{symbol}] [{char}] col={col:2d}  0xB800{offset:04X}  {desc}")
        if not found and offset <= 0x1E:
            boot_complete = False

    # Boot stages
    print(f"\n  ── Boot Stages ──")
    L_found = 'L' in seen
    M_found = 'M' in seen
    i_found = 'i' in seen
    u_found = 'u' in seen
    k_found = 'k' in seen

    print(f"  {'✓' if L_found else '○'} bootstub (Limine entry → kernel @ phys 0)")
    print(f"  {'✓' if M_found else '○'} main()  (kernel C entry → subsystem init)")
    print(f"  {'✓' if i_found else '○'} sti()   (interrupts enabled)")
    print(f"  {'✓' if u_found else '○'} user    (ring 3 transition)")
    print(f"  {'✓' if k_found else '○'} fork    (init process spawned)")

    if 'f' in seen:
        print(f"  {'✓' if 'f' in seen else '○'} init    (init process running)")
    if 't' in seen:
        print(f"  {'✓' if 't' in seen else '○'} timer   (timer interrupt handler executing)")

    if boot_complete:
        print(f"\n  ● BOOT COMPLETE — all stages reached")
    else:
        print(f"\n  ○ BOOT INCOMPLETE — kernel stalled or crashed")
        if 'i' in seen and not 'u' in seen:
            print(f"    Hint: interrupts on, but move_to_user_mode() failed")
        elif M_found and not i_found:
            print(f"    Hint: subsystem init may have crashed. Check trap_init/sched_init")

    print()


if __name__ == '__main__':
    main()
