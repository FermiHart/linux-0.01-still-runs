#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Compare two bEMU JSON Lines traces under a declared normalization.

Timestamps and per-run counters are ignored; the comparison focuses on event
type order and payload values. Scheduling-sensitive events can be filtered via
--ignore-event and --ignore-port. Equality after filtering is not raw runtime
determinism or machine-state replay.
"""

import argparse
import gzip
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Compare two bEMU traces")
    parser.add_argument("left", help="first trace file (.jsonl or .jsonl.gz)")
    parser.add_argument("right", help="second trace file (.jsonl or .jsonl.gz)")
    parser.add_argument("--max-diff", type=int, default=10,
                        help="maximum differing events to print")
    parser.add_argument("--ignore-event", action="append", default=[],
                        help="ignore events of this type (may repeat)")
    parser.add_argument("--ignore-port", action="append", default=[],
                        help="ignore io_access to this port, decimal or hex (may repeat)")
    return parser.parse_args()


def parse_port(text):
    text = text.strip()
    if text.startswith("0x") or text.startswith("0X"):
        return int(text, 16)
    return int(text)


def load_trace(path):
    opener = gzip.open if path.endswith(".gz") else open
    events = []
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def normalize(event, ignore_events, ignore_ports):
    etype = event.get("type")
    if etype in ignore_events:
        return None
    data = event.get("data", {}).copy()
    data.pop("ts", None)
    if etype == "kvm_exit":
        data.pop("exit_count", None)
    if etype == "shutdown":
        data.pop("exits", None)
    if etype == "io_access" and data.get("port") in ignore_ports:
        return None
    return {"type": etype, "data": data}


def main():
    args = parse_args()
    ignore_ports = {parse_port(p) for p in args.ignore_port}
    left = [e for e in (normalize(ev, set(args.ignore_event), ignore_ports) for ev in load_trace(args.left)) if e is not None]
    right = [e for e in (normalize(ev, set(args.ignore_event), ignore_ports) for ev in load_trace(args.right)) if e is not None]

    diffs = 0
    i = 0
    while i < len(left) and i < len(right):
        if left[i] != right[i]:
            diffs += 1
            if diffs <= args.max_diff:
                print(f"diff at event {i}:")
                print(f"  left:  {json.dumps(left[i])}")
                print(f"  right: {json.dumps(right[i])}")
        i += 1

    if len(left) != len(right):
        diffs += 1
        print(f"length mismatch: left={len(left)} right={len(right)}")

    if diffs:
        print(f"FAIL  {diffs} difference(s) found")
        return 1

    print(f"ok  {len(left)} events match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
