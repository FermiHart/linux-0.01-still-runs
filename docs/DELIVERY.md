<!-- Author: F E R M I ∞ H A R T <contact@fermihart.com> -->
<!-- SPDX-License-Identifier: Unlicense -->

# Self-contained source delivery

A clean source snapshot can be built, tested and packaged without the old
development repository. It retains useful tests, exact dataset inputs, original
licenses and attribution; it does not include `.git` working-tree metadata, private operational
records, caches, existing guest disks, build outputs or a development-history
bundle. This is a development-candidate format, not Academic Artifact 1.0 or an
independent external reproduction result.

## Export reviewed source

From a Git checkout, public inputs are tracked files plus non-ignored new files.
The export list must exactly match the reviewed authorship inventory. Symlinks, unsafe/private
paths, excessive inputs and an existing output destination are refused.

```sh
make test-authorship
python3 scripts/source_snapshot.py export --output /absolute/new/source-snapshot
python3 /absolute/new/source-snapshot/scripts/source_snapshot.py verify
```

`SOURCE-SNAPSHOT.json` records every payload path, exact executable mode, size
and SHA-256. Its `source_id` is a SHA-256 commitment to that ordered inventory,
not a fabricated Git commit. The metadata file itself is separately covered by
the delivered package manifest/archive checksum. It is generated delivery
metadata, not an additional authored source path. Tests validate the same
authorship inventory with or without `.git`.

An archive build may create ignored objects, caches and working images without
changing its source identity. Verification with `--allow-runtime` recognizes
those known output classes; strict verification of a fresh export rejects any
extra member. Export never copies those runtime outputs into another snapshot.

## Test the actual exported directory

On the documented Linux x86-64 host with toolchain, hosted-i386 test prerequisites
and usable KVM:

```sh
cd /absolute/new/source-snapshot
make doctor
make -j8 ci
make test-round25 test-round25-matrix
make test-session-persistence
make verify-reproducible
```

Git remains a host tool for local diffs and disposable test fixtures. The old
commit graph and network access are not required. The small, verified
[retained source inputs](../provenance/source-inputs/v1/README.md) supply only
the original historical bytes used by the v1 datasets and baseline matrix.
The published datasets and five identity-pinned source files remain unchanged;
the normal Make targets adapt their input access rather than replacing the
dataset algorithms or skipping assertions.

## Create the source-and-binary candidate

Inside an exported snapshot, the existing artifact front door automatically
selects source-bound packaging. A Git worktree may request it explicitly with
`SNAPSHOT=1`; the historical commit-bound evaluator mode remains available for
its original full-history workflow.

```sh
SOURCE_DATE_EPOCH=1700000000 make artifact
# From a development worktree instead:
SOURCE_DATE_EPOCH=1700000000 make artifact SNAPSHOT=1
```

The builder freezes the selected source, performs a fresh deterministic build
in a separate directory, and delivers:

- `linux-0.01-snapshot-candidate-<source-id-prefix>.tar.gz`
- its standalone `.check.py` verifier
- a `.tar.gz.sha256` sidecar covering the archive and verifier

Existing outputs are never overwritten. The archive includes complete source,
all thirteen normal artifacts, both base images, copied legal notices, build
environment identities, an exact source tree/manifest, a package-wide checksum
manifest, a short guide and `run`. The format binds content and modes, not a
nonexistent old commit/history bundle. Failed build evidence is retained locally
and is not shipped as public console evidence.

The checker validates archive paths/types, sizes, normalized metadata, source
inventory/tree identity, artifact hashes/modes and notices without executing
the included source or binaries. Checksums are not independent authentication
of a publisher. Source/build identity is not proof of functional correctness.

## Run after verification

With the archive, checker and sidecar together:

```sh
sha256sum -c linux-0.01-snapshot-candidate-<id>.tar.gz.sha256
python3 -I linux-0.01-snapshot-candidate-<id>.check.py \
  --archive linux-0.01-snapshot-candidate-<id>.tar.gz
tar -xzf linux-0.01-snapshot-candidate-<id>.tar.gz
cd linux-0.01-snapshot-candidate-<id>
./run
./run 1991
./run alive work
```

The binary runner needs Linux x86-64, usable `/dev/kvm`, a compatible glibc and
Python 3.12+ for session creation. Inspect `BUILD-ENVIRONMENT.json` for the actual
build host/tool identities; arbitrary-distribution compatibility is not claimed.
No build tools are needed merely to run this package. No privileged installation
or device-permission change is performed. Keep `state/` private and back it up
while the guest is stopped. Validate the sealed archive before use; an extracted
directory with live personal state is no longer an unchanged delivery tree.

Preparing this local candidate does not publish a repository, rewrite project
history, remove old releases, clear third-party text rights, create a DOI, or
complete the pending human external-evaluation gate.
