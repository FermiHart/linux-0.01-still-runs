# Experimental Methodology

This document defines how the questions in `docs/RESEARCH-QUESTIONS.md` are to
be investigated and how current evidence may be reported. It distinguishes the
procedures already encoded in the repository from incomplete or future designs.
It does not convert a regression suite into evidence that was never retained.
The resulting RQ1-RQ5 evidence synthesis is published in `docs/PAPER.md`.

## Status vocabulary

- `IMPLEMENTED`: an executable target and oracle exist with the stated inputs
  and decision rule.
- `PARTIAL`: useful executable evidence exists, but a required control,
  repetition, cross-product, causal link, or retained output is absent.
- `PROPOSED`: the design is declared here but no repository target implements
  it yet; it must not be reported as an observed result.

Status applies to a procedure, not an entire research question. One question
may combine all three statuses.

## Experimental environment

The reference tool versions are documented in `docs/TOOLCHAIN.md`, and the
container base and packages are declared in `Dockerfile`. This controls the
intended toolchain but does not prove that an individual run used that container.

| Variable class | Current treatment |
|---|---|
| Source baseline | Upstream tarball SHA-256 and current Git tree are documented. |
| Build inputs | Kernel ABI/flags and `SOURCE_DATE_EPOCH` are explicit. |
| Machine contract | Linux/x86-64/KVM, 8 MiB RAM, bEMU devices, BBP and fixed root geometry. |
| External oracle | util-linux `fsck.minix` reference version is documented. |
| Unfixed host state | Kernel build, CPU/microcode, KVM capabilities, nesting, load and scheduling. |
| Usually unretained | Full argv/environment, executable hashes, dirty state, durations and raw logs. |

Every published observation must name the full Git commit, dirty state,
toolchain paths/versions, host OS/kernel, CPU identity, KVM availability and
capabilities, locale/timezone, `SOURCE_DATE_EPOCH`, Make parallelism, and whether
the declared container was used. Existing `make doctor`, `make provenance`, and
`make audit` expose parts of this context but do not retain one coherent run
manifest.

## Common run envelope

`PROPOSED`: each research run should receive an immutable ID and directory that
contains an environment manifest, input hashes, exact commands, stdout, stderr,
exit status, duration, output hashes, and a final manifest. Commands run in the
predeclared order, stop according to the question's rule, and never overwrite a
prior run. All predeclared cells, including failed and missing cells, remain in
the result index.

No aggregate RQ runner currently enforces this envelope. The command
lists below describe current entry points, not proof that their outputs were
captured together. `make -j8 ci` is an `IMPLEMENTED` broad regression gate, but
its terminal output and generated evidence are not a durable research bundle.
Selection of only passing commands after execution is not permitted in a
published result.

The common logical order is:

1. Identify source, environment, question, procedure status, and planned cells.
2. Hash immutable inputs and create isolated output locations.
3. Execute negative/baseline controls before adapted or treatment cells where
   a causal comparison is claimed.
4. Execute all fixed matrix cells in canonical order.
5. Apply the predeclared normalization and decision rule.
6. Retain failures, missing cells, exclusions, raw evidence, and hashes.
7. Report only at the strongest status supported by the completed controls.

## RQ1 - Invalidated assumptions

**Current status: `PARTIAL`.** The intended unit is one
assumption/adaptation pair. `make provenance` and `make audit` compare the
current historical core to the pinned upstream source; `make doctor` probes the
current host; `make test` exercises the fully adapted state. The durable
interpretation is in `docs/PORTING_LEDGER.md`, while `tests/test_boot.py` defines
the principal boot milestones. Wave 108 newly retains 53 source-path deltas,
their hashes/modes, 19 stable adaptation IDs and nine unresolved ledger joins in
`datasets/patches/MANIFEST.json` and `datasets/patches/file_deltas.csv`.

Implemented controls include the upstream hash, current flags, fixed bEMU
machine contract, required boot markers, zero process status, and rejection of
recognized kernel-fault output. The current procedures do not bind a ledger
entry, diff hunk, host probe, baseline failure, and adapted result under one
observation ID. Most entries therefore establish adapted-state conformance, not
an isolated causal comparison.

`PROPOSED`: assign stable assumption/adaptation IDs, declare dependencies and
the expected baseline failure before execution, build baseline and adapted
states in the same captured environment, run the same focused oracle, repeat
runtime comparisons under a declared count, and retain both outcomes. Classify
as proven invalidation only when the baseline repeatedly fails the predeclared
contract and the dependency-equivalent adapted state passes. Otherwise use
qualified, under investigation, or not reproduced.

## RQ2 - Adaptation-set minimality

**Current status: `PARTIAL` for sufficiency and `PROPOSED` for minimality.**
The current unit is one complete configuration or one malformed input against
that fixed configuration. `make test-quick`, `make test-bemu-loading`,
`make test-artifact-truncation`, and `make bbp-conformance` establish one
sufficient observed configuration and its loading/BBP boundaries. The stable
adaptation IDs in `datasets/patches/adaptations.csv` describe historical ledger
groups, not a predeclared candidate universe, and do not vary membership.

