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
entering the guest. The kernel validates the HHDM, memory-map, kernel-address,
command-line and hypervisor tags plus their CRC64 fields. The IDE root image is
not a BBP payload or tag. CRC64 detects accidental corruption but does not
authenticate the producer.

**Status**: PROVEN / QUALIFIED.

**Evidence**: `bbp/linux01_bbp.c`, `bemu/bemu_linux01.c` BBP code paths,
`tests/test_boot.py` BBP checks.

### "Memory and kernel loading limits fail before KVM entry"

**Source**: `bemu/README.md` and `ARCHITECTURE.md`.

**Audit**: Guest RAM has one public size: exactly 8 MiB. Range checks use
subtraction and reject wrapping, out-of-RAM and placements overlapping the
bootstrap GDT or reserved BBP window. The enveloped kernel payload must be
nonempty and no larger than 512 KiB; incomplete reads are rejected. RAM allocation, kernel
loading and BBP construction complete before `setup_kvm()` opens `/dev/kvm`.

**Status**: PROVEN.

**Evidence**: `make test-bemu-loading` exercises exact boundaries, overflow,
adjacency, GDT/BBP overlap, deterministic `ENOMEM`, injected short reads, clean
allocation-failure state and real file loading. Its process-level cases give the
production runner empty and 512 KiB + 1 payloads and require exit status 1, the
structured diagnostic, and absence of direct-KVM-entry or guest-success output.

### "Canonical truncated kernel and root artifacts fail before KVM"

**Source**: `bemu/README.md` and `ARCHITECTURE.md`.

**Audit**: `kernel.bin` carries a 16-byte `L01KIMG1` trailer declaring the PA0
payload length. bEMU requires exact agreement between that value and file size,
loads only payload bytes, and rejects legacy raw images. Root images must equal
the fixed 977/5/17 CHS byte length; the production size check precedes `mmap`.

**Status**: PROVEN for the tested canonical artifacts.

**Evidence**: `make test-artifact-truncation` creates disposable prefix,
interior and suffix cutoffs of the canonical kernel and both root profiles,
plus an interior kernel deletion retaining the original trailer. Every case
exits 1 before direct KVM entry; source hashes remain unchanged. Code inspection
confirms the root size branch precedes the writable mapping. Loader unit
tests cover exact 512 KiB payloads, trailer exclusion from RAM, invalid/truncated
trailers, explicit length mismatch and injected short reads.

**Limit**: the length trailer detects truncation, not same-size payload
corruption. Same-size root corruption is separately scoped by filesystem fault
tests. Released raw-kernel consumers must validate and strip the final 16 bytes;
`build/kernel.raw` is an internal build intermediate. The length-only framing
does not claim to recognize every adversarial cutoff of every possible payload
containing trailer-like bytes.

### "IDE read and write failures are deterministic and bounded"

**Source**: `bemu/README.md` and `ARCHITECTURE.md`.

**Audit**: the modern IDE bridge can arm one host-side read or write failure for
a selected LBA. A matching single- or multi-sector command consumes the fault,
sets ATA abort/`ERR`, raises IRQ14, clears transfer state and does not read or
modify the failing sector. Other operations and LBAs remain unaffected. The
historical CLI exposes no fault switch.

**Status**: PROVEN / TEST-ONLY.

**Evidence**: `make test-ide-faults` exercises read and write errors, IRQ14,
zero transfer, one-shot recovery, operation/LBA scoping and later sectors of
multi-sector commands without KVM.

### "Lost and duplicated IRQ edges are deterministic and bounded"

**Source**: `bemu/README.md` and `ARCHITECTURE.md`.

**Audit**: the common modern IRQ bridge can arm one host-side drop or duplicate
for IRQ0-15. The next rising edge on that IRQ consumes it; unrelated IRQs and
redundant high levels do not. Drops suppress the matching deassertion. Duplicate
replay waits for at least one completed KVM run, a low device line, and clear
selected IRR/ISR state, including the master cascade for slave IRQs. No CLI or
guest fault control exists.

**Status**: PROVEN / TEST-ONLY.

