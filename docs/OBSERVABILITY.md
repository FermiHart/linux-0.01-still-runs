# Observability Event Schema

This document defines the machine-readable event schema used by bEMU for
deterministic observation, record and replay. The schema is intentionally
minimal: every event is a single line of JSON that can be appended to a trace
file without loss of structure.

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
| `ts` | integer | nanoseconds since `bootloader_start_ts` |
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
    "ram_mib": 8
  }
}
```

### `kvm_exit`

Emitted after every KVM exit.

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
    "port": 0x3f8,
    "size": 1,
    "value": 65
  }
}
```

### `irq`

Emitted when an IRQ is raised, lowered or acknowledged.

```json
{
  "ts": 1236,
  "type": "irq",
  "data": {
    "irq": 1,
    "action": "pulse"
  }
}
```

Valid actions: `raise`, `lower`, `pulse`, `eoi`.

### `timer`

Emitted on PIT-related activity.

```json
{
  "ts": 1237,
  "type": "timer",
  "data": {
    "port": 0x40,
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
    "source": "script"
  }
}
```

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

Emitted when the guest takes a hardware or software interrupt.

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

The `ts` field is produced by a deterministic logical clock (`bemu/trace_clock.h`).
The clock is reset at machine creation and advances by one fixed quantum for every
observable event (currently one nanosecond per KVM exit).  It does **not** read the
host wall clock, so the same guest path yields identical `ts` values across runs.

When `SOURCE_DATE_EPOCH` is present in the environment, the clock uses it as the
boot epoch; otherwise the epoch is zero.  This makes the trace stable across
reproducible builds without depending on the host `time(NULL)`.

| Function | Meaning |
|---|---|
| `trace_clock_reset()` | Reset epoch and counters |
| `trace_clock_tick()` | Advance one quantum |
| `trace_clock_now()` | Current logical timestamp |
| `trace_clock_seq()` | Monotonic event sequence number |

## Producing traces

traces are emitted by bEMU when the `--trace-file PATH` command-line option is
used.  The file contains one JSON object per line.  Pass `-` to write the trace
to standard error.  Console UART bytes (`0x3f8`) are intentionally omitted from
`io_access` events to keep traces focused on device I/O and to avoid noise.

Example:

```bash
./build/bemu-linux01 --kernel build/kernel.bin --root build/root.img \
  --expect fermihart@linux01 --trace-file boot.trace
```

## Stability guarantees

- New event types may be added without bumping the trace version.
- Event payloads are additive: new fields may appear, but existing fields will not
  be removed or change type.
- The `ts` field is monotonic within a trace but is not comparable across traces
  unless both used the same `SOURCE_DATE_EPOCH` and wall-clock source.

## Replay invariants

For deterministic replay, the following events must reproduce identical
side-effects:

1. `io_access` `in` operations must return the same value.
2. `irq` events must arrive at the same guest instruction boundary.
3. `input` events must inject the same byte sequence at the same exit count.

Non-deterministic events such as wall-clock `ts` values are ignored during
replay comparison.

## Future work

Waves 064–074 will implement the actual trace producer in bEMU, the record and
replay engine, the golden-trace comparator and the timeline visualizer. This
schema is the contract those tools share.
