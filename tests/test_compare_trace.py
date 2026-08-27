#!/usr/bin/env python3
"""Integration test: replayed trace matches golden trace (ignoring ts)."""

import argparse
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU golden trace comparison test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--golden", default="datasets/golden-traces/v1/alive-boot-machine.jsonl")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.golden):
        if not os.path.exists(path):
            print(f"  missing artifact: {path}")
            return 1

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        replay_trace = tf.name

    ret = subprocess.run(
        ["python3", "tests/replay.py", "--bemu", args.bemu,
         "--trace", args.golden, "--output-trace", replay_trace,
         "--timeout", str(args.timeout)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", timeout=args.timeout * 2,
    )
    if ret.returncode != 0:
        print("  FAIL  replay failed")
        print(ret.stdout[-2000:])
        os.unlink(replay_trace)
        return 1

    cmp = subprocess.run(
        ["python3", "tests/compare_trace.py",
         "--ignore-event", "irq",
         "--ignore-port", "0x71",
         "--ignore-port", "0x60",
         "--ignore-port", "0x61",
         "--ignore-port", "0x3d4",
         "--ignore-port", "0x3d5",
         "--ignore-port", "0x1f0",
         args.golden, replay_trace],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace",
    )
    os.unlink(replay_trace)
    print(cmp.stdout.strip())
    return cmp.returncode


if __name__ == "__main__":
    sys.exit(main())
