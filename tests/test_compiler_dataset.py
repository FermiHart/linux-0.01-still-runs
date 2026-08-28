#!/usr/bin/env python3
"""
Verify that the compiler-case academic dataset is packaged and contains a valid
manifest and checksum file.
"""

import argparse
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
DATASET_DIR = os.path.join(HARNESS_DIR, "build", "compiler-dataset")
MANIFEST_PATH = os.path.join(DATASET_DIR, "MANIFEST.json")
CHECKSUMS_PATH = os.path.join(DATASET_DIR, "SHA256SUMS.txt")
TARBALL_PATH = os.path.join(HARNESS_DIR, "build", "compiler-dataset.tar.gz")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    args = parser.parse_args()

    subprocess.run(
        ["make", "-C", HARNESS_DIR, "package-dataset"],
        cwd=REPO_ROOT,
        check=True,
    )

    assert os.path.isfile(MANIFEST_PATH), f"manifest missing: {MANIFEST_PATH}"
    assert os.path.isfile(CHECKSUMS_PATH), f"checksums missing: {CHECKSUMS_PATH}"
    assert os.path.isfile(TARBALL_PATH), f"tarball missing: {TARBALL_PATH}"

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    assert "title" in manifest
    assert "date" in manifest
    assert "files" in manifest and manifest["files"]

    required = ["buffer_freelist.c", "bitmap_inline_asm.c", "vsprintf_percent_s.c",
                "CLASSIFICATION.md", "README.md"]
    names = {entry["name"] for entry in manifest["files"]}
    for r in required:
        assert r in names, f"dataset missing {r}"

    print("compiler-case dataset packaged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
