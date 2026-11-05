#!/usr/bin/env bash
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

set -euo pipefail

cd "$(dirname "$0")/.."

status=0
missing=0

if command -v cppcheck >/dev/null 2>&1; then
    echo "==> cppcheck on bEMU"
    cppcheck --quiet --error-exitcode=1 \
        --enable=warning,style,performance,portability \
        -Ibbp/include -ibbp/include \
        bemu/*.c || status=1
else
    echo "[SKIP] cppcheck not available"
    missing=$((missing + 1))
fi

if command -v clang-tidy >/dev/null 2>&1; then
    echo "==> clang-tidy on bEMU"
    clang-tidy bemu/*.c -- -Ibbp/include || status=1
else
    echo "[SKIP] clang-tidy not available"
    missing=$((missing + 1))
fi

if [ "$status" -ne 0 ]; then
    echo "FAIL: static analysis found issues" >&2
    exit 1
fi
if [ "$missing" -ne 0 ]; then
    echo "SKIP: static analysis incomplete ($missing required analyzers unavailable)"
    exit 77
fi
echo "PASS: cppcheck and clang-tidy completed"
