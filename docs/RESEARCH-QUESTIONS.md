# Research Questions

This document turns the five questions in `MISSION.md` into bounded research
questions that can be answered with the artifact. It defines observations and
decision criteria, not conclusions. Wave 107 will consolidate the experimental
methodology; later delivery waves will publish the datasets and paper.

The supported environment is Linux/x86-64/KVM with the reference toolchain
versions in `docs/TOOLCHAIN.md`. The host kernel, CPU/KVM identity, and other
unfixed variables must be named for each result. The historical object is Linux
0.01 plus documented core patches; bEMU, BBP, image construction, tests, and
observability are the modern measurement bridge.

Three boundaries apply to every question:

1. A passing test proves its declared contract, not historical equivalence in
   every unobserved state.
2. A sufficient adaptation set is not a minimum set without ablation evidence.
3. Deterministic hashes or normalized events do not imply complete runtime,
   physical-hardware, or human-experience determinism.

## RQ1 - Invalidated assumptions

- **Question:** Which Linux 0.01 assumptions fail in the documented modern execution environment?
- **Scope:** Classify assumptions about the GCC/ABI contract, firmware-provided state, memory layout, legacy devices, time representation, and host I/O only for named Linux x86-64/KVM host instances using the documented GCC 13.3, binutils 2.42, and bEMU configuration.
- **Run:** `make provenance`, `make audit`, `make doctor`, `make test`
- **Evidence:** `docs/PORTING_LEDGER.md`, `docs/AUDIT-STATEMENTS.md`, `docs/TOOLCHAIN.md`, `tests/test_boot.py`
- **Measures:** Record toolchain and host identity, build/boot exit status, exact failure diagnostics, affected source and category, the adaptation applied, and the boot milestones or focused regression that distinguish the failing and adapted states.
- **Answer criterion:** Count an assumption as invalidated only when a documented baseline failure and a controlled adaptation are connected to reproducible evidence; classify observations without a controlled cause as qualified or under investigation.
- **Limits:** The result is bounded to the stated virtual machine, named host, and toolchain, not arbitrary modern hardware, bare metal, or all compilers; current reports do not retain complete host identity, and bEMU recreates legacy interfaces rather than proving direct compatibility with contemporary physical peripherals.

## RQ2 - Necessary adaptation set

- **Question:** What minimum adaptation set is necessary and sufficient to reach the declared execution boundary?
- **Scope:** Define execution as validated kernel framing and BBP, direct KVM entry, partition and Minix counters visible, shell prompt reached, and clean bEMU completion; predeclare a candidate universe that separates historical-core compatibility, bridge components, and experience-only changes before evaluating necessity.
- **Run:** `make test-quick`, `make test-bemu-loading`, `make test-artifact-truncation`, `make bbp-conformance`
- **Evidence:** `docs/PORTING_LEDGER.md`, `tests/test_boot.py`, `ARCHITECTURE.md`, `bemu/README.md`
- **Measures:** Inventory the predeclared candidate universe, record each evaluated configuration, file/hunk and artifact-size costs, and measure the same declared boot outcomes for every configuration selected by the Wave 107 methodology.
- **Answer criterion:** A set is sufficient when all declared execution outcomes pass; call it minimum within the candidate universe only after exhaustive subset evidence or a justified dependency proof excludes every smaller set, otherwise report only an inclusion-minimal set or the smallest observed among evaluated configurations.
- **Limits:** The repository currently proves a sufficient configuration but has no complete ablation matrix, so it does not yet answer the minimum claim; the candidate universe may omit alternative bridge designs, and BBP, direct KVM loading, VGA presentation, or shell conveniences cannot be called uniquely necessary without comparative evidence.

## RQ3 - Optimization and GNU89-era code