No candidate universe, dependency graph, subset generator, configuration ID,
ablation matrix, or per-configuration cost record exists. The historical ledger
also mixes compatibility and experience changes and does not enumerate all
modern bridge components.

`PROPOSED`: predeclare candidate IDs in historical-core, bridge, and
experience-only strata; record dependency and alternative edges; generate
dependency-valid configurations reproducibly; and measure the same clean-build
and boot-boundary vector for each selected configuration. Report sufficient,
inclusion-minimal, cardinality-minimum, cost-minimum, or smallest-observed only
under the criteria in the research-question document. A minimum claim requires
exhaustive exclusion or a justified proof over every smaller configuration in
the declared universe.

## RQ3 - Compiler experiments

**Current status: `PARTIAL`.** The versioned dataset in
`datasets/compiler-cases/v1/` retains 18 published cells: three reductions, two
hosted GNU/Linux ABIs, and `-O0`/`-O1`/`-O2`, each run once with one identified
GCC 13.3.0 executable. Seventeen pass; only the x86-64 `bitmap_inline_asm -O2`
cell fails. Its identity and cells are in
`datasets/compiler-cases/v1/MANIFEST.json`,
`datasets/compiler-cases/v1/observations.jsonl`, and
`datasets/compiler-cases/v1/classifications.json`. The live harness in
`tests/compiler-cases/Makefile` supplies `make compiler-cases`, `make compare-assembly`, and
`make compiler-audit` remain transient investigation targets. Separately,
`make compiler-matrix` discovers command names and runs nine x86-64 cells per
name. These experiments are not a compiler-version/ABI cross-product.

The observation unit is one compiler identity, reduction, ABI, optimization,
and instrumentation condition. The published reference grid retains normalized
full argv, compile and runtime status/output, compiler/ABI/tool identities,
executable hashes and payloads, and full compiler-generated assembly. The sole
assembly normalization replaces the ephemeral extracted-sysroot prefix with
`${MULTILIB_ROOT}` in comments and removes trailing horizontal whitespace. It has
zero identical repetitions and does not retain the separate diagnostic,
sanitizer, extracted-diff, or compiler-name matrix runs. Those generated files
remain ignored, compiler aliases are not deduplicated there, and those transient
artifacts are not inputs to the published classifications.

Attribution requires a reproduced behavior difference, a relevant generated
code/dataflow difference, and a language or GNU inline-assembly contract
analysis. Sanitized and unsanitized cells remain separate because instrumentation
can change manifestation. Without those links, report ABI-sensitive
manifestation or historical hypothesis, never an inferred GCC bug.

`PROPOSED`: expand beyond the one published compiler identity into a predeclared
unique compiler binary/hash x reduction x ABI x optimization cross-product,
retain repeated outcomes and diagnostic/sanitizer conditions separately, and
derive any broader attribution only from those added observations.

## RQ4 - Behavioral fidelity

**Current status: `IMPLEMENTED` as multidimensional conformance, with
`PARTIAL` retention and repetition.** The dimensions are reported separately:

| Dimension | Current entry point | Unit and current repetition |
|---|---|---|
| Profile identity, time, processes, shell and guardrails | `make test-experiences` | one session per profile; command segments are distinct cells, not repeats |
| Static Minix structure | `make test-fs-inspect` | one alive-image audit |
| Observable record/replay path | `make test-trace-workflow` | one record and one replay |
| Bounded fault responses | `make fault-test` | fixed catalog; mostly one execution per vector |

Experience sessions use unique transcript boundaries, required and forbidden
observations, profile mismatch controls, fixed historical RTC input, and a
bounded alive UTC window. Transcript control sequences and echoed marker
commands are normalized by `tests/test_experience.py` before comparison. The
external `fsck.minix` and the repository's independent Minix inspector strengthen filesystem observations,
but ordinary successful session transcripts and post-session filesystem states
are not retained.

A dimension passes only when every predeclared conjunctive assertion passes.
Dimensions are not averaged or weighted into an authenticity score. “Feel” is
not a measured variable, and one scripted session is not a user study or a
physical-1991-machine comparison.

Wave 109 publishes one inherited alive-profile console transcript and one
separate alive-profile machine trace under
`datasets/golden-traces/v1/MANIFEST.json`; the machine payload is
`datasets/golden-traces/v1/alive-boot-machine.jsonl`. Their capture environments
are incomplete, they do not share a run ID, and they do not add a second profile
or user observation.

## RQ5 - Reproducibility layers

**Current status: mixed.** Reproducibility is reported per layer, never as one
global deterministic-runtime claim.

