# Running Linux 0.01 in 2026: A Bounded Executable-Archaeology Artifact

**Fermi Hart**<br>
Vesica Piscis Academic Artifact

## Abstract

Preserving source code does not by itself preserve an executable operating-system
experience. Historical software depends on compiler contracts, firmware-created
state, device behavior, storage geometry, and interaction conventions that may no
longer be available. This paper presents a bounded executable-archaeology artifact
for Linux 0.01, released in September 1991, that runs on a contemporary
Linux/x86-64 host through a firmware-free KVM bridge. The artifact keeps a
recognizable, explicitly patched historical core separate from a modern
measurement bridge comprising bEMU, a checksummed boot protocol, deterministic
image construction, tests, traces, and three versioned datasets. We define five
research questions about invalidated assumptions, adaptation minimality, compiler
sensitivity, behavioral fidelity, and reproducibility. Results are reported only
at the strength supported by retained evidence. The patch dataset inventories 53
changed historical-core paths and 19 adaptation groups but contains no paired
baseline experiment or ablation. An 18-cell compiler dataset observes one
optimization-sensitive source-contract violation and two unreproduced historical
hypotheses. Experience, trace, build, and fault procedures establish separate
conformance dimensions rather than a scalar authenticity score. The principal
contribution is therefore not a claim of historical or hardware equivalence, but
an auditable method for keeping an early operating system executable while making
adaptations, negative results, normalization, and unresolved questions explicit.

## 1. Introduction

Software preservation has at least two distinct objects. One is the sequence of
bytes that constituted a release; the other is the behavior that appeared when
those bytes met a particular compiler, machine, storage device, clock, and user.
Archiving the first object is necessary, but an operating system is most fully
observed as the second: executing privileged instructions, receiving interrupts,
mounting a filesystem, scheduling processes, and mediating interaction. As the
surrounding technical environment changes, these objects diverge. A source tree
may remain readable while its assumptions about a compiler, firmware, disk, or
calendar make it non-executable.

Linux 0.01 is a useful case because its historical object is compact, publicly
available, and technically demanding. The original release targets an early i386
environment and expects conventions that a modern host does not directly supply.
The challenge is not merely to compile the code. A successful artifact must state
which source object it represents, identify every adaptation, expose the modern
machinery that supplies missing context, and avoid turning a successful boot into
a claim about all historical behavior.

The project described here, `linux-0.01-still-runs`, treats that challenge as
**executable software archaeology**. Its mission is defined in `MISSION.md` and
its two-layer technical boundary in `ARCHITECTURE.md`. The historical core is
derived from the pinned Linux 0.01 release and remains visibly comparable to it,
but it is not byte-identical. The modern bridge enters the guest directly through
KVM, models the required legacy devices, constructs a Minix v1 root image, and
provides test and observation surfaces. This separation makes the adaptation
layer inspectable instead of disguising it as original code.

The study asks five questions, specified operationally in
`docs/RESEARCH-QUESTIONS.md`:

1. Which Linux 0.01 assumptions fail in the documented modern environment?
2. What adaptation set is necessary and sufficient for the declared execution
   boundary?
3. How do compiler identity, hosted ABI, and optimization affect three reduced
   GNU89-era cases?
4. How can behavioral fidelity be measured without collapsing unlike evidence
   into an authenticity score?
5. Which layers of the historical operating-system experience are reproducible
   under controlled inputs?

This paper makes four contributions. First, it describes a firmware-free,
direct-KVM architecture with an explicit historical-core/modern-bridge boundary.
Second, it applies a status vocabulary that distinguishes implemented procedures,
partial evidence, and proposed experiments. Third, it reports three versioned
datasets for source deltas, inherited traces, and reduced compiler cases. Fourth,
it reports negative findings as first-class results: the present evidence does
not establish causal invalidation for most adaptations, a minimum adaptation set,
a broad compiler-version result, complete machine replay, cross-boot filesystem
persistence, or independent reproduction.

The paper is deliberately an evidence synthesis rather than a replacement for
the repository. Internal citations name versioned files and executable oracles so
that a claim can be traced to its actual boundary. Detailed reproduction commands
are reserved for the artifact appendix; this paper describes what the current
procedures mean and where they stop.

## 2. Related work