- **Question:** How do compiler version, target ABI, and optimization level affect the reduced GNU89-era cases?
- **Scope:** Study the three committed reductions across `-O0`/`-O1`/`-O2`; the dual-ABI harness compares x86-64/i386 for one selected compiler, while the available compiler-version matrix currently covers x86-64 only.
- **Run:** `make compiler-cases`, `make compare-assembly`, `make compiler-audit`, `make compiler-matrix`
- **Evidence:** `tests/compiler-cases/README.md`, `tests/compiler-cases/CLASSIFICATION.md`, `tests/compiler-cases/Makefile`, `docs/AUDIT-STATEMENTS.md`
- **Measures:** Record compile status, runtime exit/output, compiler identity, ABI, optimization level, sanitizer/diagnostic output, extracted function assembly, and pairwise assembly differences for each experimental cell.
- **Answer criterion:** Attribute a failure only when the reduced case reproduces, the relevant generated-code difference is identified, and language or inline-assembly rules support the classification; otherwise retain it as a bounded historical hypothesis rather than a compiler bug.
- **Limits:** Linux 0.01 uses C89-era GNU extensions, not pre-standard C; there is no full compiler-version/ABI cross-product, generated raw reports are not yet a published dataset, and behavior on one ABI/compiler does not establish causality or necessity for the i386 kernel build.

## RQ4 - Behavioral fidelity measurement

- **Question:** How can behavioral fidelity be measured as explicit dimensions in executable software archaeology?
- **Scope:** Treat kernel-mediated mechanisms, historical limits, profile identity/time, filesystem behavior, observable traces, and bounded fault responses as separate conformance dimensions instead of collapsing them into an authenticity score.
- **Run:** `make test-experiences`, `make test-fs-inspect`, `make test-trace-workflow`, `make fault-test`
- **Evidence:** `EXPERIENCE.md`, `tests/test_experience.py`, `docs/FAULT-CATALOG.md`, `docs/OBSERVABILITY.md`
- **Measures:** For each declared dimension, record the invariant, controlled input, expected and forbidden observations, status, transcript or machine event, independent oracle where available, and a traceable limitation for behavior not observed.
- **Answer criterion:** Support a fidelity claim only when its dimension has an explicit contract and a reproducible oracle that passes while incompatible cross-profile or modern behavior is rejected; report dimensions independently rather than averaging unlike observations.
- **Limits:** The artifact has no scalar fidelity score, weighting model, user study, physical-1991-machine comparison, or independent full-system reference execution; claims about feel and historical authenticity remain goals rather than measured equivalence.

## RQ5 - Reproducible historical experience

- **Question:** Which parts of the historical operating-system experience are reproducible under controlled inputs?
- **Scope:** Separate byte-for-byte build reproduction, deterministic initial profile/RTC state, normalized record/replay equivalence, and repeated fault outcomes from wall-clock scheduling, complete machine-state replay, cross-boot persistence, and physical-media behavior.
- **Run:** `make verify-reproducible`, `make test-rtc`, `make compare-trace`, `make fault-test`
- **Evidence:** `docs/REPRODUCIBILITY.md`, `tests/compare_trace.py`, `tests/test_power_cut.py`, `docs/OBSERVABILITY.md`
- **Measures:** Repeat controlled builds and runs; compare SHA-256 manifests, RTC register values, normalized event count/order/type/payload, exact replayed input bytes, fault exit statuses, media byte prefixes, IRQ counts, and repeated state hashes.
- **Answer criterion:** Call a layer reproducible only when repeated trials under named controls produce its predeclared identical outcome; list every normalization or ignored field and report layers that intentionally consume host time or remain scheduling-dependent separately.
- **Limits:** Current evidence does not prove full event-by-event runtime determinism, bit identity across arbitrary distributions, cross-boot filesystem persistence, guest recovery from host faults, physical power-loss durability, or independent third-party reproduction.

## Relationship to later waves

Wave 107 will define sampling, controls, execution order, evidence retention, and
analysis procedures for these questions. Wave 108 will publish the patch and
incompatibility dataset needed by RQ1/RQ2, while Waves 109-110 publish trace and
compiler-case evidence. Questions may be refined only by preserving their IDs,
recording the reason, and updating this document's validation gate.
