#!/usr/bin/env python3
"""Validate the structure of a bEMU machine-readable trace."""

import argparse
import json
import os
import subprocess
import sys
import tempfile


REQUIRED_EVENT_FIELDS = {"ts", "type", "data"}
KNOWN_EVENT_TYPES = {
    "boot_start", "kvm_exit", "io_access", "irq", "timer",
    "input", "syscall", "interrupt", "process", "shutdown",
}


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU trace format validator")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def validate_event(event, line_number):
    missing = REQUIRED_EVENT_FIELDS - set(event.keys())
    if missing:
        return f"line {line_number}: missing fields {missing}"
    if not isinstance(event["ts"], int):
        return f"line {line_number}: ts must be integer"
    if event["type"] not in KNOWN_EVENT_TYPES:
        return f"line {line_number}: unknown event type {event['type']!r}"
    if not isinstance(event["data"], dict):
        return f"line {line_number}: data must be object"
    return None


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"  missing artifact: {path}")
            return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        trace_path = tf.name

    script = "echo TRACE_FORMAT_MARKER\n"
    command = [
        args.bemu, "--kernel", args.kernel, "--root", args.img,
        "--keys", script, "--expect", "TRACE_FORMAT_MARKER",
        "--trace-file", trace_path,
    ]
    try:
        result = subprocess.run(
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

    if result.returncode != 0:
        print(f"  FAIL  bEMU exited with status {result.returncode}")
        os.unlink(trace_path)
        return 1

    errors = []
    line_count = 0
    saw_boot = False
    saw_shutdown = False
    monotonic_ts = -1

    with open(trace_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {line_count}: invalid JSON: {exc}")
                break
            err = validate_event(event, line_count)
            if err:
                errors.append(err)
                break
            if event["ts"] < monotonic_ts:
                errors.append(f"line {line_count}: non-monotonic ts")
                break
            monotonic_ts = event["ts"]
            if event["type"] == "boot_start":
                saw_boot = True
                data = event["data"]
                if data.get("trace_version") != 1:
                    errors.append(f"line {line_count}: unexpected trace_version")
            elif event["type"] == "shutdown":
                saw_shutdown = True

    os.unlink(trace_path)

    checks = [
        (line_count > 0, "trace file is non-empty"),
        (not errors, f"all {line_count} lines validate"),
        (saw_boot, "boot_start event present"),
        (saw_shutdown, "shutdown event present"),
    ]

    failed = False
    for ok, description in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok
    for err in errors:
        print(f"  FAIL  {err}")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
