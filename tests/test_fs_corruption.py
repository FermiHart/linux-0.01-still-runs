#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Inject deterministic Minix v1 metadata corruption into disposable images."""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from harness_utils import diagnostic


SECTOR_SIZE = 512
MBR_PARTITION_OFFSET = 0x1BE
SUPER_MAGIC_OFFSET = 0x410
ROOT_INODE_MODE_OFFSET = 0x1000
ZONE_BITMAP_OFFSET = 0x0C00


class TestFailure(Exception):
    pass


@dataclass(frozen=True)
class Fault:
    name: str
    offset: int
    expected: bytes
    replacement: bytes
    inspect_diagnostics: tuple
    fsck_status: int
    fsck_diagnostics: tuple


FAULTS = (
    Fault(
        "superblock-magic",
        SUPER_MAGIC_OFFSET,
        b"\x7f\x13",
        b"\x7e\x13",
        ("superblock magic", "0x137e", "0x137f"),
        8,
        ("bad magic", "super-block"),
    ),
    Fault(
        "root-inode-mode",
        ROOT_INODE_MODE_OFFSET,
        b"\xed\x41",
        b"\x00\x00",
        ("inode 1", "marked in imap", "mode is zero"),
        8,
        ("root inode", "directory"),
    ),
    Fault(
        "root-zone-bitmap",
        ZONE_BITMAP_OFFSET,
        b"\xff",
        b"\xfd",
        ("zone 12", "reachable", "not marked in zmap"),
        4,
        ("block 12", "marked not in use"),
    ),
)


def parse_args():
    parser = argparse.ArgumentParser(description="Minix v1 metadata corruption test")
    parser.add_argument("--minix-inspect", default="build/minix-inspect")
    parser.add_argument("--fsck", default="fsck.minix")
    parser.add_argument("--img", action="append", dest="images")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    if not args.images:
        args.images = ["build/root.img", "build/root-1991.img"]
    return args


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, timeout):
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise TestFailure(f"command timed out after {timeout}s: {command[0]}") from error


def require(condition, message):
    if not condition:
        raise TestFailure(message)


def changed_offsets(left_path, right_path):
    offsets = []
    position = 0
    with open(left_path, "rb") as left, open(right_path, "rb") as right:
        while True:
            left_chunk = left.read(1024 * 1024)
            right_chunk = right.read(1024 * 1024)
            require(len(left_chunk) == len(right_chunk), "corrupt copy size changed")
            if not left_chunk:
                break
            offsets.extend(
                position + index
                for index, (before, after) in enumerate(zip(left_chunk, right_chunk))
                if before != after
            )
            position += len(left_chunk)
    return offsets


def partition_geometry(path):
    with open(path, "rb") as stream:
        stream.seek(MBR_PARTITION_OFFSET + 8)
        fields = stream.read(8)
    require(len(fields) == 8, f"short MBR partition entry: {path}")
    start_sector = int.from_bytes(fields[:4], "little")
    sector_count = int.from_bytes(fields[4:], "little")
    require(start_sector > 0, f"invalid partition start in {path}")
    require(sector_count > 0, f"invalid partition size in {path}")
    offset = start_sector * SECTOR_SIZE
    size = sector_count * SECTOR_SIZE
    require(offset + size <= os.path.getsize(path), f"partition exceeds image: {path}")
    return offset, size


def extract_partition(source, destination):
    offset, size = partition_geometry(source)
    remaining = size
    with open(source, "rb") as input_stream, open(destination, "wb") as output_stream:
        input_stream.seek(offset)
        while remaining:
            chunk = input_stream.read(min(1024 * 1024, remaining))
            require(chunk, f"short partition read from {source}")
            output_stream.write(chunk)
            remaining -= len(chunk)


def create_shifted_partition_copy(source, destination):
    old_offset, size = partition_geometry(source)
    new_start_sector = old_offset // SECTOR_SIZE + 2
    new_offset = new_start_sector * SECTOR_SIZE
    require(new_offset + size <= os.path.getsize(source), "no room for shifted partition")
    with open(source, "rb") as stream:
        stream.seek(old_offset)
        partition = stream.read(size)
    require(len(partition) == size, "short source partition for shifted control")

    shutil.copyfile(source, destination)
    with open(destination, "r+b") as stream:
        stream.seek(new_offset)
        stream.write(partition)
        stream.seek(MBR_PARTITION_OFFSET + 8)
        stream.write(new_start_sector.to_bytes(4, "little"))
        stream.seek(old_offset + SUPER_MAGIC_OFFSET)
        stream.write(b"\x00\x00")


def contains_diagnostics(output, fragments):
    lowered = output.lower()
    return all(fragment in lowered for fragment in fragments)


