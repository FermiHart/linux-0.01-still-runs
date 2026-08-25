#!/usr/bin/env python3
"""Integration tests for explicit bEMU experience profiles."""

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from harness_utils import BEMU_PASS_RE, KERNEL_FAULT_RE, diagnostic, sanitize_terminal


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 experience mode tests")
    parser.add_argument("--experience", choices=("1991", "alive"), default="1991")
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

    other_experience = "alive" if args.experience == "1991" else "1991"
    mismatches = (
        [args.bemu, "--kernel", args.kernel, "--root", args.default_img,
         "--experience", args.experience],
        [args.bemu, "--kernel", args.kernel, "--root", args.img,
         "--experience", other_experience],
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
    for invalid_value in ("invalid", "1991 garbage"):
        invalid_make = subprocess.run(
            make_command + ["--no-print-directory", "-n", "run",
                            f"EXPERIENCE={invalid_value}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        if (invalid_make.returncode == 0 or
                "EXPERIENCE must be 1991 or alive" not in invalid_make.stdout):
            print(f"invalid Make experience was not rejected: {invalid_value}")
            return 1

    dry_run = subprocess.run(
        make_command + ["--no-print-directory", "-n", "run", f"EXPERIENCE={args.experience}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=args.timeout,
    )
    expected_root = "root-1991.img" if args.experience == "1991" else "root.img"
    if (dry_run.returncode or expected_root not in dry_run.stdout or
            f"--experience {args.experience}" not in dry_run.stdout):
        print(f"make run EXPERIENCE={args.experience} does not select its profile")
        return 1

    if args.experience == "alive":
        for default_args in ([], ["EXPERIENCE="]):
            default_run = subprocess.run(
                make_command + ["--no-print-directory", "-n", "run"] + default_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=args.timeout,
            )
            if (default_run.returncode or "root.img" not in default_run.stdout or
                    "--experience alive" not in default_run.stdout):
                print("plain make run did not select alive")
                return 1

    marker = f"EXPERIENCE_{args.experience.upper()}"
    profile_commands = "date\ncal\n" if args.experience == "1991" else "date\n"
    script = (
        f"echo {marker}_BEGIN\n"
        "cat /etc/issue\n"
        "cat /etc/motd\n"
        f"{profile_commands}"
        "cd /tmp\n"
        "cd\n"
        "pwd\n"
        f"echo {marker}_DONE\n"
    )
    with tempfile.TemporaryDirectory(prefix="linux001-experience-") as temp_dir:
        profile_img = os.path.join(temp_dir, "profile.img")
        corrupt_img = os.path.join(temp_dir, "corrupt.img")
        shutil.copyfile(args.img, profile_img)
        shutil.copyfile(args.img, corrupt_img)
        with open(corrupt_img, "r+b") as image:
            image.seek(0x180)
            marker_bytes = bytearray(image.read(8))
            marker_bytes[0] ^= 0x01
            image.seek(0x180)
            image.write(marker_bytes)
        corrupt = subprocess.run(
            [args.bemu, "--kernel", args.kernel, "--root", corrupt_img,
             "--experience", args.experience],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=args.timeout,
        )
        if (corrupt.returncode == 0 or
                "root image does not match selected experience" not in corrupt.stdout):
            print("corrupt experience marker was not rejected")
            return 1

        if args.experience == "alive":
            with open(profile_img, "r+b") as image:
                image.seek(0x180)
                image.write(b"\0" * 8)

        command = [args.bemu, "--kernel", args.kernel, "--root", profile_img,
                   "--experience", args.experience, "--keys", script,
                   "--expect", f"{marker}_DONE"]
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
            print(f"{args.experience} experience timed out: {diagnostic(exc.stdout, 2000)}")
            return 1

    output = sanitize_terminal(result.stdout)
    if args.experience == "1991":
        required = ("Linux 0.01 historical experience", "Experience profile: 1991",
                    "September 1991")
        forbidden_values = ("Vesica Piscis", "It still runs in 2026")
        home = "/"
    else:
        required = ("Linux 0.01 alive experience", "Vesica Piscis alive experience",
                    "It still runs in 2026")
        forbidden_values = ("Experience profile: 1991",)
        home = "/home/fermihart"
    required += (
        f"root=/dev/hd1 ide=977,5,17 experience={args.experience}",
        f"linux 0.01 -- experience: {args.experience} -- interactive shell",
        f"{marker}_DONE",
    )
    missing = [value for value in required if value not in output]
    forbidden = [value for value in forbidden_values if value in output]
    historical_date_missing = (
        args.experience == "1991" and
        re.search(r"(?m)^Tue Sep 17 00:00:[0-5][0-9] 1991$", output) is None
    )
    alive_year_missing = (
        args.experience == "alive" and
        re.search(rf"(?m)^[A-Z][a-z]{{2}} [A-Z][a-z]{{2}} +[0-9]{{1,2}} "
                  rf"[0-9:]{{8}} {time.gmtime().tm_year}$", output) is None
    )
    if (result.returncode or BEMU_PASS_RE.search(output) is None or
            KERNEL_FAULT_RE.search(output) or missing or forbidden or
            historical_date_missing or alive_year_missing or
            re.search(rf"(?m)^{re.escape(home)}$", output) is None):
        print(f"{args.experience} experience failed: missing={missing} "
              f"forbidden={forbidden} historical_date_missing={historical_date_missing} "
              f"alive_year_missing={alive_year_missing}")
        print(diagnostic(output, 3000))
        return 1

    print(f"{args.experience} experience profile passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
