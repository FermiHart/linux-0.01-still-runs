#!/usr/bin/env python3
"""Integration test: timeline visualizer produces expected output."""

import argparse
import os
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU timeline visualizer test")
    parser.add_argument("--trace", default="tests/golden/boot.jsonl")
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.trace):
        print(f"  missing trace: {args.trace}")
        return 1

    result = subprocess.run(
        ["python3", "tests/timeline.py", args.trace],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, errors="replace", timeout=30,
    )
    if result.returncode != 0:
        print("  FAIL  timeline visualizer failed")
        print(result.stderr[-1000:])
        return 1

    checks = [
        ("events:" in result.stdout, "event count line"),
        ("types:" in result.stdout, "event types line"),
        ("event density" in result.stdout, "density histogram"),
    ]
    failed = False
    for ok, description in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
