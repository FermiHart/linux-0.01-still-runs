# Golden Trace Dataset v1

This dataset publishes two inherited alive-profile regression observations:
one decoded console transcript and one raw bEMU JSON Lines event stream. Their
bytes are pinned to Git commit `14638cf9deb708680a3c58266bb4c71a865355ea`.
They were separate captures and do not share a run ID.

## Contents

- `alive-boot-console.trace`: merged stdout/stderr decoded with replacement and
  stripped of trailing horizontal whitespace by the historical capture tool.
- `alive-boot-machine.jsonl`: 23,529 raw events under trace schema version 1.
- `trace-event-v1.schema.json`: exact event envelope and payload definitions.
- `MANIFEST.json`: stable IDs, raw statistics, input join, comparison policy,
  normalized identity, missing provenance and explicit non-claims.
- `SHA256SUMS.txt`: checksums for every other dataset file.

Run `make test-golden-trace-dataset` for offline verification. New captures are
written under `build/golden-candidates/`; they must receive new IDs and complete
capture manifests rather than silently replacing these inherited observations.

## Comparison Boundary

Policy `observable-compare-v1` removes logical timestamps, KVM/shutdown counters,
all IRQ events, and I/O events on ports `0x71`, `0x60`, `0x61`, `0x3d4`, `0x3d5`,
and `0x1f0`. It then compares the remaining events positionally with exact type
and payload equality. For the published machine trace this excludes 22,917 of
23,529 events and retains 612; the normalized stream is identified by its
canonical SHA-256 in the manifest.

Replay reconstructs the 24-byte scripted input. It does not restore registers,
RAM, device state, IRQ timing or I/O read results. These traces therefore do not
establish machine-state replay, full runtime determinism, both-profile coverage,
or equivalence with physical 1991 hardware.

## Provenance Boundary

The trace payloads last changed in historical commit
`1ccb77fef673bcd8e64fed40ee99998692377a89`, but no capture commit, dirty state,
host/KVM identity, artifact hashes, environment manifest or process status was
retained with either run. The manifest records those identities as missing
rather than inferring them from current builds.
