#!/bin/bash
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Verify byte-for-byte reproducibility by building twice and comparing hashes.
set -euo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-repro.XXXXXXXX")"
WORKA="${WORK_DIR}/a"
WORKB="${WORK_DIR}/b"
cleanup() {
    local result=$?
    if [ "$result" -eq 0 ]; then
        rm -rf -- "${WORK_DIR}"
    else
        printf 'Failed reproducibility evidence retained at %s\n' "$WORK_DIR" >&2
    fi
}
trap cleanup EXIT

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"

printf 'Verifying reproducibility with SOURCE_DATE_EPOCH=%s\n' "${SOURCE_DATE_EPOCH}"

# Snapshot public tracked/new source once. Never copy .git, ignored build trees,
# guest sessions, release archives, credentials or private operational records.
python3 "${ROOT_DIR}/scripts/source_snapshot.py" export --source "$ROOT_DIR" --output "$WORKA"
python3 "${ROOT_DIR}/scripts/source_snapshot.py" export --source "$WORKA" --output "$WORKB"

cd "${WORKA}"
make reproducible BUILD=build >"${WORK_DIR}/a-build.log" 2>&1

cd "${WORKB}"
make reproducible BUILD=build >"${WORK_DIR}/b-build.log" 2>&1

if diff -q "${WORKA}/build/SHA256SUMS" "${WORKB}/build/SHA256SUMS" >/dev/null; then
    printf 'Reproducibility verified: SHA256SUMS are byte-for-byte identical.\n'
    exit 0
else
    printf 'Reproducibility failure: builds differ.\n' >&2
    diff -u "${WORKA}/build/SHA256SUMS" "${WORKB}/build/SHA256SUMS" >&2 || true
    exit 1
fi
