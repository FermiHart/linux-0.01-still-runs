# Real filesystem experience

This document seals the state of the real-filesystem work for Waves 026–040.

## What is now real

Every file operation performed by the built-in shell goes through the Linux
0.01 Minix v1 filesystem code, the buffer cache and the IDE driver:

- `echo ... > file` creates/truncates and writes
- `echo ... >> file` appends
- `cat` reads back from the buffer cache
- `touch`, `rm`, `cp`, `mv`, `ln` manage inodes and directory entries
- `mkdir`, `rmdir` manage directories and link counts

These are exercised by the new `test-fs-*` targets.

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

## What remains sealed behind bEMU IDE writes

Cross-boot persistence is prepared but not yet functional:

- bEMU now maps the root image with `MAP_SHARED`.
- The shell has a `sync` built-in backed by `lib/sync.c`.
- `init/main.c` uses the external `sync()` symbol instead of an inline
duplicate.

However, calling `sync()` from userland blocks the shell because the kernel
waits for IDE write-completion interrupts that bEMU does not yet fully
deliver. Once the bEMU IDE module is improved (Waves 047 and 050), the same
`sync` built-in and `MAP_SHARED` mapping will make persistence work without
further kernel changes.

## Test targets added

```bash
make test-fs-write     # write, append, truncate
make test-fs-mkdir     # mkdir/rmdir
make test-fs-link      # ln/rm/mv
make test-fs-large     # multi-line file
make test-fs-property  # pseudo-random read/write cases
make test-fs-inspect   # independent Minix v1 audit
make test-fs-real      # touch/ls/rm on real /tmp
make inspect-rootfs    # dump build/root.img
make fsck-rootfs       # validate with fsck.minix
```
