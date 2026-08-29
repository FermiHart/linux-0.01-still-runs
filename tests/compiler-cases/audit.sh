#!/bin/bash
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Audit the compiler cases for common undefined-behavior classes:
#   * aliasing        (-fstrict-aliasing + -Wstrict-aliasing)
#   * overflow        (-fsanitize=undefined)
#   * sequence points (-Wsequence-point)
#   * ABI/calling     (-m32 + -Wstack-protector)
#
# The audit does not require every build to pass; it records what each flag
# reports so the classification wave can use the evidence.

set -uo pipefail

cd "$(dirname "$0")"

CC=${CC:-gcc}
out=build/audit.txt
mkdir -p build

exec > >(tee "$out")

FLAGS_BASE="-Wall -Wextra -Werror -std=gnu89"
CASES="buffer_freelist bitmap_inline_asm vsprintf_percent_s"
ABIS="x86_64 i386"

echo "Compiler case audit"
echo "==================="
echo "Compiler: $CC"
$CC --version | head -n1
echo ""

for case in $CASES; do
    echo "--- $case ---"
    for abi in $ABIS; do
        if [ "$abi" = "i386" ]; then
            abi_flags="-m32 -no-pie"
        else
            abi_flags=""
        fi

        # 1. strict-aliasing diagnostic
        echo "[$abi] strict-aliasing check"
        $CC $FLAGS_BASE $abi_flags -O2 -fstrict-aliasing -Wstrict-aliasing=3 \
            -c "$case.c" -o /tmp/opencode/${case}-${abi}-alias.o 2>&1 \
            | sed 's/^/  /' || echo "  (build failed with strict aliasing)"

        # 2. sequence-point diagnostic
        echo "[$abi] sequence-point check"
        $CC $FLAGS_BASE $abi_flags -O2 -Wsequence-point \
            -c "$case.c" -o /tmp/opencode/${case}-${abi}-seq.o 2>&1 \
            | sed 's/^/  /' || echo "  (build failed with sequence-point)"

        # 3. undefined-behavior sanitizer (runtime)
        echo "[$abi] UBSan run at -O2"
        $CC $FLAGS_BASE $abi_flags -O2 -fsanitize=undefined -fno-sanitize-recover=all \
            "$case.c" -o /tmp/opencode/${case}-${abi}-ubsan 2>&1 | sed 's/^/  /'
        if [ -x /tmp/opencode/${case}-${abi}-ubsan ]; then
            /tmp/opencode/${case}-${abi}-ubsan 2>&1 | sed 's/^/  /' || true
        fi
    done
    echo ""
done

echo "Audit written to $out"
