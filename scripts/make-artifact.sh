#!/bin/bash
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

# Build a commit-bound, deterministic evaluator package from verified outputs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RELEASE_DIR="${RELEASE_DIR:-${ROOT_DIR}/release}"
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1700000000}"
EXPECTED_OUTPUTS=(
    kernel.elf kernel.bin root.img root-1991.img bemu-linux01 mkimage
    minix-inspect shell.bin update.bin hello.bin yes.bin pathcheck.bin cat.bin
)

case "${SOURCE_DATE_EPOCH}" in
    ''|*[!0-9]*)
        printf 'SOURCE_DATE_EPOCH must be a non-negative integer\n' >&2
        exit 1
        ;;
esac

for tool in git make tar gzip sha256sum sort find grep cmp mktemp; do
    if ! command -v "${tool}" >/dev/null 2>&1; then
        printf 'Required package tool not found: %s\n' "${tool}" >&2
        exit 1
    fi
done

if ! git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'Artifact construction requires a Git worktree\n' >&2
    exit 1
fi
if [ -n "$(git -C "${ROOT_DIR}" status --porcelain --untracked-files=normal)" ]; then
    printf 'Artifact construction requires a clean public worktree\n' >&2
    exit 1
fi
if [ "$(git -C "${ROOT_DIR}" rev-parse --is-shallow-repository)" != false ]; then
    printf 'Artifact construction requires complete Git history, not a shallow clone\n' >&2
    exit 1
fi

REV="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
TREE="$(git -C "${ROOT_DIR}" rev-parse HEAD^{tree})"
SHORT_REV="$(printf '%.12s' "${REV}")"
PACKAGE_NAME="linux-0.01-still-runs-evaluator-${SHORT_REV}"
ARTIFACT="${RELEASE_DIR}/${PACKAGE_NAME}.tar.gz"
SIDECAR="${ARTIFACT}.sha256"
CHECKER="${RELEASE_DIR}/${PACKAGE_NAME}.check.py"

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/linux001-evaluator.XXXXXXXX")"
cleanup() { rm -rf -- "${WORK_DIR}"; }
trap cleanup EXIT
STAGE_DIR="${WORK_DIR}/stage"
PACKAGE_DIR="${STAGE_DIR}/${PACKAGE_NAME}"
mkdir -p "${PACKAGE_DIR}/source" "${PACKAGE_DIR}/artifacts"

# Export bytes from the fixed commit, never from the live worktree.
git -C "${ROOT_DIR}" archive --format=tar "${REV}" |
    tar -xf - -C "${PACKAGE_DIR}/source"
git -C "${ROOT_DIR}" -c pack.threads=1 \
    bundle create "${PACKAGE_DIR}/repository.bundle" HEAD

# Build in a fresh checkout of the bundle so every output is owned by REV.
BUILD_SOURCE="${WORK_DIR}/build-source"
git -c advice.detachedHead=false clone --quiet \
    "${PACKAGE_DIR}/repository.bundle" "${BUILD_SOURCE}"
if [ "$(git -C "${BUILD_SOURCE}" rev-parse HEAD)" != "${REV}" ]; then
    printf 'History bundle checkout did not resolve to the fixed commit\n' >&2
    exit 1
fi
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH}" make -C "${BUILD_SOURCE}" reproducible >/dev/null
PACKAGE_BUILD_DIR="${BUILD_SOURCE}/build"

for manifest in SHA256SUMS REPRODUCIBLE.sha256; do
    if [ ! -f "${PACKAGE_BUILD_DIR}/${manifest}" ]; then
        printf 'Commit-bound build manifest is missing: %s\n' "${manifest}" >&2
        exit 1
    fi
done
if ! cmp -s "${PACKAGE_BUILD_DIR}/SHA256SUMS" "${PACKAGE_BUILD_DIR}/REPRODUCIBLE.sha256"; then
    printf 'Commit-bound build manifests differ\n' >&2
    exit 1
fi
if ! (cd "${PACKAGE_BUILD_DIR}" && sha256sum --check SHA256SUMS >/dev/null); then
    printf 'Commit-bound build manifest does not validate its outputs\n' >&2
    exit 1
fi
for output in "${EXPECTED_OUTPUTS[@]}"; do
    if [ ! -f "${PACKAGE_BUILD_DIR}/${output}" ] \
        || ! grep -Eq "^[0-9a-f]{64}  ${output}$" "${PACKAGE_BUILD_DIR}/SHA256SUMS"; then
        printf 'Commit-bound build lacks selected output: %s\n' "${output}" >&2
        exit 1
    fi