The work intersects source preservation, virtual-machine execution,
reproducibility, and artifact evaluation. Each area solves part of the problem,
but none alone defines behavioral fidelity for a patched historical operating
system.

Large-scale source archives establish durable provenance. Software Heritage, for
example, represents public source and development history in a content-addressed
graph and supports persistent references to software objects [3]. That model
addresses availability and integrity of source material. This artifact adopts
the same general principle at a smaller scale by pinning the upstream Linux 0.01
tarball with SHA-256 and by publishing path-level hashes. Its additional concern
is execution: a preserved source object may still require documented adaptation
before it can be observed on a current machine.

Emulation and virtualization supply execution environments. QEMU demonstrates a
portable dynamic-translation architecture for complete machine execution [4].
KVM instead exposes Linux hardware virtualization through a userspace API [5].
The present bridge uses KVM directly rather than embedding a conventional virtual
machine monitor frontend. bEMU creates the VM, initializes registers and memory,
and models only the legacy interfaces required by this artifact. This design
reduces hidden firmware and platform state, but it does not remove emulation:
legacy PIC, PIT, UART, IDE, keyboard, CMOS, and VGA behavior is implemented by the
bridge. Hardware-assisted CPU execution and modeled devices are therefore named
separately.

Reproducible-build research defines a strong and useful relationship between
declared source inputs and generated bytes. Lamb and Zacchiroli describe
bit-for-bit rebuildability as both a supply-chain integrity mechanism and a
quality-assurance practice [6]. This project applies that concept to two clean
build directories on one host and toolchain. Runtime reproducibility is a
different claim. A byte-identical kernel does not imply identical interrupt
timing, host scheduling, complete event streams, filesystem outcomes, or human
experience. The methodology therefore reports build identity, controlled RTC
state, normalized observable traces, and fixed fault outcomes as separate layers.

Artifact-review practice contributes another boundary: evaluators need claims
that map to obtainable, reusable, and reproducible evidence [7]. The repository
adopts this orientation before external evaluation. Claims link to tests,
manifests, retained observations, or explicit evidence gaps. Failed and missing
experimental cells are not silently promoted to success. The approach also draws
on preservation guidance that emphasizes retaining enough contextual information
to render digital objects meaningful over time [8]. In this case that context
includes compiler identity, ABI, KVM requirements, device contracts, profile
selection, normalization policy, and the exact distinction between a historical
source delta and an observed experiment.

The difference from a conventional port is consequently epistemic as well as
technical. A port typically optimizes for continued function. This artifact also
asks which part of that function is evidence, which part is adaptation, and which
historical interpretation remains untested. A test suite is necessary for this
purpose, but passing current tests cannot retroactively create a controlled
baseline or a retained run. That distinction drives the methodology below.

## 3. Artifact architecture

The artifact has two deliberately unequal layers. The **historical core** contains
the Linux 0.01-derived code under `init/`, `kernel/`, `mm/`, `fs/`, `lib/`, and
`include/`. The **modern bridge** contains bEMU, BBP, boot assembly and linker
work, image construction, userland additions, build logic, and tests. The porting
ledger in `docs/PORTING_LEDGER.md` interprets historical-core modifications; the
patch dataset records the source-level object independently of that prose.

The boot flow removes firmware as an uncontrolled intermediary. bEMU allocates a
fixed 8 MiB guest memory region and validates a kernel artifact before opening
KVM. `kernel.bin` is a physical-address-zero payload followed by a deterministic
16-byte host envelope: the eight-byte `L01KIMG1` marker and an eight-byte
little-endian payload length. The payload must be nonempty and no larger than 512
KiB. Range checks reject arithmetic wrap, out-of-memory placement, overlap with
the bootstrap GDT, and overlap with the reserved handoff window. The IDE root
image is separately required to have the exact 977/5/17 CHS-derived byte length.

After validation, bEMU builds the Bear Boot Protocol handoff in the 64 KiB
physical window `0xC0000..0xD0000`. Five tag classes convey the higher-half direct
map, memory map, kernel address, command line, and hypervisor identity. Each
structure is covered by CRC64. The kernel-side consumer checks framing, bounds,
alignment, tag-chain topology, cardinality, and Linux 0.01-specific semantics.
CRC64 is an integrity check against accidental corruption, not authentication of
the producer. The production consumer and its bounded mutation matrix are
documented in `docs/AUDIT-STATEMENTS.md`.

