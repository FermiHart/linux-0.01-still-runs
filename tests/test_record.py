#!/usr/bin/env python3
"""Integration test: make record produces a valid compressed trace."""

import argparse
import gzip
import json
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU record mode test")
    parser.add_argument("--make", default="make")
    parser.add_argument("--timeout", type=int, default=120)
    return parser.parse_args()


def main():
    args = parse_args()

    with tempfile.TemporaryDirectory(prefix="record-test-", dir="build") as temp_dir:
        env = os.environ.copy()
        env["BUILD"] = os.path.abspath(temp_dir)
        result = subprocess.run(
            [args.make, "record"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        if result.returncode != 0:
            print("  FAIL  make record failed")
            print(result.stdout[-2000:])
            print(result.stderr[-2000:])
            return 1

        trace_dir = os.path.join(temp_dir, "traces")
        files = [f for f in os.listdir(trace_dir) if f.endswith(".jsonl.gz")] if os.path.isdir(trace_dir) else []
        if not files:
            print("  FAIL  no .jsonl.gz trace produced")
            return 1

        trace_path = os.path.join(trace_dir, files[0])
        try:
            with gzip.open(trace_path, "rt", encoding="utf-8", errors="replace") as f:
                first = json.loads(f.readline())
                line_count = 1
                for line in f:
                    if line.strip():
                        line_count += 1
                        event = json.loads(line)
                        if event.get("type") not in {
                            "boot_start", "kvm_exit", "io_access", "irq", "timer",
                            "input", "syscall", "interrupt", "process", "shutdown",
                        }:
                            print(f"  FAIL  unknown event type {event.get('type')!r}")
                            return 1
        except Exception as exc:
            print(f"  FAIL  could not read compressed trace: {exc}")
            return 1

        print(f"  ok  record produced {trace_path} ({line_count} events)")
        print(f"  ok  first event type: {first.get('type')}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
