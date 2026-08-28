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
| Bear Boot Protocol (BBP) | `bbp/` | Per-file BSD-3-Clause identifiers; otherwise project terms where applicable | Firmware-free boot handoff with CRC-checked tags |
| bEMU KVM runner | `bemu/` | Per-file BSD-3-Clause identifier and author-declared bEMU-NANO provenance; see evaluator notices | Minimal emulator that loads the kernel directly into KVM |
| Minix v1 image forge | `tools/mkimage.c` | Unlicense for original material; embedded quotation separately inventoried | Build the bootable root filesystem by hand |
| Kernel image wrapper | `tools/kernel_image.py` | Unlicense | Add the deterministic host-side payload-length trailer |
| Interactive shell | `userland/shell.c` | Unlicense for original material; embedded third-party text separately inventoried | Userland smoke-test shell |
| C runtime | `userland/crt0.S` | Unlicense | Userland entry point and syscall wrappers |
| Hello demo | `userland/programs/hello.c` | Unlicense | Minimal C userland program |
| Sync daemon | `userland/update.asm` | Unlicense | Calls `sync()` in a loop |
| VGA 80×50 driver | `kernel/vga_text50.c`, `kernel/vga_font8x8.h` | Modern driver under project terms; Joseph Gil/SeaBIOS font data is public domain | Higher-density text mode for the boot experience |

## Research datasets

| Dataset | Location | Contents |
|---|---|---|
| Historical-core patches | `datasets/patches/` | Pinned source deltas, adaptation joins and evidence gaps |
| Golden traces v1 | `datasets/golden-traces/v1/` | Two bounded inherited traces, schema and normalization policy |
| Reduced compiler cases v1 | `datasets/compiler-cases/v1/` | Three source snapshots, 18 hosted GCC 13.3.0 cells, binaries, assembly, outputs and identities |

The compiler-case executables are retained research observations, not components
of the bootable guest. Their GCC, binutils, glibc loader/libc and five multilib
package identities are recorded in `environment.json` inside the dataset. This
identity record is not a complete archive of every host build input.

## Evaluator-package redistribution

`evaluation/v1/THIRD-PARTY-NOTICES.md` is the package-specific engineering
inventory. It preserves the Linux 0.01 no-fee/full-source terms, the font
provenance, bEMU-NANO's unresolved public upstream identity, glibc linkage, and
the rights-review boundary for attributed historical text and quotations. The
included `evaluation/v1/licenses/LGPL-2.1.txt` supplies the complete applicable
LGPL document, while `GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt` preserves the GCC
target-code exception. These notices prevent the root Unlicense from being
interpreted as a blanket license for third-party material.

The generated host tools are dynamic PIE executables and do not bundle the glibc
shared library. Generated and retained GCC target code can include startup/runtime
material under the GCC Runtime Library Exception. Referenced Ubuntu, GCC,
Binutils and NASM packages are dependencies, not redistributed package archives.

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
