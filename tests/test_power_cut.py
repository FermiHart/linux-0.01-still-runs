#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Prove deterministic IDE power-cut states on disposable Minix images."""

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
BLOCK_SIZE = 1024
MBR_PARTITION_OFFSET = 0x1BE
MINIX_SUPERBLOCK_OFFSET = 1024
MINIX_INODE_SIZE = 32
MINIX_REGULAR = 0x8000


class TestFailure(Exception):
    pass


@dataclass(frozen=True)
class Scenario:
    name: str
    boundary: str
    target_sector: int
    changed_bytes: int
    irq_raises: int
    triggered: int = 1


SCENARIOS = (
    Scenario("accepted-first", "accepted", 0, 0, 0),
    Scenario("payload-first", "payload", 0, 0, 0),
    Scenario("committed-first", "committed", 0, 512, 0),
    Scenario("irq-first", "irq", 0, 512, 1),
    Scenario("payload-second", "payload", 1, 512, 1),
    Scenario("committed-second", "committed", 1, 1024, 1),
    Scenario("irq-second", "irq", 1, 1024, 2),
    Scenario("no-cut", "none", 0, 1024, 2, 0),
)


def parse_args():
    parser = argparse.ArgumentParser(description="deterministic IDE power-cut test")
    parser.add_argument("--driver", default="build/test-ide-power-cut")
    parser.add_argument("--minix-inspect", default="build/minix-inspect")
    parser.add_argument("--fsck", default="fsck.minix")
    parser.add_argument("--img", action="append", dest="images")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    if not args.images:
        args.images = ["build/root.img", "build/root-1991.img"]
    return args


def require(condition, message):
    if not condition:
        raise TestFailure(message)


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


def partition_geometry(path):
    with open(path, "rb") as stream:
        stream.seek(MBR_PARTITION_OFFSET + 8)
        fields = stream.read(8)
    require(len(fields) == 8, f"short MBR partition entry: {path}")
    start_sector = int.from_bytes(fields[:4], "little")
    sector_count = int.from_bytes(fields[4:], "little")
    require(start_sector > 0 and sector_count > 0, f"invalid partition: {path}")
    offset = start_sector * SECTOR_SIZE
    size = sector_count * SECTOR_SIZE
    require(offset + size <= os.path.getsize(path), f"partition exceeds image: {path}")
    return offset, size


def regular_file_lba(path):
    partition_offset, partition_size = partition_geometry(path)
    with open(path, "rb") as stream:
        stream.seek(partition_offset + MINIX_SUPERBLOCK_OFFSET)
        superblock = stream.read(18)
        require(len(superblock) == 18, f"short Minix superblock: {path}")
        ninodes = int.from_bytes(superblock[0:2], "little")
        imap_blocks = int.from_bytes(superblock[4:6], "little")
        zmap_blocks = int.from_bytes(superblock[6:8], "little")
        first_data_zone = int.from_bytes(superblock[8:10], "little")
        log_zone_size = int.from_bytes(superblock[10:12], "little")
        magic = int.from_bytes(superblock[16:18], "little")
        require(magic == 0x137F, f"not a Minix v1 filesystem: {path}")
        require(log_zone_size == 0, f"unsupported Minix zone size: {path}")
        inode_table = partition_offset + (2 + imap_blocks + zmap_blocks) * BLOCK_SIZE
        for index in range(ninodes):
            stream.seek(inode_table + index * MINIX_INODE_SIZE)
            inode = stream.read(MINIX_INODE_SIZE)
            require(len(inode) == MINIX_INODE_SIZE, f"short inode table: {path}")
            mode = int.from_bytes(inode[0:2], "little")
            size = int.from_bytes(inode[4:8], "little")
            first_zone = int.from_bytes(inode[14:16], "little")
            if mode & 0xF000 == MINIX_REGULAR and size >= BLOCK_SIZE and first_zone:
                require(first_zone >= first_data_zone, "regular file uses pre-data zone")
                offset = partition_offset + first_zone * BLOCK_SIZE
                require(offset + BLOCK_SIZE <= partition_offset + partition_size,
                        "regular file zone exceeds partition")
                require(offset % SECTOR_SIZE == 0, "regular file zone is unaligned")
                return offset // SECTOR_SIZE
    raise TestFailure(f"no full direct regular-file zone found: {path}")


def changed_offsets(left_path, right_path):
    offsets = []
    position = 0
    with open(left_path, "rb") as left, open(right_path, "rb") as right:
        while True:
            left_chunk = left.read(1024 * 1024)
            right_chunk = right.read(1024 * 1024)
            require(len(left_chunk) == len(right_chunk), "power-cut copy size changed")
            if not left_chunk:
                return offsets
            offsets.extend(
                position + index
                for index, (before, after) in enumerate(zip(left_chunk, right_chunk))
                if before != after
            )
            position += len(left_chunk)