done
if [ "$(wc -l < "${PACKAGE_BUILD_DIR}/SHA256SUMS")" -ne "${#EXPECTED_OUTPUTS[@]}" ]; then
    printf 'Commit-bound build manifest contains an unexpected inventory\n' >&2
    exit 1
fi

SOURCE_MANIFEST="${PACKAGE_DIR}/SOURCE-MANIFEST.tsv"
: > "${SOURCE_MANIFEST}"
while IFS=$'\t' read -r metadata path; do
    read -r mode type object <<< "${metadata}"
    if [ "${type}" != blob ] || { [ "${mode}" != 100644 ] && [ "${mode}" != 100755 ]; }; then
        printf 'Unsupported tracked entry in source snapshot: %s %s\n' "${mode}" "${path}" >&2
        exit 1
    fi
    printf '%s\t%s\t%s\n' "${mode}" "${object}" "${path}" >> "${SOURCE_MANIFEST}"
done < <(git -C "${ROOT_DIR}" ls-tree -r "${REV}")
SOURCE_FILE_COUNT="$(wc -l < "${SOURCE_MANIFEST}")"

cp -a "${PACKAGE_DIR}/source/evaluation/v1" "${PACKAGE_DIR}/evaluation"
cp "${PACKAGE_DIR}/source/LICENSE" "${PACKAGE_DIR}/LICENSE"
for output in "${EXPECTED_OUTPUTS[@]}"; do
    cp "${PACKAGE_BUILD_DIR}/${output}" "${PACKAGE_DIR}/artifacts/${output}"
done
cp "${PACKAGE_BUILD_DIR}/SHA256SUMS" "${PACKAGE_DIR}/artifacts/SHA256SUMS"
cp "${PACKAGE_BUILD_DIR}/REPRODUCIBLE.sha256" "${PACKAGE_DIR}/artifacts/REPRODUCIBLE.sha256"

cat > "${PACKAGE_DIR}/ARTIFACT-IDENTITY.json" <<EOF
{
  "build_manifest": "artifacts/SHA256SUMS",
  "format": "vesica-piscis-evaluator-v1",
  "history_bundle": "repository.bundle",
  "package_manifest": "SHA256SUMS",
  "source_commit": "${REV}",
  "source_date_epoch": ${SOURCE_DATE_EPOCH},
  "source_file_count": ${SOURCE_FILE_COUNT},
  "source_tree": "${TREE}"
}
EOF

# Normalize staged modes while retaining executable bits declared by Git.
find "${PACKAGE_DIR}" -type d -exec chmod 0755 {} +
find "${PACKAGE_DIR}" -type f -exec chmod 0644 {} +
while IFS=$'\t' read -r mode _ path; do
    if [ "${mode}" = 100755 ]; then
        chmod 0755 "${PACKAGE_DIR}/source/${path}"
    fi
done < "${SOURCE_MANIFEST}"
for executable in bemu-linux01 mkimage minix-inspect; do
    chmod 0755 "${PACKAGE_DIR}/artifacts/${executable}"
done

PACKAGE_MANIFEST="${PACKAGE_DIR}/SHA256SUMS"
(
    cd "${PACKAGE_DIR}"
    : > SHA256SUMS
    while IFS= read -r -d '' path; do
        relative="${path#./}"
        sha256sum "${relative}" >> SHA256SUMS
    done < <(find . -type f ! -path ./SHA256SUMS -print0 | LC_ALL=C sort -z)
    sha256sum --check SHA256SUMS >/dev/null
)
chmod 0644 "${PACKAGE_MANIFEST}"

mkdir -p "${RELEASE_DIR}"
TEMP_ARTIFACT="${WORK_DIR}/${PACKAGE_NAME}.tar.gz"
LC_ALL=C tar --sort=name --format=ustar \
    --mtime="@${SOURCE_DATE_EPOCH}" --owner=0 --group=0 --numeric-owner \
    -C "${STAGE_DIR}" -cf - "${PACKAGE_NAME}" |
    gzip -n -9 > "${TEMP_ARTIFACT}"
mv -f -- "${TEMP_ARTIFACT}" "${ARTIFACT}"
cp "${PACKAGE_DIR}/source/scripts/check-evaluator-package.py" "${CHECKER}"
chmod 0755 "${CHECKER}"
(
    cd "${RELEASE_DIR}"
    sha256sum "${PACKAGE_NAME}.tar.gz" "${PACKAGE_NAME}.check.py" \
        > "${PACKAGE_NAME}.tar.gz.sha256"
    sha256sum --check "${PACKAGE_NAME}.tar.gz.sha256" >/dev/null
)

printf 'Created evaluator package fixed to %s\n' "${REV}"
printf '%s\n%s\n%s\n' "${ARTIFACT}" "${SIDECAR}" "${CHECKER}"
