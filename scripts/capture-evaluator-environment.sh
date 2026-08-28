#!/bin/bash
# Capture an evaluator-owned environment record without asserting test success.
set -euo pipefail

OUTPUT_DIR="${1:-evaluator-record}"
if [ -e "${OUTPUT_DIR}" ]; then
    printf 'Refusing to overwrite evaluator record: %s\n' "${OUTPUT_DIR}" >&2
    exit 1
fi
mkdir -p "${OUTPUT_DIR}"

capture() {
    local name="$1"
    shift
    {
        printf '$'
        printf ' %q' "$@"
        printf '\n'
        "$@"
    } > "${OUTPUT_DIR}/${name}.txt" 2>&1 || true
}

{
    printf 'format=vesica-piscis-evaluator-environment-v1\n'
    printf 'captured_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'working_directory=%s\n' "$(pwd -P)"
    if [ -r ARTIFACT-IDENTITY.json ]; then
        python3 -c 'import json; d=json.load(open("ARTIFACT-IDENTITY.json")); print("source_commit=" + d["source_commit"]); print("source_tree=" + d["source_tree"])'
    fi
} > "${OUTPUT_DIR}/identity.txt"

capture uname uname -a
capture os-release sh -c 'test -r /etc/os-release && sed -n "1,40p" /etc/os-release'
capture cpu sh -c 'command -v lscpu >/dev/null 2>&1 && lscpu'
capture kvm sh -c 'ls -l /dev/kvm; test -r /dev/kvm; test -w /dev/kvm'
capture toolchain sh -c 'gcc --version; ld --version; nasm -v; make --version; python3 --version; git --version; tar --version; gzip --version; fsck.minix --version'

cat > "${OUTPUT_DIR}/RUNS.tsv" <<'EOF'
run_id	command	started_utc	duration_seconds	exit_status	stdout_path	stderr_path	skips_or_notes
EOF
cat > "${OUTPUT_DIR}/README.txt" <<'EOF'
This directory is evaluator-owned evidence. RUNS.tsv has only a header until the
evaluator records commands and outcomes. Do not infer success from environment
capture. Preserve failures, skips, stdout, stderr, duration, and exit status.
EOF

printf 'Evaluator environment captured under %s\n' "${OUTPUT_DIR}"
