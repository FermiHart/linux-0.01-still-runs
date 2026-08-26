# Filesystem real — known limitations

This document records the current state of real filesystem operations in
`linux-0.01-still-runs`.

## What works in a single boot

- `echo`, `cat`, `touch`, `rm`, `cp`, `mv`, `ln`
- `mkdir`, `rmdir`
- `>` truncation and `>>` append
- reading files back from the buffer cache

These are covered by `make test-fs-write`, `make test-fs-mkdir` and
`make test-fs-link`.

## What does not yet work

### Cross-boot persistence

Guest writes are mapped back to the host `root.img` via `MAP_SHARED` in bEMU,
and the shell now has a `sync` built-in backed by `lib/sync.c`. However,
calling `sync()` from userland causes the kernel to block waiting for IDE
write-completion interrupts that are not yet fully delivered by bEMU.

Therefore:

- `sync` in the shell blocks.
- `halt`/`reboot` block after flushing.
- Files created in one boot are not visible in a subsequent boot.

The next bEMU high-level wave (IDE IRQ handling during writes) will resolve
this.

### `update` daemon

`/bin/update` is built but not started by `init`. Even if it were started, it
would block on the same `sync()` issue.

### Full disk / full inode

Not exercised by the smoke-test suite. The current root image has 961 free
blocks and 241 free inodes, which is enough for the tests above.

### Corruption, IDE errors and power loss

Host-only deterministic tests now cover one-shot IDE read/write errors and
simulated power cuts at semantic write boundaries. IDE payload bytes are staged
until a complete 512-byte sector is available; a cut before commit preserves the
old sector, while a cut after commit preserves the complete new sector. Cuts at
an unmasked completion-IRQ request have the same bytes as post-commit cuts and a
distinct IRQ history.

`make test-power-cut` operates only on disposable copies of both profile images.
It selects a full regular-file data block from Minix metadata, repeats each
scenario, and requires exact 0, 512 or 1024 changed bytes plus stable hashes.
`minix-inspect --audit` and read-only `fsck.minix` remain clean because only file
content changes; that demonstrates the limit of metadata checking, not recovery
or correctness of file data.

This is bEMU's virtual-medium contract. `MAP_SHARED` plus test-side `msync` does
not reproduce controller caches, host page-cache loss, platter behavior or a
physical power failure. The seam is unavailable to the guest and CLI.

### Multi-boot persistence

See the cross-boot persistence note above. Files created in one bEMU run are
not yet visible in a second run because dirty buffers are not flushed to the
backing image.

## Workarounds

For testing, all filesystem operations are verified within a single boot using
a writable copy of `build/root.img`. Cross-boot tests will be enabled once the
IDE write path is fixed.
