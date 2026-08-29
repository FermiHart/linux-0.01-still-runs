#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Prove guest-driven halt and Minix persistence across bEMU processes."""

import argparse
import hashlib
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    extract_command_output,
    sanitize_terminal,
)


SECTOR_SIZE = 512
MBR_PARTITION_OFFSET = 0x1BE
HALT_MESSAGE = "[bemu-linux01] guest halted with interrupts disabled"
UNREQUESTED_HALT_MESSAGE = "[bemu-linux01] unrequested guest halt with interrupts disabled"


class TestFailure(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Linux 0.01 cross-process filesystem persistence test"
    )
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--alive-img", default="build/root.img")
    parser.add_argument("--historical-img", default="build/root-1991.img")
    parser.add_argument("--minix-inspect", default="build/minix-inspect")
    parser.add_argument("--fsck", default="fsck.minix")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def require(condition, message):
    if not condition:
        raise TestFailure(message)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command, timeout, text=True):
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=text,
            errors="replace" if text else None,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        output = diagnostic(error.stdout, 3000)
        raise TestFailure(
            f"command timed out after {timeout}s: {command[0]}\n{output}"
        ) from error


def run_guest(args, profile, image, script):
    result = run([
        args.bemu,
        "--kernel", args.kernel,
        "--root", image,
        "--experience", profile,
        "--keys", script,
    ], args.timeout)
    output = sanitize_terminal(result.stdout)
    require(
        result.returncode == 0,
        f"{profile}: bEMU exited {result.returncode}:\n{diagnostic(output, 3000)}",
    )
    require(
        BEMU_PASS_RE.search(output) is not None,
        f"{profile}: bEMU omitted its PASS result",
    )
    require(
        KERNEL_FAULT_RE.search(output) is None,
        f"{profile}: kernel fault during persistence test",
    )
    require(HALT_MESSAGE in output, f"{profile}: terminal guest HLT was not classified")
    require(
        re.search(r"(?m)^System halted\.$", output) is not None,
        f"{profile}: guest did not reach its post-sync halt message",
    )
    return output


def inode_section(output, inode):
    match = re.search(rb"(?m)^inode\s+" + str(inode).encode() + rb"\s+.*$", output)
    require(match is not None, f"inspector omitted inode {inode}")
    next_inode = re.search(rb"(?m)^inode\s+\d+\s+", output[match.end():])
    end = len(output) if next_inode is None else match.end() + next_inode.start()
    return output[match.start():end]


def child_inode(output, parent_inode, name):
    section = inode_section(output, parent_inode)
    match = re.search(
        rb"(?m)^\s+" + re.escape(name.encode()) + rb"\s+-> inode\s+(\d+)\s*$",
        section,
    )
    require(match is not None, f"inspector did not resolve {name!r} below inode {parent_inode}")
    return int(match.group(1))


def inspect_payload(args, profile, image, payload):
    image_hash = sha256(image)
    result = run([args.minix_inspect, "--audit", image], args.timeout, text=False)
    require(
        result.returncode == 0,
        f"{profile}: minix-inspect rejected persisted image:\n{diagnostic(result.stdout, 3000)}",
    )
    require(
        b"bitmaps, inodes and directory entries are consistent" in result.stdout,
        f"{profile}: minix-inspect omitted its consistency result",
    )

    tmp_inode = child_inode(result.stdout, 1, "tmp")
    proof_dir_inode = child_inode(result.stdout, tmp_inode, "d01p")
    proof_inode = child_inode(result.stdout, proof_dir_inode, "proof")
    expected = payload.encode() + b"\n"
    header = re.search(
        rb"(?m)^--- inode\s+" + str(proof_inode).encode() +
        rb"\s+\((\d+) bytes\) ---\n",
        result.stdout,
    )
    require(header is not None, f"{profile}: inspector omitted proof file contents")
    size = int(header.group(1))
    content = result.stdout[header.end():header.end() + size]
    require(size == len(expected), f"{profile}: persisted proof has size {size}, expected {len(expected)}")
    require(content == expected, f"{profile}: inspector found incorrect persisted bytes")
    require(sha256(image) == image_hash, f"{profile}: minix-inspect modified its input")


def partition_geometry(path):
    with open(path, "rb") as stream:
        stream.seek(MBR_PARTITION_OFFSET + 8)
        fields = stream.read(8)
    require(len(fields) == 8, f"short MBR partition entry: {path}")
    start_sector = int.from_bytes(fields[:4], "little")
    sector_count = int.from_bytes(fields[4:], "little")
    require(start_sector > 0 and sector_count > 0, f"invalid MBR partition: {path}")
    offset = start_sector * SECTOR_SIZE
    size = sector_count * SECTOR_SIZE
    require(offset + size <= os.path.getsize(path), f"partition exceeds image: {path}")
    return offset, size


