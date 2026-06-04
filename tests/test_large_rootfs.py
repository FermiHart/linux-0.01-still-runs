#!/usr/bin/env python3
"""Smoke test a root filesystem with an oversized /bin/shell."""

import argparse
import os
import subprocess
import sys
import tempfile


def parse_args():
    p = argparse.ArgumentParser(description="Large rootfs shell smoke test")
    p.add_argument("--iso", default="build/linux-0.01.iso")
    p.add_argument("--mkimage", default="build/mkimage")
    p.add_argument("--shell", default="build/shell.bin")
    p.add_argument("--update", default="build/update.bin")
    p.add_argument("--hello", default="build/hello.bin")
    p.add_argument("--factor", type=int, default=3)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def require(path):
    if not os.path.exists(path):
        print(f"  ✗ missing artifact: {path}")
        return False
    return True


def inflate_shell(src, dst, factor):
    with open(src, "rb") as f:
        data = f.read()
    with open(dst, "wb") as f:
        for _ in range(factor):
            f.write(data)
    return len(data), len(data) * factor


def main():
    args = parse_args()
    artifacts = [args.iso, args.mkimage, args.shell, args.update, args.hello]
    if not all(require(path) for path in artifacts):
        return 1
    if args.factor < 1:
        print("  ✗ --factor must be >= 1")
        return 1

    with tempfile.TemporaryDirectory(prefix="linux001-large-rootfs-") as td:
        big_shell = os.path.join(td, "shell.bin")
        root_img = os.path.join(td, "root.img")
        original, inflated = inflate_shell(args.shell, big_shell, args.factor)
        print(f"  Large shell: {original} -> {inflated} bytes ({args.factor}x)", flush=True)

        mkimage = subprocess.run(
            [args.mkimage, root_img, big_shell, args.update, args.hello],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if mkimage.returncode != 0:
            print("  ✗ mkimage failed")
            if args.verbose:
                print(mkimage.stdout)
            return mkimage.returncode

        cmd = [
            sys.executable,
            "tests/test_boot.py",
            "--iso", args.iso,
            "--img", root_img,
            "--timeout", str(args.timeout),
        ]
        if args.verbose:
            cmd.append("--verbose")
        return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