bEMU then creates a KVM VM and vCPU, registers validated RAM, installs bootstrap
state, and enters at physical address zero. No BIOS, UEFI, bootloader, or disk
boot sector executes. The guest configures its IDT, GDT, paging, PIC, and
subsystems before forking init. CPU instructions execute using hardware
virtualization; bEMU supplies the required PC-compatible interfaces. These
include programmable interrupt and interval timers, CMOS/RTC, serial and VGA
console paths, keyboard input, and a CHS IDE device backed by the root image.
The Linux KVM API is the authoritative host interface [2].

The guest filesystem is Minix v1. `tools/mkimage.c` constructs MBR partitioning,
superblock, bitmaps, inodes, directories, device nodes, and files directly. An
independent read-only inspector and util-linux `fsck.minix` provide stronger
metadata oracles than guest self-report alone. In-session operations such as
create, read, append, link, move, remove, directory creation, pipes, and
redirection traverse real Linux 0.01 syscalls and kernel structures. Cross-boot
persistence is outside the current successful boundary because IDE
write-completion interrupt delivery can leave `sync()` blocked. This limitation
is not inferred from a clean offline filesystem check.

Two experience profiles share the same kernel mechanisms and machine ceiling.
The `1991` profile uses a distinct root image, a period-oriented identity,
`HOME=/`, and a CMOS epoch fixed at 1991-09-17 00:00:00 UTC. The `alive` profile
uses a coherent host UTC snapshot, an explicitly modern narrative, and
`HOME=/home/fermihart`. Profile identity travels through the checked BBP command
line and must match an image marker before KVM entry. `EXPERIENCE.md` defines
their common invariants and forbidden guest feature growth. Neither profile adds
networking, package management, a guest compiler, a language runtime, or a
desktop.

Observation surfaces are also layered. Console tests inspect bounded transcripts.
Machine tracing records a schema-versioned JSON Lines stream. Record/replay
reconstructs scripted input and compares selected observable events after a
declared filter. Host-only fault seams exercise device state machines without
pretending that a guest ran. KVM irqchip fixtures observe in-kernel PIC state but
do not infer guest handler completion. Offline filesystem mutation never boots a
corrupt image. These layer labels prevent a bridge response from being described
as Linux 0.01 recovery.

## 4. Experimental methodology

The consolidated procedure is defined in `docs/METHODOLOGY.md`. It uses three
status labels. `IMPLEMENTED` means that an executable target and an oracle exist
for the stated inputs and decision rule. `PARTIAL` means useful evidence exists
but a required control, repetition, cross-product, causal link, or retained output
is absent. `PROPOSED` describes a design not yet implemented by a repository
target. Status attaches to a procedure, not to an entire research question.

The reference environment is Linux/x86-64 with KVM, the compiler and utilities
identified in the toolchain documentation, fixed 8 MiB guest RAM, the bEMU device
contract, BBP, and fixed root geometry. Source identity is anchored by the
upstream SHA-256
`24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d` and Git
commits named by datasets. `SOURCE_DATE_EPOCH` controls build timestamps. Host
kernel, CPU and microcode, KVM capabilities, nesting, scheduling, and load are not
globally fixed. A published observation should name those variables; earlier
traces do not contain all of them.

The intended unit differs by question. RQ1 requires an assumption/adaptation pair
with the same focused oracle applied to a baseline and adapted state. RQ2 requires
a dependency-valid adaptation configuration evaluated against one fixed execution
boundary. RQ3 uses a compiler identity, reduction, hosted ABI, optimization, and
instrumentation condition. RQ4 uses a declared conformance dimension with
required and forbidden observations. RQ5 uses a separately named reproducibility
layer, because byte identity and runtime event identity are not interchangeable.

The strongest general run envelope remains `PROPOSED`. It would assign an
immutable run ID, retain environment, exact commands, stdout, stderr, status,
duration, input and output hashes, and preserve failed or missing cells. Current
`make -j8 ci` is a broad regression gate, not such a research bundle: much of its
successful output and temporary state is overwritten or deleted. The three
published datasets improve retention for bounded subsets without implying that
all project history was captured under one experiment.

