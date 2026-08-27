# Artifact Reproduction Appendix

## Scope

This appendix is the shortest operational path from a normal Git clone to the
current academic tarball and its bounded validation gates. The historical
Linux-derived **i386 guest/kernel** executes through KVM on a **Linux/x86-64
host**. This is **not a port of the kernel to the x86-64 ISA**: bEMU is the
x86-64 host process, while the guest remains 32-bit i386.

Three commands answer different questions. The one-command build below creates
the current binary/documentation/data bundle. `make -j8 ci` tests the supported
behavior. `make verify-reproducible` compares two builds on one host and
toolchain. None of these commands alone is an external artifact evaluation.

## Prerequisites

Use a Linux/x86-64 host with a full Git history and the reference tools in
`docs/TOOLCHAIN.md`: GCC 13.3.0, Binutils 2.42 (including `readelf`), NASM
2.16.01, GNU Make 4.3, Python 3.12.3, Bash 5.x, util-linux with `fsck.minix`
2.39.3, Git, GNU tar, gzip, coreutils (`dd` and `sha256sum`), static libc
development files, and Linux KVM headers. The hosted i386 compiler-case cells
also need `-m32` multilib headers, startup objects, libraries, and host execution
support; this is separate from freestanding i386 kernel compilation.

`/dev/kvm` must exist and be readable and writable by the evaluating user. The
host must expose the KVM API and in-kernel irqchip capabilities used by bEMU.
There is **no supported fallback backend**. Nested or restricted virtualization
can pass a file-permission check and still fail a required KVM ioctl.

On Ubuntu 24.04, the hosted i386 path normally requires `gcc-multilib` and
`libc6-dev-i386` in addition to the packages in `docs/CONTAINER.md`. At this
revision, **make toolchain does not provision hosted multilib**; it may install
other packages or build a cross compiler and can require network and privilege.
The container path is not the primary procedure here because a complete
successful container run has not yet been retained.

## Clean clone

Clone the public repository normally, enter it, and verify that the checkout is
not shallow:

```bash
git clone https://github.com/fermihart/linux-0.01-still-runs
cd linux-0.01-still-runs
git rev-parse --is-shallow-repository
```

The expected answer is `false`. A shallow clone or source archive can compile,
but dataset validation needs historical Git objects named by the patch and trace
manifests. If the answer is `true`, obtain the missing history before proceeding:

```bash
git fetch --unshallow --tags
```

Record `git rev-parse HEAD` for the run. Start from a clean checkout. Release
products belong under `build/` and `release/`; ignored compiler intermediates are
also created beside historical sources and are removed by `make clean`.

Now run the preflight from the repository root:

```bash
make doctor
```

`make doctor` checks required command-line tools, freestanding i386 compilation,
hosted i386 compile/link/execute support, static PIE linking, KVM headers, and
`/dev/kvm` access. It is not a complete KVM-capability probe, environment capture,
or substitute for CI. Wave 113 will define an immutable evaluator package and run
envelope, so this appendix does not invent either.

## Behavioral validation

Run the broad clean-build regression gate separately:

```bash
make -j8 ci
```

This rebuilds and exercises documentation and dataset validators, host fixtures,
KVM boot, both experience profiles, shell and filesystem paths, BBP, traces,
compiler cases, sanitizers, and deterministic fault scenarios before writing
checksums. A zero status is the aggregate decision. Individual successful boots
also end with `[bemu-linux01] RESULT: PASS after <N> KVM exits` and reject known
kernel-fault markers.

CI is behavioral validation, not an immutable research-run bundle. Most logs and
disposable images are not retained, and the hosted GitHub workflow is a selected
matrix rather than a claim that every runner executes this exact local aggregate.
The clean phase means **CI removes build/REPRODUCIBLE.sha256** if an earlier
artifact build created it; for that reason, construct the final bundle only after
all cleaning gates below.

## Two-build verification

Run the actual two-build comparator independently:

```bash
make verify-reproducible
```

This copies the current working tree into two temporary locations, runs the
reproducible target in each, and compares their complete checksum manifests. It
therefore proves equality for **two copied-tree builds** on the same host and
toolchain. It does not perform two network clones and does not prove cross-host,
cross-distribution, or cross-linker byte identity.

`make reproducible` and `make verify-reproducible` are intentionally named here
at their implemented strength: the former makes one build; the latter performs
the two-build comparison. Verify the current main-tree manifest from the working
directory expected by its relative paths:

```bash
(cd build && sha256sum --check SHA256SUMS)
```

## One-command artifact build

After CI and the two-build comparator pass, reproduce and package the current
bounded artifact with one final Make invocation from the repository root:

```bash
SOURCE_DATE_EPOCH=1700000000 make reproducible artifact
```

The first goal performs **one deterministic build**, writes
`build/SHA256SUMS`, verifies its entries, and copies the manifest to
`build/REPRODUCIBLE.sha256`. The second goal creates
`release/linux-0.01-still-runs-<rev>.tar.gz`, where `<rev>` is the short Git
revision. Goal order matters: `make artifact` alone packages existing outputs and
does not build or test them.

