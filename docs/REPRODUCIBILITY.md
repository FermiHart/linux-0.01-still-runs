# Reproducibility

This document defines the current build-byte boundary. The operational clean-clone
procedure, prerequisites, artifact command and troubleshooting are in
`docs/REPRODUCTION.md`.

## Deterministic sources

The following non-deterministic inputs have been eliminated or controlled:

| Input | Control |
|---|---|
| Build timestamp | `SOURCE_DATE_EPOCH` honored by the Makefile |
| Upstream tarball | Pinned by SHA-256 in `upstream/SHA256SUMS` |
| Toolchain | Documented in `docs/TOOLCHAIN.md` |
| Container | Pinned in `Dockerfile` and `docs/CONTAINER.md` |
| Filesystem timestamps | `tools/mkimage.c` writes `i_time = 0` for all inodes |

## Bit-for-bit verification

Run the one-build reproducible target:

```bash
make reproducible
```

This performs one build and:

1. Cleans the build tree.
2. Exports a fixed `SOURCE_DATE_EPOCH` (or honors an externally supplied one).
3. Builds all artifacts.
4. Writes `build/SHA256SUMS`.
5. Copies it to `build/REPRODUCIBLE.sha256` for later comparison.

The separate `make verify-reproducible` target copies the current working tree to
two temporary directories, runs this target in each, and compares the resulting
manifests. It proves two copied-tree builds on one host and toolchain, not two
clean network clones or arbitrary-host identity. The kernel and userland binaries
contain no timestamps or host paths, so they are identical when the declared
inputs remain fixed.

## Reference hashes

The reference reproducible build was produced with:

```bash
SOURCE_DATE_EPOCH=1700000000 make reproducible
```

| Artifact | Reference SHA-256 (prefix) |
|---|---|
| `build/kernel.elf` | `79499f3b` |
| `build/kernel.bin` | `df45852a` |
| `build/root.img` | `d9c47086` |
| `build/root-1991.img` | `4ff943e2` |
| `build/bemu-linux01` | `358345ec` |
| `build/mkimage` | `c6f441e5` |
| `build/minix-inspect` | `c044de95` |
| `build/shell.bin` | `4296fc4a` |
| `build/update.bin` | `4a0212fc` |
| `build/hello.bin` | `7596c6b3` |
| `build/yes.bin` | `32937906` |
| `build/pathcheck.bin` | `95c7a190` |
| `build/cat.bin` | `0b555928` |

See `build/REPRODUCIBLE.sha256` after running `make reproducible` for the full
checksums.

## Evaluator package bytes

`SOURCE_DATE_EPOCH=1700000000 make reproducible artifact` builds a package named
for the first 12 digits of the clean source commit. It exports tracked bytes from
that commit, includes its reachable history as `repository.bundle`, records the
full commit/tree and Git blob inventory, covers every non-self-referential file
with the root `SHA256SUMS`, and emits a detached pre-extraction checker plus a
checksum manifest covering both checker and archive. The package builder performs
its own fresh build in a clone of the fixed history bundle rather than trusting
ignored outputs left in the caller's checkout.

Archive members use lexical order, ustar format, the fixed epoch, uid/gid zero,
and normalized modes; gzip uses `-n`. Run:

```bash
make verify-artifact-reproducible
make artifact-check ARTIFACT=release/linux-0.01-still-runs-evaluator-<commit-prefix>.tar.gz
```

The first target performs two commit-bound builds and package constructions and
requires equal archive bytes. The second independently checks transfer hash, safe paths,
metadata, package-wide inventory, source Git objects, identity, and build hashes.
This package-byte claim does not erase the cross-host limits below.

## Known non-determinism

`build/bemu-linux01` is a host ELF binary. It is deterministic between runs on
the same host with the same toolchain, but different distributions or linker
versions may produce different host binary bytes. The kernel (`build/kernel.bin`)
and root images (`build/root.img` and `build/root-1991.img`) are fully
deterministic. `kernel.bin` is the deterministic flat PA0 payload followed by
the deterministic 16-byte `L01KIMG1` length trailer.