Controls and oracles are classified by independence. util-linux `fsck.minix` is
an external oracle. The repository's Minix inspector is an independently
implemented reader relative to guest filesystem code. Production integration
tests exercise the actual bEMU process, KVM irqchip, BBP consumer, or generated
artifact through a separate harness. White-box fixtures link production bridge
code and assert exact state. Guest or bridge transcript checks are self-report
unless focused evidence supports the underlying mechanism. A passing self-report
cannot substitute for a stronger state oracle.

Analysis uses complete deterministic matrices rather than random samples. No
confidence interval or probability over arbitrary hosts is inferred. Every
normalization, ignored field, timeout, profile, ABI, and instrumentation condition
must remain visible. Baseline and treatment are distinct from optimized and
sanitized configurations; the latter are not repeated trials. Results use exact
counts and retain `NOT_ESTABLISHED` where a proposition was not observed, rather
than converting absence into a boolean refutation.

The paper follows the same rule for causal language. A source delta plus a passing
adapted build supports an inventory and adapted-state conformance. It establishes
invalidation only when a controlled baseline fails and the dependency-equivalent
adapted state passes. A working configuration establishes sufficiency for its
declared boundary, not minimality. A compiler-sensitive reduction requires both
behavioral and generated-code evidence plus a language or inline-assembly
contract analysis before attribution. A normalized trace establishes equality
only for the events retained by its comparison policy.

## 5. Published datasets

The first dataset is the historical-core patch and incompatibility publication
under `datasets/patches/`. Its `datasets/patches/MANIFEST.json` identifies the
pinned upstream object, port commit, generator, and counts. The deterministic
patch spans 53 paths. `datasets/patches/file_deltas.csv` records old and new
hashes, modes, line counts, and per-path patch hashes.
`datasets/patches/adaptations.csv` assigns 19 stable identifiers to interpreted
ledger groups, while the join table leaves nine paths explicitly unresolved.
This dataset publishes a source comparison and historical interpretation; it
does not contain execution logs for paired baselines or adaptation ablations.

The second dataset, `datasets/golden-traces/v1/`, publishes two inherited
alive-profile observations. One is a 2,553-byte, 152-line decoded console
transcript. The other is `datasets/golden-traces/v1/alive-boot-machine.jsonl`, a
2,068,065-byte stream of 23,529 schema-version-1 events. The two payloads were
separate captures and have no common run identifier. Their current manifest,
`datasets/golden-traces/v1/MANIFEST.json`, records missing capture commit, dirty
state, host/KVM identity, artifact hashes, environment manifest, and process
status rather than inferring them from a later build.

The trace comparison policy drops logical timestamps and selected counters, then
excludes all IRQ events and I/O at ports `0x71`, `0x60`, `0x61`, `0x3d4`,
`0x3d5`, and `0x1f0`. For the retained machine observation, 22,917 events are
excluded and 612 remain. The normalized stream has SHA-256
`c75dde26f3bea54406548a6d69f47b48ab7399f5271b6a024080e7936bd53e15`.
This is a durable observable-comparison boundary, not a full execution history.

The third dataset, `datasets/compiler-cases/v1/`, is a newly executed reference
grid. It contains three exact reduced sources, two hosted GNU/Linux ABIs
(x86-64 SysV and i386 SysV), and three optimization levels, yielding 18
observations. `datasets/compiler-cases/v1/MANIFEST.json` bounds the run to one
identified GCC 13.3.0 executable. `datasets/compiler-cases/v1/observations.jsonl`
retains normalized compile and run argv, statuses, output, assembly, binary
hashes, and identities. `datasets/compiler-cases/v1/classifications.json` links
conclusions to observation IDs. Executables and full compiler-generated assembly
are retained for all cells.

Together the datasets illustrate three levels of evidence. Patch data can be
reconstructed exactly but lacks historical experiments. Trace bytes are retained
but have incomplete original environment provenance. Compiler observations are
newly executed with substantially stronger environment and payload identity, but
cover only one compiler and hosted process ABIs. Publishing all three at their
actual strength is preferable to presenting them as a uniform benchmark.

## 6. Results

### RQ1 - Invalidated assumptions

The patch publication identifies **53 historical-core path deltas**, consisting
of modified, added, and one mode-only path, grouped under **19 adaptation IDs**.
The path-to-ledger mapping retains **9 unresolved joins** instead of assigning
them by inference. The ledger documents compiler declarations, inline-assembly
contracts, firmware-provided disk geometry, time representation, serial behavior,
boot layout, filesystem integration, and experience changes. This is a concrete,
reproducible answer to what changed between the pinned source object and the
published port.

