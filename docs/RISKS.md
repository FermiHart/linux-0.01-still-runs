# Project Risks and Invariants

## Invariants

These must remain true across all waves. A wave that violates an invariant is
blocked until the conflict is resolved.

1. **Historical core identity**: `init/`, `kernel/`, `mm/`, `fs/`, `lib/` and
   `include/` remain recognizable as Linux 0.01 unless a patch is documented in
   the porting ledger.
2. **Boot without firmware**: `bEMU` enters the kernel directly through
   Linux/KVM without loading BIOS, UEFI or a third-party bootloader.
3. **Syscalls are real**: every user command that can use a Linux 0.01 syscall
   must do so; simulation is allowed only when the syscall is genuinely absent.
4. **Tests are green**: `make -j8 ci` passes on the reference host before any
   wave is marked complete.
5. **Private roadmap stays private**: `.local/` and `AGENTS.md` are never
   committed.
6. **Author identity**: every public commit uses
   `F E R M I ∞ H A R T <contact@fermihart.com>`.

## Known risks

| Risk | Impact | Mitigation | Owner wave |
|---|---|---|---|
| GCC optimization cases are UB, not compiler bugs | We would misattribute historical behavior | Investigate with disassembly and reproducers | 075–083 |
| Real Minix v1 persistence breaks existing shell assumptions | Userland tests fail | Stage persistence work behind feature flag, update tests | 026–040 |
| KVM behavior differs across host CPUs/kernels | Non-reproducible boot or tests | Document reference host, test matrix, record/replay | 024, 063–074 |
| bEMU monolith is hard to test | Bugs in device emulation | Modularize and add unit tests | 041–054 |
| Guest RAM or kernel placement exceeds a host mapping | Host crash or corrupted handoff before boot | Checked half-open ranges, fixed allocation and pre-KVM loader tests | 096 |
| Toolchain ages or disappears | Builds no longer reproducible | Pin versions, archive tarballs, container digests | 016–025 |
| Over-ambitious scope creep | 120 waves become unfinishable | Reject features not in roadmap; use discovery waves sparingly | Programa todo |
| Loss of local roadmap files | Project context disappears | Backup `.local/` separately, checksums, agent protocol | Continuo |

## Risk acceptance criteria

- A risk is **owned** when a wave is assigned to address it.
- A risk is **mitigated** when the wave is complete and evidence is recorded.
- A risk is **accepted** only by explicit user decision and must be documented
  in the journal.