def run_clean_controls(args, image, partition):
    inspect = run([args.minix_inspect, "--audit", image], args.timeout)
    require(
        inspect.returncode == 0,
        f"clean inspector control failed for {image}:\n{diagnostic(inspect.stdout, 2000)}",
    )
    require(
        "bitmaps, inodes and directory entries are consistent" in inspect.stdout,
        f"clean inspector control lacked success diagnostic for {image}",
    )

    extract_partition(image, partition)
    partition_hash = sha256(partition)
    fsck = run([args.fsck, "-f", "-v", partition], args.timeout)
    require(
        fsck.returncode == 0,
        f"clean fsck control failed for {image}:\n{diagnostic(fsck.stdout, 2000)}",
    )
    require(sha256(partition) == partition_hash, f"fsck modified clean partition from {image}")


def inject_fault(source, destination, fault, partition_offset):
    shutil.copyfile(source, destination)
    require(sha256(source) == sha256(destination), "disposable copy differs before injection")
    offset = partition_offset + fault.offset
    with open(destination, "r+b") as stream:
        stream.seek(offset)
        actual = stream.read(len(fault.expected))
        require(
            actual == fault.expected,
            f"{fault.name}: expected {fault.expected.hex()} at 0x{offset:x}, got {actual.hex()}",
        )
        stream.seek(offset)
        stream.write(fault.replacement)

    expected_offsets = [
        offset + index
        for index, (before, after) in enumerate(zip(fault.expected, fault.replacement))
        if before != after
    ]
    require(
        changed_offsets(source, destination) == expected_offsets,
        f"{fault.name}: bytes outside the declared mutation changed",
    )


def run_fault(args, source, destination, partition, fault):
    partition_offset, _ = partition_geometry(source)
    inject_fault(source, destination, fault, partition_offset)
    corrupt_hash = sha256(destination)

    inspect = run([args.minix_inspect, "--audit", destination], args.timeout)
    require(
        inspect.returncode == 1,
        f"{fault.name}: inspector returned {inspect.returncode}, expected 1",
    )
    require(
        contains_diagnostics(inspect.stdout, fault.inspect_diagnostics),
        f"{fault.name}: inspector diagnostic mismatch:\n{diagnostic(inspect.stdout, 2000)}",
    )
    require(
        sha256(destination) == corrupt_hash,
        f"{fault.name}: inspector modified the corrupt copy",
    )

    extract_partition(destination, partition)
    partition_hash = sha256(partition)
    fsck = run([args.fsck, "-f", "-v", partition], args.timeout)
    require(
        fsck.returncode == fault.fsck_status,
        f"{fault.name}: fsck returned {fsck.returncode}, expected {fault.fsck_status}",
    )
    require(
        contains_diagnostics(fsck.stdout, fault.fsck_diagnostics),
        f"{fault.name}: fsck diagnostic mismatch:\n{diagnostic(fsck.stdout, 2000)}",
    )
    require(
        sha256(partition) == partition_hash,
        f"{fault.name}: fsck modified its corrupt partition operand",
    )
    require(sha256(destination) == corrupt_hash, f"{fault.name}: raw corrupt copy changed")


def run_suite(args):
    for path in (args.minix_inspect, *args.images):
        require(os.path.exists(path), f"missing artifact: {path}")
    require(shutil.which(args.fsck) is not None, f"missing fsck command: {args.fsck}")

    with tempfile.TemporaryDirectory(prefix="linux001-fs-corruption-") as temp_dir:
        shifted_image = os.path.join(temp_dir, "shifted-root.img")
        shifted_partition = os.path.join(temp_dir, "shifted-root.minix")
        create_shifted_partition_copy(args.images[0], shifted_image)
        run_clean_controls(args, shifted_image, shifted_partition)
        if args.verbose:
            print("shifted MBR partition accepted by both oracles")

        for image in args.images:
            profile_dir = os.path.join(temp_dir, os.path.basename(image))
            os.mkdir(profile_dir)
            clean_partition = os.path.join(profile_dir, "clean.minix")
            run_clean_controls(args, image, clean_partition)
            for fault in FAULTS:
                destination = os.path.join(profile_dir, f"{fault.name}.img")
                partition = os.path.join(profile_dir, f"{fault.name}.minix")
                run_fault(args, image, destination, partition, fault)
                if args.verbose:
                    print(f"{os.path.basename(image)}: {fault.name} rejected by both oracles")


def main():
    args = parse_args()
    original_hashes = {
        image: sha256(image) for image in args.images if os.path.exists(image)
    }
    failure = None
    try:
        run_suite(args)
    except (OSError, TestFailure) as error:
        failure = str(error)

    for image, original_hash in original_hashes.items():
        if sha256(image) != original_hash:
            failure = f"canonical image changed during corruption test: {image}"

    if failure:
        print(f"filesystem corruption test failed: {failure}")
        return 1
    print("deterministic filesystem corruption test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
