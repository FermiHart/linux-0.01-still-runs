# Linux 0.01 engineering round: 25 evidence gates

Base: `e6076cb47fd27e1f6ce1b831852a1efe11de99c0`, branch `main`.
This increment was delivered as an uncommitted local source package. The
upstream archive, historical attribution and original licenses are preserved.
`baseline.json` freezes the 358 tracked paths before this increment.

## Evidence vocabulary

- **PASS**: the specified check executed and met its oracle at its named layer
- **FAIL**: executed and contradicted the oracle; retain the counterexample
- **BLOCKED**: not executed because a required capability is absent
- **PARTIAL**: some implementation/checks exist; the gate is not fully qualified

Host unit tests, abstract models, compilation and actual Linux 0.01 execution
are different evidence layers. A host PASS never upgrades a guest BLOCKED.
The original delivery host had no `/dev/kvm`; executing an i386 ELF directly also
gave `Exec format error`. Subsequent local KVM validation is recorded separately
in the `RESULTS.md` appendix. bEMU-NANO is the Linux-specific host runner adapted
from the author's shared bEMU implementation;
the system being studied remains Linux 0.01 in `kernel/`, `mm/`, `fs/`, `init/`.

## Gate plan

1. Freeze upstream archive and current source hashes
2. Separate historical behavior, existing port contracts and new experiments
3. Correct main-return to exit ABI, with a failing control
4. Correct dup2 same-descriptor and invalid-source behavior
5. Reject command echo and failed runner results as guest evidence
6. Audit inline assembly register, memory and condition-code contracts
7. Reproduce protected-O1 cases without declaring a compiler bug
8. Compile a freestanding i386 optimization matrix
9. Fix demonstrated source/ABI causes with minimal regressions
10. Bound ablation to declared fixes, retaining unresolved runtime cells
11. Implement a stateful bounded Minix operation model
12. Seed generation and minimize failing sequences
13. Exercise block, inode and descriptor exhaustion at declared layers
14. Prepare guest-driven semantic write-cut experiments
15. Independently inspect persistent directory, inode and payload state
16. Test pipe EOF, closed-reader and SIGPIPE behavior
17. Test wait, zombie, signal and descriptor-inheritance contracts
18. Check user-pointer range and length-overflow boundaries
19. Check page bounds and reference counts
20. Check COW/fork allocation-failure paths
21. Define measurable scheduler observations and bounded fairness assumptions
22. Translate segmented/paged guest instruction addresses before syscall tracing
23. Compare bounded checkpoint evidence without claiming full-machine replay
24. Define a typed experiment seam for the existing jash integration (not connected)
25. Independent review, repeatable checks, patch and complete source package

## Contract boundaries

The vendored 1991 tarball is the immutable historical reference. Existing port
behavior at the base commit is the control, including defects. This increment
changes only explicitly documented contracts; it does not claim POSIX coverage,
whole-kernel verification, production isolation, universal replay, or physical
storage durability. Existing published datasets remain immutable historical
observations rather than being silently regenerated from the new source.

Final results and exact reproduction commands are recorded in `RESULTS.md`.
