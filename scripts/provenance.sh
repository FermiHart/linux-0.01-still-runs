#!/bin/bash
# Generate a provenance report for the porting changes.
# Compares the current historical-core files against the upstream Linux 0.01
# tarball and cross-checks docs/PORTING_LEDGER.md.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
UPSTREAM_DIR="${ROOT_DIR}/upstream"
TARBALL="${UPSTREAM_DIR}/linux-0.01.tar.gz"
EXTRACT_DIR="${UPSTREAM_DIR}/extracted"
UPSTREAM_SRC="${EXTRACT_DIR}/linux"
REPORT_DIR="${ROOT_DIR}/build"
REPORT="${REPORT_DIR}/PROVENANCE.txt"
LEDGER="${ROOT_DIR}/docs/PORTING_LEDGER.md"

if [ ! -f "${TARBALL}" ]; then
    printf 'Upstream tarball not found: %s\n' "${TARBALL}" >&2
    exit 1
fi

cd "${UPSTREAM_DIR}"
sha256sum --check SHA256SUMS

if [ ! -d "${UPSTREAM_SRC}" ]; then
    printf 'Extracting upstream source for comparison...\n' >&2
    bash "${SCRIPT_DIR}/import-upstream.sh" >/dev/null
fi

mkdir -p "${REPORT_DIR}"

{
    printf 'Provenance Report for linux-0.01-still-runs\n'
    printf 'Generated: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'Upstream:  %s\n' "$(sha256sum "${TARBALL}" | cut -c1-64)"
    printf 'Ledger:    %s\n' "$(sha256sum "${LEDGER}" | cut -c1-64)"
    printf 'Git rev:   %s\n' "$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo 'no-git')"
    printf '\n'

    printf '═══ Files with content changes vs upstream Linux 0.01 ═══\n\n'
    changed=0
    while IFS= read -r -d '' file; do
        rel="${file#${ROOT_DIR}/}"
        up="${UPSTREAM_SRC}/${rel}"
        if [ ! -f "${up}" ]; then
            continue
        fi
        if ! cmp -s "${file}" "${up}"; then
            printf '  M %s\n' "${rel}"
            changed=$((changed + 1))
        fi
    done < <(find "${ROOT_DIR}/init" "${ROOT_DIR}/kernel" "${ROOT_DIR}/mm" \
                  "${ROOT_DIR}/fs" "${ROOT_DIR}/lib" "${ROOT_DIR}/include" \
                  -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \) -print0)

    if [ "${changed}" -eq 0 ]; then
        printf '  (no content changes detected)\n'
    fi
    printf '\n'

    printf '═══ Files present only in this port (not in upstream) ═══\n\n'
    added=0
    while IFS= read -r -r -d '' file; do
        rel="${file#${ROOT_DIR}/}"
        printf '  + %s\n' "${rel}"
        added=$((added + 1))
    done < <(find "${ROOT_DIR}/init" "${ROOT_DIR}/kernel" "${ROOT_DIR}/mm" \
                  "${ROOT_DIR}/fs" "${ROOT_DIR}/lib" "${ROOT_DIR}/include" \
                  -type f \( -name '*.c' -o -name '*.h' -o -name '*.s' -o -name '*.S' \) -print0 | \
             while IFS= read -r -d '' file; do
                 rel="${file#${ROOT_DIR}/}"
                 [ -f "${UPSTREAM_SRC}/${rel}" ] || printf '%s\0' "${file}"
             done)
    if [ "${added}" -eq 0 ]; then
        printf '  (no added files detected)\n'
    fi
    printf '\n'

    printf '═══ Ledger cross-check ═══\n\n'
    missing=0
    for rel in $(git -C "${ROOT_DIR}" diff --name-only "${UPSTREAM_SRC}" -- \
        init kernel mm fs lib include 2>/dev/null | sort -u || true); do
        base=$(basename "${rel}")
        if ! grep -q "${base}" "${LEDGER}"; then
            printf '  ! %s is not mentioned in PORTING_LEDGER.md\n' "${rel}"
            missing=$((missing + 1))
        fi
    done
    if [ "${missing}" -eq 0 ]; then
        printf '  All changed files are referenced in the ledger.\n'
    else
        printf '  %d changed file(s) not documented in the ledger.\n' "${missing}"
    fi
} > "${REPORT}"

printf '%s\n' "${REPORT}"
