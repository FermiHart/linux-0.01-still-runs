#!/bin/bash
# Independent release verifier for linux-0.01-still-runs.
# Run from the repository root. Exits non-zero if release criteria fail.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"
REPRO_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"

ERRORS=0
fail() { printf '  FAIL: %s\n' "$1" >&2; ERRORS=$((ERRORS + 1)); }

printf '=== Independent release check ===\n\n'

printf 'Checking git state...\n'
if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
    fail 'HEAD is unavailable'
elif [ -n "$(git status --porcelain --untracked-files=normal)" ]; then
    fail 'worktree is dirty'
else
    printf '  OK: worktree is clean\n'
fi

printf 'Checking required documentation...\n'
for doc in MISSION.md EXPERIENCE.md docs/AUDIT-STATEMENTS.md \
           docs/ADRS.md docs/RISKS.md docs/PORTING_LEDGER.md \
           docs/TOOLCHAIN.md docs/CONTAINER.md docs/REPRODUCIBILITY.md \
           docs/SBOM.md docs/PAPER.md docs/REPRODUCTION.md \
           evaluation/v1/README.md evaluation/v1/CHECKLIST.md \
           evaluation/v1/CLAIM-EVIDENCE.tsv \
           evaluation/v1/THIRD-PARTY-NOTICES.md \
           evaluation/v1/licenses/LGPL-2.1.txt \
           evaluation/v1/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt; do
    if [ -f "${doc}" ]; then
        printf '  OK: %s\n' "${doc}"
    else
        fail "missing ${doc}"
    fi
done

printf 'Checking upstream reference...\n'
if [ -f upstream/linux-0.01.tar.gz ]; then
    printf '  OK: upstream/linux-0.01.tar.gz\n'
    if (cd upstream && sha256sum --check SHA256SUMS >/dev/null 2>&1); then
        printf '  OK: upstream tarball hash\n'
    else
        fail 'upstream tarball hash mismatch'
    fi
else
    fail 'missing upstream/linux-0.01.tar.gz'
fi

printf 'Running make ci...\n'
if env -u SOURCE_DATE_EPOCH make -j8 ci >/dev/null 2>&1; then
    printf '  OK: CI suite passed\n'
else
    fail 'make ci failed'
fi

printf 'Running make verify-reproducible...\n'
if SOURCE_DATE_EPOCH="${REPRO_EPOCH}" make verify-reproducible >/dev/null 2>&1; then
    printf '  OK: two-build output comparison passed\n'
else
    fail 'make verify-reproducible failed'
fi

printf 'Building final reproducible outputs...\n'
if SOURCE_DATE_EPOCH="${REPRO_EPOCH}" make reproducible >/dev/null 2>&1; then
    printf '  OK: reproducible output set built\n'
else
    fail 'make reproducible failed'
fi

printf 'Building and checking evaluator package...\n'
REV="$(git rev-parse --short=12 HEAD 2>/dev/null || true)"
PACKAGE="release/linux-0.01-still-runs-evaluator-${REV}.tar.gz"
if SOURCE_DATE_EPOCH="${REPRO_EPOCH}" make artifact >/dev/null 2>&1 \
    && python3 scripts/check-evaluator-package.py --archive "${PACKAGE}" >/dev/null 2>&1; then
    printf '  OK: evaluator package passed independent validation\n'
else
    fail 'evaluator package build or validation failed'
fi

printf 'Comparing two evaluator package builds...\n'
if SOURCE_DATE_EPOCH="${REPRO_EPOCH}" make verify-artifact-reproducible >/dev/null 2>&1; then
    printf '  OK: evaluator package bytes are reproducible\n'
else
    fail 'make verify-artifact-reproducible failed'
fi

printf '\n'
if [ "${ERRORS}" -eq 0 ]; then
    printf 'Release check PASSED.\n'
    exit 0
fi
printf 'Release check FAILED with %d error(s).\n' "${ERRORS}" >&2
exit 1
