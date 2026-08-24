#!/usr/bin/env python3
"""Integration tests for explicit bEMU experience profiles."""

import argparse
import os
import re
import shlex
import subprocess
import sys

from harness_utils import BEMU_PASS_RE, KERNEL_FAULT_RE, diagnostic, sanitize_terminal


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 experience mode tests")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root-1991.img")
    parser.add_argument("--default-img", default="build/root.img")
    parser.add_argument("--make", default="make")
    parser.add_argument("--timeout", type=int, default=60)
    return parser.parse_args()


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img, args.default_img):
        if not os.path.exists(path):
            print(f"missing artifact: {path}")
            return 1

    invalid = subprocess.run(
        [args.bemu, "--experience", "invalid"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=args.timeout,
    )
    if invalid.returncode != 2 or "invalid experience: invalid" not in invalid.stdout:
        print("invalid bEMU experience was not rejected")
        return 1

    mismatches = (
        [args.bemu, "--kernel", args.kernel, "--root", args.default_img,
         "--experience", "1991"],
        [args.bemu, "--kernel", args.kernel, "--root", args.img],
    )
    for mismatch in mismatches:
        result = subprocess.run(
            mismatch,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        if result.returncode == 0 or "root image does not match selected experience" not in result.stdout:
            print("mismatched experience image was not rejected")
            return 1

    make_command = shlex.split(args.make)
    invalid_make = subprocess.run(
        make_command + ["--no-print-directory", "-n", "run", "EXPERIENCE=invalid"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=args.timeout,
    )
    if invalid_make.returncode == 0 or "EXPERIENCE must be empty or 1991" not in invalid_make.stdout:
        print("invalid Make experience was not rejected")
        return 1

    dry_run = subprocess.run(
        make_command + ["--no-print-directory", "-n", "run", "EXPERIENCE=1991"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=args.timeout,
    )
    if dry_run.returncode or "root-1991.img" not in dry_run.stdout or "--experience 1991" not in dry_run.stdout:
        print("make run EXPERIENCE=1991 does not select the historical profile")
        return 1

    script = (
        "echo EXPERIENCE_1991_BEGIN\n"
        "cat /etc/issue\n"
        "cat /etc/motd\n"
        "cd /tmp\n"
        "cd\n"
        "pwd\n"
        "echo EXPERIENCE_1991_DONE\n"
    )
    command = [
        args.bemu, "--kernel", args.kernel, "--experience", "1991",
        "--keys", script, "--expect", "EXPERIENCE_1991_DONE",
    ]
    if os.path.normpath(args.img) != os.path.normpath("build/root-1991.img"):
        command.extend(("--root", args.img))
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"1991 experience timed out: {diagnostic(exc.stdout, 2000)}")
        return 1

    output = sanitize_terminal(result.stdout)
    required = (
        "root=/dev/hd1 ide=977,5,17 experience=1991",
        "Linux 0.01 historical experience",
        "Experience profile: 1991",
        "linux 0.01 -- experience: 1991 -- interactive shell",
        "EXPERIENCE_1991_DONE",
    )
    missing = [value for value in required if value not in output]
    forbidden = [value for value in ("Vesica Piscis", "It still runs in 2026") if value in output]
    if (result.returncode or BEMU_PASS_RE.search(output) is None or
            KERNEL_FAULT_RE.search(output) or missing or forbidden or
            re.search(r"(?m)^/$", output) is None):
        print(f"1991 experience failed: missing={missing} forbidden={forbidden}")
        print(diagnostic(output, 3000))
        return 1

    print("1991 experience profile passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
