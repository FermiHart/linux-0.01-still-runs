#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Verify that the upstream bug-report script runs and produces an index.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
INDEX_PATH = os.path.join(HARNESS_DIR, "build", "upstream-reports", "index.txt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "bugreport"],
        cwd=REPO_ROOT,
        check=True,
    )

    assert os.path.isfile(INDEX_PATH), f"upstream report index not found: {INDEX_PATH}"
    text = open(INDEX_PATH, "r").read()
    assert "bitmap_inline_asm" in text or "No upstream bug-report" in text

    print("upstream bug-report index generated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