def fsck_image(args, profile, image, partition):
    offset, size = partition_geometry(image)
    image_hash = sha256(image)
    with open(image, "rb") as source, open(partition, "wb") as destination:
        source.seek(offset)
        remaining = size
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            require(chunk, f"{profile}: short read while extracting Minix partition")
            destination.write(chunk)
            remaining -= len(chunk)
    partition_hash = sha256(partition)
    result = run([args.fsck, "-f", "-v", partition], args.timeout)
    require(
        result.returncode == 0,
        f"{profile}: fsck.minix rejected persisted image:\n{diagnostic(result.stdout, 3000)}",
    )
    require(sha256(partition) == partition_hash, f"{profile}: fsck.minix modified partition")
    require(sha256(image) == image_hash, f"{profile}: filesystem oracles modified image")


def run_profile(args, profile, source, temp_dir):
    image = os.path.join(temp_dir, f"{profile}.img")
    partition = os.path.join(temp_dir, f"{profile}.minix")
    shutil.copyfile(source, image)
    source_hash = sha256(source)
    require(sha256(image) == source_hash, f"{profile}: disposable copy differs from source")

    nonce = secrets.token_hex(8).upper()
    payload = f"D01_{profile}_{nonce}"
    sync_marker = f"D01SYNC_{profile}_{nonce}"
    first_script = (
        "mkdir /tmp/d01p\n"
        f"echo {payload} > /tmp/d01p/proof\n"
        "sync\n"
        f"echo {sync_marker}\n"
        "halt\n"
    )
    first_output = run_guest(args, profile, image, first_script)
    require(
        len(re.findall(rf"(?m)^{re.escape(sync_marker)}$", first_output)) == 1,
        f"{profile}: no unambiguous marker after sync returned",
    )
    persisted_hash = sha256(image)
    require(persisted_hash != source_hash, f"{profile}: first boot did not change image hash")
    require(sha256(source) == source_hash, f"{profile}: first boot changed canonical image")

    inspect_payload(args, profile, image, payload)
    fsck_image(args, profile, image, partition)

    begin = f"D01BEGIN_{profile}_{nonce}"
    end = f"D01END_{profile}_{nonce}"
    second_script = (
        f"echo {begin}\n"
        "cat /tmp/d01p/proof\n"
        f"echo {end}\n"
        "halt\n"
    )
    second_output = run_guest(args, profile, image, second_script)
    try:
        segment, _ = extract_command_output(
            second_output, begin, end, command="cat /tmp/d01p/proof", validate=True,
        )
    except ValueError as error:
        raise TestFailure(f"{profile}: invalid second-boot command boundary: {error}") from error
    require(
        len(re.findall(rf"(?m)^{re.escape(payload)}$", segment)) == 1,
        f"{profile}: second process did not read the exact persisted payload",
    )
    require(sha256(source) == source_hash, f"{profile}: second boot changed canonical image")
    if args.verbose:
        print(f"{profile}: {source_hash[:12]} -> {persisted_hash[:12]}, payload {payload}")


def reject_unrequested_panic_halt(args, source, temp_dir):
    image = os.path.join(temp_dir, "panic.img")
    shutil.copyfile(source, image)
    offset, _ = partition_geometry(image)
    with open(image, "r+b") as stream:
        stream.seek(offset + 1024 + 16)
        stream.write(b"\0\0")
    result = run([
        args.bemu,
        "--kernel", args.kernel,
        "--root", image,
        "--experience", "alive",
    ], args.timeout)
    output = sanitize_terminal(result.stdout)
    require(result.returncode != 0, "kernel panic was misclassified as successful shutdown")
    require("Kernel panic:" in output, "corrupt-root control did not reach kernel panic")
    require(UNREQUESTED_HALT_MESSAGE in output, "unrequested panic HLT was not rejected")
    require(BEMU_PASS_RE.search(output) is None, "kernel panic emitted a bEMU PASS result")


def main():
    args = parse_args()
    profiles = (("alive", args.alive_img), ("1991", args.historical_img))
    required_paths = (args.bemu, args.kernel, args.minix_inspect, *(path for _, path in profiles))
    for path in required_paths:
        if not os.path.exists(path):
            print(f"missing artifact: {path}; run make all first")
            return 1
    if shutil.which(args.fsck) is None:
        print(f"missing fsck command: {args.fsck}")
        return 1

    canonical_hashes = {path: sha256(path) for _, path in profiles}
    failure = None
    try:
        with tempfile.TemporaryDirectory(prefix="linux001-persistence-") as temp_dir:
            reject_unrequested_panic_halt(args, args.alive_img, temp_dir)
            for profile, image in profiles:
                run_profile(args, profile, image, temp_dir)
    except (OSError, TestFailure) as error:
        failure = str(error)
    for path, original_hash in canonical_hashes.items():
        if sha256(path) != original_hash:
            failure = f"canonical image changed during persistence test: {path}"
    if failure:
        print(f"cross-process filesystem persistence test failed: {failure}")
        return 1
    print("cross-process filesystem persistence test passed for alive and 1991")
    return 0


if __name__ == "__main__":
    sys.exit(main())
