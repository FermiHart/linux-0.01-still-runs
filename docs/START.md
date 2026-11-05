<!-- Author: F E R M I ∞ H A R T <contact@fermihart.com> -->
<!-- SPDX-License-Identifier: Unlicense -->

# Run Linux 0.01 today

A restored Linux 0.01 i386 guest, running through a small firmware-free KVM
bridge on a Linux x86-64 host. This is executable software archaeology, not a
modern distribution, an unmodified historical binary, or a security sandbox.

## Start

From this source tree, with GCC, binutils, NASM, Make, Python 3.12+ and usable
`/dev/kvm`:

```sh
make all
make run
```

Use `make toolchain` to check prerequisites and install missing build packages
on supported package managers; inspect its package actions before running it.
On Arch Linux it instead prints the supported full-upgrade command for your
administrator to review. Do not run the guest as root just to bypass KVM device
permissions. There is no supported non-KVM execution fallback.

## Keep your work

Inside the guest:

```sh
mkdir notes
echo hello > notes/first
sync
halt
```

Run `make run` again and read `notes/first`. Your disk is
`state/alive/default.img`; `make clean` clears tools and generated bases, not
this session. Back up the disk while the guest is stopped.

```sh
make run SESSION=work       # a separate persistent disk
make run EXPERIENCE=1991    # separate historical-profile disk
```

The historical profile starts its clock in September 1991; the default alive
profile starts from the host's UTC snapshot. Each profile then advances through
the guest clock. A new session starts from the current generated base. Existing
sessions keep their files and guest programs across rebuilds.

Old build-owned disks are recovered before replacement or cleanup. See the
[disk lifecycle](FS-EXPERIENCE.md#guest-disk-lifecycle) for paths and migration.
Direct runner `--root FILE` selects a writable disk: use a session or a copy.

## Downloads and trust

The [source delivery guide](DELIVERY.md) covers self-contained snapshots and
source-bound candidates. An extracted candidate's `./run` launcher creates a
persistent session without installing tools or changing KVM permissions.

The historical `v0.1` ISO uses Limine/QEMU and is not this bEMU/KVM edition.
Source, runner and disk images must belong to the same qualified edition. Check
the supplied manifest before running a binary package. A checksum detects
changed bytes; it does not independently authenticate a publisher.

The [reproduction guide](REPRODUCTION.md) documents the full checks and limits.
`make test-host-safety` checks input preservation, disk lifecycle and host
orchestration. `make test-fs-persistence` boots both profiles and verifies files
across fresh runner processes. Analysis tools that are unavailable are reported
as SKIP, not PASS; provenance gaps are reported as PARTIAL, not cleared.

## Attribution and limits

Linux 0.01 is Linus Torvalds's 1991 work. The bridge and restoration have their
own attribution boundaries. The original Linux 0.01 terms are not simply GPL
and include source-availability and no-fee redistribution conditions. Read the
[license](../LICENSE), [authorship](AUTHORSHIP.md) and
[component notices](../evaluation/v1/THIRD-PARTY-NOTICES.md), including bEMU-NANO's
shared bEMU lineage and the separate third-party text rights limits.

Guest `sync` plus orderly halt is tested on a virtual medium; physical-media
durability and arbitrary crash recovery are not promised. Producer-controlled
tests do not replace independent external reproduction.
