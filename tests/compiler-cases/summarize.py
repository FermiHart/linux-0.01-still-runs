#!/usr/bin/env python3
"""
Generate a machine-readable summary (build/summary.json) of the compiler-case
harness results.  The summary is used by the compiler-version matrix and by the
academic dataset packaging.
"""

import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
BUILD_DIR = os.path.join(HARNESS_DIR, "build")
REPORT_PATH = os.path.join(BUILD_DIR, "report.txt")

CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
ABIS = ["x86_64", "i386"]
OPTS = ["O0", "O1", "O2"]


def compiler_version():
    try:
        out = subprocess.check_output(["gcc", "--version"], text=True)
        return out.splitlines()[0]
    except Exception:
        return "unknown"


def parse_report():
    if not os.path.isfile(REPORT_PATH):
        return {}
    text = open(REPORT_PATH, "r").read()
    results = {}
    for case in CASES:
        results[case] = {}
        for abi in ABIS:
            results[case][abi] = {}
            for opt in OPTS:
                key = f"{case}-{abi}-{opt}:"
                m = re.search(re.escape(key) + r"\s*(\S+)", text)
                status = m.group(1) if m else "unknown"
                results[case][abi][opt] = {
                    "status": status,
                    "pass": status.startswith("PASS"),
                }
    return results


def main():
    subprocess.run(
        ["make", "-C", HARNESS_DIR, "run"],
        cwd=REPO_ROOT,
        check=True,
    )

    summary = {
        "compiler": compiler_version(),
        "host": os.uname().machine,
        "date": subprocess.check_output(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True
        ).strip(),
        "results": parse_report(),
    }

    out_path = os.path.join(BUILD_DIR, "summary.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"summary written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