| Layer | Status | Current procedure and repetition | Exact decision rule |
|---|---|---|---|
| Build artifacts | `IMPLEMENTED` | `make verify-reproducible`; exactly two independent build directories on one host | complete SHA-256 manifests are byte-identical |
| Initial RTC conversion | `IMPLEMENTED` unit contract, `PARTIAL` runtime claim | `make test-rtc`; one conversion per controlled profile/input | exact BCD register values |
| Observable trace | `PARTIAL` | `make compare-trace`; one golden-versus-replay comparison | positional equality after declared normalization/filtering |
| Fault outcomes | `IMPLEMENTED` fixed vectors, mostly `PARTIAL` repetition | `make fault-test`; Wave 103 has two repeats per profile/scenario | exact statuses/state, bytes, IRQ counts and hashes |

The double-build procedure is implemented by
`scripts/verify-reproducibility.sh`; its two temporary trees share one host and
toolchain and are deleted after their SHA-256 manifests are compared.

Trace comparison removes logical timestamps, KVM exit counts, and shutdown exit
counts. The standard workflow also excludes all IRQ events and I/O ports
`0x71`, `0x60`, `0x61`, `0x3d4`, `0x3d5`, and `0x1f0`. Remaining event count,
order, type, and payload must match exactly. `tests/compare_trace.py` implements
the comparator; replay reconstructs scripted input, not complete machine state.
For the published inherited machine trace, this policy filters 22,917 of 23,529
raw events and retains 612. Publication makes that boundary and normalized hash
durable; it does not strengthen the procedure beyond `PARTIAL`.

The power-cut image procedure in `tests/test_power_cut.py` is the only current
fault path with identical scenario repetition: each of eight scenarios for each
profile runs twice and must preserve its expected 0/512/1024-byte prefix, IRQ
count, and state hash. Sanitized versus optimized execution is a configuration
comparison, not a repeat.

## Oracle independence

Oracles are classified by the layer they observe:

1. External independent: util-linux `fsck.minix`.
2. Repository-independent implementation: `tools/minix-inspect.c` versus guest
   filesystem code.
3. Production integration: production bEMU process, KVM irqchip, BBP consumer,
   or generated artifact exercised by a separate harness.
4. Production-linked white-box: bridge source linked into a fixture with exact
   state assertions.
5. Self-report: guest or bridge transcript checked without an independent state
   oracle.

Claims must name the oracle class. KVM line/PIC state does not prove guest
handler entry; clean filesystem metadata does not prove correct file content;
CRC64 does not authenticate the producer; a transcript does not prove every
underlying mechanism without focused trace or independent evidence.

## Evidence retention

Currently versioned evidence includes source, tests, specifications, golden
traces, fault catalog, the Wave 108 source-delta dataset, the Wave 109 inherited
trace dataset, and the Wave 110 compiler-case dataset with 18 newly retained
hosted observations. The
patch dataset records zero paired RQ1 observations and zero RQ2 ablation
configurations. The trace dataset records incomplete capture identities and two
separate legacy runs rather than a new controlled repetition.
Generated `build/` reports, successful transcripts, temporary images, replay
traces, power-cut hashes, sanitizer logs, and double-build artifacts are usually
overwritten or deleted.

`PROPOSED`: the common run envelope retains immutable raw and normalized outputs
plus manifests. Waves 108-110 now curate stable bounded subsets, but only Wave
110 contains newly executed cells; the patch dataset has no paired experiment
logs and the traces are inherited. The common run envelope is therefore
`PROPOSED`, not implemented across the research program.

## Analysis and reporting rules

- These are fixed deterministic conformance matrices, not random population
  samples. No inferential statistics, confidence intervals, or probability of
  success over arbitrary hosts is inferred.
- Report the number of planned, passed, failed, skipped, and missing cells. A
  fail-fast aggregate may be a regression gate, but publication must retain
  failed and missing cells instead of hiding later unexecuted cases.
- Keep baseline and treatment, optimized and sanitized, ABI, profile, oracle
  layer, and repeat index as distinct variables.
- Declare all normalization, filters, tolerances, timeouts, locale controls, and
  excluded fields before comparison.
- Preserve negative results and “not reproduced” classifications. Do not update
  a hypothesis solely because a current full suite passes.
- Distinguish source mechanism, observed association, and causal attribution.
- Use full hashes and stable IDs in published datasets; narrative labels alone
  are not sufficient joins.

## Threats to validity

- **Construct:** scripted conformance is not complete historical authenticity or
  human experience; bridge tests are not guest recovery.
- **Internal:** many incompatibility claims lack paired baseline/adapted runs;
  instrumentation can change compiler-case behavior.
- **External:** one Linux/KVM host family and a small compiler set do not
  generalize to arbitrary hardware or toolchains.
- **Conclusion:** most cells have one execution, so stability beyond fixed
  vectors is unmeasured; deterministic matrices do not justify probabilities.
- **Reproducibility:** Wave 110 retains one immutable compiler reference run,
  but the common environment envelope and most other raw outputs are not yet
  retained as immutable run bundles.
- **Completeness:** RQ2 ablation, the compiler cross-product, cross-boot
  persistence, complete machine replay, and third-party reproduction remain
  absent and must be reported as such.
