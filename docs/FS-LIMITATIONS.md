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

## Orderly cross-process persistence

`make test-fs-persistence` now proves the guest filesystem lifecycle in both
`alive` and `1991` profiles. For each profile the harness:

- hashes a canonical image and copies it to a temporary directory;
- creates a file through Linux 0.01, calls the real `sync()` path, emits an
  unambiguous post-sync marker, and invokes `halt`;
- requires an explicit guest power request followed by a halted vCPU with
  interrupts disabled, then normal disk unmap and a zero exit;
- requires the disposable image hash to change while the canonical hash does not;
- resolves `/tmp/d01p/proof` and its exact bytes with `minix-inspect --audit`,
  then checks the extracted partition with util-linux `fsck.minix`;
- starts a new bEMU process with new KVM and RAM state over the same copy and
  reads exactly the previously written payload without recreating it.

This is cross-boot persistence at the artifact's process boundary. It is not an
in-process machine reset: the guest's keyboard-controller reset request is not
modeled, so `reboot` terminates the current runner rather than recreating the VM.

## What does not yet work

### Physical-media durability

The backing file is a `MAP_SHARED` virtual medium. The test proves guest flush,
normal bEMU cleanup, a changed backing image, independent metadata consistency,
and a fresh-process read. It does not model controller caches, host page-cache
loss, platter behavior, flush barriers, or physical power failure.

### `update` daemon

`/bin/update` is built but not started by `init`; orderly persistence currently
depends on an explicit `sync`, `halt`, `reboot`, or `exit` path.

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

### Abrupt process loss

The cross-process gate is intentionally orderly. Killing bEMU before guest
`sync()` is outside that proof and may leave only the sector prefixes described
by the deterministic power-cut model above.
