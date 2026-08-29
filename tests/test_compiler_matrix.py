#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Verify that the compiler-version matrix is generated and contains results for
all discovered compilers.
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
MATRIX_PATH = os.path.join(HARNESS_DIR, "build", "matrix.json")

CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
OPTS = ["O0", "O1", "O2"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "matrix"],
        cwd=REPO_ROOT,
        check=True,
    )

    assert os.path.isfile(MATRIX_PATH), f"matrix not found: {MATRIX_PATH}"
    with open(MATRIX_PATH, "r") as f:
        matrix = json.load(f)

    assert "compilers" in matrix and matrix["compilers"], "no compilers in matrix"
    for entry in matrix["compilers"]:
        assert "command" in entry and "version" in entry
        for case in CASES:
            assert case in entry["results"], f"missing case {case}"
            for opt in OPTS:
                assert opt in entry["results"][case]
                assert "compiled" in entry["results"][case][opt]

    print(f"compiler matrix valid: {len(matrix['compilers'])} compilers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
