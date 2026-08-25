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

**Source**: README.md "Notable fixes" and Makefile comments.

**Audit**: the full-kernel symptom is real: at `-O2` the second `_open3(O_CREAT)`
after a filesystem write panics.  An isolated reproduction of the original
`getblk()` free-list pattern in `tests/compiler-cases/buffer_freelist.c` does
not fail on GCC 13.3 at any optimization level.  The case is therefore classified
as **HISTORICAL_HYPOTHESIS / NOT_REPRODUCED** in `tests/compiler-cases/CLASSIFICATION.md`.
The `-O1` workaround is retained as a conservative shield while the historical
claim remains unproven on modern toolchains.

**Status**: QUALIFIED → Waves 075–083 completed.

**Correction**: Makefile comments now describe the `-O1` override as a
"compiler-shield" rather than asserting a GCC bug.  README and porting ledger
refer to `tests/compiler-cases/` for the investigation outcome.

### "GCC -O2 mis-compiled fs/bitmap.c"

**Source**: Makefile comments and `docs/PORTING_LEDGER.md`.

**Audit**: the isolated reproduction `tests/compiler-cases/bitmap_inline_asm.c`
fails at `-O2` on x86_64.  The root cause is the inline-asm macros in
`fs/bitmap.c` (`set_bit`, `clear_bit`, `find_first_zero`) that modify memory
without declaring a `"memory"` clobber.  GCC is therefore permitted to keep the
bitmap word in a register across the asm block, making the write invisible to a
subsequent read.  This is undefined behavior in the GCC inline-asm contract, not
a compiler bug.  The case is classified as **UNDEFINED_BEHAVIOR** in
`tests/compiler-cases/CLASSIFICATION.md`.

**Status**: CORRECTED → Waves 075–083 completed.

**Correction**: Makefile comments now describe the `-O1` override as an
"asm-memory-shield" and point to the classification.  The porting ledger was
updated to reflect the real root cause.

### "GCC -O2 mis-compiled kernel/vsprintf.c %s handling"

**Source**: Makefile comments and `docs/PORTING_LEDGER.md`.

**Audit**: an isolated reproduction of the `%s` case in
`tests/compiler-cases/vsprintf_percent_s.c` does not fail on GCC 13.3 at any
optimization level for either x86_64 or i386.  No strict-aliasing,
sequence-point or UBSan issues were found.  The case is classified as
**HISTORICAL_HYPOTHESIS / NOT_REPRODUCED** in
`tests/compiler-cases/CLASSIFICATION.md`.

**Status**: QUALIFIED → Waves 075–083 completed.

**Correction**: Makefile comments now describe the `-O1` override as a
"compiler-shield" rather than asserting a GCC bug.  The porting ledger was
updated.

### "CMOS Y2K rollover"

**Source**: README.md and ARCHITECTURE.md.

**Audit**: verified. `kernel_mktime()` treats `tm_year < 70` as `20yy`, so CMOS
year `26` becomes `2026` instead of `1926`. The alive runtime returns the host
UTC-derived RTC year.

**Status**: PROVEN.

**Evidence**: `tests/test_shell.py` checks the current year in `date` output;
the boot log shows the same RTC-derived date.

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

### "Real filesystem operations"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: the shell no longer maintains a private VFS. File creation, reads,
writes, links, moves via link/copy/unlink, and directories use Linux 0.01 syscalls against the
mounted Minix v1 image. Cross-boot durability is still limited because bEMU does
not yet complete the IDE interrupt path required by `sync()`.

**Status**: CORRECTED / QUALIFIED.

**Evidence**: `tests/test_shell.py` and the filesystem tests exercise the real
kernel paths; `docs/FS-LIMITATIONS.md` records the remaining reboot limitation.

### "Pipes and redirection are handled by the kernel"

**Source**: `EXPERIENCE.md`.

**Audit**: the shell parses simple pipelines and `<`, `>`, `>>`, then creates
child processes with `fork`, connects stages with Linux 0.01 `pipe(2)` and
`dup2(2)`, and opens redirected files through the real Minix v1 VFS.

**Status**: PROVEN.

