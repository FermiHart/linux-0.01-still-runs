# Experience Fidelity Specification

This document defines what "fidelity" means for the Vesica Piscis artifact and
how it is enforced by two deliberate experience modes.

## Dimensions of fidelity

| Dimension | 1991 mode | alive mode |
|---|---|---|
| Kernel source | Historical Linux 0.01 with documented patches | Same |
| Boot path | Direct bEMU/KVM, no firmware | Same |
| Date source | Fixed historical reference date | Real CMOS date |
| Memory ceiling | Period-appropriate limit (e.g., 8 MiB) | Same unless overridden |
| Shell | Minimal built-ins using real syscalls | Same plus quality-of-life helpers |
| Filesystem | Real Minix v1 persistence | Same |
| Output style | Period Unix messages | Vesica Piscis MOTD and modern glyphs |
| Input | Raw scancodes, no host paste | Same |
| Network | None | None |
| Sound/graphics | VGA 80x50 text only | Same |

## 1991 mode

Goal: reproduce the closest possible feel of sitting in front of a 1991 PC
running Linux 0.01.

- Boot date fixed to a reference point (e.g., 1991-10-05).
- MOTD is the original era message.
- Prompt uses `/` as home and minimal path.
- No anachronistic quotes, Easter eggs or Unicode art.
- Commands fail with historically plausible error messages.
- `date`, `uptime`, `cal` report the fixed historical time.

## alive mode

Goal: demonstrate that the 1991 kernel is literally still running today.

- Real CMOS date and time (Y2K-corrected).
- Vesica Piscis MOTD, identity and checksum banner.
- Modern terminal glyphs where the 8x8 font supports them.
- Shell retains historical behavior; conveniences are cosmetic only.
- `linus` Easter egg remains available because it is documentation, not a
  modern feature.

## Invariants shared by both modes

The following must remain true regardless of mode:

- All filesystem operations go through real Linux 0.01 syscalls.
- All process creation uses the real scheduler and `fork`/`execve`.
- Pipes and redirection are handled by the kernel.
- `ps aux` shows the real task table.
- `sync` flushes the real Minix v1 superblock, inodes and zones.
- Reboot reads back the same bytes written before shutdown.

## What breaks fidelity

The following are considered regressions in either mode:

- A shell built-in that simulates a syscall instead of using it.
- Filesystem state that only lives in the shell process.
- A program that bypasses the kernel to read or write data.
- A fake `ps`, `mount`, `df` or `date` that returns invented output.
- Any claim that the system is original when patches are not documented.

## Testing fidelity

Each release must pass:

1. Boot to shell in both modes.
2. Create, read, write and delete a file, then reboot and verify.
3. Run `/bin/hello` as a real external process.
4. Use a pipe between two real programs.
5. Verify `ps aux` matches scheduler state.

## Future modes

Additional experience modes may be added only if they are documented here and do
not violate the shared invariants.
