# Deterministic Fault Catalog

This is the public catalog for the deterministic fault-injection work completed
in Waves 096-103. It records what is injected, where the oracle runs, and what
the current executable evidence observes. A passing harness means that all
responses stated below were observed; a failed assertion makes its target exit
nonzero.

The layers are deliberately distinct:

| Layer | Meaning |
|---|---|
| `host-only` | Production bridge code is linked into an in-process host fixture; no virtual CPU runs. |
| `pre-KVM process` | The production bEMU process receives a malformed artifact and must reject it before opening KVM. |
| `KVM` | The production runner enters KVM to exercise host input wiring; the fault oracle does not claim guest-handler recovery. |
| `KVM irqchip` | A minimal single-step fixture observes the real in-kernel PIC through KVM ioctls. |
| `offline filesystem` | Disposable image copies are inspected without booting or writable bEMU mapping. |

All fault controls are test-only host interfaces. None is exposed through the
historical guest or the public bEMU CLI. `make test-fault-catalog` checks that
all eight entries, their Make targets, layer labels, and evidence files remain
present. Wave 105 will provide the separate command that executes every fault
scenario.

| Wave | Subject | Completion commit |
|---:|---|---|
| 096 | Memory and loading limits | `0ffe743` |
| 097 | IDE read/write failures | `bbe94fd` |
| 098 | Minix metadata corruption | `bff041e` |
| 099 | Lost and duplicated IRQ edges | `8719c5f` |
| 100 | Invalid scancodes and truncated input | `1b5d649` |
| 101 | Truncated kernel and root artifacts | `744cf7f` |
| 102 | Corrupted BBP handoffs | `dc552b1` |
| 103 | Deterministic IDE power cuts | `28fec02` |

## Wave 096 - Memory and loading limits

- **Fault:** Exercise the fixed 8 MiB RAM boundary, allocation failure, wrapping and reserved-range overlap, empty and oversized kernels, invalid `L01KIMG1` framing, and an injected short read.
- **Run:** `make test-bemu-loading`
- **Layer:** `host-only` unit checks plus `pre-KVM process` rejection through the production runner.
- **Expected response:** Return the matching `BEMU_MEMORY_*` or `BEMU_LOAD_*` status without partial allocation state; process cases exit 1 with `kernel is empty` or `kernel exceeds 524288-byte limit` and omit direct-KVM and guest-success markers.
- **Observed response:** The host harness exits 0 with `all memory/loader tests passed`; both production-process faults exit 1 before KVM and the wrapper reports each rejection as `ok`.
- **Evidence:** `tests/bemu/test_memory_loader.c`, `tests/test_loading_limits.py`
- **Artifact policy:** Unit inputs use anonymous RAM and temporary kernel files; process inputs are temporary, and rejection precedes opening or mapping the root image.
- **Requirements:** Linux headers, a host C compiler, Python 3, and built bEMU/root prerequisites; writable `/dev/kvm` is not required for the injected rejection cases.
- **Does not prove:** No injected case executes the guest, and no public RAM-size, allocation-failure, or short-read control is provided.

## Wave 097 - IDE read and write failures

- **Fault:** Arm one read or write ATA abort for a selected LBA, including a later sector of a two-sector command, while checking operation/LBA isolation and one-shot retry.
- **Run:** `make test-ide-faults`
- **Layer:** `host-only` IDE state-machine fixture.
- **Expected response:** A matching operation sets ATA `ERR` with abort code 4, clears `DRQ` and transfer state, requests IRQ14, transfers no failing-sector data, and consumes only the selected one-shot fault.
- **Observed response:** The fixture exits 0 with `all IDE fault-injection tests passed`; retry succeeds, mismatches do not consume the fault, and sectors before a later failing LBA are the only ones committed.
- **Evidence:** `tests/bemu/test_ide_faults.c`
- **Artifact policy:** The fixture uses stack-backed sectors and opens no kernel, root image, KVM VM, or guest artifact.
- **Requirements:** A host C compiler and Linux KVM headers included by the shared machine contract; no writable `/dev/kvm` is needed.
- **Does not prove:** ATA host state does not prove Linux 0.01 driver recovery, guest IRQ14 handler entry, or filesystem recovery.

## Wave 098 - Minix metadata corruption