It is not yet a strict answer to which assumptions were invalidated. The dataset
contains **0 paired baseline/adapted observations** satisfying the declared
causal criterion. Some ledger entries preserve historical failure diagnostics or
focused current tests, but they are not joined under a single observation ID with
the same captured host and oracle. The defensible result is therefore an
adaptation inventory plus adapted-state conformance. The RQ1 invalidation
procedure remains `PARTIAL`. Evidence: `datasets/patches/MANIFEST.json`,
`datasets/patches/file_deltas.csv`, and `datasets/patches/adaptations.csv`.

### RQ2 - Necessary adaptation set

The artifact demonstrates **one sufficient observed configuration** for its
declared boundary: valid kernel framing and BBP, direct KVM entry, partition and
Minix counters, shell prompt, and clean bEMU completion. Loading tests enforce the
8 MiB and 512 KiB limits; BBP tests enforce structural and semantic boundaries;
boot tests require the named guest milestones. This establishes that the complete
published configuration is sufficient for that contract on the supported
environment.

The patch dataset records **0 ablation configurations**. No predeclared
candidate universe covers historical changes, bridge components, alternatives,
and experience-only changes. There is no dependency graph, subset generator, or
per-configuration cost matrix. The 19 ledger groups cannot be substituted for
that design because they do not enumerate the whole modern bridge or vary group
membership. The current evidence therefore **does not establish a minimum
adaptation set**, inclusion-minimality, unique necessity, or the smallest possible
bridge. The sufficiency procedure is `PARTIAL`; minimality remains `PROPOSED`.
Evidence: `datasets/patches/MANIFEST.json` and `tests/test_boot.py`.

### RQ3 - Optimization and GNU89-era code

The published reference grid has **18 cells**: three reduced cases, two hosted
ABIs, and `-O0`, `-O1`, and `-O2`, each executed once with one identified GCC
13.3.0 binary. **17 PASS and 1 FAIL.** All six `buffer_freelist` cells and all
six `vsprintf_percent_s` cells pass, so those reductions do not reproduce their
historical full-kernel symptoms. Their classifications remain
`HISTORICAL_HYPOTHESIS_NOT_REPRODUCED`, which does not refute every untested
context.

Only `bitmap_inline_asm` under the **hosted x86-64 `-O2`** cell exits 1 and emits
`bit 0 not visible`. The reduced source modifies a memory operand that its GNU
inline assembly declares as input-only, permitting reuse of a stale value after
the assembly. The observation and contract analysis support a **source-contract
violation** for that reduction, **not a GCC defect** and not a demonstration that
the kernel's `-O1` shield is necessary. Both ABIs are hosted processes, not the
freestanding i386 kernel ABI, and no compiler-version cross-product or repeated
cell is retained. The compiler procedure remains `PARTIAL`. Evidence:
`datasets/compiler-cases/v1/MANIFEST.json`,
`datasets/compiler-cases/v1/observations.jsonl`, and
`datasets/compiler-cases/v1/classifications.json`.

### RQ4 - Behavioral fidelity

The artifact operationalizes fidelity as **multidimensional conformance**. The
dimensions include profile identity and RTC behavior, kernel-mediated processes,
filesystem and pipe operations, shell guardrails, static Minix structure,
observable record/replay, and bounded fault responses. Each dimension has
required and forbidden observations. Results are conjunctive within a dimension
and are not averaged across dimensions; there is **no scalar fidelity score**.

The experience harness executes one bounded session per profile. Its current
case construction produces **59 command segments** in alive and **62 command
segments** in 1991, including profile identity, time, six manual pages, external
processes, scheduler visibility, pipes, redirection, a create/read/remove cycle,
literal unsupported shell syntax, and rejection of modern guest facilities.
These segments are distinct checks inside one session, not 59 or 62 independent
trials. Successful transcripts and post-session images are usually not retained.

The result supports a practical measurement model: a historical claim can be
decomposed into explicit contracts and oracle classes while incompatible modern
behavior is tested negatively. It does not measure user perception, compare a
physical 1991 PC, or exhaust unobserved kernel state. The conformance procedure
is `IMPLEMENTED`; retention and repetition remain `PARTIAL`. Evidence:
`EXPERIENCE.md` and `tests/test_experience.py`.

