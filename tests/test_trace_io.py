#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Integration test: bEMU emits IO and IRQ trace events."""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU IO/IDE trace event test")
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

    event_types = set()
    ide_ports = {0x1F0 + i for i in range(8)}
    saw_ide = False
    saw_irq = False
    saw_shutdown = False
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
            etype = event.get("type")
            event_types.add(etype)
            data = event.get("data", {})
            if etype == "io_access":
                port = data.get("port")
                if port in ide_ports:
                    saw_ide = True
            elif etype == "irq":
                saw_irq = True
            elif etype == "shutdown":
                saw_shutdown = True

    os.unlink(trace_path)

    checks = [
        ("boot_start" in event_types, "boot_start event emitted"),
        ("io_access" in event_types, "io_access events emitted"),
        (saw_ide, "IDE port (0x1f0-0x1f7) io_access seen"),
        (saw_irq, "irq event emitted"),
        (saw_shutdown, "shutdown event emitted"),
        (line_count > 100, "trace contains multiple events"),
    ]

    failed = False
    for ok, description in checks:
        print(f"  {'ok' if ok else 'FAIL'}  {description}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
