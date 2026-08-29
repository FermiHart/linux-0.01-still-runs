#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Verify that the compiler-case summary JSON is generated and contains results for
all cases, ABIs and optimization levels.
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
SUMMARY_PATH = os.path.join(HARNESS_DIR, "build", "summary.json")

CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
ABIS = ["x86_64", "i386"]
OPTS = ["O0", "O1", "O2"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "summarize"],
        cwd=REPO_ROOT,
        check=True,
    )

    with open(SUMMARY_PATH, "r") as f:
        summary = json.load(f)

    assert "compiler" in summary
    assert "host" in summary
    assert "date" in summary
    assert "results" in summary

    for case in CASES:
        assert case in summary["results"], f"missing case {case}"
        for abi in ABIS:
            assert abi in summary["results"][case], f"missing abi {abi}"
            for opt in OPTS:
                assert opt in summary["results"][case][abi], f"missing opt {opt}"
                entry = summary["results"][case][abi][opt]
                assert "status" in entry and "pass" in entry

    print("compiler-case summary JSON valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
