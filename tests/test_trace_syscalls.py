#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Integration test: bEMU non-intrusive syscall instrumentation via single-step."""

import argparse
import json
import os
import subprocess
import sys
import tempfile

from harness_utils import BEMU_PASS_RE, KERNEL_FAULT_RE, sanitize_terminal


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU syscall instrumentation test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def validate_trace_result(returncode, output, events):
    output = sanitize_terminal(output)
    if returncode != 0 or not BEMU_PASS_RE.search(output):
        raise ValueError("runner did not finish successfully")
    if KERNEL_FAULT_RE.search(output):
        raise ValueError("kernel fault in runner output")
    if not events or events[0].get("type") != "boot_start":
        raise ValueError("missing initial boot event")
    shutdown = events[-1]
    if shutdown.get("type") != "shutdown" or shutdown.get("data", {}).get("status") != 0:
        raise ValueError("missing successful final shutdown event")
    numbers = {e.get("data", {}).get("number") for e in events if e.get("type") == "syscall"}
    if not {3, 4}.issubset(numbers):
        raise ValueError("read and write syscall events are required")
    return sum(e.get("type") == "syscall" for e in events)


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"  missing artifact: {path}")
            return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        trace_path = tf.name
    os.unlink(trace_path)

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
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("  FAIL  bEMU timed out")
        os.unlink(trace_path)
        return 1

    try:
        with open(trace_path, "r", encoding="utf-8") as f:
            events = [json.loads(line) for line in f if line.strip()]
        count = validate_trace_result(result.returncode, result.stdout, events)
    except (ValueError, OSError) as error:
        print(f"  FAIL  {error}")
        return 1
    finally:
        os.unlink(trace_path)
    print(f"  ok  completed run with read/write instrumentation ({count} syscall events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
