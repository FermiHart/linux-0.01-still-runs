#!/bin/bash
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Use the canonical dataset snapshot and ledger-join implementation on live bytes.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="${BUILD:-build}"
case "$BUILD_DIR" in
    /*) ;;
    *) BUILD_DIR="${ROOT_DIR}/${BUILD_DIR}" ;;
esac
exec python3 "${ROOT_DIR}/scripts/provenance-report.py" \
    --output "${BUILD_DIR}/PROVENANCE.txt"
