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

## Workarounds

For testing, all filesystem operations are verified within a single boot using
a writable copy of `build/root.img`. Cross-boot tests will be enabled once the
IDE write path is fixed.
