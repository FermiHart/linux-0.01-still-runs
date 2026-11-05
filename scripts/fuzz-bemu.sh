#!/usr/bin/env bash
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# fuzz-bemu.sh - lightweight fault injection for bEMU loader/root/CLI/BBP.
# Not a coverage-guided fuzzer; it exercises a small set of malformed
# inputs and verifies bEMU exits cleanly (no hang/crash).
set -euo pipefail

cd "$(dirname "$0")/.."

BUILD="${BUILD:-build}"
BEMU="$BUILD/bemu-linux01"
KERNEL="$BUILD/kernel.bin"
ROOT="$BUILD/root.img"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-fuzz.XXXXXXXX")"
trap 'rm -rf -- "$WORK_DIR"' EXIT

if [ ! -x "$BEMU" ] || [ ! -f "$KERNEL" ] || [ ! -f "$ROOT" ]; then
    echo "missing artifacts; run 'make all' first" >&2
    exit 1
fi

status=0
cases=0
source_hashes="$(sha256sum "$KERNEL" "$ROOT")"

run_case() {
    local name="$1"
    local allowed="$2"
    shift 2
    local rc=0
    local index
    local args=("$@")
    cases=$((cases + 1))
    # Every case gets its own writable medium, including malformed-kernel cases.
    for ((index=0; index<${#args[@]}; index++)); do
        if [ "${args[index]}" = --root ]; then
            cp -- "${args[index+1]}" "$WORK_DIR/case-$cases.img"
            args[index+1]="$WORK_DIR/case-$cases.img"
        fi
    done
    timeout --kill-after=2s 10 "${args[@]}" >"$WORK_DIR/case-$cases.log" 2>&1 || rc=$?
    # Admission tests require their exact status. Mutation runs allow normal
    # completion or runtime rejection, never timeout, signal or launch failure.
    if [[ " $allowed " != *" $rc "* ]]; then
        echo "  FAIL $name (unexpected rc=$rc; allowed: $allowed)"
        tail -n 20 "$WORK_DIR/case-$cases.log"
        status=$((status + 1))
    else
        echo "  ok  $name (rc=$rc)"
    fi
}

# CLI fuzz: invalid arguments
run_case "cli invalid flag" "2" "$BEMU" --nope
run_case "cli missing kernel" "1" "$BEMU" --kernel /nonexistent --root "$ROOT"
run_case "cli zero max-exits" "2" "$BEMU" --kernel "$KERNEL" --root "$ROOT" --max-exits 0

# Kernel corruption fuzz: flip random bytes using Perl
for i in 1 2 3 4 5; do
    cp "$KERNEL" "$WORK_DIR/kernel-$i.bin"
    perl -e '
        srand('$i');
        open(F, "+<", $ARGV[0]) or die;
        seek(F, 0, 2); my $sz = tell(F);
        for (1..int(rand(8))+1) {
            seek(F, int(rand($sz)), 0);
            read(F, my $b, 1);
            seek(F, -1, 1);
            print F chr(ord($b) ^ (int(rand(255))+1));
        }
        close(F);
    ' "$WORK_DIR/kernel-$i.bin"
    run_case "kernel corruption $i" "0 1" "$BEMU" --kernel "$WORK_DIR/kernel-$i.bin" --root "$ROOT" --max-exits 1000
done

# Root corruption fuzz: flip random bytes in root image
for i in 1 2 3; do
    cp "$ROOT" "$WORK_DIR/root-$i.img"
    perl -e '
        srand(100 + '$i');
        open(F, "+<", $ARGV[0]) or die;
        seek(F, 0, 2); my $sz = tell(F);
        for (1..int(rand(16))+1) {
            seek(F, int(rand($sz)), 0);
            read(F, my $b, 1);
            seek(F, -1, 1);
            print F chr(ord($b) ^ (int(rand(255))+1));
        }
        close(F);
    ' "$WORK_DIR/root-$i.img"
    run_case "root corruption $i" "0 1" "$BEMU" --kernel "$KERNEL" --root "$WORK_DIR/root-$i.img" --max-exits 1000
done

# Kernel artifact truncation at several payload points
for trunc in 1 512 4096 8192; do
    head -c "$trunc" "$KERNEL" > "$WORK_DIR/kernel-trunc-$trunc.bin"
    run_case "kernel truncated at $trunc" "1" "$BEMU" --kernel "$WORK_DIR/kernel-trunc-$trunc.bin" --root "$ROOT" --max-exits 1000
done

if [ "$(sha256sum "$KERNEL" "$ROOT")" != "$source_hashes" ]; then
    echo "  FAIL canonical kernel or root image changed" >&2
    status=$((status + 1))
fi
if [ "$status" -eq 0 ]; then
    echo "fuzz: all $cases cases handled cleanly"
else
    echo "fuzz: $status case(s) failed" >&2
fi
test "$status" -eq 0
