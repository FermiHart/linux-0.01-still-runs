# Experience Fidelity Specification

This document defines the target meaning of "fidelity" for the Vesica Piscis
artifact. The historical mode is selected with `make run EXPERIENCE=1991`.
The alive mode is selected with `make run EXPERIENCE=alive` and is also the
default for `make run`. Both selectors are explicit in the bEMU and guest
contracts; there is no third transitional runtime mode.

## Dimensions of fidelity

| Dimension | 1991 mode | alive mode |
|---|---|---|
| Kernel source | Historical Linux 0.01 with documented patches | Same |
| Boot path | Direct bEMU/KVM, no firmware | Same |
| Date source | Fixed historical reference date (Wave 091) | Real CMOS date |
| Memory ceiling | Fixed 8 MiB | Fixed 8 MiB |
| Shell | Minimal built-ins using real syscalls | Same plus quality-of-life helpers |
| Filesystem | Real Minix v1 persistence | Same |
| Output style | Period Unix messages | Vesica Piscis MOTD and modern glyphs |
| Input | Raw scancodes, no host paste | Same |
| Network | None | None |
| Sound/graphics | VGA 80x50 text only | Same |

## 1991 mode

Goal: reproduce the closest possible feel of sitting in front of a 1991 PC
running Linux 0.01.

Implemented in Wave 089:

- Explicit Make and bEMU profile validation.
- A distinct `root-1991.img` containing a concise ASCII MOTD and period identity.
- Profile identity carried through the CRC-checked BBP command line.
- `HOME=/` and `EXPERIENCE=1991` supplied by init to the real shell process.
- The same 8 MiB machine, Minix v1 filesystem, syscalls, process model, pipes,
  redirections, and documented shell limits as the alive runtime.

Scheduled for Waves 091 and 095:

- Boot date fixed to a reference point (e.g., 1991-10-05).
- No anachronistic quotes, Easter eggs or Unicode art.
- Commands fail with historically plausible error messages.
- `date`, `uptime`, `cal` report the fixed historical time.

## alive mode

Goal: demonstrate that the 1991 kernel is literally still running today.

Implemented in Wave 090:

- `alive` is the validated Make, bEMU, BBP, init, image, and shell default.
- The alive image carries its own host-side marker and Vesica Piscis identity.
- Profile/image mismatch is rejected before KVM entry in either direction.
- `HOME=/home/fermihart` and `EXPERIENCE=alive` reach the shell through init.
- Legacy unmarked images remain accepted as alive images so existing writable
  research images are not made unusable by the profile marker.

Wave 092 separately validates and documents the real-time policy and complete
alive narrative.

- Real CMOS date and time (Y2K-corrected).
- Vesica Piscis MOTD, identity and checksum banner.
- Modern terminal glyphs where the 8x8 font supports them.
- Shell retains historical behavior; conveniences are cosmetic only.
- `linus` Easter egg remains available because it is documentation, not a
  modern feature.

## Required invariants for both modes

The following must remain true regardless of mode:

- All filesystem operations go through real Linux 0.01 syscalls.
- All process creation uses the real scheduler and `fork`/`execve`.
- Pipes and redirection are handled by the kernel.
- `ps aux` shows a bounded snapshot of real scheduler task slots.
- `sync` flushes the real Minix v1 superblock, inodes and zones.
- Reboot reads back the same bytes written before shutdown.

## What breaks fidelity

The following are considered regressions in either mode:

- A shell built-in that simulates a syscall instead of using it.
- Filesystem state that only lives in the shell process.
- A program that bypasses the kernel to read or write data.
- A fake `ps`, `mount`, `df` or `date` that returns invented output.
- Any claim that the system is original when patches are not documented.

## Current gaps

- `EXPERIENCE=1991` still uses the alive real-time RTC source until Wave 091.
- Cross-boot persistence is blocked by incomplete IDE write-completion IRQ
  delivery in bEMU; `sync()` can still block.
- `mount` reports the configured root mount because Linux 0.01 has no live
  mount-table interface; `ps` exposes at most 16 task slots.
- Guest halt/reset requests do not yet terminate or restart the bEMU host
  process, and they remain downstream of the blocking `sync()` path.
- Prompt and help remain shared while Wave 095 audits conveniences that should
  not appear in the historical profile.

## Future fidelity gate

Completion of Waves 089-095 must establish:

1. Boot to shell in both modes.
2. Create, read, write and delete a file, then reboot and verify.
3. Run `/bin/hello` as a real external process.
4. Use a pipe between two real programs.
5. Verify `ps aux` matches scheduler state.

## Future modes

Additional experience modes may be added only if they are documented here and do
not violate the shared invariants.