The tarball contains four runtime outputs, the two build manifests, the `docs/`
tree, all three published datasets, `LICENSE`, and `README.md`. The embedded
`build/SHA256SUMS` covers the complete selected `ARTIFACT_NAMES` set, some of
which is not packaged; the **embedded manifest is not a bundle manifest**. The result bundle is
**not a self-contained source package**: source, root-level research documents,
Makefile, scripts, Dockerfile, and Git history remain in the clone. Preparing a
self-contained package and package-wide manifest belongs to Wave 113.

The current tar/gzip recipe does not normalize archive ordering, ownership, or
timestamps. Consequently, **outer tarball bytes are not claimed reproducible**.
The build payload manifests carry the current byte-reproducibility claim; the
outer digest recorded below is a **transfer-integrity hash** for that generated
file, not a cross-clone reference digest.

## Expected outputs

The one-command artifact build must leave these principal files:

| Path | Meaning |
|---|---|
| `build/kernel.bin` | Deterministic i386 kernel payload plus `L01KIMG1` trailer |
| `build/root.img` | Alive-profile Minix v1 image |
| `build/root-1991.img` | Historical-profile Minix v1 image |
| `build/bemu-linux01` | Linux/x86-64 KVM host runner |
| `build/SHA256SUMS` | Manifest of the selected build outputs |
| `build/REPRODUCIBLE.sha256` | Copy retained by the one-build reproducible target |
| `release/linux-0.01-still-runs-<rev>.tar.gz` | Current binary, docs, and datasets bundle |

Confirm live build self-consistency, inspect the tarball rather than trusting its
name, and retain an outer hash when transferring that exact file:

```bash
REV=$(git rev-parse --short HEAD)
(cd build && sha256sum --check SHA256SUMS)
tar -tzf "release/linux-0.01-still-runs-${REV}.tar.gz"
sha256sum "release/linux-0.01-still-runs-${REV}.tar.gz"
```

This generated manifest proves self-consistency of the just-built files; the
two-build target supplies the same-host comparison. It is not a commit-bound
reference manifest and cannot validate an extracted bundle whose omitted build
outputs are absent. Host-linked bEMU bytes can differ across distributions or
linker versions. The kernel and root-image byte claims are narrower than
arbitrary-host identity.

## Timing

All durations are planning **estimates, not guarantees**. A Wave 112 local run on
the LinuxMint x86-64/KVM development host measured 732.95 seconds for
`make -j8 ci`, 56.55 seconds for `make verify-reproducible`, and 16.00 seconds
for the final one-command artifact build. These values describe one loaded host
and the temporary reference-tool paths used for that run; they are not a
canonical performance result or a third-party measurement.

For planning, allow under one minute for `make doctor`, up to 20 minutes for CI,
and several minutes each for the comparator and final bundle. Shared or nested
KVM, CPU load, storage, sanitizer speed, and `-j` selection can change these
ranges. Evaluators should record their own measured duration with
`/usr/bin/time -p` and environment. Test `timeout` values, which range up to 180
seconds for individual subprocesses, are failure ceilings rather than expected
duration.

## Troubleshooting

| Symptom | Boundary and action |
|---|---|
| `/dev/kvm: Permission denied` or missing device | Grant the current user read/write access and confirm host virtualization; do not expect a software fallback. |
| KVM API, irqchip, guest-debug, or IRQ-state ioctl failure | The host or nested hypervisor lacks a capability used by the suite even if `make doctor` passed basic access. |
| `git rev-parse --is-shallow-repository` returns `true`, or a dataset reports a missing commit | Fetch full history with `git fetch --unshallow --tags`; a source archive has no historical Git objects. |
| Host static PIE probe or bEMU link fails | Install the host static libc development support required by `-static-pie`. |
| Hosted i386 case fails around `-m32` headers or linking | On Ubuntu 24.04 install `gcc-multilib` and `libc6-dev-i386`; a freestanding cross compiler does not replace hosted libraries. |
| `fsck.minix not found` | Install the util-linux package that supplies the independent `fsck.minix` oracle. |
| `make artifact` reports missing inputs | Run the complete one-command build above; `make all && make checksums` does not create `build/REPRODUCIBLE.sha256`. |
| `sync`, orderly shutdown, or a persistence experiment stalls | Stop treating that run as successful cross-boot evidence; see `docs/FS-LIMITATIONS.md`. |

## Known limits

- The i386 guest executes on a Linux/x86-64/KVM host; CPU virtualization and
  bEMU-modeled devices are not physical 1991 hardware equivalence.
- IDE write-completion delivery can leave guest `sync()` blocked, so
  **cross-boot persistence remains outside the successful boundary**.
- Record/replay reconstructs input and compares a filtered observable event
  projection; it is **not machine-state replay**.
- The published golden console and machine traces are separate alive-profile
  captures with incomplete original environment identity, and 97.399% of raw
  machine events are excluded by the default comparison policy.
- Two-build equality is currently bounded to one host/toolchain family; host ELF
  differences are possible elsewhere.
- The current `.tar.gz` metadata is not normalized, and its embedded build
  manifest does not cover every packaged file; package-wide reproducibility is
  reserved for Wave 113.
- **independent third-party reproduction has not yet occurred**; that belongs to
  Waves 114-115.
- **no DOI or archival deposit exists yet**; Zenodo archival and citation belong
  to Waves 116-118.
