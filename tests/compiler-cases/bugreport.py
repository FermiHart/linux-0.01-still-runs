#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Generate upstream bug-report drafts for any compiler case classified as a
GCC bug.  If no case is classified as a GCC bug, produce a note explaining why
no upstream report is currently warranted.
"""

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
BUILD_DIR = os.path.join(HARNESS_DIR, "build")
CLASSIFICATION_PATH = os.path.join(BUILD_DIR, "classification.json")
REPORT_DIR = os.path.join(BUILD_DIR, "upstream-reports")

TEMPLATE = """\
Component: c
Summary: GCC -O2 miscompiles {case} pattern from Linux 0.01
Version tested: {compiler}
Host: {host}

Description:
The attached minimal reproducer {case}.c behaves differently at -O2 than at
-O0/-O1.  It is classified as a GCC bug in the project dataset.  See the
assembly diffs and audit log in tests/compiler-cases/build/asm/ and
build/audit.txt for details.

Steps to reproduce:
    cd tests/compiler-cases
    make clean run
    ./build/{case}-x86_64-O2

Expected result: <fill in>
Observed result: <fill in>

Attachments:
- {case}.c
- build/summary.json
- build/asm/{case}-*-O*.asm
- build/asm/{case}-*-O1-vs-O2.diff
- build/audit.txt
- build/classification.json
"""


def main():
    subprocess.run(
        ["make", "-C", HARNESS_DIR, "classify"],
        cwd=REPO_ROOT,
        check=True,
    )

    with open(CLASSIFICATION_PATH, "r") as f:
        classification = json.load(f)

    os.makedirs(REPORT_DIR, exist_ok=True)
    generated = []
    for case, meta in classification["cases"].items():
        if meta.get("category") == "GCC_BUG":
            path = os.path.join(REPORT_DIR, f"{case}.txt")
            with open(path, "w") as f:
                f.write(TEMPLATE.format(
                    case=case,
                    compiler=classification.get("compiler", "unknown"),
                    host=classification.get("host", "unknown"),
                ))
            generated.append(path)

    index_path = os.path.join(REPORT_DIR, "index.txt")
    with open(index_path, "w") as f:
        if generated:
            f.write("Upstream bug-report drafts generated for:\n")
            for g in generated:
                f.write(f"  - {g}\n")
        else:
            f.write(
                "No upstream bug-report drafted.\n\n"
                "None of the compiler cases is currently classified as a GCC bug.\n"
                "bitmap_inline_asm is classified as UNDEFINED_BEHAVIOR in the source;\n"
                "buffer_freelist and vsprintf_percent_s could not be reproduced in isolation.\n"
                "See tests/compiler-cases/CLASSIFICATION.md for the rationale.\n"
            )

    print(f"upstream report index written to {index_path}")
    if generated:
        print("drafts:")
        for g in generated:
            print(f"  {g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
