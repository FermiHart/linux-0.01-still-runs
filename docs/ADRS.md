# Architectural Decision Records

## ADR-001: Firmware-free KVM entry through bEMU

**Status**: accepted

**Context**: Linux 0.01 expects to be loaded at physical address zero and to
own the machine. Traditional approaches use a bootloader such as Limine or a
full emulator such as QEMU. The project wanted the smallest possible modern
surface and a boot path that could be inspected and tested as code.

**Decision**: Use `bEMU`, a small Linux/KVM runner that creates a VM, maps the
kernel at physical zero, builds a CRC64-checksummed handoff (BBP) at `0xC0000`,
and starts the vCPU directly. No BIOS, UEFI or third-party bootloader is
involved.

**Consequences**:

- The boot path is fully in source control.
- Tests can validate BBP tags independently.
- The project only runs on Linux hosts with `/dev/kvm`.
- Device emulation (PIC, PIT, UART, IDE, keyboard) is our responsibility.

## ADR-002: Preserve historical core, harden modern bridge

**Status**: accepted

**Context**: The value of the project is the 1991 kernel running. Modernizing
the historical core would destroy the archaeological signal. At the same time,
the bridge to modern hardware must be safe, testable and maintainable.

**Decision**: Keep `init/`, `kernel/`, `mm/`, `fs/`, `lib/` and `include/`
close to the original structure and style; apply only documented, minimal
patches. Treat `bemu/`, `bbp/`, `tools/`, `tests/` and the build system as
modern code with clear interfaces, tests and static checks.

**Consequences**:

- The historical core remains readable as a 1991 artifact.
- The bridge can use modern C, sanitizers and fuzzing.
- Every change to the core must be recorded in the porting ledger.

## ADR-003: Reproducible builds with pinned toolchain

**Status**: accepted

**Context**: Academic artifacts must be reproducible. Modern distributions and
compiler versions change behavior, especially for pre-standard C.

**Decision**: Pin toolchain versions, container digest, package versions and
`SOURCE_DATE_EPOCH`. Provide `make reproducible` for one controlled build and
`make verify-reproducible` to build twice and compare
artifacts byte for byte.

**Consequences**:

- Third parties can obtain identical artifacts.
- Compiler-optimization investigations are anchored to a known version.
- Maintenance cost increases when toolchain versions age.

## ADR-004: Real Minix v1 persistence instead of shell VFS

**Status**: accepted

**Context**: Early versions of the shell simulated some filesystem operations
in memory. This is convenient but breaks the promise of a real 1991
experience.

**Decision**: Route all filesystem operations through the kernel's Minix v1
driver. Writes must update the disk image and survive reboot. The shell may
still cache metadata for speed, but authoritative state lives on disk.

**Consequences**:

- `sync`, reboot and remount produce observable persistence.
- Disk-full, inode-full and corruption cases become real test scenarios.
- Performance may be lower than pure in-memory simulation.

## ADR-005: Automated tests as regression evidence

**Status**: accepted

**Context**: Manual testing of a booting kernel is slow and non-repeatable.

**Decision**: Maintain automated boot, shell, large-rootfs and fault-injection
tests that run through `bEMU`. Every wave must add or update tests that cover
positive and negative cases.

**Consequences**:

- Regressions are caught immediately.
- External reviewers can reproduce validation.
- Test runtime limits acceptable CI duration.

## ADR-006: One atomic commit per completed wave

**Status**: accepted

**Context**: The 120-wave roadmap is granular. Losing that granularity in a
single megacommit would destroy academic traceability.

**Decision**: Each completed wave becomes one atomic, reviewed commit. Waves
that are too large may use local preparatory commits, but the final history
must be coherent and bisectable. The private roadmap files stay out of Git.

**Consequences**:

- History tells the story of the project.
- Bisect and blame remain useful.
- Commit discipline is required from all agents.

## ADR-007: Self-describing kernel artifact length

**Status**: accepted

**Context**: a headerless flat binary has no external end marker. Once a file
has been truncated, `fstat()` cannot distinguish it from an intentionally
shorter valid kernel, so suffix truncation could reach KVM.

**Decision**: Keep the PA0 payload unchanged and append a versioned 16-byte
`L01KIMG1` trailer containing its little-endian length. bEMU requires exact
agreement, loads only payload bytes, and rejects unwrapped legacy kernels.

**Consequences**:

- Tested prefix, interior and suffix cutoffs of the canonical artifact are
  rejected before KVM entry.
- The historical kernel and BBP-visible kernel size are unchanged.
- Released consumers that need only the flat payload must validate and strip
  the final 16 bytes; `build/kernel.raw` is an internal build intermediate.
- Length validation does not replace a content-integrity checksum.
