#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Test real link/unlink/rename in a single boot."""

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
    parser = argparse.ArgumentParser(description="Linux 0.01 link/unlink/rename test")
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

    nonce = "LINK"
    begin = f"BEMU{nonce}START"
    end = f"BEMU{nonce}END"

    script = (
        f"echo {begin}\n"
        "cd /tmp\n"
        "echo original > a\n"
        "ln a b\n"
        "cat b\n"
        "rm a\n"
        "cat b\n"
        "mv b c\n"
        "cat c\n"
        f"echo {end}\n"
    )

    with tempfile.TemporaryDirectory(prefix="linux001-fs-link-") as temp_dir:
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
            print("link test timed out")
            return 1

    output = sanitize_terminal(result.stdout)
    if result.returncode or BEMU_PASS_RE.search(output) is None:
        print(f"bEMU failed with status {result.returncode}")
        if args.verbose:
            print(output[-4000:])
        return 1
    if KERNEL_FAULT_RE.search(output):
        print("kernel fault during link test")
        return 1

    seg = output[output.find(begin):output.find(end)]
    if seg.count("original") < 3:
        print("link/unlink/rename did not preserve content")
        if args.verbose:
            print(seg[-1000:])
        return 1

    print("link/unlink/rename test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
