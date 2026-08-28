#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

status=0

if command -v cppcheck >/dev/null 2>&1; then
    echo "==> cppcheck on bEMU"
    cppcheck --quiet --error-exitcode=1 \
        --enable=warning,style,performance,portability \
        -Ibbp/include -ibbp/include \
        bemu/*.c || status=1
else
    echo "[WARN] cppcheck not available"
fi

if command -v clang-tidy >/dev/null 2>&1; then
    echo "==> clang-tidy on bEMU"
    clang-tidy bemu/*.c -- -Ibbp/include || status=1
else
    echo "[WARN] clang-tidy not available"
fi

if [ "$status" -eq 0 ]; then
    echo "==> static analysis passed"
else
    echo "==> static analysis found issues" >&2
fi

exit "$status"
