#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Wrap a flat PA0 kernel payload in the versioned Linux 0.01 image envelope."""

import argparse
import os
import shutil
import struct
import tempfile


MAGIC = b"L01KIMG1"


def main():
    parser = argparse.ArgumentParser(description="build a Linux 0.01 kernel image")
    parser.add_argument("payload")
    parser.add_argument("output")
    args = parser.parse_args()

    payload_size = os.path.getsize(args.payload)
    output_dir = os.path.dirname(os.path.abspath(args.output))
    fd, temporary = tempfile.mkstemp(prefix=".kernel-image-", dir=output_dir)
    try:
        with os.fdopen(fd, "wb") as dst, open(args.payload, "rb") as src:
            shutil.copyfileobj(src, dst)
            dst.write(MAGIC)
            dst.write(struct.pack("<Q", payload_size))
            dst.flush()
            os.fsync(dst.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, args.output)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    main()
