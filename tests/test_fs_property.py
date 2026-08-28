#!/usr/bin/env python3
"""Property-style test for basic filesystem operations."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    sanitize_terminal,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 fs property test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--cases", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def shell_quote(s):
    return s.replace("'", "'\\''")


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1

    import secrets
    nonce = secrets.token_hex(4).upper()
    begin = f"BEMU{nonce}START"
    end = f"BEMU{nonce}END"

    # Keep strings short and alphanumeric to avoid shell/meta issues.
    cases = []
    for i in range(args.cases):
        data = secrets.token_hex(8)  # 16 hex chars
        cases.append((f"f{i}.txt", data))

    script_lines = [f"echo {begin}", "cd /tmp"]
    for name, data in cases:
        script_lines.append(f"echo {data} > {name}")
        script_lines.append(f"cat {name}")
    script_lines.append(f"echo {end}")
    script = "\n".join(script_lines) + "\n"

    with tempfile.TemporaryDirectory(prefix="linux001-fs-prop-") as temp_dir:
        root_copy = os.path.join(temp_dir, "root.img")
        shutil.copyfile(args.img, root_copy)
        command = [
            args.bemu, "--kernel", args.kernel, "--root", root_copy,
            "--keys", script, "--expect", end,
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            print("property test timed out")
            return 1

    output = sanitize_terminal(result.stdout)
    if result.returncode or BEMU_PASS_RE.search(output) is None:
        print(f"bEMU failed with status {result.returncode}")
        if args.verbose:
            print(output[-4000:])
        return 1
    if KERNEL_FAULT_RE.search(output):
        print("kernel fault during property test")
        return 1

    seg = output[output.find(begin):output.find(end)]
    for name, data in cases:
        if data not in seg:
            print(f"case {name}: expected {data!r} not found")
            if args.verbose:
                print(seg[-1000:])
            return 1

    print(f"property test passed ({args.cases} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
