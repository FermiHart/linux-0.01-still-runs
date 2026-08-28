#!/bin/bash
# Verify byte-for-byte reproducibility by building twice and comparing hashes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TMPDIR="${TMPDIR:-/tmp}"
WORKA="$(mktemp -d "${TMPDIR}/linux001-repro-a.XXXXXXXX")"
WORKB="$(mktemp -d "${TMPDIR}/linux001-repro-b.XXXXXXXX")"
cleanup() { rm -rf -- "${WORKA}" "${WORKB}"; }
trap cleanup EXIT

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"

printf 'Verifying reproducibility with SOURCE_DATE_EPOCH=%s\n' "${SOURCE_DATE_EPOCH}"

cp -a "${ROOT_DIR}/." "${WORKA}/"
cp -a "${ROOT_DIR}/." "${WORKB}/"

cd "${WORKA}"
make reproducible >/dev/null 2>&1
cp "${WORKA}/build/SHA256SUMS" "${TMPDIR}/repro-a.sha256"

cd "${WORKB}"
make reproducible >/dev/null 2>&1
cp "${WORKB}/build/SHA256SUMS" "${TMPDIR}/repro-b.sha256"

if diff -q "${TMPDIR}/repro-a.sha256" "${TMPDIR}/repro-b.sha256" >/dev/null; then
    printf 'Reproducibility verified: SHA256SUMS are byte-for-byte identical.\n'
    exit 0
else
    printf 'Reproducibility failure: builds differ.\n' >&2
    diff -u "${TMPDIR}/repro-a.sha256" "${TMPDIR}/repro-b.sha256" >&2 || true
    exit 1
fi
