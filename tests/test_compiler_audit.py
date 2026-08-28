#!/usr/bin/env python3
"""
Verify that the compiler-case audit script runs and produces an audit log.

The audit checks aliasing, sequence-point, and undefined-behavior sanitizer
behavior for each isolated compiler case.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
AUDIT_PATH = os.path.join(HARNESS_DIR, "build", "audit.txt")

REQUIRED_CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "audit"],
        cwd=REPO_ROOT,
        check=True,
    )

    assert os.path.isfile(AUDIT_PATH), f"audit log not found: {AUDIT_PATH}"
    text = open(AUDIT_PATH, "r").read()
    for case in REQUIRED_CASES:
        assert case in text, f"audit log missing case: {case}"
    assert "strict-aliasing" in text, "audit missing aliasing check"
    assert "sequence-point" in text, "audit missing sequence-point check"
    assert "UBSan" in text, "audit missing UBSan check"

    print("compiler-case audit log generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
