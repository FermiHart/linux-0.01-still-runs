#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Validate the published historical-core patch and incompatibility dataset."""

import csv
import hashlib
import json
import os
import stat
import subprocess
import sys
import tarfile
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(REPO_ROOT, "datasets", "patches")
MANIFEST_PATH = os.path.join(DATASET_DIR, "MANIFEST.json")
REQUIRED_FILES = {
    "README.md",
    "MANIFEST.json",
    "SHA256SUMS.txt",
    "adaptations.csv",
    "adaptation_files.csv",
    "evidence_links.csv",
    "file_deltas.csv",
    "historical-core.patch",
}
EXPECTED_ADAPTATIONS = {
    "A-ATA-PIO",
    "A-BITMAP-O1",
    "A-BUFFER-FREELIST",
    "A-CMOS-Y2K",
    "A-COLORED-PRINTK",
    "A-CONSOLE-DEDUPE",
    "A-CP437-FILTER",
    "A-EXPERIENCE-ENV",
    "A-INCLUDE-COMPAT",
    "A-IOCTL-VOLATILE",
    "A-KERNEL-ASM",
    "A-LIB-OPEN",
    "A-MINIX-ROOTFS",
    "A-MM-COMPAT",
    "A-PIPE-HEAD",
    "A-SYSCALL-GCC",
    "A-UART-115200",
    "A-VGA-80X50",
    "A-VSPRINTF-O1",
}
EXPECTED_PORT_COMMIT = "ae458306905d4fee85121ac3c2b42e86ed099310"
EXPECTED_UNRESOLVED = {
    "kernel/exit.c",
    "kernel/fork.c",
    "kernel/panic.c",
    "kernel/printk.c",
    "kernel/sched.c",
    "kernel/sys.c",
    "kernel/traps.c",
    "lib/_exit.c",
    "lib/sync.c",
}


def fail(message):
    raise AssertionError(message)