- **Fault:** In disposable copies of both profile images, flip only the Minix v1 superblock magic, zero the root inode mode, or clear the root-zone allocation bit located relative to the MBR partition.
- **Run:** `make test-fs-corruption`
- **Layer:** `offline filesystem` mutation and two independent host oracles.
- **Expected response:** `minix-inspect --audit` exits 1 for every fault; `fsck.minix -f -v` exits 8 for bad magic/root inode and 4 for the zone bitmap, with the cataloged semantic diagnostic fragments.
- **Observed response:** The harness exits 0 with `deterministic filesystem corruption test passed`; six copies are rejected, a displaced-partition control proves MBR-relative lookup, and both oracles leave their inputs unchanged.
- **Evidence:** `tests/test_fs_corruption.py`
- **Artifact policy:** Every mutation targets a temporary copy; exact byte deltas and SHA-256 hashes prove that canonical images and read-only oracle operands remain unchanged.
- **Requirements:** Python 3, generated alive/1991 root images, the host `minix-inspect` build, temporary storage, and util-linux `fsck.minix` (reference observations used 2.39.3).
- **Does not prove:** Corrupt images are never booted, so guest panic behavior, repair, and recovery from corrupt metadata are not claimed.

## Wave 099 - Lost and duplicated IRQ edges

- **Fault:** Drop or duplicate one selected rising edge on IRQ0-15; duplicate replay waits for a completed run, a low line, clear IRR/ISR, and a clear master cascade for slave IRQs.
- **Run:** `make test-irq-faults`, `make test-irq-faults-kvm`
- **Layer:** `host-only` callback-policy coverage plus `KVM irqchip` integration for IRQ0 and IRQ14.
- **Expected response:** Drop suppresses exactly one pulse; duplicate forwards the original then replays exactly once after quiescence, with trace actions `fault_drop`, `fault_duplicate_queued`, and `fault_duplicate_replayed`.
- **Observed response:** Both harnesses exit 0 with their `all ... IRQ fault-injection tests passed` markers; KVM IRR observations show IRQ0 drop/recovery and IRQ14 slave/master-cascade deferral without a third edge.
- **Evidence:** `tests/bemu/test_irq_faults.c`, `tests/bemu/test_irq_faults_kvm.c`
- **Artifact policy:** The host fixture uses in-memory event arrays; the KVM fixture uses anonymous RAM containing one `nop` and opens no disk or canonical kernel/root image.
- **Requirements:** The policy target needs a host C compiler; the integration target additionally needs writable `/dev/kvm`, in-kernel PIC support, guest single-step, and IRQ-chip get/set ioctls.
- **Does not prove:** Line traces and PIC IRR/ISR state do not prove vector delivery, guest handler entry/completion, EOI-driven recovery, or safe Linux recovery from keyboard/IDE IRQ faults.

## Wave 100 - Invalid scancodes and truncated input

- **Fault:** Inject only Set-1 error bytes `0x00`/`0xff`, split terminal escapes across polls, and finalize non-TTY EOF after a lone Escape or incomplete CSI/SS3 sequence.
- **Run:** `make test-keyboard-faults`, `make test-trace-input`
- **Layer:** `host-only` keyboard/decoder matrix plus `KVM` production pipe-EOF wiring.
- **Expected response:** Only the two error bytes enter the latch and request IRQ1; normal input recovers, lone Escape emits make/break, and incomplete CSI/SS3 is discarded once with `discarded truncated stdin escape sequence`.
- **Observed response:** The host harness exits 0 with `all keyboard fault-injection tests passed`; KVM pipe cases exit 0 with `RESULT: PASS`, and only the incomplete sequence prints the truncation diagnostic once.
- **Evidence:** `tests/bemu/test_keyboard_faults.c`, `tests/test_trace_input.py`
- **Artifact policy:** The primary matrix mutates only in-memory queue/decoder state; the KVM wiring uses normal built artifacts and sends a bounded `echo` script rather than modifying canonical sources.
- **Requirements:** A host C compiler and Linux headers for the matrix; built bEMU/kernel/root artifacts and writable `/dev/kvm` for the pipe-EOF integration target.
- **Does not prove:** IRQ1 requests do not prove guest handler recovery; arbitrary malformed scancode prefixes, stuck modifiers, PTY hangup, unusual non-TTY devices, and full-queue recovery remain outside the matrix.

## Wave 101 - Truncated kernel and root artifacts