### RQ5 - Reproducible historical experience

Reproducibility is mixed across layers. The build procedure compares complete
SHA-256 manifests from exactly two independent build directories sharing one host
and toolchain. The historical profile's RTC input is fixed; alive consumes one
bounded host UTC snapshot. Fixed fault vectors require exact statuses and state.
The power-cut image procedure executes eight scenarios for two profiles with two
identical repeats, yielding **32 image runs** whose committed prefixes must be
exactly 0, 512, or 1024 bytes with stable hashes and expected IRQ counts.

The published machine trace contains **23,529 raw events**. Its declared filter
removes **22,917** and compares **612 retained events** by exact position, type,
and payload after counter/timestamp normalization. Replay reconstructs **24 input
bytes** from the recorded script. It is **not machine-state replay**: registers,
RAM, device state, IRQ timing, I/O read values, and injection boundaries are not
restored. The inherited console and machine captures are alive-only and come from
different runs with incomplete environment identity.

Thus build bytes and selected fixed-vector outcomes have implemented deterministic
procedures, while runtime trace equivalence remains partial. Cross-host byte
identity, full event equality, cross-boot filesystem persistence, and third-party
reproduction remain outside the evidence. The build and fixed-vector procedures
are `IMPLEMENTED`, while observable trace equivalence remains `PARTIAL`.
Evidence: `datasets/golden-traces/v1/MANIFEST.json`, `tests/test_power_cut.py`,
and `docs/REPRODUCIBILITY.md`.

## 7. Fault model and bounded responses

Fault injection tests the modern bridge's boundary behavior without converting
host observations into guest recovery claims. `docs/FAULT-CATALOG.md` publishes
eight subjects from memory/loading limits through IDE power cuts and exposes 11
canonical Make targets through the aggregate. The subjects are divided among
host-only fixtures, pre-KVM production-process rejection, KVM execution, KVM
irqchip observation, and offline filesystem mutation.

The loading matrix rejects allocation and range failures, malformed or oversized
kernels, short reads, and canonical artifact truncations before KVM. IDE fixtures
inject one-shot read/write aborts and power loss at write acceptance, payload
receipt, 512-byte sector commit, or completion-IRQ request. IRQ fixtures drop or
defer one duplicate edge under explicit PIC quiescence rules. Keyboard fixtures
bound Set-1 error bytes and incomplete host escape sequences. BBP tests accept two
controls and reject 24 structural, integrity, and semantic mutations through the
production consumer. Filesystem tests apply three deterministic Minix metadata
mutations to disposable copies of both profiles; both the independent inspector
and external `fsck.minix` reject all six copies.

These observations establish error handling for the named bridge state machines
and artifacts. They do not show that Linux 0.01 recovers from an IDE error,
missing interrupt, corrupt handoff, corrupt filesystem, or power loss. The
power-cut model concerns bEMU's virtual medium and atomic sector copy; it excludes
host page-cache loss, controller caches, platter behavior, and physical-media
durability. KVM line or PIC state also does not prove guest handler entry.

## 8. Discussion

The first general lesson is that adaptation transparency is more useful than a
binary original/modified label. The historical source is neither untouched nor
silently modernized. A pinned upstream hash, complete path-level patch, stable
adaptation identifiers, and unresolved joins make the transformation inspectable.
The nine unresolved joins are not merely cleanup debt; publishing them prevents
prose categories from appearing more precise than the source mapping.

The second lesson is that negative evidence changes the interpretation of a
working port. A booting system can prove one sufficient configuration without
showing that every patch is necessary. A passing modern compiler reduction can
show that an old symptom was not reproduced without disproving the symptom in
its original context. Conversely, an optimization-sensitive result need not be a
compiler defect. The bitmap case became more precise when it was reclassified as
a source/inline-assembly contract problem bounded to one hosted cell.

The third lesson is that fidelity benefits from decomposition. Kernel-mediated
file operations, profile identity, historical clock initialization, shell syntax
limits, trace equality, and fault responses have different oracles and threats.
A weighted score would hide these distinctions and make a strong dimension
compensate for an absent one. Reporting dimensions separately allows the artifact
to support real process and filesystem behavior while stating plainly that
cross-boot persistence and physical-machine comparison are missing.

