#!/bin/bash
# Independent release verifier for linux-0.01-still-runs.
# Run from the repository root. Exits non-zero if the release criteria fail.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

ERRORS=0
fail() { printf '  FAIL: %s\n' "$1" >&2; ERRORS=$((ERRORS + 1)); }

printf '═══ Independent release check ═══\n\n'

printf 'Checking git state...\n'
if [ -n "$(git status --porcelain 2>/dev/null || true)" ]; then
    fail 'worktree is dirty'
else
    printf '  OK: worktree is clean\n'
fi

printf 'Checking required documentation...\n'
for doc in MISSION.md EXPERIENCE.md docs/AUDIT-STATEMENTS.md \
           docs/ADRS.md docs/RISKS.md docs/PORTING_LEDGER.md \
           docs/TOOLCHAIN.md docs/CONTAINER.md docs/REPRODUCIBILITY.md \
           docs/SBOM.md docs/PAPER.md; do
    if [ -f "${doc}" ]; then
        printf '  OK: %s\n' "${doc}"
    else
        fail "missing ${doc}"
    fi
done

printf 'Checking upstream reference...\n'
if [ -f "upstream/linux-0.01.tar.gz" ]; then
    printf '  OK: upstream/linux-0.01.tar.gz\n'
    if sha256sum --check "upstream/SHA256SUMS" >/dev/null 2>&1; then
        printf '  OK: upstream tarball hash\n'
    else
        fail 'upstream tarball hash mismatch'
    fi
else
    fail 'missing upstream/linux-0.01.tar.gz'
fi

printf 'Running make reproducible...\n'
if make reproducible >/dev/null 2>&1; then
    printf '  OK: reproducible build succeeded\n'
else
    fail 'make reproducible failed'
fi

printf 'Running make ci...\n'
if make ci >/dev/null 2>&1; then
    printf '  OK: CI suite passed\n'
else
    fail 'make ci failed'
fi

printf '\n'
if [ "${ERRORS}" -eq 0 ]; then
    printf 'Release check PASSED.\n'
    exit 0
else
    printf 'Release check FAILED with %d error(s).\n' "${ERRORS}" >&2
    exit 1
fi
