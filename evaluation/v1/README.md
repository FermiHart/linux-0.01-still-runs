# Vesica Piscis Evaluator Package v1

This directory defines the operational envelope for evaluating
`linux-0.01-still-runs`. The package is fixed to the full commit and tree in
`ARTIFACT-IDENTITY.json`; its directory name uses the first 12 commit digits.
It contains a byte-checked tracked source snapshot, a Git bundle with the
history reachable from that commit, the complete selected build-output set,
the published datasets, notices, and independent package checks.

The historical Linux-derived guest/kernel remains 32-bit i386. bEMU is a
Linux/x86-64 host process using KVM. This package does not represent a port of
the kernel to the x86-64 ISA and provides no software-emulation fallback.

## Package Layout

| Path | Role |
|---|---|
| `ARTIFACT-IDENTITY.json` | Full commit, tree, epoch, format, and manifest identities |
| `SHA256SUMS` | Every regular package file except this self-referential manifest |
| `SOURCE-MANIFEST.tsv` | Git mode and blob identity for every exported tracked file |
| `repository.bundle` | Complete history reachable from the fixed `HEAD` |
| `source/` | Direct tracked-file export of the fixed commit |
| `artifacts/` | Selected deterministic outputs and their build manifests |
| `evaluation/` | This guide, checklist, claim map, and redistribution notices |

The sibling `.check.py` validates the archive before extraction, and the
`.tar.gz.sha256` file covers both archive and checker. GNU tar metadata
uses lexical member order, one fixed timestamp, uid/gid zero, and normalized
modes; gzip stores no original name or timestamp.

## Evaluation Boundary

Run `CHECKLIST.md` in order and retain the evaluator-owned record created by
`capture-evaluator-environment.sh`. Clone `repository.bundle` for tests that
inspect historical Git objects. The exported `source/` tree is independently
useful for inspection and byte comparison, but it has no `.git` directory.

The package creator's green gates are not an evaluator result. Wave 114 owns
independent reproduction, including stdout, stderr, statuses, durations, skips,
failures, and environment. Wave 115 owns corrections found by that exercise.
There is no DOI or archival deposit in this package.

`CLAIM-EVIDENCE.tsv` maps bounded claims to commands and expected evidence.
Commands can fail on an unsupported host; preserve those failures rather than
weakening the claim or recording a synthetic success. The current project
demonstrates a sufficient, delimited bridge, not a proven minimal bridge.
