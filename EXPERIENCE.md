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
| Date source | 1991-09-17 00:00:00 UTC boot epoch | Host UTC snapshot at boot |
| Memory ceiling | Fixed 8 MiB | Fixed 8 MiB |
| Shell | Small grammar and bounded interaction aids | Same grammar plus narrative commands |
| Filesystem | Real Minix v1 operations and orderly cross-process persistence | Same |
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

Implemented in Wave 091:

- CMOS boot date fixed to the Linux 0.01 release date, 1991-09-17 00:00:00 UTC.
- `date` and `cal` consume the kernel clock initialized from that real CMOS
  interface; no shell output is substituted or forged.
- The fixed epoch advances through the normal Linux 0.01 PIT and `jiffies` path.

Implemented in Wave 095:

- No anachronistic quotes, Easter eggs or Unicode art.
- Commands fail with historically plausible error messages.
- `fortune` and the retrospective `linus` presentation are available only in
  alive; 1991 resolves them normally and reports `not found`.
- `hello` and `yes` are external programs reached through `$PATH`, not bounded
  shell simulations. The historical `/bin/yes | head` close/SIGPIPE limitation
  is exposed rather than hidden by a terminating courtesy.

## alive mode

Goal: demonstrate that the 1991 kernel is literally still running today.

Implemented in Wave 090:

- `alive` is the validated Make, bEMU, BBP, init, image, and shell default.
- The alive image carries its own host-side marker and Vesica Piscis identity.
- Profile/image mismatch is rejected before KVM entry in either direction.
- `HOME=/home/fermihart` and `EXPERIENCE=alive` reach the shell through init.
- Legacy unmarked images remain accepted as alive images so existing writable
  research images are not made unusable by the profile marker.

Implemented in Wave 092:

- Real CMOS date and time, validated against the host UTC window and corrected
  for the two-digit CMOS year in the historical kernel.
- Vesica Piscis MOTD and identity, including an explicit statement that `date`
  reads Linux's kernel clock rather than profile-specific shell output.
- Modern terminal glyphs where the 8x8 font supports them.
- Shell retains historical behavior; conveniences are cosmetic only.
- `linus` Easter egg remains available because it is documentation, not a
  modern feature.

## Required invariants for both modes

The following must remain true regardless of mode:

- All filesystem operations go through real Linux 0.01 syscalls.
- All process creation uses the real scheduler and `fork`/`execve`.
- Pipes and redirection are handled by the kernel.
- `man` reads shared internal Unix manual pages from the real Minix v1 image.
- `ps aux` shows a bounded snapshot of real scheduler task slots.
- `sync` uses the real Linux 0.01 filesystem path; an orderly terminal halt
  flushes a disposable image before a fresh bEMU/KVM/RAM instance reads it.

`make test-experiences` runs complete, bounded sessions in both profiles. Each
command has unique transcript boundaries and independently proves identity,
kernel time, manual lookup, external processes, process visibility, pipes,
redirection, and a create/read/remove filesystem cycle. Profile-specific text is
also rejected from the other session.

## Guest surface guardrails

The guest remains a historical experiment rather than a small modern
distribution. These boundaries apply to both profiles:

| Surface | Policy |
|---|---|
| Package management | No package managers, repositories or installers |
| Network | No clients, servers, configuration tools or network stack claims |
| Language/build tools | No guest compiler, build suite or general-purpose runtime |
| Graphics | No desktop, display server or browser |
| Shell grammar | No variables, globbing, quoting, command substitution, command lists or background jobs |

The shell treats unsupported expansion syntax literally. It implements only
whitespace-separated arguments, foreground execution, pipes, and `<`, `>`,
`>>`. Bounded history, completion and line editing are interaction aids, not new
kernel capabilities. Alive may add current-time and retrospective narrative,
but not capabilities absent from 1991.

This policy does not apply to the host bridge: compilers, Python, containers,
KVM, sanitizers and test tooling are required to build and observe the artifact.
They must not be installed or surfaced as guest facilities.

## What breaks fidelity

The following are considered regressions in either mode:

- A shell built-in that simulates a syscall instead of using it.
- Filesystem state that only lives in the shell process.
- A program that bypasses the kernel to read or write data.
- A fake `ps`, `mount`, `df` or `date` that returns invented output.
- Any claim that the system is original when patches are not documented.
- A package manager, network facility, runtime, build suite, desktop or browser
  exposed inside either guest.
- Expansion syntax or background execution beyond the documented small shell
  grammar.

## Current gaps

- `mount` reports the configured root mount because Linux 0.01 has no live
  mount-table interface; `ps` exposes at most 16 task slots.
- A guest terminal halt now ends the current bEMU process, but the keyboard
  controller reset request does not restart the VM in-process.
- Persistence evidence covers bEMU's `MAP_SHARED` virtual medium after orderly
  `sync`; it does not establish controller-cache or physical-media durability.
- Bounded history, completion, editing and ANSI colors remain shared interaction
  aids; they do not add kernel or distribution capabilities.

## Fidelity gate

The implemented experience gate requires:

1. Boot to shell in both modes.
2. Create and sync a file, halt, then read its exact bytes in a fresh process.
3. Run `/bin/hello` as a real external process.
4. Use a pipe between two real programs.
5. Verify `ps aux` matches scheduler state.

## Future modes

Additional experience modes may be added only if they are documented here and do
not violate the shared invariants.
