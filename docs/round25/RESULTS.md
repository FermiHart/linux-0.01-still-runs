# Results and limits: engineering rounds 1–25

This increment is based on main `e6076cb47fd27e1f6ce1b831852a1efe11de99c0`.
It was delivered as an uncommitted source package, without a push, pull request,
fork or publication. The per-round ledger below records that delivery host's
results. Subsequent local validation is recorded in the appendix at the end;
the upstream archive and original attribution are preserved.

## What changed

Production fixes cover the C runtime exit argument; dup2 validation/order;
bitmap and descriptor inline-assembly contracts; zero-progress broken-pipe
errors; readable user-buffer bounds and overflow-safe writable-range walking;
read-length clamping; managed physical-page bounds/refcount underflow; and cleanup of an allocated
but unmapped data page when page-table allocation fails during a page fault.
The host syscall observer now fetches instruction bytes through CS.base and
KVM linear-to-physical translation, independently across page boundaries.

The runner can trigger its existing IDE cut boundaries from guest writes.
Crash mode requires `--power-cut-copy NEW_FILE`: it creates that file with
O_EXCL and maps the copy, leaving the input image read-only. Existing files and
symlinks are rejected. This protects trusted local experiment directories;
it is not a defense against hostile concurrent path replacement. A reached cut
exits with code 3, never the ordinary guest PASS status.

The existing filesystem and syscall integration oracles were tightened.
Readback requires isolated command output, exact payload lines and validated
boundaries. Trace success requires successful runner termination, no kernel
fault, a boot event, read/write syscall events and successful final shutdown.

## Per-round ledger

“Local PASS” names the executed layer. Guest qualifications below are all
BLOCKED by absent `/dev/kvm`. This is not 25 completed guest-qualified waves.

| Round | Local result | Remaining qualification |
|---|---|---|
| 1 | PASS: official vendored archive checksum and 358 baseline path hashes | None for local reference freeze |
| 2 | PASS: historical/control/treatment and evidence-layer contracts documented | External historical verification beyond the retained archive is not claimed |
| 3 | PASS: assembled crt0 regression red then green; EBX receives main's result | Actual main→wait status in Linux 0.01 BLOCKED |
| 4 | PASS: extracted production dup2 tests at O0/O1/O2/Os, including fd exhaustion | Actual guest descriptor lifecycle BLOCKED |
| 5 | PASS: echo-only, missing/corrupt/duplicate readbacks and trace termination/event mutants rejected | Live guest oracle qualification BLOCKED |
| 6 | PASS for selected bitmap and descriptor asm: memory, registers, flags and neighboring bytes checked | PARTIAL whole-tree audit; unrelated asm remains unaudited |
| 7 | PASS: original bitmap/descriptor regressions retained; original O1 shields kept | Buffer/vsprintf runtime causes unresolved; no compiler-bug claim |
| 8 | PASS: treatment 32/32 freestanding i386 compile cells; baseline 31/32 | Guest O0/O1/O2/Os execution BLOCKED; one GCC version only |
| 9 | PASS: demonstrated source/ABI fixes and production-body regressions | Guest integration BLOCKED |
| 10 | PASS: exhaustive eight combinations of three declared fixes; only all-enabled passes | No global minimum claim; no guest ablation |
| 11 | PASS: bounded abstract namespace, hard-link and resource model | PARTIAL kernel-to-model refinement; atomic ENOSPC writes are an explicit abstraction |
| 12 | PASS: 64 seeds × 200 operations, deterministic replay; deletion-minimal reducer test | No actual kernel counterexample minimized yet |
| 13 | PASS: model inode/block/fd exhaustion and production dupfd exhaustion | Guest exhaustion and all resource rollback paths BLOCKED |
| 14 | PASS: existing host IDE phase matrix, crash-copy and CLI tests; guest driver added | Guest-driven data/metadata cuts BLOCKED; no reboot-recovery claim |
| 15 | PASS: separate Python reader and C minix-inspect on real mkimage output; exact payload checks | Guest-created persistence/reboot qualification BLOCKED |
| 16 | PASS: production pipe body with controlled wait/close stubs, EOF, SIGPIPE, EPIPE and partial writes | True scheduling interleavings and `yes | head` remain unqualified |
| 17 | PASS: production wait body, reap-once, null status, WNOHANG, groups, interruption | PARTIAL signal-delivery and inheritance coverage; guest lifecycle BLOCKED |
| 18 | PASS: production range body with host-width UBSan plus explicit 32-bit arithmetic model; write dispatch independently reviewed | Actual segmented reads/page faults BLOCKED; no all-syscall-pointer claim |
| 19 | PASS: production free/put-page bounds and refcount underflow checks | Other page-table/refcount paths remain outside this bounded test |
| 20 | PASS: production COW/copy_mem/do_no_page control flow under explicit allocator/copy stubs; page-table OOM leak reproduced and fixed | No physical-page leak, TLB or real fork isolation proof |
| 21 | PASS: production schedule/do_timer bodies; 600 modeled user ticks yield 100/200/300 for priorities 1/2/3 | No real-time latency, guest throughput or universal fairness result |
| 22 | PASS: segmented, cross-page, invalid-translation/bounds fetch tests; runner builds | Live KVM observation BLOCKED; translation failure omits an event and is not a synthetic syscall |
| 23 | PASS: fail-closed selected-state checkpoint comparator and mutation tests | PARTIAL: no checkpoint producer, snapshot restoration or machine replay implemented |
| 24 | PASS: typed bounded JSON schema, safe command rendering, retained result protocol and negative tests | jash integration is a file seam only; jash source/connection unavailable |
| 25 | Independent read-only review plus local reproduction/package gates | Guest acceptance and external reproduction remain BLOCKED |

