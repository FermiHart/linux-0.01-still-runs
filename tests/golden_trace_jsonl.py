#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Capture a golden JSON Lines machine trace from bEMU."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def is_published_path(path):
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    published = os.path.realpath(os.path.join(repo_root, "datasets", "golden-traces"))
    output = os.path.realpath(path)
    return os.path.commonpath((published, output)) == published



def parse_args():
    parser = argparse.ArgumentParser(description="Capture golden bEMU machine trace")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--output", default="build/golden-candidates/alive-boot-machine.jsonl")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_args()
    if is_published_path(args.output):
        print("refusing to overwrite a published golden-trace observation")
        return 1
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1

    script = "echo GOLDEN_BOOT_MARKER\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as trace_tmp:
        trace_path = trace_tmp.name
    command = [
        args.bemu, "--kernel", args.kernel, "--root", args.img,
        "--keys", script, "--expect", "GOLDEN_BOOT_MARKER",
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
        print("golden machine trace capture timed out")
        os.unlink(trace_path)
        return 1

    if result.returncode != 0:
        print(f"golden machine trace capture failed with status {result.returncode}")
        os.unlink(trace_path)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    shutil.copy(trace_path, args.output)
    os.unlink(trace_path)
    print(f"golden machine trace written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
