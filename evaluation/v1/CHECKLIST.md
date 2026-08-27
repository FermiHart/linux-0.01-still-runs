# Evaluator Checklist v1

Run from the directory containing the downloaded archive unless a step says
otherwise. Replace `<archive>` and `<commit>` from the actual package identity.

## 1. Transfer And Package Integrity

```bash
sha256sum --check <archive>.sha256
python3 <archive-without-.tar.gz>.check.py --archive <archive>
tar -xzf <archive>
cd linux-0.01-still-runs-evaluator-<commit-prefix>
python3 source/scripts/check-evaluator-package.py --directory .
```

Expected evidence: zero exit statuses, the full commit/tree printed by the
verifier, and no unchecked, absent, unsafe, or metadata-mismatched member.
Obtain the archive, detached checker, and checksum manifest from the fixed
release channel. The checksum is an integrity value, not a digital signature;
compare it with the producer's independently published value before execution.

## 2. Evaluator-Owned Environment

```bash
bash source/scripts/capture-evaluator-environment.sh evaluator-record
```

Inspect every file under `evaluator-record/`. `RUNS.tsv` intentionally starts
with only a header. Add one row per command with UTC start, duration, exit
status, stdout/stderr paths, and skips or notes. Environment capture alone is
not a successful reproduction.

## 3. Fixed Source With History

```bash
COMMIT=$(python3 -c 'import json; print(json.load(open("ARTIFACT-IDENTITY.json"))["source_commit"])')
git clone repository.bundle work
git -C work checkout --detach "$COMMIT"
test "$(git -C work rev-parse HEAD)" = "$COMMIT"
git -C work bundle verify ../repository.bundle
```

Use `work/` for the historical-provenance and full-CI gates. The package
verifier has already compared every direct `source/` byte to its Git blob.

## 4. Preflight

```bash
cd work
make doctor
```

Record failures as environment limitations. `/dev/kvm`, the required KVM
capabilities, hosted libc development support, hosted i386 multilib, NASM,
`fsck.minix`, and the pinned toolchain remain prerequisites.

## 5. Behavioral And Persistence Gates

```bash
/usr/bin/time -p make -j8 ci >../evaluator-record/ci.stdout 2>../evaluator-record/ci.stderr
/usr/bin/time -p make test-fs-persistence >../evaluator-record/persistence.stdout 2>../evaluator-record/persistence.stderr
```

Record both exit statuses even when the first command fails. Persistence is
bounded to orderly guest `sync` plus termination and a new bEMU/KVM/RAM process
over the same disposable image; it is not a physical-media durability claim.

## 6. Build And Package Reproducibility

```bash
/usr/bin/time -p make verify-reproducible >../evaluator-record/build-repro.stdout 2>../evaluator-record/build-repro.stderr
SOURCE_DATE_EPOCH=1700000000 make reproducible
make verify-artifact-reproducible
```

The first comparator covers two copied-tree builds on one host/toolchain. The
last command covers two evaluator-package constructions from the same clean
commit and selected outputs. Neither command establishes arbitrary cross-host
byte identity for host-linked binaries.

## 7. Claim Map And Non-Claims

Review `evaluation/v1/CLAIM-EVIDENCE.tsv` in the checkout against retained outputs. Do not report a
claim whose command failed or whose named evidence is absent.

- **independent third-party reproduction has not yet occurred** in the producer
  record shipped here; the evaluator's retained run is the Wave 114 evidence.
- Record/replay is input reconstruction plus filtered observable equality; it is
  **not machine-state replay**.
- **no DOI or archival deposit exists yet**; those are later roadmap waves.
- The demonstrated bridge is sufficient for the tested scope, not proven
  minimal, and the guest is not a port to x86-64.

## 8. Retain The Run

Preserve `evaluator-record/` unchanged, including failures and skips. Record the
archive SHA-256, full commit/tree, host environment, commands, stdout, stderr,
statuses, durations, generated build hashes, and any deviations. Do not add the
record to a published dataset until its status and retention policy are reviewed.
