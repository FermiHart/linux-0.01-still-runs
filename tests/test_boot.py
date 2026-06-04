#!/usr/bin/env python3
"""
test_boot.py — QEMU Boot Test Harness for linux-0.01-still-runs.

Verifies the kernel boots successfully by:
1. Launching QEMU with the built ISO + root filesystem
2. Capturing serial output
3. Checking for boot progress markers

Usage:
    python3 tests/test_boot.py [--iso build/linux-0.01.iso] [--img build/root.img]
                              [--timeout 30] [--verbose]

Returns exit code 0 on success, 1 on failure.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import re


SERIAL_PATTERNS = [
    (r'LINUP', 'Bootstub markers'),
    (r'Partition table [a-z]+\.', 'Partition table read'),
    (r'free blocks', 'Filesystem stats visible'),
    (r'free inodes', 'Filesystem inodes visible'),
]


def parse_args():
    parser = argparse.ArgumentParser(description='Linux 0.01 Boot Test Harness')
    parser.add_argument('--iso', default='build/linux-0.01.iso',
                        help='Path to ISO (default: build/linux-0.01.iso)')
    parser.add_argument('--img', default='build/root.img',
                        help='Path to root disk image (default: build/root.img)')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Boot timeout in seconds (default: 30)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show all captured output')
    parser.add_argument('--qemu', default='qemu-system-i386',
                        help='QEMU binary (default: qemu-system-i386)')
    return parser.parse_args()


def run_qemu(args, serial_log):
    """Launch QEMU and capture serial output to a file."""
    qemu_args = [
        args.qemu,
        '-cdrom', args.iso,
        '-drive', f'file={args.img},format=raw,if=none,id=hd0',
        '-device', 'ide-hd,drive=hd0,bus=ide.0,unit=0,cyls=977,heads=5,secs=17',
        '-boot', 'd',
        '-m', '8M',
        '-no-reboot',
        '-nographic',
        '-d', 'guest_errors,int',
        '-D', os.path.join(os.path.dirname(serial_log), 'qemu_test.log'),
        '-serial', f'file:{serial_log}',
        '-display', 'none',
    ]

    if args.verbose:
        print(f"  ◄ Launching: {' '.join(qemu_args)}")

    proc = subprocess.Popen(
        qemu_args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def check_serial_patterns(content):
    """Check expected patterns in serial output."""
    results = []
    for pattern, description in SERIAL_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            results.append((description, True))
        else:
            results.append((description, False))
    return results


def check_triple_fault(qemu_log):
    """Check QEMU debug log for triple faults or resets."""
    try:
        with open(qemu_log, 'r') as f:
            log = f.read()
        if 'Triple Fault' in log or 'CPU Reset' in log or 'guest reset' in log.lower():
            return True, log
        return False, log
    except FileNotFoundError:
        return False, ""


def main():
    args = parse_args()

    if not os.path.exists(args.iso):
        print(f"  ✗ ISO not found: {args.iso}")
        print(f"    Run 'make' first to build.")
        sys.exit(1)

    if not os.path.exists(args.img):
        print(f"  ✗ Root image not found: {args.img}")
        sys.exit(1)

    root_tmp = tempfile.TemporaryDirectory(prefix='linux001-boot-')
    root_copy = os.path.join(root_tmp.name, 'root.img')
    shutil.copyfile(args.img, root_copy)
    args.img = root_copy

    with tempfile.NamedTemporaryFile(suffix='.log', delete=False, mode='w') as f:
        serial_log = f.name

    qemu_log = os.path.join(os.path.dirname(serial_log), 'qemu_test.log')

    if args.verbose:
        print(f"\n  ◄ Serial log: {serial_log}")
        print(f"  ◄ QEMU log:   {qemu_log}")
        print(f"  ◄ Timeout:    {args.timeout}s\n")

    print("  Starting QEMU boot test...")
    proc = run_qemu(args, serial_log)

    # Wait for QEMU to finish or timeout
    start = time.time()
    poll_interval = 0.5
    boot_detected = False
    while time.time() - start < args.timeout:
        ret = proc.poll()
        if ret is not None:
            elapsed = time.time() - start
            if args.verbose:
                print(f"  ◄ QEMU exited with code {ret} after {elapsed:.1f}s")
            break
        # Check serial log for boot progress
        try:
            with open(serial_log, 'r') as f:
                content = f.read()
            if 'free inodes' in content:
                if not boot_detected:
                    boot_detected = True
                    if args.verbose:
                        print(f"  ◄ Boot progress detected after {time.time() - start:.1f}s")
        except (FileNotFoundError, IOError):
            pass
        time.sleep(poll_interval)
    else:
        elapsed = time.time() - start
        if not boot_detected:
            print(f"  ✗ Timeout after {elapsed:.1f}s — no boot progress detected")
        else:
            if args.verbose:
                print(f"  ◄ Timeout after {elapsed:.1f}s (kernel running idle)")
        proc.kill()
        proc.wait()

    # Collect results
    triple_fault, qemu_log_content = check_triple_fault(qemu_log)

    try:
        with open(serial_log, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    serial_results = check_serial_patterns(content)

    # Print results
    print(f"\n  {'=' * 50}")
    print(f"  BOOT TEST RESULTS")
    print(f"  {'=' * 50}")

    # Check for triple fault (fatal)
    if triple_fault:
        print(f"  ✗ TRIPLE FAULT detected! Kernel crashed.")
        if args.verbose:
            print(f"\n  QEMU log excerpt:")
            for line in qemu_log_content.split('\n')[-20:]:
                print(f"    {line}")
        cleanup(serial_log)
        sys.exit(1)

    # Check serial patterns
    all_ok = True
    for desc, ok in serial_results:
        status = '✓' if ok else '○'
        print(f"  {status} {desc}")
        if not ok:
            all_ok = False

    if not serial_results:
        all_ok = False

    # Check for boot markers
    boot_markers = []
    if 'LINUP' in content:
        boot_markers.append("Bootstub markers (LINUP)")
    if 'Partition table' in content:
        boot_markers.append("Partition table read")
    if 'free blocks' in content:
        boot_markers.append("Filesystem mounted")
    if 'free inodes' in content:
        boot_markers.append("Filesystem inodes OK")

    for m in boot_markers:
        print(f"  ✓ {m}")
    if not boot_markers:
        print(f"  ○ No boot progress markers found")
        all_ok = False

    # Print last lines of serial output (excluding terminal escape junk)
    if args.verbose and content:
        clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', content)
        lines = clean.strip().split('\n')
        meaningful = [l for l in lines if l.strip() and not l.startswith('\x1b')]
        if meaningful:
            print(f"\n  Serial output (last {min(8, len(meaningful))} lines):")
            for line in meaningful[-8:]:
                print(f"    | {line.strip()}")

    cleanup(serial_log)

    if all_ok:
        print(f"\n  ✓ BOOT TEST PASSED")
        sys.exit(0)
    else:
        print(f"\n  ✗ BOOT TEST FAILED")
        sys.exit(1)


def cleanup(serial_log):
    try:
        os.unlink(serial_log)
    except OSError:
        pass


if __name__ == '__main__':
    main()
