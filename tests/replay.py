#!/usr/bin/env python3
"""Replay input events from a bEMU JSON Lines trace."""

import argparse
import gzip
import json
import os
import subprocess
import sys
import tempfile


def parse_args():
    parser = argparse.ArgumentParser(description="Replay bEMU trace inputs")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--trace", default="datasets/golden-traces/v1/alive-boot-machine.jsonl")
    parser.add_argument("--output-trace", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--expect", default="Welcome to 1991")
    return parser.parse_args()


def load_trace(path):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def extract_boot(events):
    for event in events:
        if event.get("type") == "boot_start":
            return event.get("data", {})
    return None


def extract_script(events):
    parts = []
    for event in events:
        if event.get("type") != "input":
            continue
        data = event.get("data", {})
        if data.get("source") != "script":
            continue
        hex_text = data.get("hex", "")
        if not hex_text:
            continue
        raw = bytes.fromhex(hex_text)
        if data.get("bytes") != len(raw):
            raise ValueError("input hex is truncated or has the wrong byte count")
        parts.append(raw)
    return b"".join(parts)


def main():
    args = parse_args()
    for path in (args.bemu, args.trace):
        if not os.path.exists(path):
            print(f"missing artifact: {path}")
            return 1

    events = load_trace(args.trace)
    boot = extract_boot(events)
    if not boot:
        print("FAIL  no boot_start event in trace")
        return 1

    script = extract_script(events)
    if not script:
        print("FAIL  no script input events in trace")
        return 1

    kernel = boot.get("kernel", "build/kernel.bin")
    root = boot.get("root", "build/root.img")
    if not os.path.exists(kernel) and not os.path.isabs(kernel):
        kernel = os.path.join(os.path.dirname(args.trace), kernel)
    if not os.path.exists(root) and not os.path.isabs(root):
        root = os.path.join(os.path.dirname(args.trace), root)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        output_trace = args.output_trace or tf.name

    command = [
        args.bemu, "--kernel", kernel, "--root", root,
        "--keys", script.decode("utf-8", errors="replace"),
        "--expect", args.expect,
        "--trace-file", output_trace,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("FAIL  replay timed out")
        if not args.output_trace:
            os.unlink(output_trace)
        return 1

    if result.returncode != 0:
        print(f"FAIL  bEMU replay exited with status {result.returncode}")
        if not args.output_trace:
            os.unlink(output_trace)
        return 1

    replay_events = load_trace(output_trace)
    replay_script = extract_script(replay_events)
    if replay_script != script:
        print("FAIL  replayed script does not match original")
        if not args.output_trace:
            os.unlink(output_trace)
        return 1

    print(f"ok  replayed {len(events)} events -> {len(replay_events)} events")
    print(f"ok  script replayed exactly ({len(script)} bytes)")
    if args.output_trace:
        print(f"ok  wrote replay trace to {output_trace}")
    else:
        os.unlink(output_trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
