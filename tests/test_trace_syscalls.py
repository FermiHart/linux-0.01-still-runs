#!/usr/bin/env python3
"""Integration test: bEMU non-intrusive syscall instrumentation via single-step."""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU syscall instrumentation test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"  missing artifact: {path}")
            return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        trace_path = tf.name

    script = "cat /etc/motd\n"
    command = [
        args.bemu,
        "--kernel", args.kernel,
        "--root", args.img,
        "--keys", script,
        "--expect", "Welcome to 1991",
        "--trace-file", trace_path,
        "--trace-syscalls",
    ]
    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("  FAIL  bEMU timed out")
        os.unlink(trace_path)
        return 1

    syscall_count = 0
    with open(trace_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("type") == "syscall":
                syscall_count += 1

    os.unlink(trace_path)

    checks = [
        (syscall_count > 0, f"at least one syscall event emitted ({syscall_count})"),
    ]

    failed = False
    for ok, description in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
