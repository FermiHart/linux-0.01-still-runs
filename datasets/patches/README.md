# Historical-Core Patch and Incompatibility Dataset

This versioned dataset compares the pinned Linux 0.01 tarball with port commit
`ae458306905d4fee85121ac3c2b42e86ed099310`. It publishes source deltas and ledger
interpretations for RQ1/RQ2; it does not retroactively create execution logs.

## Contents

- `historical-core.patch`: deterministic Git-format patch for 53 source paths.
- `file_deltas.csv`: hashes, modes, line counts and per-path patch hashes.
- `adaptations.csv`: 19 stable IDs derived from `docs/PORTING_LEDGER.md`.
- `adaptation_files.csv`: explicit/glob joins and nine unresolved path deltas.
- `evidence_links.csv`: retained oracle definitions and evidence gaps.
- `MANIFEST.json` and `SHA256SUMS.txt`: immutable source identities and checksums.

Run `make patch-dataset` to reproduce the tracked files and
`make test-patch-dataset` to verify them against both pinned snapshots.

## Interpretation Boundary

The patch and hashes are newly retained observations. Ledger prose is a
versioned historical interpretation. Test source defines an oracle but is not a
retained execution result; generated outputs marked `generated_unretained` were
not preserved with observation IDs or raw-output hashes.

Consequently this release contains zero paired baseline/adapted observations
meeting the RQ1 invalidation criterion and zero RQ2 ablation configurations. It
supports inspection of one observed sufficient port, not a claim of causal
invalidation, necessity, inclusion-minimality or a minimum adaptation set.