**Evidence**: `tests/test_shell.py` covers external-to-external pipelines,
builtin pipelines, input/output/append redirection, pipeline output to a file,
byte counts, and malformed syntax. `tests/bemu/test_bemu_devices.c` validates
the Finnish-keymap scancode sequence used to inject `|` and `<`.

### "Coherent identity and documented shell limits"

**Source**: README.md, `EXPERIENCE.md`, and shell help.

**Audit**: the shell runs as euid 0 in both profiles and therefore uses
`root@linux01:path#`. Help and README expose the effective 255-byte input,
30-argument, 64-token, eight-stage, 64-completion-match, and 14-byte Minix name
limits. Selected boundaries produce explicit diagnostics instead of being
hidden behind generic syntax errors.

**Status**: QUALIFIED.

**Evidence**: `tests/test_shell.py` checks root prompt identity, help text,
eight-stage success, nine-stage rejection, argument and input-line limits,
the exact 30-argument and 64-token boundaries, Minix name boundaries, and
non-destructive `touch` behavior. The completion-match cap is a documented
structural limit but does not yet have a boundary test. `bemu/console.c`
recognizes the same prompt contract for scripted input while rejecting
carriage-return redraws.

### "System views are live"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: `df` uses live `ustat` counters and `ps` reads a real but bounded
16-slot scheduler snapshot. `mount` reports the configured `/dev/hd1` root; it
is not a general mount-table query. `uptime` measures from shell startup and no
longer prints invented user counts or load averages.

**Status**: QUALIFIED.

### "EXPERIENCE=1991 selects a historical profile"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: Make selects a distinct Minix v1 image and passes `--experience
1991`; bEMU includes the selector in the CRC-checked BBP command line; init
derives the shell environment only after validating that handoff. The profile
has a concise ASCII identity and uses `/` as root's home. Its deterministic
historical boot epoch is supplied by the bEMU CMOS model.

**Status**: PROVEN.

**Evidence**: `tests/test_experience.py` checks invalid selectors, rejects both
directions of profile/image mismatch, verifies Make dry-run selection, guest BBP
output, real `/etc/issue` and `/etc/motd` files, shell mode identity, and bare
`cd` behavior.

### "1991 mode starts from the Linux 0.01 release date"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: The bEMU CMOS model snapshots `1991-09-17 00:00:00 UTC` for the 1991
profile. Linux 0.01 reads that model during `time_init()` and advances the epoch
through its normal PIT, scheduler tick, `jiffies`, and `CURRENT_TIME` paths.
Neither `date` nor `cal` contains a profile-specific output path.

**Status**: PROVEN.

**Evidence**: `tests/bemu/test_rtc.c` verifies exact BCD registers and coherent
snapshots; `tests/test_experience.py` boots the historical guest and verifies
the Tuesday 17 September 1991 `date` output and September 1991 calendar.

### "EXPERIENCE=alive is the explicit default"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: Empty Make selection and the bEMU CLI default resolve to `alive`, use
the alive image, emit the exact alive BBP command line, and provide
`HOME=/home/fermihart` plus `EXPERIENCE=alive` to the shell. The image contains
the Vesica Piscis narrative and states that `date` reads the kernel clock.

**Status**: PROVEN.

**Evidence**: `make test-experiences` boots both modes back-to-back and checks
their images, BBP identities, HOME behavior, banners, required narrative, and
cross-profile exclusions. The alive run parses the guest `date` output as UTC
and proves that it falls within the surrounding host-time window.

### "The guest contains an internal Unix manual"

**Source**: README.md and `EXPERIENCE.md`.

**Audit**: Six ASCII pages are regular files under `/usr/man/man1` in both
profile images. The `man` built-in validates a single topic, opens the
corresponding `.1` file through Linux 0.01, and streams its bytes; it contains no
embedded page text and accepts no path separators.

**Status**: PROVEN.

**Evidence**: `tests/test_shell.py` checks default, named, missing, and traversal
cases. `tests/test_experience.py` enumerates every page in both profiles, reads
`limits.1`, removes it on a temporary image, and then observes lookup failure.
Both filesystem images pass `fsck.minix` through the `test-experiences` graph.

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
