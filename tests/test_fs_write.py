#!/usr/bin/env python3
"""Test real filesystem write, append and truncate in a single boot."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    sanitize_terminal,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 fs write/append/truncate test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1

    nonce = "WRITE"
    begin = f"BEMU{nonce}START"
    end = f"BEMU{nonce}END"

    script = (
        f"echo {begin}\n"
        "cd /tmp\n"
        "echo first > t.txt\n"
        "echo second >> t.txt\n"
        "cat t.txt\n"
        "echo short > t.txt\n"
        "cat t.txt\n"
        f"echo {end}\n"
    )

    with tempfile.TemporaryDirectory(prefix="linux001-fs-write-") as temp_dir:
        root_copy = os.path.join(temp_dir, "root.img")
        shutil.copyfile(args.img, root_copy)
        command = [
            args.bemu, "--kernel", args.kernel, "--root", root_copy,
            "--keys", script, "--expect", end,
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
        except subprocess.TimeoutExpired:
            print("fs write test timed out")
            return 1

    output = sanitize_terminal(result.stdout)
    if result.returncode or BEMU_PASS_RE.search(output) is None:
        print(f"bEMU failed with status {result.returncode}")
        if args.verbose:
            print(output[-4000:])
        return 1
    if KERNEL_FAULT_RE.search(output):
        print("kernel fault during fs write test")
        return 1

    if begin not in output or end not in output:
        print("missing markers in output")
        if args.verbose:
            print(output[-2000:])
        return 1

    seg = output[output.find(begin):output.find(end)]
    first_pos = seg.find("first")
    second_pos = seg.find("second")
    short_pos = seg.find("short")
    if first_pos < 0 or second_pos < 0 or short_pos < 0:
        print("missing expected content")
        if args.verbose:
            print(seg[-1000:])
        return 1
    if not (first_pos < second_pos < short_pos):
        print("content order wrong")
        return 1
    # Ensure 'second' does not appear after 'short' (truncate worked)
    if seg[short_pos:].find("second") >= 0:
        print("truncate did not overwrite file")
        return 1

    print("fs write/append/truncate test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
