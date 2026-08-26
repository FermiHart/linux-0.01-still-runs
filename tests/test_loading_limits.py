#!/usr/bin/env python3
"""Verify invalid kernels are rejected before KVM entry."""

import argparse
import os
import subprocess
import sys
import tempfile

from harness_utils import diagnostic, sanitize_terminal

KERNEL_MAX = 512 << 10


def main():
    parser = argparse.ArgumentParser(description="bEMU loading-limit test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    for path in (args.bemu, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}")
            return 1

    with tempfile.TemporaryDirectory(prefix="bemu-loading-") as temp_dir:
        cases = (
            ("empty", 0, "kernel is empty"),
            ("oversized", KERNEL_MAX + 1, "kernel exceeds 524288-byte limit"),
        )
        for name, size, message in cases:
            kernel = os.path.join(temp_dir, f"{name}-kernel.bin")
            with open(kernel, "wb") as stream:
                stream.truncate(size)
            result = subprocess.run(
                [args.bemu, "--kernel", kernel, "--root", args.img],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=args.timeout,
            )
            output = sanitize_terminal(result.stdout)
            expected = f"[bemu-linux01] kernel load rejected: {message}"
            forbidden = ("direct KVM entry", "RESULT: PASS", "BBP handoff validated")
            if (result.returncode != 1 or expected not in output or
                    any(value in output for value in forbidden)):
                print(f"{name} kernel was not rejected before KVM entry: rc={result.returncode}")
                print(diagnostic(output, 3000))
                return 1
            print(f"ok  {name} kernel rejected before KVM entry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
