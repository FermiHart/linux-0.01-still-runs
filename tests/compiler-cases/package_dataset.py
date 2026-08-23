#!/usr/bin/env python3
"""
Package the compiler-case investigation as an academic dataset.

The dataset includes:
  * the three minimal reproduction sources (C files)
  * the Makefile, scripts and documentation (README, CLASSIFICATION, UPSTREAM_TEMPLATE)
  * the generated report, audit log, classification, matrix and assembly diffs
  * a manifest and SHA-256 checksums

The output directory is build/compiler-dataset/ and is suitable for archival or
release (e.g. as part of the artifact package or Zenodo deposit).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
BUILD_DIR = os.path.join(HARNESS_DIR, "build")
DATASET_DIR = os.path.join(BUILD_DIR, "compiler-dataset")

STATIC_FILES = [
    "Makefile",
    "run.sh",
    "compare_asm.sh",
    "audit.sh",
    "summarize.py",
    "classify.py",
    "bugreport.py",
    "matrix.py",
    "buffer_freelist.c",
    "bitmap_inline_asm.c",
    "vsprintf_percent_s.c",
    "README.md",
    "CLASSIFICATION.md",
    "UPSTREAM_TEMPLATE.md",
]

GENERATED_FILES = [
    "report.txt",
    "audit.txt",
    "summary.json",
    "classification.json",
    "classification.txt",
    "matrix.json",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    subprocess.run(
        ["make", "-C", HARNESS_DIR, "matrix", "bugreport", "compare-assembly"],
        cwd=REPO_ROOT,
        check=True,
    )

    if os.path.isdir(DATASET_DIR):
        shutil.rmtree(DATASET_DIR)
    os.makedirs(DATASET_DIR, exist_ok=True)

    manifest = {
        "title": "Linux 0.01 porting layer: -O2 sensitive compiler cases",
        "source_project": "linux-0.01-still-runs",
        "date": subprocess.check_output(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True
        ).strip(),
        "files": [],
    }

    def add(path, dest_name=None):
        if not os.path.isfile(path):
            return
        name = dest_name or os.path.basename(path)
        dst = os.path.join(DATASET_DIR, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(path, dst)
        manifest["files"].append({
            "name": name,
            "sha256": sha256(path),
        })

    for f in STATIC_FILES:
        add(os.path.join(HARNESS_DIR, f))

    for f in GENERATED_FILES:
        add(os.path.join(BUILD_DIR, f))

    # Copy assembly diffs (if generated)
    asm_dir = os.path.join(BUILD_DIR, "asm")
    if os.path.isdir(asm_dir):
        for name in sorted(os.listdir(asm_dir)):
            add(os.path.join(asm_dir, name), dest_name=f"asm/{name}")

    manifest_path = os.path.join(DATASET_DIR, "MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    checksums_path = os.path.join(DATASET_DIR, "SHA256SUMS.txt")
    with open(checksums_path, "w") as f:
        for entry in manifest["files"]:
            f.write(f"{entry['sha256']}  {entry['name']}\n")

    tar_path = os.path.join(BUILD_DIR, "compiler-dataset.tar.gz")
    subprocess.run(
        ["tar", "-czf", tar_path, "-C", BUILD_DIR, "compiler-dataset"],
        cwd=REPO_ROOT,
        check=True,
    )

    print(f"dataset written to {DATASET_DIR}")
    print(f"archive: {tar_path}")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
