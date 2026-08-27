#!/bin/bash
# Build the evaluator archive twice and require identical outer bytes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-package-repro.XXXXXXXX")"
cleanup() { rm -rf -- "${WORK_DIR}"; }
trap cleanup EXIT

export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
mkdir -p "${WORK_DIR}/a" "${WORK_DIR}/b"

RELEASE_DIR="${WORK_DIR}/a" bash "${ROOT_DIR}/scripts/make-artifact.sh" >/dev/null
RELEASE_DIR="${WORK_DIR}/b" bash "${ROOT_DIR}/scripts/make-artifact.sh" >/dev/null

ARCHIVE_A="$(printf '%s\n' "${WORK_DIR}/a"/*.tar.gz)"
ARCHIVE_B="$(printf '%s\n' "${WORK_DIR}/b"/*.tar.gz)"
if ! cmp -s "${ARCHIVE_A}" "${ARCHIVE_B}"; then
    printf 'Evaluator package reproducibility failure: archive bytes differ\n' >&2
    sha256sum "${ARCHIVE_A}" "${ARCHIVE_B}" >&2
    exit 1
fi

python3 "${ROOT_DIR}/scripts/check-evaluator-package.py" --archive "${ARCHIVE_A}" >/dev/null
python3 "${ROOT_DIR}/scripts/check-evaluator-package.py" --archive "${ARCHIVE_B}" >/dev/null
printf 'Evaluator package reproducibility verified: %s\n' "$(sha256sum "${ARCHIVE_A}" | cut -d' ' -f1)"
