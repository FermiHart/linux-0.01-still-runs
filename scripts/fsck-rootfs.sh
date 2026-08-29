#!/bin/bash
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Validate the Minix v1 root filesystem with fsck.minix.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ROOT_IMG="${1:-${ROOT_DIR}/build/root.img}"
TMP_IMG=$(mktemp "${ROOT_DIR}/build/.root-partition.XXXXXX.img")
trap 'rm -f "${TMP_IMG}"' EXIT

if [ ! -f "${ROOT_IMG}" ]; then
    printf 'root image not found: %s\n' "${ROOT_IMG}" >&2
    exit 1
fi

if ! command -v fsck.minix >/dev/null 2>&1; then
    printf 'fsck.minix not found; install util-linux\n' >&2
    exit 1
fi

# Extract partition 0 (starts at sector 1, ends at end of image).
sectors=$(stat -c%s "${ROOT_IMG}")
sectors=$((sectors / 512 - 1))
dd if="${ROOT_IMG}" of="${TMP_IMG}" bs=512 skip=1 count="${sectors}" status=none

fsck.minix -v "${TMP_IMG}"
