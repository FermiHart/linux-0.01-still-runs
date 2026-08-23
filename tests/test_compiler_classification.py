#!/usr/bin/env python3
"""
Verify that the compiler-case classification artifacts are generated and
contain the expected categories for each case.
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
CLASSIFICATION_PATH = os.path.join(HARNESS_DIR, "build", "classification.json")

REQUIRED_CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
VALID_CATEGORIES = {"GCC_BUG", "UNDEFINED_BEHAVIOR", "HISTORICAL_HYPOTHESIS"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "classify"],
        cwd=REPO_ROOT,
        check=True,
    )

    with open(CLASSIFICATION_PATH, "r") as f:
        classification = json.load(f)

    assert "compiler" in classification
    assert "host" in classification
    assert "date" in classification
    assert "cases" in classification

    for case in REQUIRED_CASES:
        assert case in classification["cases"], f"missing classification for {case}"
        meta = classification["cases"][case]
        assert "category" in meta
        assert "gcc_bug" in meta
        assert "source_ub" in meta
        assert "rationale" in meta
        assert meta["category"] in VALID_CATEGORIES

    print("compiler-case classification valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
