#!/usr/bin/env python3
"""Quick single-command bEMU test."""

import argparse
import secrets
import subprocess
import sys

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    extract_command_output,
    line_contains,
    sanitize_terminal,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("--expect", required=True)
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--setup", default="", help="commands separated by |")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    setup = "\n".join(part.strip() for part in args.setup.split("|") if part.strip())
    nonce = secrets.token_hex(8).upper()
    begin = f"BEMUQQ{nonce}BEGIN"
    end = f"BEMUQQ{nonce}END"
    script = (
        (setup + "\n" if setup else "")
        + f"echo {begin}\n{args.command}\necho {end}\n"
    )
    try:
        result = subprocess.run([
            args.bemu, "--kernel", args.kernel, "--root", args.img,
            "--keys", script, "--expect", end,
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
           errors="replace", timeout=args.timeout)
    except subprocess.TimeoutExpired as exc:
        print("FAIL: bEMU timed out")
        if exc.stdout:
            print(diagnostic(exc.stdout, 1000))
        return 1
    except OSError as exc:
        print(f"FAIL: could not run bEMU: {diagnostic(exc, 1000)}")
        return 1

    output = sanitize_terminal(result.stdout)
    try:
        segment, _ = extract_command_output(
            output, begin, end, command=args.command, validate=True,
        )
    except ValueError as exc:
        print(f"FAIL: invalid command transcript: {exc}")
        print(diagnostic(output, 1000))
        return 1
    if (result.returncode or BEMU_PASS_RE.search(output) is None
            or not line_contains(segment, args.expect)
            or KERNEL_FAULT_RE.search(output)):
        print(f"FAIL: {args.expect!r} not produced safely")
        print(diagnostic(segment, 1000))
        return 1
    print(f"OK: {args.expect!r} found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