The fourth lesson is that normalization is part of the result, not an
implementation detail. The golden comparison retains only 612 of 23,529 events.
That policy is useful as a bounded regression oracle, but the excluded 97.399%
contains precisely the timing- and device-sensitive activity that would matter to
a stronger runtime-determinism claim. Publishing both raw bytes and the policy
makes the claim auditable and permits a later version to choose a stricter
boundary without rewriting the original observation.

Finally, executable archaeology requires preserving context around the
historical object. Direct KVM entry avoids dependence on firmware, but it creates
a modern machine contract that must itself be specified and tested. The bridge is
not neutral: it chooses memory size, device models, disk geometry, time inputs,
and input transport. Treating these choices as first-class research variables is
what makes continued execution compatible with historical honesty.

## 9. Threats to validity

**Construct validity.** The project measures scripted conformance, not an
essential notion of authenticity. The two profiles deliberately encode different
presentation goals while sharing kernel mechanisms. The term "experience" is
therefore limited to declared interactions and constraints. No user study,
perceptual measure, physical-machine baseline, or scalar weighting validates the
subjective feel described by the mission. Console text may also be consistent
with a result while hiding incorrect internal state; focused traces and
independent filesystem oracles mitigate this only for named mechanisms.

**Internal validity.** Most RQ1 interpretations lack paired baseline and adapted
runs in one captured environment. Historical failure descriptions, current tests,
and source diffs may be correct individually while failing to establish a causal
chain. RQ2 has no ablation matrix. Compiler instrumentation can alter behavior,
and the retained reference grid has one execution per cell. Fault fixtures often
link production bridge code but do not execute the guest, so their conclusions
must stay at the bridge layer.

**External validity.** The supported environment is a Linux/x86-64/KVM host
family. Results do not generalize automatically to physical i386 systems,
non-Linux hypervisors, different CPU virtualization behavior, arbitrary modern
peripherals, or all compiler/linker versions. The compiler dataset uses one GCC
13.3.0 identity and two hosted GNU/Linux process ABIs. The two golden traces cover
only alive and lack complete host provenance. The expected AMD row in the public
matrix is not treated as an observed execution.

**Conclusion validity.** Deterministic matrices provide exact observations for
their cells but do not justify statistical probabilities. Most cells are
executed once; the 32 power-cut image runs contain defined repeats, but optimized
and sanitized executions elsewhere are configuration comparisons, not repeats.
A passing aggregate that stops at first failure is appropriate for regression
control but cannot be used as a publication record unless skipped and missing
cells are retained.

**Reproducibility validity.** The build comparator uses two directories on one
host and toolchain. Different distributions, linker versions, CPUs, kernels, or
KVM implementations may produce different host binaries or runtime scheduling.
The current common run envelope does not retain all successful transcripts,
temporary filesystems, raw logs, exact environment, or durations. Golden trace
payloads are durable, but their original capture identity is incomplete. An
external evaluator has not yet executed the artifact under a separately recorded
environment.

**Completeness.** Important absences are part of the result. No experiment proves
minimality of the adaptation set. The compiler-version/ABI cross-product is
missing. Full machine-state replay, both-profile trace publication, cross-boot
persistence, guest fault recovery, arbitrary-host bit identity, and third-party
reproduction remain open. The system-call count shown in architectural
documentation has not been promoted here to an audited completeness result.

## 10. Reproducibility boundary

`docs/REPRODUCIBILITY.md` defines the current build-level procedure.
`scripts/verify-reproducibility.sh` constructs two isolated trees and compares
complete SHA-256 manifests on one machine. The broader CI path builds the kernel,
both root images, bEMU, userland and host tools; validates documentation and all
three datasets; executes host, KVM, shell, filesystem, trace, compiler, and fault
gates; and writes checksums. The repository's default execution backend requires
a readable and writable `/dev/kvm`; there is no supported fallback backend.

For runtime evidence, inputs and outputs must be interpreted per layer. RTC tests
verify conversion and bounded host time, not identical elapsed execution. Trace
comparison verifies only its normalized event projection. Experience tests verify
one scripted session per profile, not a population of sessions. Power-cut repeats
verify the virtual-medium model, not physical storage. Dataset validators verify
manifest, payload, source, identity, and checksum consistency without recreating
missing historical provenance.

