#!/bin/bash
# Extract and compare the disassembly of the function under investigation for
# each compiler case across -O0, -O1 and -O2.

set -euo pipefail

cd "$(dirname "$0")"

build=build/asm
mkdir -p "$build"

abi=${1:-x86_64}
shift 2>/dev/null || true

# Function name to extract per case.
declare -A funcs=(
    [buffer_freelist]=get_node_original
    [bitmap_inline_asm]=use_bit
    [vsprintf_percent_s]=mini_vsprintf
)

for case in buffer_freelist bitmap_inline_asm vsprintf_percent_s; do
    fn=${funcs[$case]}
    for opt in O0 O1 O2; do
        bin="build/${case}-${abi}-${opt}"
        out="$build/${case}-${abi}-${opt}.asm"
        objdump -d --disassemble="$fn" "$bin" > "$out" 2>/dev/null || true
    done
    diff -u "$build/${case}-${abi}-O0.asm" "$build/${case}-${abi}-O1.asm" \
        > "$build/${case}-${abi}-O0-vs-O1.diff" 2>/dev/null || true
    diff -u "$build/${case}-${abi}-O1.asm" "$build/${case}-${abi}-O2.asm" \
        > "$build/${case}-${abi}-O1-vs-O2.diff" 2>/dev/null || true
    diff -u "$build/${case}-${abi}-O0.asm" "$build/${case}-${abi}-O2.asm" \
        > "$build/${case}-${abi}-O0-vs-O2.diff" 2>/dev/null || true
    echo "--- ${case} (${abi}) ---"
    wc -l "$build/${case}-${abi}"-*.asm "$build/${case}-${abi}"-*.diff 2>/dev/null \
        | sed 's/^/  /'
done
