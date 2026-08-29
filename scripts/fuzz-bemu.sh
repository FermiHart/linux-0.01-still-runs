#!/usr/bin/env bash
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
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
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

if [ ! -x "$BEMU" ] || [ ! -f "$KERNEL" ] || [ ! -f "$ROOT" ]; then
    echo "missing artifacts; run 'make all' first" >&2
    exit 1
fi

status=0
cases=0

run_case() {
    local name="$1"
    shift
    local rc=0
    cases=$((cases + 1))
    timeout 10 "$@" >/dev/null 2>&1 || rc=$?
    # 124 = timeout (likely guest hang), 137 = SIGKILL, 134 = SIGABRT
    if [ "$rc" -eq 137 ] || [ "$rc" -eq 134 ] || [ "$rc" -eq 139 ]; then
        echo "  FAIL $name (crash, rc=$rc)"
        status=1
    else
        echo "  ok  $name (rc=$rc)"
    fi
}

# CLI fuzz: invalid arguments
run_case "cli invalid flag" "$BEMU" --nope
run_case "cli missing kernel" "$BEMU" --kernel /nonexistent --root "$ROOT"
run_case "cli zero max-exits" "$BEMU" --kernel "$KERNEL" --root "$ROOT" --max-exits 0

# Kernel corruption fuzz: flip random bytes using Perl
for i in 1 2 3 4 5; do
    cp "$KERNEL" "$TMPDIR/kernel-$i.bin"
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
    ' "$TMPDIR/kernel-$i.bin"
    run_case "kernel corruption $i" "$BEMU" --kernel "$TMPDIR/kernel-$i.bin" --root "$ROOT" --max-exits 1000
done

# Root corruption fuzz: flip random bytes in root image
for i in 1 2 3; do
    cp "$ROOT" "$TMPDIR/root-$i.img"
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
    ' "$TMPDIR/root-$i.img"
    run_case "root corruption $i" "$BEMU" --kernel "$KERNEL" --root "$TMPDIR/root-$i.img" --max-exits 1000
done

# Kernel artifact truncation at several payload points
for trunc in 1 512 4096 8192; do
    head -c "$trunc" "$KERNEL" > "$TMPDIR/kernel-trunc-$trunc.bin"
    run_case "kernel truncated at $trunc" "$BEMU" --kernel "$TMPDIR/kernel-trunc-$trunc.bin" --root "$ROOT" --max-exits 1000
done

if [ "$status" -eq 0 ]; then
    echo "fuzz: all $cases cases handled cleanly"
else
    echo "fuzz: $status case(s) failed" >&2
fi
exit "$status"
