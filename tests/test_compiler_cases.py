#!/usr/bin/env python3
"""
Verify that the compiler-case investigation harness runs and produces a report.

The harness compiles tiny, isolated reproductions of the three -O2 sensitive
patterns from the Linux 0.01 port at -O0, -O1 and -O2, for both x86_64 and i386.
This test does not require the full kernel build; it only checks that the
report is generated and contains the expected cases.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
REPORT_PATH = os.path.join(HARNESS_DIR, "build", "report.txt")


def run_harness(make_command):
    subprocess.run(
        ["make", "-C", HARNESS_DIR, "clean", "run"],
        cwd=REPO_ROOT,
        check=True,
    )


def check_report():
    assert os.path.isfile(REPORT_PATH), f"report not found: {REPORT_PATH}"
    text = open(REPORT_PATH, "r").read()
    required = [
        "buffer_freelist",
        "bitmap_inline_asm",
        "vsprintf_percent_s",
        "ABI: x86_64",
        "ABI: i386",
    ]
    for token in required:
        assert token in text, f"report missing expected section: {token}"
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    run_harness(args.make)
    text = check_report()

    print("compiler-case harness report generated")
    print("cases found:", sum(1 for c in ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"] if c in text))
    print("report:", REPORT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
