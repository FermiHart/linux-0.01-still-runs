# Toolchain pinning

This document records the exact toolchain versions used to build and verify
`linux-0.01-still-runs`. The project builds successfully on a broader range of
versions, but the entries below are the reference configuration for academic
reproducibility.

## Reference host

| Tool | Version | Role |
|---|---|---|
| GCC | 13.3.0 | Kernel, userland and BBP compilation |
| GNU Binutils | 2.42 | Assembler (`as`) and linker (`ld`) |
| NASM | 2.16.01 | Userland assembly (`sh.asm`, `update.asm`) |
| GNU Make | 4.3 | Build orchestration |
| Python | 3.12.3 | Test harness (`tests/*.py`) |
| Bash | 5.x | Shell scripts |
| util-linux | 2.39.3 | Independent Minix v1 `fsck.minix` oracle |
| Linux kernel headers | 6.x | KVM interface for bEMU |

## Cross-compiler alternative

The Makefile auto-detects a prefixed cross-compiler in this order:

1. `x86_64-elf-gcc` on `PATH`
2. `$(HOME)/.local/cross/bin/x86_64-elf-gcc`
3. `/opt/cross/bin/x86_64-elf-gcc`
4. Native host compiler (Linux only)

Any of the above may be used, but the pinned reference is GCC 13.3.0 for the
native path.

## Important compiler flags

| Flag | Reason |
|---|---|
| `-m32 -march=i386` | Build 32-bit i386 code |
| `-ffreestanding -nostdinc -fno-builtin` | No hosted C library |
| `-fno-pie -fno-pic` | Generate absolute code for the bootloader-free BBP path |
| `-fleading-underscore` | Matches original Linux 0.01 symbol naming (`_printk`) |
| `-fno-omit-frame-pointer` | Required by the original inline assembly |
| `-std=gnu89` | Kernel and historical userland |
| `-std=gnu11` | BBP core only |

## Heisenbug workarounds

The following files are deliberately compiled at `-O1` as a conservative shield
against historical `-O2` sensitivity:

- `fs/buffer.c`
- `fs/bitmap.c`
- `kernel/vsprintf.c`

The investigation in `tests/compiler-cases/` (Waves 075–083) found that
`fs/bitmap.c` contains inline-asm macros that modify memory without a `"memory"`
clobber, which is undefined behavior in the GCC contract and explains the `-O2`
failure on x86_64. The `-O2` symptoms originally attributed to
`fs/buffer.c` and `kernel/vsprintf.c` could not be reproduced in isolation on
GCC 13.3 and are recorded as historical hypotheses. See
`tests/compiler-cases/CLASSIFICATION.md` and `docs/AUDIT-STATEMENTS.md`.

## Container lock

For bit-for-bit reproducibility, use the container described in
`docs/CONTAINER.md` (Wave 018). The lock file pins the OS package versions
that supply the tools above.
