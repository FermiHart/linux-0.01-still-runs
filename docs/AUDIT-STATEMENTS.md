# Audited Technical Statements

This document records claims made in project communications, their current
status, and the evidence or correction applied. It is part of the academic
discipline of the project: every strong claim must be defensible.

## Audit criteria

- **PROVEN**: supported by test, trace, disassembly or external reference.
- **QUALIFIED**: true only with stated assumptions or caveats.
- **PENDING**: claim is reasonable but evidence is still being assembled.
- **CORRECTED**: statement was rephrased after audit.

## Statements

### "Not emulated"

**Source**: README.md tagline, public communication.

**Audit**: the guest kernel runs inside a KVM virtual machine created by
`bEMU`. KVM uses hardware virtualization extensions, not pure software
emulation, but it is still a virtualized environment with emulated legacy
devices (PIC, PIT, UART, IDE, keyboard). The accurate distinction is that there
is no traditional emulator frontend, no BIOS/UEFI firmware and no bootloader.

**Status**: CORRECTED.

**Correction**: README now reads "Not emulated behind a traditional emulator;
hardware-virtualized and firmware-free."

### "The original linux-0.01 source is still here"

**Source**: README.md narrative.

**Audit**: the historical core (`init/`, `kernel/`, `mm/`, `fs/`, `lib/`,
`include/`) is derived from the Linux 0.01 tarball and remains recognizable
line-for-line. It is not byte-for-byte identical because documented patches
were required for modern GCC, CMOS Y2K, serial throughput and other
incompatibilities. The two-layer design section already clarifies this.

**Status**: QUALIFIED.

**Correction**: README narrative softened to "recognizable line-for-line
against the official tarball" and references the two-layer design.

### "GCC -O2 mis-compiled fs/buffer.c"

**Source**: README.md "Notable fixes".

**Audit**: the symptom is real and reproducible: at `-O2` the second
`_open3(O_CREAT)` after a filesystem write panics. The root cause is not yet
fully classified. Possibilities include a GCC optimization bug, undefined
behavior in the original `while (tmp != free_list || (tmp=NULL))` idiom,
aliasing assumptions, or calling-convention dependence. The `-O1` workaround is
valid but does not prove the cause.

**Status**: PENDING → investigation assigned to Waves 075–083.

**Correction**: README now describes the symptom and the `-O1` workaround
without asserting an unproven GCC bug. A reference to the investigation waves
is included.

### "CMOS Y2K rollover"

**Source**: README.md and ARCHITECTURE.md.

**Audit**: verified. `kernel_mktime()` treats `tm_year < 70` as `20yy`, so CMOS
year `26` becomes `2026` instead of `1926`. The `date` command returns the
current year in the alive mode.

**Status**: PROVEN.

**Evidence**: `tests/test_shell.py` checks `date` output; boot log shows the
correct year.

### "Firmware-free bEMU boot"

**Source**: README.md.

**Audit**: `bemu/bemu_linux01.c` uses `KVM_CREATE_VM`, maps memory and sets
registers directly. No BIOS, UEFI, GRUB, Limine or other firmware is loaded.
Guest devices are implemented by bEMU itself.

**Status**: PROVEN.

**Evidence**: source inspection, `make run` boot path, absence of firmware
binaries in the repository.

### "Real BBP handoff"

**Source**: README.md.

**Audit**: bEMU writes a structured handoff at physical `0xC0000` before
entering the guest. The kernel validates CRC64 tags for RAM, kernel and root
disk. CRC64 detects accidental corruption but does not authenticate the
producer.

**Status**: PROVEN / QUALIFIED.

**Evidence**: `bbp/linux01_bbp.c`, `bemu/bemu_linux01.c` BBP code paths,
`tests/test_boot.py` BBP checks.

### "Automated validation: build → direct KVM boot → full shell smoke suite"

**Source**: README.md.

**Audit**: `make test` and `make ci` build, boot via bEMU/KVM, and run
`test_boot.py`, two `test_shell.py` passes (normal and interactive) and
`test_large_rootfs.py`. All pass on the reference Linux/KVM host.

**Status**: PROVEN.

**Evidence**: `make -j8 ci` green on the reference host; GitHub Actions
workflow.

### "Session-local filesystem"

**Source**: README.md "Known limitations".

**Audit**: currently true. The shell implements some filesystem operations in
its own VFS layer rather than writing through to the Minix v1 disk. The project
has identified real persistent filesystem as the highest-priority next step.

**Status**: PROVEN / PLANNED.

**Correction**: limitation retained but cross-referenced to Waves 026–040.

### bEMU provenance

**Source**: `bemu/README.md`.

**Audit**: `bemu/bemu_linux01.c` is adapted from bEMU-NANO. The upstream
license and provenance are preserved in the file header.

**Status**: PROVEN.

**Evidence**: file header license block.

## Outstanding claims requiring future audit

- Exact CHS geometry and its compatibility with Linux 0.01 HD driver.
- Completeness of the 67 system calls table.
- Whether all `-O1` workarounds are due to compiler issues or UB.
- Determinism of boot under different host CPU/KVM versions.

These are tracked in the 120-wave roadmap, Waves 075–083 and related waves.