## Exact evidence layers and assumptions

`tests/round25/test_contracts.py` reads actual production function bodies/macros
from the working tree. Harness declarations replace kernel globals and external
services explicitly. The C runs on the x86_64 host with GCC 14.2.0; it does not
execute Linux 0.01. `unsigned long` is 64-bit in these harnesses. The separate
I386RangeModel checks the 32-bit wrap boundary as an independent arithmetic
model, while the freestanding compiler matrix checks actual `-m32 -march=i386`
translation units. None substitutes for guest execution.

The filesystem model has reusable bounded inode slots and retains directory
allocation high-water marks. `namespace_references` counts modeled path aliases;
it is not the Minix directory `i_nlinks` field. File writes are atomic on modeled
ENOSPC; the historical kernel may partially write. The model counts direct,
single-indirect and double-indirect blocks but is not a disk allocator or crash
recovery model. No model inode number is compared directly with a guest inode.

The independent reader supports Minix v1, 14-byte names, 1 KiB zones, holes,
single and double indirection. This inspector is limited to 128 MiB images
and 8 MiB individual payloads. It is a bounded read-only payload oracle, not a
replacement for the existing structural bitmap/link-count audit. Its exact-byte
checks expose corruption that a structural audit alone can miss.

The scheduler harness uses three permanently runnable tasks and a stubbed
context switch, with equal simulated user ticks. Host wall time is not guest
elapsed time, and logical KVM-exit counters are not retired-instruction clocks.

The paired compile matrix snapshots **baseline headers separately**, preventing
new asm fixes from contaminating the baseline. The baseline fork O0 compile
fails with impossible TSS/LDT asm constraints; the treatment compiles at all
four levels. No optimization shield is removed without real guest evidence.
The three-group ablation concerns only crt0, dup2 and bitmap source contracts.

## Reproduction

From the source tree:

```sh
make test-round25
make test-round25-matrix
make kernel build/bemu-linux01
python3 tests/round25/experiment.py tests/round25/example-experiment.json \
  --output build/round25/local-guest-run
```

The output directory must not exist: old evidence is not silently overwritten.
The example returns 77 and records BLOCKED if `/dev/kvm` is absent. When it can
run, stdin is closed, input is bounded, the source image is hashed, all guest
writes use a private copy, and exact bytes plus the complete `/tmp/r25` namespace
and hard-link equivalence are inspected after terminal guest HLT. Crash specs
measure whether the requested IDE boundary was reached; semantic differences
are observations, not an invented recovery success.

