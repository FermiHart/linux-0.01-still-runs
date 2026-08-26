#!/usr/bin/env python3
"""Reject truncated kernel and root artifacts before writable/KVM use."""

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run_rejection(command, expected, timeout):
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env={**os.environ, "LC_ALL": "C"},
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
    )
    forbidden = ("direct KVM entry", "RESULT: PASS", "BBP handoff validated")
    return (result.returncode == 1 and expected in result.stdout and
            not any(marker in result.stdout for marker in forbidden))


def truncated_copy(source, target, size):
    with open(source, "rb") as src, open(target, "wb") as dst:
        remaining = size
        while remaining:
            chunk = src.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise RuntimeError("source ended before requested cutoff")
            dst.write(chunk)
            remaining -= len(chunk)
    return os.path.getsize(target) == size


def main():
    parser = argparse.ArgumentParser(description="artifact truncation fault test")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--root", default="build/root.img")
    parser.add_argument("--root-1991", default="build/root-1991.img")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    sources = (args.kernel, args.root, args.root_1991)
    for path in (args.bemu, *sources):
        if not os.path.exists(path):
            print(f"FAIL  missing artifact: {path}")
            return 1
    original_hashes = {path: digest(path) for path in sources}

    with tempfile.TemporaryDirectory(prefix="artifact-truncation-") as temp_dir:
        kernel_size = os.path.getsize(args.kernel)
        for label, cutoff in (("prefix", 1), ("interior", kernel_size // 2),
                              ("suffix", kernel_size - 1)):
            copy = os.path.join(temp_dir, f"kernel-{label}.bin")
            ok = truncated_copy(args.kernel, copy, cutoff) and run_rejection(
                [args.bemu, "--kernel", copy,
                 "--root", os.path.join(temp_dir, "must-not-open.img")],
                "[bemu-linux01] kernel load rejected: "
                "kernel image has no valid L01KIMG1 trailer",
                args.timeout,
            )
            print(f"{'ok' if ok else 'FAIL'}  kernel {label} truncation rejected")
            if not ok:
                return 1

        with open(args.kernel, "rb") as stream:
            kernel = stream.read()
        interior = os.path.join(temp_dir, "kernel-interior-delete.bin")
        with open(interior, "wb") as stream:
            stream.write(kernel[:32] + kernel[64:])
        ok = run_rejection(
            [args.bemu, "--kernel", interior,
             "--root", os.path.join(temp_dir, "must-not-open.img")],
            "[bemu-linux01] kernel load rejected: "
            "kernel image size does not match its trailer",
            args.timeout,
        )
        print(f"{'ok' if ok else 'FAIL'}  kernel interior deletion rejected")
        if not ok:
            return 1

        for source in (args.root, args.root_1991):
            size = os.path.getsize(source)
            profile = "1991" if source == args.root_1991 else "alive"
            for label, cutoff in (("prefix", 1), ("interior", size // 2),
                                  ("suffix", size - 1)):
                copy = os.path.join(temp_dir, f"root-{profile}-{label}.img")
                ok = truncated_copy(source, copy, cutoff) and run_rejection(
                    [args.bemu, "--kernel", args.kernel, "--root", copy,
                     "--experience", profile],
                    "[bemu-linux01] root image does not match 977/5/17 CHS geometry",
                    args.timeout,
                )
                print(f"{'ok' if ok else 'FAIL'}  {profile} root {label} truncation rejected")
                if not ok:
                    return 1

    if any(digest(path) != original_hashes[path] for path in sources):
        print("FAIL  canonical artifact changed during truncation tests")
        return 1
    print("ok  canonical kernel and root artifacts remain unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
