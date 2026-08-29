#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Integration test: bEMU emits keyboard input trace events."""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU keyboard input trace event test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"  missing artifact: {path}")
            return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".trace", delete=False) as tf:
        trace_path = tf.name

    command = [
        args.bemu,
        "--kernel", args.kernel,
        "--root", args.img,
        "--keys", "ls\n",
        "--expect", "root@linux01",
        "--trace-file", trace_path,
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

    saw_script_input = False
    line_count = 0

    with open(trace_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            line_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  FAIL  invalid JSON on line {line_count}: {exc}")
                os.unlink(trace_path)
                return 1
            if event.get("type") == "input":
                data = event.get("data", {})
                if data.get("source") == "script":
                    saw_script_input = True

    os.unlink(trace_path)

    checks = [
        (saw_script_input, "script input event emitted"),
    ]

    eof_diagnostic = b"[bemu-linux01] discarded truncated stdin escape sequence\n"
    eof_cases = [
        ("EOF_ESC_MARK", b"\x1b", False),
        ("EOF_TRUNC_MARK", b"\x1b[", True),
    ]
    for marker, suffix, should_diagnose in eof_cases:
        command = [
            args.bemu,
            "--kernel", args.kernel,
            "--root", args.img,
            "--expect", marker,
        ]
        try:
            result = subprocess.run(
                command,
                input=b"echo " + marker.encode("ascii") + b"\n" + suffix,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=args.timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            checks.append((False, f"{marker} EOF production path completes"))
            continue
        checks.extend([
            (
                result.returncode == 0
                and marker.encode("ascii") in result.stdout
                and b"[bemu-linux01] RESULT: PASS" in result.stderr,
                f"{marker} EOF production path completes",
            ),
            (
                result.stderr.count(eof_diagnostic) == int(should_diagnose),
                f"{marker} EOF diagnostic policy",
            ),
        ])

    failed = False
    for ok, description in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
