#!/usr/bin/env python3
"""Compare mkimage output against the independent minix-inspect parser."""

import argparse
import os
import subprocess
import sys

from harness_utils import diagnostic


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 fs inspector consistency test")
    parser.add_argument("--minix-inspect", default="build/minix-inspect")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.minix_inspect, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1

    result = subprocess.run(
        [args.minix_inspect, "--audit", args.img],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        print("minix-inspect audit failed")
        if args.verbose:
            print(diagnostic(result.stdout, 4000))
        return 1

    output = result.stdout
    expected = [
        "s_magic         0x137F (v1)",
        "/bin/shell",
        "/bin/hello",
        "bitmaps, inodes and directory entries are consistent",
    ]
    missing = [e for e in expected if e not in output]
    if missing:
        print(f"missing in inspector output: {missing}")
        if args.verbose:
            print(diagnostic(output, 2000))
        return 1

    if output.count("inode") < 10:
        print("inspector did not enumerate inodes")
        return 1

    print("independent fs inspector consistency test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
