#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Test creation of a multi-zone file in a single boot."""

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
    parser = argparse.ArgumentParser(description="Linux 0.01 large file test")
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

    nonce = "LARGE"
    begin = f"BEMU{nonce}START"
    end = f"BEMU{nonce}END"

    # Stay well under the bEMU keyboard queue by using a modest append chain.
    script_lines = [f"echo {begin}", "cd /tmp", "echo a0b1c2d3e4f5g6h7i8j9 > big.txt"]
    for _ in range(7):
        script_lines.append("echo a0b1c2d3e4f5g6h7i8j9 >> big.txt")
    script_lines.extend(["wc big.txt", f"echo {end}"])
    script = "\n".join(script_lines) + "\n"

    with tempfile.TemporaryDirectory(prefix="linux001-fs-large-") as temp_dir:
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
            print("large file test timed out")
            return 1

    output = sanitize_terminal(result.stdout)
    if result.returncode or BEMU_PASS_RE.search(output) is None:
        print(f"bEMU failed with status {result.returncode}")
        if args.verbose:
            print(output[-4000:])
        return 1
    if KERNEL_FAULT_RE.search(output):
        print("kernel fault during large file test")
        return 1

    seg = output[output.find(begin):output.find(end)]
    # wc output: lines words bytes
    if "168" not in seg:
        print("large file did not reach expected size")
        if args.verbose:
            print(seg[-1000:])
        return 1

    print("large file test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
