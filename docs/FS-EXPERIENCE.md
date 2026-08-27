# Real filesystem experience

This document records the real-filesystem work from Waves 026–040, the offline
metadata-corruption gate from Wave 098, virtual-media power cuts from Wave 103,
and the orderly cross-process lifecycle proved by Discovery Wave D01.

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

## What persists across bEMU processes

`make test-fs-persistence` runs the following proof for both profile images:

- copy the canonical image and record both hashes;
- create `/tmp/d01p/proof`, return from the real `sync()` path, and halt;
- terminate bEMU only after an explicit power request and KVM halted state with
  IF=0; reject the same CPU state without a request as an error;
- require a changed copy and unchanged canonical image;
- resolve the path and exact file bytes with `minix-inspect --audit` and require
  a clean read-only `fsck.minix` result;
- boot a second bEMU process with fresh KVM/RAM state and read the exact payload.

This proves orderly persistence on bEMU's virtual medium, not an in-process reset
or physical-media durability. `reboot` ends the current process after sync because
the keyboard-controller reset command is not modeled; a fresh invocation creates
the next boot.

## Test targets added

```bash
make test-fs-write     # write, append, truncate
make test-fs-mkdir     # mkdir/rmdir
make test-fs-link      # ln/rm/mv
make test-fs-large     # multi-line file
make test-fs-property  # pseudo-random read/write cases
make test-fs-persistence # sync/halt and exact read in a fresh bEMU process
make test-fs-inspect   # independent Minix v1 audit
make test-fs-corruption # offline metadata fault injection
make test-power-cut     # disposable-image IDE write cut matrix
make test-fs-real      # touch/ls/rm on real /tmp
make inspect-rootfs    # dump build/root.img
make fsck-rootfs       # validate with fsck.minix
```
