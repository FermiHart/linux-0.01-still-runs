# Real filesystem experience

This document records the real-filesystem work from Waves 026–040, the offline
metadata-corruption gate from Wave 098 and virtual-media power cuts from Wave
103.

## What is now real

Every file operation performed by the built-in shell goes through the Linux
0.01 Minix v1 filesystem code, the buffer cache and the IDE driver:

- `echo ... > file` creates/truncates and writes
- `echo ... >> file` appends
- `cat` reads back from the buffer cache
- `touch`, `rm`, `cp`, `mv`, `ln` manage inodes and directory entries
- `mkdir`, `rmdir` manage directories and link counts
- `man` reads ASCII pages from real files under `/usr/man/man1`

Filesystem mutation commands are exercised by the `test-fs-*` targets. Manual
lookup and removal are exercised on temporary profile images by
`make test-experiences`.

## What is independently verified

`tools/minix-inspect.c` is a standalone Minix v1 parser. It reads the first
partition of `build/root.img` and:

- validates the superblock magic (`0x137F`)
- lists used inodes and zones
- dumps the inode table and directories
- checks consistency between bitmaps, inode table and directory entries
- dumps regular-file contents

`make test-fs-inspect` runs `minix-inspect --audit` against the freshly
forged `build/root.img`.

`make test-fs-corruption` copies both profile images to a temporary directory
and deterministically corrupts the superblock magic, root inode mode, or root
zone bitmap. The independent inspector and util-linux `fsck.minix` must reject
every copy with the expected diagnosis. Hash and byte-offset checks prove that
the oracles do not repair their input and that canonical images are untouched.

`make test-power-cut` derives an allocated regular-file data block from each
profile, applies LBA-selected IDE cuts only to disposable copies and checks
exact 0/512/1024-byte commit prefixes. Both metadata oracles remain clean after
the data-only mutation. That is evidence that filesystem structure survived,
not that the old or new file content was recovered correctly.

## What remains sealed behind bEMU IDE writes

Cross-boot persistence is prepared but not yet functional:

- bEMU now maps the root image with `MAP_SHARED`.
- The shell has a `sync` built-in backed by `lib/sync.c`.
- `init/main.c` uses the external `sync()` symbol instead of an inline
duplicate.

The IDE module now completes and signals sector writes in host tests, but the
full guest `sync`/halt/cross-boot lifecycle remains unproven and is not repaired
by the host-only Wave 103 cut seam. `MAP_SHARED` and test-side `msync` must not be
treated as evidence of guest flush completion or physical durability.

## Test targets added

```bash
make test-fs-write     # write, append, truncate
make test-fs-mkdir     # mkdir/rmdir
make test-fs-link      # ln/rm/mv
make test-fs-large     # multi-line file
make test-fs-property  # pseudo-random read/write cases
make test-fs-inspect   # independent Minix v1 audit
make test-fs-corruption # offline metadata fault injection
make test-power-cut     # disposable-image IDE write cut matrix
make test-fs-real      # touch/ls/rm on real /tmp
make inspect-rootfs    # dump build/root.img
make fsck-rootfs       # validate with fsck.minix
```
