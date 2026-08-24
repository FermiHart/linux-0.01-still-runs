#!/bin/bash
# Create a release artifact tarball for linux-0.01-still-runs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build"
RELEASE_DIR="${ROOT_DIR}/release"
REV="$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
ARTIFACT="${RELEASE_DIR}/linux-0.01-still-runs-${REV}.tar.gz"

if [ ! -d "${BUILD_DIR}" ]; then
    printf 'Build directory not found: %s\n' "${BUILD_DIR}" >&2
    exit 1
fi

mkdir -p "${RELEASE_DIR}"

printf 'Creating artifact %s\n' "${ARTIFACT}"

tar -czf "${ARTIFACT}" \
    -C "${ROOT_DIR}" \
    --exclude='*.o' --exclude='*.d' --exclude='*.tmp' \
    build/kernel.bin \
    build/root.img \
    build/root-1991.img \
    build/bemu-linux01 \
    build/SHA256SUMS \
    build/REPRODUCIBLE.sha256 \
    docs/ \
    LICENSE \
    README.md \
    2>/dev/null || {
        printf 'Artifact creation failed. Ensure make all && make checksums have been run.\n' >&2
        exit 1
    }

printf '%s\n' "${ARTIFACT}"