This paper intentionally stops short of a command-by-command artifact appendix.
The repository exposes named Make targets alongside each research question and
dataset; the separate appendix will specify clean-clone setup, environment
capture, expected durations and outputs, and troubleshooting. Keeping that
operational layer separate avoids presenting future publication, archival, or
external-evaluation steps as completed observations.

## 11. Conclusion

Linux 0.01 can remain executable on a contemporary KVM host without pretending
that its environment, source, or behavior is unchanged. The artifact achieves
this through a visible two-layer design: a pinned and explicitly patched
historical core, and a modern bridge that supplies controlled boot state, legacy
devices, storage, profiles, tests, traces, and fault seams.

The five research questions are only partly closed. RQ1 yields a reproducible
adaptation inventory but lacks paired causal observations. RQ2 establishes one
sufficient configuration but has no minimality experiment. RQ3 reports one
bounded source-contract violation and two hypotheses not reproduced in an
18-cell hosted grid. RQ4 demonstrates that fidelity can be measured as separate
conformance dimensions. RQ5 establishes build and selected fixed-vector
reproducibility while keeping filtered trace equivalence distinct from complete
runtime replay.

The most durable outcome is methodological: preserve the upstream object, expose
the adaptation layer, bind strong statements to versioned evidence, retain
negative results, name oracle layers, and treat normalization and missing data as
part of the claim. Future work should implement paired RQ1 experiments, a
dependency-aware RQ2 ablation universe, a broader compiler matrix, complete run
envelopes, cross-boot persistence, stronger replay, and independent evaluation.

## Data availability

All evidence discussed in this paper is contained in the public repository at
https://github.com/fermihart/linux-0.01-still-runs. The source-delta publication is under
`datasets/patches/`; the trace publication is under
`datasets/golden-traces/v1/`; and the compiler reference run is under
`datasets/compiler-cases/v1/`. Each directory includes a manifest and checksums.
The governing claims and limits are in `docs/AUDIT-STATEMENTS.md`; trace semantics
are in `docs/OBSERVABILITY.md`; the research questions and procedures are in
`docs/RESEARCH-QUESTIONS.md` and `docs/METHODOLOGY.md`.

The local academic tarball produced by `make artifact` packages documentation
and datasets, but this in-repository availability is not a claim of long-term archival deposit,
DOI assignment, artifact badging, or third-party reproduction. Those publication
steps require separate identities and external evidence. The pinned original
Linux 0.01 source remains available from the kernel.org historical archive [1],
with the exact local tarball identity recorded in the patch manifest.

## References

1. Linux Kernel Archives. "Historic Linux kernel releases: Linux 0.01."
   https://www.kernel.org/pub/linux/kernel/Historic/
2. Linux Kernel Documentation. "The Linux Kernel Virtual Machine (KVM) API."
   https://docs.kernel.org/virt/kvm/api.html
3. Roberto Di Cosmo and Stefano Zacchiroli. "The Software Heritage Open Science
   Ecosystem." *Software Ecosystems*, 2023. DOI 10.1007/978-3-031-36060-2_2.
   https://arxiv.org/abs/2310.10295
4. Fabrice Bellard. "QEMU, a Fast and Portable Dynamic Translator." *USENIX
   Annual Technical Conference*, 2005.
   https://www.usenix.org/legacy/events/usenix05/tech/freenix/full_papers/bellard/bellard.pdf
5. Avi Kivity, Yaniv Kamay, Dor Laor, Uri Lublin, and Anthony Liguori. "kvm: the
   Linux Virtual Machine Monitor." *Ottawa Linux Symposium*, 2007.
   https://www.kernel.org/doc/ols/2007/ols2007v1-pages-225-230.pdf
6. Chris Lamb and Stefano Zacchiroli. "Reproducible Builds: Increasing the
   Integrity of Software Supply Chains." *IEEE Software*, 2022.
   DOI 10.1109/MS.2021.3073045. https://arxiv.org/abs/2104.06020
7. Association for Computing Machinery. "Artifact Review and Badging, Version
   1.1." https://www.acm.org/publications/policies/artifact-review-and-badging-current
8. David S. H. Rosenthal, Thomas Robertson, Tom Lipkis, Vicky Reich, and Seth
   Morabito. "Requirements for Digital Preservation Systems: A Bottom-Up
   Approach." *D-Lib Magazine* 11(11), 2005.
   https://www.dlib.org/dlib/november05/rosenthal/11rosenthal.html
