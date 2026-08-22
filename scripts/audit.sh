#!/bin/bash
# Audit the historical core against the extracted upstream Linux 0.01 source.
# Produces build/AUDIT.txt with a line-oriented diff summary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstream"
TARBALL="${UPSTREAM_DIR}/linux-0.01.tar.gz"
EXTRACT_DIR="${UPSTREAM_DIR}/extracted"
UPSTREAM_SRC="${EXTRACT_DIR}/linux"
REPORT_DIR="${ROOT_DIR}/build"
REPORT="${REPORT_DIR}/AUDIT.txt"

if [ ! -f "${TARBALL}" ]; then
    printf 'Upstream tarball not found: %s\n' "${TARBALL}" >&2
    exit 1
fi

cd "${UPSTREAM_DIR}"
sha256sum --check SHA256SUMS

if [ ! -d "${UPSTREAM_SRC}" ]; then
    printf 'Extracting upstream source for comparison...\n' >&2
    bash "${SCRIPT_DIR}/import-upstream.sh" >/dev/null
fi

mkdir -p "${REPORT_DIR}"

{
    printf 'Audit Report for linux-0.01-still-runs\n'
    printf 'Generated: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'Upstream:  %s\n' "$(sha256sum "${TARBALL}" | cut -c1-64)"
    printf 'Git rev:   %s\n' "$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo 'no-git')"
    printf '\n'

    printf '═══ Historical-core diff summary ═══\n\n'
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/init" "${ROOT_DIR}/init" || true
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/kernel" "${ROOT_DIR}/kernel" || true
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/mm" "${ROOT_DIR}/mm" || true
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/fs" "${ROOT_DIR}/fs" || true
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/lib" "${ROOT_DIR}/lib" || true
    diff -ruN --exclude='*.o' --exclude='*.d' \
        "${UPSTREAM_SRC}/include" "${ROOT_DIR}/include" || true
} > "${REPORT}"

printf '%s\n' "${REPORT}"