def extract_partition(source, destination):
    offset, size = partition_geometry(source)
    with open(source, "rb") as input_stream, open(destination, "wb") as output_stream:
        input_stream.seek(offset)
        remaining = size
        while remaining:
            chunk = input_stream.read(min(1024 * 1024, remaining))
            require(chunk, f"short partition read from {source}")
            output_stream.write(chunk)
            remaining -= len(chunk)


def run_oracles(args, image, partition):
    image_hash = sha256(image)
    inspect = run([args.minix_inspect, "--audit", image], args.timeout)
    require(inspect.returncode == 0,
            f"inspector rejected data-only power-cut state:\n{diagnostic(inspect.stdout, 2000)}")
    require("bitmaps, inodes and directory entries are consistent" in inspect.stdout,
            "inspector omitted metadata-consistency diagnostic")
    require(sha256(image) == image_hash, "inspector modified power-cut image")

    extract_partition(image, partition)
    partition_hash = sha256(partition)
    fsck = run([args.fsck, "-f", "-v", partition], args.timeout)
    require(fsck.returncode == 0,
            f"fsck rejected data-only power-cut state:\n{diagnostic(fsck.stdout, 2000)}")
    require(sha256(partition) == partition_hash, "fsck modified extracted partition")
    require(sha256(image) == image_hash, "filesystem oracles modified power-cut image")


def run_scenario(args, source, destination, start_lba, scenario):
    shutil.copyfile(source, destination)
    require(sha256(source) == sha256(destination), "disposable copy differs before cut")
    cut_lba = start_lba + scenario.target_sector
    result = run([
        args.driver,
        "--drive",
        destination,
        str(start_lba),
        scenario.boundary,
        str(cut_lba),
    ], args.timeout)
    require(result.returncode == 0,
            f"{scenario.name}: driver failed:\n{diagnostic(result.stdout, 2000)}")
    expected = (
        f"triggered={scenario.triggered} powered_off={scenario.triggered} "
        f"irq_raises={scenario.irq_raises} remaining=0"
    )
    require(result.stdout.strip() == expected,
            f"{scenario.name}: state mismatch: {result.stdout.strip()!r}")
    target_offset = start_lba * SECTOR_SIZE
    expected_offsets = list(range(target_offset, target_offset + scenario.changed_bytes))
    require(changed_offsets(source, destination) == expected_offsets,
            f"{scenario.name}: bytes outside exact committed prefix changed")
    return sha256(destination)


def run_profile(args, source, temp_dir):
    start_lba = regular_file_lba(source)
    profile_dir = os.path.join(temp_dir, os.path.basename(source))
    os.mkdir(profile_dir)
    hashes_by_size = {}

    for scenario in SCENARIOS:
        observed = []
        for repeat in range(2):
            destination = os.path.join(profile_dir, f"{scenario.name}-{repeat}.img")
            observed.append(run_scenario(args, source, destination, start_lba, scenario))
            if repeat == 0:
                partition = os.path.join(profile_dir, f"{scenario.name}.minix")
                run_oracles(args, destination, partition)
                os.unlink(partition)
            os.unlink(destination)
        require(observed[0] == observed[1],
                f"{scenario.name}: repeated runs produced different hashes")
        previous = hashes_by_size.setdefault(scenario.changed_bytes, observed[0])
        require(previous == observed[0],
                f"{scenario.name}: equivalent committed-prefix hash differs")
        if args.verbose:
            print(f"{os.path.basename(source)}: {scenario.name} -> "
                  f"{scenario.changed_bytes} changed bytes, {scenario.irq_raises} IRQs")

    require(hashes_by_size[0] == sha256(source), "zero-commit cut changed image hash")
    require(len(set(hashes_by_size.values())) == 3,
            "0/512/1024-byte states do not have three distinct hashes")


def run_suite(args):
    for path in (args.driver, args.minix_inspect, *args.images):
        require(os.path.exists(path), f"missing artifact: {path}")
    require(shutil.which(args.fsck) is not None, f"missing fsck command: {args.fsck}")
    with tempfile.TemporaryDirectory(prefix="linux001-power-cut-") as temp_dir:
        for image in args.images:
            run_profile(args, image, temp_dir)


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
            failure = f"canonical image changed during power-cut test: {image}"
    if failure:
        print(f"deterministic power-cut test failed: {failure}")
        return 1
    print("deterministic IDE power-cut image test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
