#!/usr/bin/env python3
"""Generate a text timeline summary from a bEMU JSON Lines trace."""

import argparse
import gzip
import json
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="bEMU trace timeline visualizer")
    parser.add_argument("trace", help="trace file (.jsonl or .jsonl.gz)")
    parser.add_argument("--width", type=int, default=60,
                        help="histogram width in characters")
    parser.add_argument("--output", "-o", default=None,
                        help="output file (default: stdout)")
    return parser.parse_args()


def load_trace(path):
    opener = gzip.open if path.endswith(".gz") else open
    events = []
    with opener(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def bucket(events, width):
    if not events:
        return []
    first_ts = events[0]["ts"]
    last_ts = events[-1]["ts"]
    span = max(last_ts - first_ts, 1)
    buckets = [0] * width
    for event in events:
        idx = int((event["ts"] - first_ts) * (width - 1) / span)
        buckets[idx] += 1
    return buckets


def bar(buckets, width, max_count):
    if not max_count:
        return [" " * width for _ in buckets]
    chars = " ▁▂▃▄▅▆▇█"
    lines = []
    for count in buckets:
        level = int(count * (len(chars) - 1) / max_count)
        lines.append(chars[level])
    return lines


def main():
    args = parse_args()
    events = load_trace(args.trace)
    if not events:
        print("no events in trace", file=sys.stderr)
        return 1

    counts = {}
    for event in events:
        counts[event["type"]] = counts.get(event["type"], 0) + 1

    first_ts = events[0]["ts"]
    last_ts = events[-1]["ts"]
    span = last_ts - first_ts

    buckets = bucket(events, args.width)
    max_count = max(buckets) if buckets else 0
    bars = bar(buckets, args.width, max_count)

    lines = []
    lines.append("bEMU trace timeline")
    lines.append(f"  events:   {len(events)}")
    lines.append(f"  span:     {span} logical ns")
    lines.append("  types:")
    for etype, count in sorted(counts.items(), key=lambda x: -x[1]):
        lines.append(f"    {etype:12s} {count:8d}")
    lines.append("")
    lines.append("  event density over time:")
    lines.append("  " + "".join(bars))
    lines.append(f"  ts={first_ts}" + " " * (args.width - len(str(first_ts)) - len(str(last_ts))) + f"ts={last_ts}")

    out = "\n".join(lines) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
