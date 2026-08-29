#!/bin/bash
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Import and verify the upstream Linux 0.01 tarball.
# This script is idempotent: running it again cleans and re-extracts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstream"
TARBALL="${UPSTREAM_DIR}/linux-0.01.tar.gz"
EXTRACT_DIR="${UPSTREAM_DIR}/extracted"

if [ ! -f "${TARBALL}" ]; then
    printf 'Upstream tarball not found: %s\n' "${TARBALL}" >&2
    printf 'Run from the repository root or place the tarball manually.\n' >&2
    exit 1
fi

printf 'Verifying upstream tarball...\n'
cd "${UPSTREAM_DIR}"
sha256sum --check SHA256SUMS

printf 'Cleaning previous extraction...\n'
rm -rf "${EXTRACT_DIR}"

printf 'Extracting to %s\n' "${EXTRACT_DIR}"
mkdir -p "${EXTRACT_DIR}"
tar --extract --file "${TARBALL}" --directory "${EXTRACT_DIR}"

printf 'Upstream source ready at %s/linux/\n' "${EXTRACT_DIR}"
