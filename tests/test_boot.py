#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Boot Linux 0.01 directly through bEMU and validate serial milestones."""

import argparse
import os
import re
import subprocess
import sys

from harness_utils import BEMU_PASS_RE, KERNEL_FAULT_RE, diagnostic, sanitize_terminal


PATTERNS = [
    (r"^\[bemu-linux01\] BBP @ 0xc0000: 5 tags(?:,.*)?$", "bEMU produced BBP"),
    (r"^\[bbp\] bEMU handoff: ok(?:,.*)?$", "Kernel validated BBP"),
    (r"^Partition table [^\n]*ok\.$", "Partition table read"),
    (r"^[0-9]+/[0-9]+ free blocks$", "Filesystem blocks visible"),
    (r"^[0-9]+/[0-9]+ free inodes$", "Filesystem inodes visible"),
    (r"^root@linux01:/[^\n]*# ?$", "Shell prompt reached"),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 bEMU boot test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"  missing artifact: {diagnostic(path, 1000)}")
            return 1

    command = [
        args.bemu,
        "--kernel", args.kernel,
        "--root", args.img,
        "--expect", "root@linux01",
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"  bEMU timed out after {args.timeout}s")
        if args.verbose and exc.stdout:
            print(diagnostic(exc.stdout, 3000))
        return 1
    except OSError as exc:
        print(f"  failed to run bEMU: {diagnostic(exc, 1000)}")
        return 1

    output = sanitize_terminal(result.stdout)
    failed = False
    for pattern, description in PATTERNS:
        ok = re.search(pattern, output, re.IGNORECASE | re.MULTILINE) is not None
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok
    pass_seen = BEMU_PASS_RE.search(output) is not None
    print(f"  {'ok' if pass_seen else 'FAIL'}  bEMU completed")
    failed |= not pass_seen
    if result.returncode:
        print(f"  FAIL  bEMU exited with {result.returncode}")
        failed = True
    if KERNEL_FAULT_RE.search(output):
        print("  FAIL  kernel fault detected")
        failed = True

    script_command = [
        args.bemu,
        "--kernel", args.kernel,
        "--root", args.img,
        "--keys", "echo BEMU_SCRIPT_FIRST\necho BEMU_SCRIPT_LAST\n",
    ]
    try:
        script_result = subprocess.run(
            script_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        script_output = sanitize_terminal(script_result.stdout)
        script_ok = (
            script_result.returncode == 0
            and re.search(r"^BEMU_SCRIPT_LAST$", script_output, re.MULTILINE)
            and BEMU_PASS_RE.search(script_output)
            and not KERNEL_FAULT_RE.search(script_output)
        )
    except (subprocess.TimeoutExpired, OSError):
        script_ok = False
    print(f"  {'ok' if script_ok else 'FAIL'}  bEMU consumed complete key script")
    failed |= not script_ok

    stdin_command = [
        args.bemu,
        "--kernel", args.kernel,
        "--root", args.img,
        "--expect", "HOST_INPUT_DONE",
    ]
    try:
        stdin_result = subprocess.run(
            stdin_command,
            input=(
                "echo HOST_OLD\n"
                "echo HOST_NEW\n"
                "\x1b[A\x1b[A\x1b[B\n"
                "echo HOST_BACKSPACX\x7fE\n"
                "echo HOST_INPUT_DONE\n"
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        stdin_output = sanitize_terminal(stdin_result.stdout)
        stdin_ok = (
            stdin_result.returncode == 0
            and len(re.findall(r"^HOST_OLD$", stdin_output, re.MULTILINE)) == 1
            and len(re.findall(r"^HOST_NEW$", stdin_output, re.MULTILINE)) == 2
            and re.search(r"^HOST_BACKSPACE$", stdin_output, re.MULTILINE)
            and BEMU_PASS_RE.search(stdin_output)
            and not KERNEL_FAULT_RE.search(stdin_output)
        )
    except (subprocess.TimeoutExpired, OSError):
        stdin_ok = False
    print(f"  {'ok' if stdin_ok else 'FAIL'}  host arrow input recalls history")
    failed |= not stdin_ok
    if failed and args.verbose:
        print(output[-4000:])
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
