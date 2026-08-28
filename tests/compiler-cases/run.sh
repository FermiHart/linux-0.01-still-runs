#!/bin/bash
# Run all compiler-case binaries at -O0, -O1 and -O2, for each ABI, and
# produce a report.

set -euo pipefail

cd "$(dirname "$0")"
mkdir -p build

report=build/report.txt
meta=build/meta.txt

{
    echo "Compiler case investigation report"
    echo "=================================="
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Compiler: ${CC:-gcc}"
    ${CC:-gcc} --version | head -n1
    echo "Host: $(uname -m)"
    echo ""
} > "$meta"

rm -f build/result-*.txt

for abi in x86_64 i386; do
    echo "ABI: $abi" >> "$meta"
    if [ "$abi" = "i386" ]; then
        if ! ${CC:-gcc} -m32 -E - </dev/null >/dev/null 2>&1; then
            echo "  SKIPPED: compiler does not support -m32" >> "$meta"
            continue
        fi
    fi
    for case in buffer_freelist bitmap_inline_asm vsprintf_percent_s; do
        for opt in O0 O1 O2; do
            bin="build/${case}-${abi}-${opt}"
            asm="build/${case}-${abi}-${opt}.s"
            out="build/${case}-${abi}-${opt}.out"
            echo -n "Testing $case at -$opt ($abi) ... "
            if "./$bin" > "$out" 2>&1; then
                status="PASS"
            else
                status="FAIL(rc=$?)"
            fi
            echo "$status"
            echo "  ${case}-${abi}-${opt}: ${status}" >> "$meta"
            if [ -f "$asm" ]; then
                lines=$(wc -l < "$asm")
                echo "    ${case}-${abi}-${opt}.s: ${lines} lines" >> "$meta"
            fi
        done
    done
    echo "" >> "$meta"
done

cat "$meta" > "$report"
echo "" >> "$report"
echo "Per-case details (last 5 lines of each run):" >> "$report"
for abi in x86_64 i386; do
    for case in buffer_freelist bitmap_inline_asm vsprintf_percent_s; do
        for opt in O0 O1 O2; do
            out="build/${case}-${abi}-${opt}.out"
            [ -f "$out" ] || continue
            echo "" >> "$report"
            echo "--- ${case}-${abi}-${opt} ---" >> "$report"
            tail -n 5 "$out" >> "$report"
        done
    done
done

echo "Report written to $report"
