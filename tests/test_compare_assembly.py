#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Verify that assembly comparison diffs are generated for all compiler cases.

This test runs the compare-assembly harness and checks that disassembly and
per-optimization diffs exist for each case and ABI.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
ASM_DIR = os.path.join(HARNESS_DIR, "build", "asm")

CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
ABIS = ["x86_64", "i386"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "compare-assembly"],
        cwd=REPO_ROOT,
        check=True,
    )

    missing = []
    for case in CASES:
        for abi in ABIS:
            for opt in ["O0", "O1", "O2"]:
                asm = os.path.join(ASM_DIR, f"{case}-{abi}-{opt}.asm")
                if not os.path.isfile(asm):
                    missing.append(asm)
            for a, b in [("O0", "O1"), ("O1", "O2"), ("O0", "O2")]:
                diff = os.path.join(ASM_DIR, f"{case}-{abi}-{a}-vs-{b}.diff")
                if not os.path.isfile(diff):
                    missing.append(diff)

    if missing:
        print("missing asm/diff files:")
        for m in missing:
            print(" ", m)
        return 1

    print("assembly comparison artifacts generated for all cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