- **Fault:** Create prefix, interior, and suffix truncations of the canonical kernel and both root profiles, plus an interior kernel deletion that retains its original length trailer.
- **Run:** `make test-artifact-truncation`
- **Layer:** `pre-KVM process` rejection by production bEMU.
- **Expected response:** All ten processes exit 1 before direct KVM entry; kernel cutoffs report an invalid `L01KIMG1` trailer or size mismatch, and root cutoffs report the fixed 977/5/17 CHS geometry mismatch.
- **Observed response:** The harness exits 0 after observing all ten status-1 rejections, no BBP/guest-success marker, and unchanged SHA-256 hashes for the canonical kernel and root images.
- **Evidence:** `tests/test_artifact_truncation.py`
- **Artifact policy:** All malformed inputs are temporary copies; root size rejection precedes writable mapping, and the canonical source hashes are checked after the full matrix.
- **Requirements:** Python 3 and built production bEMU, enveloped kernel, and alive/1991 root images; writable `/dev/kvm` is not needed because every case is rejected first.
- **Does not prove:** Length framing is not content integrity, does not detect same-size corruption, and cannot recognize every adversarial payload containing trailer-like bytes.

## Wave 102 - Corrupted BBP handoffs

- **Fault:** Restore a clean handoff before each mutation of magic, versions, CRC64, bounds, alignment, tag pointers/overlap/cycles/counts, required-tag cardinality, command blobs, or Linux 0.01 semantic values.
- **Run:** `make test-bbp-corruption`, `make test-bbp-corruption-sanitized`
- **Layer:** `host-only` fixed-address mapping linked to the exact production parser and Linux 0.01 consumer.
- **Expected response:** Two canonical controls return `BBP_OK`; 24 corruptions return the independently expected `BBP_ERR_MAGIC`, `BBP_ERR_VERSION`, `BBP_ERR_CHECKSUM`, `BBP_ERR_TAG_CHECKSUM`, or `BBP_ERR_SIZE`, print the matching production diagnosis, and clear accessors.
- **Observed response:** Optimized and ASan/UBSan harnesses exit 0 with `all production BBP corruption tests passed`; the CRC-valid overlap reaches the generic parser before Linux 0.01 semantics rejects it.
- **Evidence:** `tests/bemu/test_bbp_corruption.c`
- **Artifact policy:** Each case restores an in-memory snapshot in a private anonymous `0xC0000..0xD0000` mapping; no kernel, root, or serialized BBP artifact is opened.
- **Requirements:** Linux `MAP_FIXED_NOREPLACE`, an unused fixed window, a host C compiler, and AddressSanitizer/UndefinedBehaviorSanitizer runtime for the sanitized target.
- **Does not prove:** The host fixture is not guest execution, the 24-case matrix is not exhaustive fuzzing, and CRC64 detects accidental corruption but does not authenticate a producer able to reseal forged content.

## Wave 103 - Deterministic IDE power cuts

- **Fault:** Power off one selected LBA at write acceptance, complete payload receipt, atomic 512-byte sector commit, or normal unmasked completion-IRQ request, across first/second-sector writes.
- **Run:** `make test-ide-power-cut`, `make test-power-cut`
- **Layer:** `host-only` optimized/sanitized IDE model plus `offline filesystem` inspection of disposable profile copies.
- **Expected response:** Cuts expose only exact 0, 512, or 1024-byte committed prefixes and the boundary-specific IRQ count; power-off discards staging, lowers IRQ14, clears transfer state, and blocks PIO until reset.
- **Observed response:** Device and image harnesses exit 0, the latter with `deterministic IDE power-cut image test passed`; repeated scenarios have stable SHA-256 classes, while inspector and `fsck.minix` both remain metadata-clean.
- **Evidence:** `tests/bemu/test_ide_power_cut.c`, `tests/test_power_cut.py`
- **Artifact policy:** A regular-file data block is derived from Minix metadata in a fresh temporary copy for every run; exact deltas and final hashes prove both canonical profile images remain unchanged.
- **Requirements:** A host C compiler, ASan/UBSan runtime, Python 3, both root profiles, `minix-inspect`, temporary storage, and util-linux `fsck.minix`; no writable `/dev/kvm` is needed.
- **Does not prove:** The virtual-medium model omits host page-cache loss, drive caches, platter behavior, and physical power loss; clean metadata does not prove file-content recovery, and IRQ request does not prove guest handling or cross-boot durability.

## Reading the results

The expected responses are assertions encoded by the listed evidence, not
predictions inferred from documentation. The observed responses are reproduced
when the corresponding target exits zero. External `fsck.minix` wording is
matched by stable semantic fragments rather than a full golden transcript; its
reference version is recorded in `docs/TOOLCHAIN.md`.

The catalog intentionally does not claim that host-side fault injection proves
Linux 0.01 recovery. Normal boot, shell, trace, and experience regressions are
separate gates in `make test` and `make ci`.