def read_csv(name):
    with open(os.path.join(DATASET_DIR, name), newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_environment():
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("GIT_"):
            environment.pop(name)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["GIT_PAGER"] = "cat"
    environment["HOME"] = os.devnull
    environment["XDG_CONFIG_HOME"] = os.devnull
    environment["LC_ALL"] = "C"
    return environment


def main():
    environment = git_environment()
    if not os.path.isdir(DATASET_DIR):
        fail("datasets/patches is missing")

    actual_files = set(os.listdir(DATASET_DIR))
    if actual_files != REQUIRED_FILES:
        fail(f"dataset files are {sorted(actual_files)}, expected {sorted(REQUIRED_FILES)}")

    with open(MANIFEST_PATH, encoding="utf-8") as source:
        manifest = json.load(source)

    expected_manifest = {
        "schema_version": 1,
        "dataset_id": "linux-0.01-historical-core-patches-v1",
        "historical_core_path_count": 53,
        "adaptation_count": 19,
        "unresolved_path_count": 9,
        "paired_observation_count": 0,
        "rq2_ablation_configuration_count": 0,
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            fail(f"manifest {field!r} is {manifest.get(field)!r}, expected {expected!r}")

    if manifest.get("upstream_sha256") != (
        "24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d"
    ):
        fail("manifest does not pin the canonical upstream tarball")
    if manifest.get("port_commit") != EXPECTED_PORT_COMMIT:
        fail(f"manifest does not pin Wave 107 commit {EXPECTED_PORT_COMMIT}")
    if not re_full_hash(manifest.get("port_tree", "")):
        fail("manifest port_tree is not a full Git hash")
    generator_path = os.path.join(REPO_ROOT, manifest.get("generator_path", ""))
    if not os.path.isfile(generator_path) or sha256(generator_path) != manifest.get("generator_sha256"):
        fail("manifest generator identity does not match the live generator")
    ledger = subprocess.check_output(
        ["git", "show", f"{manifest['port_commit']}:{manifest['ledger_path']}"],
        cwd=REPO_ROOT,
        env=environment,
    )
    if hashlib.sha256(ledger).hexdigest() != manifest.get("ledger_sha256"):
        fail("manifest ledger identity does not match the pinned port commit")

    deltas = read_csv("file_deltas.csv")
    if len(deltas) != 53 or len({row["delta_id"] for row in deltas}) != 53:
        fail("file_deltas.csv must contain 53 unique deltas")
    if len({row["path"] for row in deltas}) != 53:
        fail("file_deltas.csv contains duplicate paths")
    change_counts = {}
    for row in deltas:
        change_counts[row["change_type"]] = change_counts.get(row["change_type"], 0) + 1
    if change_counts != {"modified": 49, "mode_only": 1, "added": 3}:
        fail(f"unexpected historical-core change counts: {change_counts}")
    mode_only = [row for row in deltas if row["change_type"] == "mode_only"]
    if [row["path"] for row in mode_only] != ["include/stdarg.h"]:
        fail("include/stdarg.h must be the sole mode-only delta")

    adaptations = read_csv("adaptations.csv")
    adaptation_ids = {row["adaptation_id"] for row in adaptations}
    if adaptation_ids != EXPECTED_ADAPTATIONS or len(adaptations) != len(EXPECTED_ADAPTATIONS):
        fail("adaptations.csv lost the exact 19 stable adaptation IDs")
    forbidden_claims = {"invalidated_assumption", "minimum", "inclusion_minimal"}
    for row in adaptations:
        if row["rq1_claim_level"] in forbidden_claims or row["rq2_role"] in forbidden_claims:
            fail(f"unsupported claim in adaptation {row['adaptation_id']}")
        if row["rq2_role"] != "not_in_predeclared_universe":
            fail(f"adaptation {row['adaptation_id']} overstates its RQ2 role")

    joins = read_csv("adaptation_files.csv")
    unresolved = {
        row["path"] for row in joins
        if not row["adaptation_id"] and row["semantic_attribution"] == "unresolved"
    }
    if unresolved != EXPECTED_UNRESOLVED:
        fail(f"unresolved delta paths are {sorted(unresolved)}")
    if {row["join_basis"] for row in joins} - {"explicit_path", "declared_glob", "none"}:
        fail("adaptation_files.csv contains an unknown join basis")
    delta_ids = {row["delta_id"] for row in deltas}
    if {row["delta_id"] for row in joins if row["delta_id"]} != delta_ids:
        fail("adaptation_files.csv does not cover every delta ID")

    evidence = read_csv("evidence_links.csv")
    if {row["adaptation_id"] for row in evidence} != EXPECTED_ADAPTATIONS:
        fail("every adaptation must retain at least one evidence or gap row")
    for row in evidence:
        if row["observation_id"] or row["raw_output_sha256"]:
            fail("dataset fabricates a retained observation or raw output")
        if row["reference_kind"] in {"test_source", "compiler_reduction"}:
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{manifest['port_commit']}:{row['reference']}"],
                cwd=REPO_ROOT,
                env=environment,
            )
            if result.returncode:
                fail(f"evidence reference is absent from the pinned port: {row['reference']}")

    patch_path = os.path.join(DATASET_DIR, "historical-core.patch")
    if sha256(patch_path) != manifest.get("historical_core_patch_sha256"):
        fail("manifest historical-core patch hash is stale")
    with open(patch_path, encoding="utf-8") as source:
        patch = source.read()
    if "old mode 100755\nnew mode 100644" not in patch:
        fail("historical-core.patch lost the include/stdarg.h mode change")

    with tempfile.TemporaryDirectory(prefix="patch-dataset-apply-") as temporary:
        with tarfile.open(os.path.join(REPO_ROOT, manifest["upstream_path"]), "r:gz") as archive:
            archive.extractall(temporary, filter="data")
        upstream_root = os.path.join(temporary, "linux")
        subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn", patch_path],
            cwd=upstream_root,
            check=True,
            env=environment,
        )
        subprocess.run(
            ["git", "apply", "--whitespace=nowarn", patch_path],
            cwd=upstream_root,
            check=True,
            env=environment,
        )
        tree = subprocess.check_output(
            [
                "git", "ls-tree", "-rz", "--full-tree", EXPECTED_PORT_COMMIT, "--",
                "init", "kernel", "mm", "fs", "lib", "include",
            ],
            cwd=REPO_ROOT,
            env=environment,
        )
        expected_snapshot = {}
        for record in tree.split(b"\0"):
            if not record:
                continue
            metadata, encoded_path = record.split(b"\t", 1)
            mode, object_type, _object_hash = metadata.decode("ascii").split()
            path = encoded_path.decode("utf-8")
            if object_type != "blob" or not path.endswith((".c", ".h", ".s", ".S")):
                continue
            expected_snapshot[path] = (
                subprocess.check_output(
                    ["git", "show", f"{EXPECTED_PORT_COMMIT}:{path}"],
                    cwd=REPO_ROOT,
                    env=environment,
                ),
                mode,
            )
        actual_paths = set()
        for directory in ("init", "kernel", "mm", "fs", "lib", "include"):
            for current, directories, files in os.walk(os.path.join(upstream_root, directory)):
                directories.sort()
                for name in sorted(files):
                    path = os.path.relpath(os.path.join(current, name), upstream_root)
                    if path.endswith((".c", ".h", ".s", ".S")):
                        actual_paths.add(path)
        if actual_paths != set(expected_snapshot):
            fail("applied patch source paths do not match the pinned port tree")
        for path, (expected_content, expected_mode) in expected_snapshot.items():
            full_path = os.path.join(upstream_root, path)
            with open(full_path, "rb") as source:
                if source.read() != expected_content:
                    fail(f"applied patch differs from the pinned port at {path}")
            actual_mode = "100755" if os.stat(full_path).st_mode & stat.S_IXUSR else "100644"
            if actual_mode != expected_mode:
                fail(f"applied patch mode differs from the pinned port at {path}")
        for row in deltas:
            path = os.path.join(upstream_root, row["path"])
            if row["change_type"] == "deleted":
                if os.path.exists(path):
                    fail(f"patch retained deleted path {row['path']}")
                continue
            if sha256(path) != row["port_sha256"]:
                fail(f"applied patch has wrong content for {row['path']}")
            mode = "100755" if os.stat(path).st_mode & stat.S_IXUSR else "100644"
            if mode != row["port_mode"]:
                fail(f"applied patch has wrong mode for {row['path']}")

    checksums = {}
    with open(os.path.join(DATASET_DIR, "SHA256SUMS.txt"), encoding="ascii") as source:
        for line in source:
            digest, name = line.rstrip("\n").split("  ", 1)
            checksums[name] = digest
    expected_checksummed = REQUIRED_FILES - {"SHA256SUMS.txt"}
    if set(checksums) != expected_checksummed:
        fail("SHA256SUMS.txt does not cover every non-self-referential dataset file")
    for name, digest in checksums.items():
        if sha256(os.path.join(DATASET_DIR, name)) != digest:
            fail(f"checksum mismatch for {name}")

    subprocess.run(
        [sys.executable, "scripts/build-patch-dataset.py", "--check"],
        cwd=REPO_ROOT,
        check=True,
    )
    print("patch dataset matches the pinned upstream and port snapshots")
    return 0


def re_full_hash(value):
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f"patch dataset check failed: {error}", file=sys.stderr)
        sys.exit(1)