NASM was initially absent, and the first `make all` stopped at update.asm.
The official [NASM 2.16.03 source](https://www.nasm.us/pub/nasm/releasebuilds/2.16.03/)
was then downloaded and built inside the workspace, with no OS installation or
security changes. Archive SHA-256:
`1412a1c760bbd05db026b6c0d1657affd6631cd0a63cddb6f73cc6d4aa616148`.
`make NASM=<workspace-built-nasm> all` subsequently PASSED. The full kernel,
bEMU, all userland programs and both canonical root-image profiles build.
Both images pass the C structural audit and independent exact inspection of
all six ZMAGIC program payloads. The earlier host-oracle image is retained as
an offline fixture, not as guest boot evidence. NASM configuration/build and
both initial/final project build logs remain in the evidence archive.

The existing ASan power-cut executable reaches all test assertions but its
LeakSanitizer teardown fails because this execution host uses ptrace. The
ordinary power-cut binary passes. LeakSanitizer was not disabled to manufacture
a green aggregate result. KVM and native i386 execution were not enabled by
changing host security settings.

## Evidence retention

`build/round25/` contains command logs, the paired compiler objects/disassembly,
all eight ablation results, scheduler observations, and the BLOCKED guest result.
The delivery evidence archive preserves those files separately from source.
Pre-fix logs are retained as historical observations. Some early failed harness
attempts also exposed fixture mistakes; the authoritative paired ablation and
final aggregate logs distinguish source failures from harness setup failures.
Existing published versioned datasets are unchanged.

## Local KVM validation: 2026-09-30

The delivery patch applied cleanly to the GitHub `main` base above. Before local
adjustments, the reconstructed tree exactly matched all 379 packaged source
files, and every entry in the package's `SHA256SUMS` verified.

This validation host has usable `/dev/kvm`, Linux 7.0.0-30-generic, GCC 13.3.0,
binutils 2.42, NASM 2.16.01 and Python 3.12.3. Hosted i386 dependencies were
extracted locally from the Ubuntu `lib32gcc-13-dev`, `lib32gcc-s1`, `libc6-dev`,
`libc6-dev-i386` and `libc6-i386` packages. A temporary GCC wrapper supplies the
sysroot, startup objects, loader and library paths for hosted `-m32` tests;
freestanding kernel compilation uses the native compiler unchanged.

| Check | Local result |
|---|---|
| `make doctor` with the local multilib toolchain | PASS, including hosted i386 execution and KVM access |
| `make all` | PASS: kernel, userland, root image and bEMU |
| `make test-round25` | PASS: 35 host tests |
| `make test-round25-matrix` | PASS: treatment 32/32, baseline 31/32, expected all-enabled-only ablation success |
| `make test` with the local multilib toolchain | PASS: complete aggregate, including real boot, normal/interactive shell, traces, both experience profiles and cross-process persistence |
| `make test-fs-write test-fs-mkdir test-fs-link test-fs-large test-fs-property test-fs-inspect test-fs-real` | PASS |
| `make test-sanitized` | PASS: boot with the default UBSan runner |
| ASan/UBSan BBP and IDE power-cut executables in `make test` | PASS with their default sanitizer settings |
| `make verify-reproducible` | PASS: two fresh builds have byte-identical artifact manifests |
| Round25 example experiment | PASS: orderly guest halt, exact payload/namespace/hard-link inspection and unchanged source image |
| Guest-driven cuts at inode bitmap LBA 5 and payload LBA 175 | PASS: all four requested phases reached at each LBA; each runner returned the dedicated status 3 |

The ordinary guest experiment used the delivered `minix-link-persistence` spec
with seed 25001. At LBA 5, all four cut images lacked the final `/tmp/r25`
namespace. At LBA 175, accepted/payload cuts lacked the final file payload,
whereas committed/IRQ cuts matched the final namespace and payload. These are
bounded post-cut observations, not reboot recovery or durability proofs.

The retained historical `bitmap_inline_asm/x86_64/O2` compiler reduction still
fails intentionally. Likewise, the baseline fork O0 compile and seven disabled
fix combinations remain failing controls. Those observations are distinct from
the passing treatment and aggregate test targets.

Local testing exposed a false negative in the new filesystem readback test:
Python text-mode capture expanded serial CR/CRLF into extra newlines. Capturing
bytes until terminal sanitization fixed it; live guest readback and the existing
negative oracle tests both pass. The compiler matrix now labels guest execution
`NOT_RUN: compile-only matrix` rather than hardcoding absent KVM. CI also runs
the Round25 host contracts and freestanding compiler matrix.

The first aggregate attempt lacked hosted i386 headers. After local dependency
setup, a second attempt reached an outer command timeout. The final aggregate
was run with a longer outer limit and completed successfully. Earlier failed
and interrupted logs are retained alongside the final evidence.

These checks qualify the named default-build guest paths on this host. They do
not complete every remaining qualification in the original 25-round ledger,
including whole-tree asm auditing, guest optimization/ablation grids, arbitrary
resource exhaustion, checkpoint replay or an actual jash connection.
