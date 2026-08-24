#!/usr/bin/env python3
"""Capture a golden boot trace from bEMU for regression comparison."""

import argparse
import os
import re
import subprocess
import sys

from harness_utils import diagnostic


def parse_args():
    parser = argparse.ArgumentParser(description="Capture golden bEMU boot trace")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--output", default="tests/golden/boot.trace")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1

    script = "echo GOLDEN_BOOT_MARKER\n"
    command = [
        args.bemu, "--kernel", args.kernel, "--root", args.img,
        "--keys", script, "--expect", "GOLDEN_BOOT_MARKER",
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
        print("golden trace capture timed out")
        if exc.stdout:
            print(diagnostic(exc.stdout, 4000))
        return 1

    # Prompt padding is terminal presentation, not semantic trace data.
    output = re.sub(r"[ \t]+(?=\r?$)", "", result.stdout, flags=re.MULTILINE)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8", errors="replace") as f:
        f.write(output)
    print(f"golden trace written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
