# Software Bill of Materials

This document inventories every component that contributes to a bootable
`linux-0.01-still-runs` artifact.

## Origin

| Component | Version / Source | License | Purpose |
|---|---|---|---|
| Linux 0.01 | `upstream/linux-0.01.tar.gz` (kernel.org mirror) | Linux 0.01 terms (see `LICENSE`) | Historical kernel source |

SHA-256 of upstream tarball:
`24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d`

## In-tree additions

| Component | Location | License | Purpose |
|---|---|---|---|
| Bear Boot Protocol (BBP) | `bbp/` | BSD-3-Clause / Unlicense | Firmware-free boot handoff with CRC-checked tags |
| bEMU KVM runner | `bemu/bemu_linux01.c` | BSD-3-Clause / Unlicense | Minimal emulator that loads the kernel directly into KVM |
| Minix v1 image forge | `tools/mkimage.c` | BSD-3-Clause / Unlicense | Build the bootable root filesystem by hand |
| Kernel image wrapper | `tools/kernel_image.py` | BSD-3-Clause / Unlicense | Add the deterministic host-side payload-length trailer |
| Interactive shell | `userland/shell.c` | BSD-3-Clause / Unlicense | Userland smoke-test shell |
| C runtime | `userland/crt0.S` | BSD-3-Clause / Unlicense | Userland entry point and syscall wrappers |
| Hello demo | `userland/programs/hello.c` | BSD-3-Clause / Unlicense | Minimal C userland program |
| Sync daemon | `userland/update.asm` | BSD-3-Clause / Unlicense | Calls `sync()` in a loop |
| VGA 80×50 driver | `kernel/vga_text50.c`, `kernel/vga_font8x8.h` | BSD-3-Clause / Unlicense | Higher-density text mode for the boot experience |

## Modified historical files

All source-path changes to the original Linux 0.01 core are enumerated and
hashed in `datasets/patches/`; interpreted adaptation groups and unresolved
joins are documented there and in `docs/PORTING_LEDGER.md`. The historical core
directories are:

- `init/`
- `kernel/`
- `mm/`
- `fs/`
- `lib/`
- `include/`

## Build-time dependencies

| Dependency | Reference version | Source |
|---|---|---|
| GCC | 13.3.0 | Ubuntu 24.04 package |
| GNU Binutils | 2.42 | Ubuntu 24.04 package |
| NASM | 2.16.01 | Ubuntu 24.04 package |
| GNU Make | 4.3 | Ubuntu 24.04 package |
| Python | 3.12.3 | Ubuntu 24.04 package |

See `docs/TOOLCHAIN.md` and `docs/CONTAINER.md` for pinning details.

## Runtime dependencies

| Dependency | Minimum version | Notes |
|---|---|---|
| Linux host kernel | 5.x or newer | KVM API (`/dev/kvm`) |
| KVM module | enabled | Required by bEMU |

## Verification

The provenance of every modified file can be audited with:

```bash
make provenance
make audit
```

These targets write `build/PROVENANCE.txt` and `build/AUDIT.txt`.
