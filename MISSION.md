# Mission Statement

## What this project is

An executable archaeology experiment: Linus Torvalds' first kernel (Linux 0.01,
September 1991) booting and running on modern silicon through a deliberately
bounded modern bridge.

The goal is not to preserve every byte of the original source, nor to build a
modern distribution. The goal is to make the 1991 experience observable,
reproducible and academically defensible.

## What "fidelity" means here

Fidelity means preserving the **behavior, constraints and feel** of the original
system:

- Real Linux 0.01 syscalls, scheduler, VFS and Minix v1 filesystem.
- Real process creation, pipes and redirection through the kernel.
- Real hardware limits and assumptions from the era.
- Real boot without BIOS, UEFI or a traditional bootloader.

It does **not** mean:

- Byte-for-byte identity with the 1991 tarball.
- Running on physical 1991 hardware.
- Keeping every historical bug intact.
- Becoming a usable daily-driver operating system.

## What the modern bridge does

The bridge supplies only what 1991 hardware and toolchains no longer provide:

- A firmware-free KVM loader (`bEMU`).
- A checksummed boot handoff (`BBP`).
- A Minix v1 root-image forge.
- A cross/native toolchain that speaks modern GCC while respecting 1991 ABI.
- Automated tests, traces and reproducible builds.

Bridge claims are scoped to their documented tests, host requirements and
reproducibility limits.

## What we deliberately do not do

- No package manager.
- No networking for the sake of feature count.
- No modern desktop or browser.
- No competition with contemporary distributions.
- No aggressive modernization of the historical core.
- No hidden limitations or unproven claims.

## Long-term success criteria

These are completion criteria for the full artifact, not claims that every item
already works:

1. `make -j8 ci` passes from a clean clone on a supported Linux/KVM host.
2. The kernel boots, reaches a shell and passes the full smoke suite.
3. Every historical change is recorded in the porting ledger.
4. Builds are reproducible byte for byte on the same toolchain.
5. The filesystem persists real writes across reboot.
6. Every claim about compilers, hardware or behavior is backed by evidence.
7. The artifact can be reproduced independently by a third party.

## Academic intent

This project exists to ask and answer concrete research questions:

- Which assumptions in Linux 0.01 became invalid on modern hardware and compilers?
- What is the minimum set of adaptations required to execute it today?
- How do modern compiler optimizations interact with GNU89-era C and inline assembly?
- How can we measure behavioral fidelity in software archaeology?
- Can a historical operating-system experience be reproduced deterministically?

All findings, failures and fixes are published as part of the artifact.
The operational scopes, measures, answer criteria and non-claims for these five
questions are defined in `docs/RESEARCH-QUESTIONS.md`.
The implemented, partial and proposed procedures are distinguished in
`docs/METHODOLOGY.md`.
