#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""
Generate classification.json and classification.txt for the three -O2
sensitive compiler cases, using the evidence collected by the harness, the
assembly comparison and the audit.
"""

import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
BUILD_DIR = os.path.join(HARNESS_DIR, "build")
SUMMARY_PATH = os.path.join(BUILD_DIR, "summary.json")
CLASSIFICATION_PATH = os.path.join(BUILD_DIR, "classification.json")
TEXT_PATH = os.path.join(BUILD_DIR, "classification.txt")

CLASSIFICATIONS = {
    "buffer_freelist": {
        "category": "HISTORICAL_HYPOTHESIS",
        "gcc_bug_status": "NOT_ESTABLISHED",
        "source_contract_status": "NOT_ESTABLISHED",
        "rationale": (
            "Isolated reproduction passes on GCC 13.3 at all optimization levels. "
            "The claimed -O2 miscompilation could not be reproduced; the -O1 workaround "
            "is conservative."
        ),
    },
    "bitmap_inline_asm": {
        "category": "UNDEFINED_BEHAVIOR",
        "gcc_bug_status": "NOT_SUPPORTED",
        "source_contract_status": "SUPPORTED_FOR_REDUCED_X86_64_O2_CASE",
        "rationale": (
            "The inline asm modifies an operand declared as input-only. GCC may keep the "
            "bitmap word in a register across set_bit, so the write is not observed. This "
            "supports a source contract violation in the reduction, not a compiler bug."
        ),
    },
    "vsprintf_percent_s": {
        "category": "HISTORICAL_HYPOTHESIS",
        "gcc_bug_status": "NOT_ESTABLISHED",
        "source_contract_status": "NOT_ESTABLISHED",
        "rationale": (
            "Isolated reproduction passes on GCC 13.3 at all optimization levels. "
            "The va_arg(args, char*) fetch for %s behaves correctly in isolation; "
            "the original symptom may depend on the full printk call path or an older compiler."
        ),
    },
}


def main():
    subprocess.run(
        ["make", "-C", HARNESS_DIR, "summarize"],
        cwd=REPO_ROOT,
        check=True,
    )

    with open(SUMMARY_PATH, "r") as f:
        summary = json.load(f)

    classification = {
        "compiler": summary.get("compiler"),
        "host": summary.get("host"),
        "date": summary.get("date"),
        "cases": {},
    }

    for case, meta in CLASSIFICATIONS.items():
        classification["cases"][case] = {
            "category": meta["category"],
            "gcc_bug_status": meta["gcc_bug_status"],
            "source_contract_status": meta["source_contract_status"],
            "rationale": meta["rationale"],
            "results": summary["results"].get(case, {}),
        }

    with open(CLASSIFICATION_PATH, "w") as f:
        json.dump(classification, f, indent=2)

    with open(TEXT_PATH, "w") as f:
        f.write("Compiler-case classification\n")
        f.write("==========================\n\n")
        f.write(f"Compiler: {classification['compiler']}\n")
        f.write(f"Host: {classification['host']}\n")
        f.write(f"Date: {classification['date']}\n\n")
        for case, meta in classification["cases"].items():
            f.write(f"--- {case} ---\n")
            f.write(f"Category: {meta['category']}\n")
            f.write(f"GCC bug status: {meta['gcc_bug_status']}\n")
            f.write(f"Source contract status: {meta['source_contract_status']}\n")
            f.write(f"Rationale: {meta['rationale']}\n\n")

    print(f"classification written to {CLASSIFICATION_PATH} and {TEXT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
