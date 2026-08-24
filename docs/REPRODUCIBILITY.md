# Reproducibility

This document explains how to obtain bit-for-bit identical artifacts from a
clean checkout of `linux-0.01-still-runs`.

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

Run the reproducible target:

```bash
make reproducible
```

This:

1. Cleans the build tree.
2. Exports a fixed `SOURCE_DATE_EPOCH` (or honors an externally supplied one).
3. Builds all artifacts.
4. Writes `build/SHA256SUMS`.
5. Copies it to `build/REPRODUCIBLE.sha256` for later comparison.

Two consecutive runs on the same machine with the same toolchain produce the
same `build/SHA256SUMS`. The kernel and userland binaries contain no timestamps
or host paths, so they are identical even when `SOURCE_DATE_EPOCH` changes.

## Reference hashes

The reference reproducible build was produced with:

```bash
SOURCE_DATE_EPOCH=1700000000 make reproducible
```

| Artifact | Reference SHA-256 (prefix) |
|---|---|
| `build/kernel.elf` | `5cb6e6fd` |
| `build/kernel.bin` | `be754669` |
| `build/root.img` | `b1b1a197` |
| `build/root-1991.img` | `7c2df309` |
| `build/bemu-linux01` | `739269d8` |
| `build/mkimage` | `f77331fa` |
| `build/shell.bin` | `9fd7a474` |
| `build/update.bin` | `4a0212fc` |
| `build/hello.bin` | `7596c6b3` |
| `build/yes.bin` | `32937906` |
| `build/pathcheck.bin` | `95c7a190` |
| `build/cat.bin` | `0b555928` |

See `build/REPRODUCIBLE.sha256` after running `make reproducible` for the full
checksums.

## Known non-determinism

`build/bemu-linux01` is a host ELF binary. It is deterministic between runs on
the same host with the same toolchain, but different distributions or linker
versions may produce different host binary bytes. The kernel (`build/kernel.bin`)
and root images (`build/root.img` and `build/root-1991.img`) are fully
deterministic.
