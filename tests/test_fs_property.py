#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Property-style test for basic filesystem operations."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    sanitize_terminal,
    extract_command_output,
    PROMPT_RE,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 fs property test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--cases", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.cases <= 64:
        parser.error("--cases must be between 1 and 64")
    if not 1 <= args.timeout <= 300:
        parser.error("--timeout must be between 1 and 300 seconds")
    return args


def validate_readbacks(output, cases, nonce):
    """Only isolated cat output is evidence, never its earlier write command."""
    cursor = 0
    for i, (name, data) in enumerate(cases):
        begin, end = f"R25{nonce}B{i}", f"R25{nonce}E{i}"
        segment, cursor = extract_command_output(
            output, begin, end, cursor, command=f"cat {name}", validate=True)
        lines = segment.splitlines()
        if not lines or re.fullmatch(PROMPT_RE, lines[-1]) is None:
            raise ValueError(f"case {name}: missing final prompt")
        if lines[:-1] != [data]:
            raise ValueError(f"case {name}: readback differs from exact expected line")


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
    for i, (name, data) in enumerate(cases):
        script_lines.append(f"echo {data} > {name}")
        script_lines.append(f"echo R25{nonce}B{i}")
        script_lines.append(f"cat {name}")
        script_lines.append(f"echo R25{nonce}E{i}")
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
            # Preserve serial CR/CRLF bytes until sanitize_terminal handles them.
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
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

    try:
        validate_readbacks(output, cases, nonce)
    except ValueError as error:
        print(str(error))
        if args.verbose:
            print(diagnostic(output, 2000))
        return 1

    print(f"property test passed ({args.cases} cases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
