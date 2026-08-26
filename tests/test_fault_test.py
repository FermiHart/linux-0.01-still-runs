#!/usr/bin/env python3
"""Verify fault-test ordering and failure propagation with a probe command."""

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_TARGETS = (
    "test-bemu-loading",
    "test-ide-faults",
    "test-fs-corruption",
    "test-irq-faults",
    "test-irq-faults-kvm",
    "test-keyboard-faults",
    "test-trace-input",
    "test-artifact-truncation",
    "test-bbp-corruption",
    "test-bbp-corruption-sanitized",
    "test-power-cut",
)


def jobserver_available():
    match = re.search(r"--jobserver-(?:auth|fds)=([^ ]+)", os.environ.get("MAKEFLAGS", ""))
    if not match:
        return False
    auth = match.group(1)
    if auth.startswith("fifo:"):
        return os.path.exists(auth[5:])
    try:
        read_fd, write_fd = (int(value) for value in auth.split(",", 1))
        os.fstat(read_fd)
        os.fstat(write_fd)
    except (OSError, ValueError):
        return False
    return True


def probe(log_path, fail_target, require_jobserver, target):
    if require_jobserver and not jobserver_available():
        return 24
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(target + "\n")
    return 23 if target == fail_target else 0


def read_log(path):
    with open(path, "r", encoding="utf-8") as log:
        return tuple(line.rstrip("\n") for line in log)


def run_fault_test(make_command, fail_target=None, require_jobserver=False):
    with tempfile.TemporaryDirectory(prefix="fault-test-orchestration-") as temp_dir:
        log_path = os.path.join(temp_dir, "targets.log")
        probe_command = [sys.executable, os.path.abspath(__file__), "--probe", log_path]
        if fail_target:
            probe_command.extend(("--fail-target", fail_target))
        if require_jobserver:
            probe_command.append("--require-jobserver")

        result = subprocess.run(
            [
                make_command,
                "--no-print-directory",
                "-j2" if require_jobserver else "-j1",
                "NO_COLOR=1",
                "fault-test",
                f"FAULT_TEST_COMMAND={shlex.join(probe_command)}",
            ],
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        targets = read_log(log_path) if os.path.exists(log_path) else ()
        return result, targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--make", default="make")
    parser.add_argument("--probe")
    parser.add_argument("--fail-target")
    parser.add_argument("--require-jobserver", action="store_true")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args()

    if args.probe:
        if not args.target:
            parser.error("probe mode requires a target")
        return probe(args.probe, args.fail_target, args.require_jobserver, args.target)

    success, targets = run_fault_test(args.make, require_jobserver=True)
    assert success.returncode == 0, success.stderr
    assert targets == EXPECTED_TARGETS, (targets, EXPECTED_TARGETS)

    fail_target = "test-fs-corruption"
    failure, targets = run_fault_test(args.make, fail_target)
    fail_index = EXPECTED_TARGETS.index(fail_target)
    assert failure.returncode != 0, "fault-test hid a failing scenario"
    assert targets == EXPECTED_TARGETS[:fail_index + 1], targets

    print("fault-test runs every cataloged target once and stops on failure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
