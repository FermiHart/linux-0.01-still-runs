# Observability Event Schema

This document defines the machine-readable event schema used by bEMU for
observation, input reconstruction and normalized regression comparison. The
schema is intentionally minimal: every event is a single line of JSON. The
machine-readable contract is published in
`datasets/golden-traces/v1/trace-event-v1.schema.json`.

## Event envelope

```json
{
  "ts": 1234567890,
  "type": "kvm_exit",
  "data": { ... }
}
```

| Field | Type | Meaning |
|---|---|---|
| `ts` | integer | logical run-attempt clock, offset by `SOURCE_DATE_EPOCH` when set |
| `type` | string | event category |
| `data` | object | event-specific payload |

## Event types

### `boot_start`

Emitted when bEMU enters the main KVM loop.

```json
{
  "ts": 0,
  "type": "boot_start",
  "data": {
    "kernel": "build/kernel.bin",
    "root": "build/root.img",
    "ram_mib": 8,
    "trace_version": 1
  }
}
```

### `kvm_exit`

The emitter is defined for KVM exits, but the production main loop does not
currently call it. Unit fixtures exercise this schema member.

```json
{
  "ts": 1234,
  "type": "kvm_exit",
  "data": {
    "exit_reason": 2,
    "exit_reason_name": "KVM_EXIT_IO",
    "exit_count": 1
  }
}
```

### `io_access`

Emitted for `KVM_EXIT_IO` exits.

```json
{
  "ts": 1235,
  "type": "io_access",
  "data": {
    "direction": "out",
    "port": 1016,
    "size": 1,
    "value": 65
  }
}
```

### `irq`

Emitted for host IRQ line transitions and test-only fault decisions. These
events do not prove that KVM's in-kernel PIC delivered a vector or that the guest
handler completed.

```json
{
  "ts": 1236,
  "type": "irq",
  "data": {
    "irq": 1,
    "action": "raise"
  }
}
```

Valid actions currently emitted: `raise`, `lower`, `fault_drop`,
`fault_duplicate_queued`, and `fault_duplicate_replayed`.

### `timer`

The emitter is defined for PIT-related activity, but production currently emits
PIT I/O and IRQ observations instead. Unit fixtures exercise this schema member.

```json
{
  "ts": 1237,
  "type": "timer",
  "data": {
    "port": 64,
    "action": "latch"
  }
}
```

### `input`

Emitted when host input is injected into the guest.

```json
{
  "ts": 1238,
  "type": "input",
  "data": {
    "bytes": 1,
    "hex": "78",
    "source": "script"
  }
}
```

The producer records at most the first 64 input bytes in `hex`; `bytes` reports
the original length. Replay can reconstruct an event completely only when these
lengths agree.

### `syscall`

Emitted when the guest executes a system call.  On the KVM backend used by
bEMU this event is produced only when explicit instrumentation is available
(Wave 073); the schema contract is defined now so that record/replay tools can
consume it.

```json
{
  "ts": 1239,
  "type": "syscall",
  "data": {
    "number": 1,
    "args": [0, 1, 2, 0, 0, 0]
  }
}
```

### `interrupt`

The emitter is defined for explicitly instrumented interrupt observations, but
production currently has no call site. Unit fixtures exercise this schema member.

```json
{
  "ts": 1240,
  "type": "interrupt",
  "data": {
    "vector": 128
  }
}
```

### `process`

Emitted on process lifecycle transitions when instrumentation is available.

```json
{
  "ts": 1241,
  "type": "process",
  "data": {
    "pid": 1,
    "action": "fork",
    "name": "init"
  }
}
```

Valid actions: `fork`, `exec`, `exit`, `wait`, `switch`.

### `shutdown`

Emitted when the guest halts or bEMU gives up.

```json
{
  "ts": 9999,
  "type": "shutdown",
  "data": {
    "reason": "halt",
    "exits": 1000,
    "status": 0
  }
}
```

Valid reasons: `halt`, `max_exits`, `triple_fault`, `signal`, `error`.

## Trace file format

A trace file is a UTF-8 text file containing one JSON object per line (newline
delimited JSON, also known as JSON Lines). Lines may be compressed with `gzip`
if the file extension is `.trace.gz`.

## Logical clock

The `ts` field is produced by a logical clock (`bemu/trace_clock.h`). The clock
is reset at machine creation and advances by one fixed quantum before each KVM
run attempt. Multiple events emitted during one attempt share a timestamp, and
attempts interrupted by the host may still advance it. It does **not** read the
host wall clock directly.

When `SOURCE_DATE_EPOCH` is present in the environment, the clock uses it as the
logical offset in epoch nanoseconds; otherwise the offset is zero. Matching
timestamps therefore require matching epoch and run-attempt progression, not
merely matching observable events.

| Function | Meaning |
|---|---|
| `trace_clock_reset()` | Reset epoch and counters |
| `trace_clock_tick()` | Advance one quantum |
| `trace_clock_now()` | Current logical timestamp |
| `trace_clock_seq()` | Monotonic event sequence number |

## Producing traces

traces are emitted by bEMU when the `--trace-file PATH` command-line option is
used.  The file contains one JSON object per line.  Pass `-` to write the trace
to standard error. Console UART data and line-status ports (`0x3f8` and `0x3fd`)
are intentionally omitted from
`io_access` events to keep traces focused on device I/O and to avoid noise.

Useful CLI flags:

| Flag | Meaning |
|---|---|
| `--trace-file PATH` | Write machine-readable trace to file |
| `--trace-syscalls` | Single-step the guest and emit `syscall` events for `int 0x80` |
| `--no-timer` | Disable PIT timer IRQs (more deterministic, but may affect `date`/`uptime`) |

Example:

```bash
./build/bemu-linux01 --kernel build/kernel.bin --root build/root.img \
  --expect root@linux01 --trace-file boot.trace
```

## Make targets

| Target | Purpose |
|---|---|
| `make record` | Record a compressed boot trace to `build/traces/boot-<ts>.jsonl.gz` |
| `make replay` | Reconstruct the published trace's scripted input and emit a new trace |
| `make compare-trace` | Compare a replayed trace to `datasets/golden-traces/v1/alive-boot-machine.jsonl` |
| `make timeline` | Generate a text timeline from the golden trace |
| `make trace-workflow` | Run record → replay → compare → timeline in one shot |
| `make test-golden-trace-dataset` | Validate the offline published traces, schema, policy and checksums |

## Stability guarantees

- The published v1 dataset requires the exact envelope and payload fields in its
  JSON schema. New event types or incompatible payload changes require a new
  schema/dataset version.
- The `ts` field is monotonic within a trace but is comparable across traces only
  when both use the same `SOURCE_DATE_EPOCH` and matching event sequences.

## Replay invariants

The current replay tool concatenates complete `input` events whose source is
`script` and injects those bytes into a fresh run. It does not replay I/O read
values, IRQ delivery, timestamps, registers, RAM or device state, and it does
not preserve separate injection boundaries. The comparator then drops logical
timestamps and declared counters and may filter whole event types or I/O ports
before exact positional comparison. This is input reconstruction plus an
observable regression oracle, not machine-state replay.

## Future work

Waves 064-074 implemented the trace producer, input reconstruction, comparator,
and timeline visualizer. Wave 109 publishes the inherited fixtures with their
incomplete provenance and exact comparison boundary. Future captures require
new IDs and retained environment/artifact identities rather than overwriting the
published observations.