**Evidence**: `make test-irq-faults` uses a callback transport to verify exact
edge order, scope, one-shot consumption, deferral, PIC/cascade quiescence, reset,
re-arm and recovery without KVM. `make test-irq-faults-kvm` uses the production
VM setup and irqchip ioctls to prove drop/replay against IRR across completed
single-step `KVM_RUN` calls. Default-path boot remains a separate regression.

**Limit**: line traces and callback edges do not prove guest handler entry.
Recovery from dropped or duplicated keyboard/IDE interrupts is not claimed.

### "Invalid scancodes and truncated host input are bounded"

**Source**: `bemu/README.md` and `ARCHITECTURE.md`.

**Audit**: the modern keyboard test seam accepts only the Set-1 error/overrun
bytes `0x00` and `0xff`; other make, break and prefix bytes are rejected without
changing the queue. Host terminal escape state survives input polling boundaries.
At declared non-TTY EOF, a lone Escape is emitted normally while an incomplete
CSI or SS3 sequence is discarded and the decoder returns to idle. No CLI or
guest fault control exists.

**Status**: PROVEN / TEST-ONLY.

**Evidence**: `make test-keyboard-faults` verifies injection scope and order,
single IRQ1 requests through the controller latch, occupied-latch backpressure,
normal-input recovery, split navigation input, EOF finalization, truncation of
CSI/SS3 parameter sequences, idempotence and complete-but-unsupported escapes.
Normal boot tests separately exercise the production keyboard path.

**Limit**: host queue and IRQ1 requests do not prove guest handler entry. Guest
recovery from arbitrary malformed prefix streams or stuck modifiers is not
claimed, and a full keyboard queue remains fatal rather than truncating input.

### "Minix metadata corruption is deterministic and isolated"

**Source**: `docs/FS-EXPERIENCE.md` and `ARCHITECTURE.md`.

**Audit**: fixed filesystem-relative offsets, located from the MBR partition
entry in disposable copies of both profile images, alter only the Minix v1
superblock magic, root inode mode, or root-zone allocation bit.
Each fault must be rejected by both the repository's read-only independent
inspector and util-linux `fsck.minix`. Corrupt files are never booted.

**Status**: PROVEN / TEST-ONLY.

**Evidence**: `make test-fs-corruption` checks clean controls, exact changed
bytes, expected diagnostics, oracle non-mutation and canonical-image hashes.

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

### "Both experience profiles pass complete scripted sessions"

**Source**: `EXPERIENCE.md`.

**Audit**: The same integration runner boots disposable copies of the 1991 and
alive images with explicit profile selection. Unique boundaries isolate every
command result so echoed input, boot text, or another command cannot satisfy an
assertion. Each session covers identity, time, the manual, a real external
process, scheduler visibility, a kernel pipe, redirection, and real Minix v1
create/read/remove operations. Profile-specific identity is forbidden in the
other profile's command output.

**Status**: PROVEN.

**Evidence**: `make test-experiences` runs both sessions after independent
`fsck.minix` validation. `tests/test_harness_utils.py` separately validates the
transcript-boundary extractor.

### "The guest surface is protected from modern feature creep"

**Source**: `MISSION.md`, `EXPERIENCE.md` and `README.md`.

**Audit**: Both disposable profile sessions probe package managers, network
tools, language runtimes, guest compilers/build tools, desktops and browsers and
require a command-local `not found` result. Literal probes cover variables,
globbing, quoting, command substitution, command lists and background syntax.
The 1991 session additionally rejects `fortune` and the retrospective `linus`
command, while alive retains them as narrative only. `hello` and `yes` resolve
to real external programs instead of bounded built-in simulations.

The deny policy is intentionally guest-scoped. Modern host compilers, Python,
KVM, containers, sanitizers and tests remain part of the documented bridge.

**Status**: PROVEN.

**Evidence**: `make test-experiences`, `make test-shell` and
`make test-bemu-devices`. The device test proves that the host input bridge
actually transports the unsupported punctuation being tested instead of
silently deleting it.

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
