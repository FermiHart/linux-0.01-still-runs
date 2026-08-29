#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Validate the public fault catalog's static contract against the source tree."""

import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(REPO_ROOT, "docs", "FAULT-CATALOG.md")
MAKEFILE_PATH = os.path.join(REPO_ROOT, "Makefile")

EXPECTED_TARGETS = {
    "096": {"test-bemu-loading"},
    "097": {"test-ide-faults"},
    "098": {"test-fs-corruption"},
    "099": {"test-irq-faults", "test-irq-faults-kvm"},
    "100": {"test-keyboard-faults", "test-trace-input"},
    "101": {"test-artifact-truncation"},
    "102": {"test-bbp-corruption", "test-bbp-corruption-sanitized"},
    "103": {"test-power-cut"},
}

EXPECTED_LAYERS = {
    "096": {"host-only", "pre-KVM process"},
    "097": {"host-only"},
    "098": {"offline filesystem"},
    "099": {"host-only", "KVM irqchip"},
    "100": {"host-only", "KVM"},
    "101": {"pre-KVM process"},
    "102": {"host-only"},
    "103": {"host-only", "offline filesystem"},
}

REQUIRED_EVIDENCE = {
    "096": {"tests/bemu/test_memory_loader.c", "tests/test_loading_limits.py"},
    "097": {"tests/bemu/test_ide_faults.c"},
    "098": {"tests/test_fs_corruption.py"},
    "099": {"tests/bemu/test_irq_faults.c", "tests/bemu/test_irq_faults_kvm.c"},
    "100": {"tests/bemu/test_keyboard_faults.c", "tests/test_trace_input.py"},
    "101": {"tests/test_artifact_truncation.py"},
    "102": {"tests/bemu/test_bbp_corruption.c"},
    "103": {"tests/bemu/test_ide_power_cut.c", "tests/test_power_cut.py"},
}

REQUIRED_SOURCE_ANCHORS = {
    "096": {
        "tests/bemu/test_memory_loader.c": ("all memory/loader tests passed",),
        "tests/test_loading_limits.py": ("kernel rejected before KVM entry",),
    },
    "097": {
        "tests/bemu/test_ide_faults.c":
            ("all IDE fault-injection tests passed", "ERR without DRQ", "ATA abort state"),
    },
    "098": {
        "tests/test_fs_corruption.py":
            ("deterministic filesystem corruption test passed", "marked not in use"),
    },
    "099": {
        "tests/bemu/test_irq_faults.c":
            ("all IRQ fault-injection tests passed", "fault_duplicate_replayed"),
        "tests/bemu/test_irq_faults_kvm.c":
            ("all KVM IRQ fault-injection tests passed", "KVM_GET_IRQCHIP"),
    },
    "100": {
        "tests/bemu/test_keyboard_faults.c":
            ("all keyboard fault-injection tests passed",),
        "tests/test_trace_input.py":
            ("discarded truncated stdin escape sequence", "RESULT: PASS"),
    },
    "101": {
        "tests/test_artifact_truncation.py": (
            "kernel image has no valid L01KIMG1 trailer",
            "root image does not match 977/5/17 CHS geometry",
            "canonical kernel and root artifacts remain unchanged",
        ),
    },
    "102": {
        "tests/bemu/test_bbp_corruption.c":
            ("BBP_ERR_TAG_CHECKSUM", "BBP_ERR_SIZE", "all production BBP corruption tests passed"),
    },
    "103": {
        "tests/bemu/test_ide_power_cut.c":
            ("all deterministic IDE power-cut tests passed", "committed_sectors", "irq_raises"),
        "tests/test_power_cut.py":
            ("deterministic IDE power-cut image test passed", "changed_bytes", "irq_raises"),
    },
}

REQUIRED_CATALOG_ANCHORS = {
    "096": ("exit 1", "kernel is empty", "all memory/loader tests passed"),
    "097": ("abort code 4", "IRQ14", "all IDE fault-injection tests passed"),
    "098": ("exits 8", "and 4 for the zone bitmap", "deterministic filesystem corruption test passed"),
    "099": ("fault_drop", "fault_duplicate_replayed", "KVM IRR"),
    "100": ("discarded truncated stdin escape sequence", "RESULT: PASS"),
    "101": ("exit 1", "977/5/17 CHS geometry", "unchanged SHA-256 hashes"),
    "102": ("BBP_ERR_TAG_CHECKSUM", "24 corruptions", "all production BBP corruption tests passed"),
    "103": ("0, 512, or 1024-byte", "IRQ count", "deterministic IDE power-cut image test passed"),
}

REQUIRED_MAKE_BINDINGS = {
    "096": ("test-bemu-loading: $(BUILD)/test-memory-loader", "tests/test_loading_limits.py"),
    "097": ("test-ide-faults: $(BUILD)/test-ide-faults", "tests/bemu/test_ide_faults.c"),
    "098": ("test-fs-corruption:", "tests/test_fs_corruption.py"),
    "099": ("test-irq-faults: $(BUILD)/test-irq-faults", "test-irq-faults-kvm: $(BUILD)/test-irq-faults-kvm"),
    "100": ("test-keyboard-faults: $(BUILD)/test-keyboard-faults", "test-trace-input: require-artifacts"),
    "101": ("test-artifact-truncation:", "tests/test_artifact_truncation.py"),
    "102": ("test-bbp-corruption: $(BUILD)/test-bbp-corruption", "test-bbp-corruption-sanitized: $(BUILD)/test-bbp-corruption-sanitized"),
    "103": ("test-ide-power-cut: $(BUILD)/test-ide-power-cut", "test-power-cut: $(BUILD)/test-ide-power-cut"),
}

REQUIRED_FIELDS = (
    "Fault",
    "Run",
    "Layer",
    "Expected response",
    "Observed response",
    "Evidence",
    "Artifact policy",
    "Requirements",
    "Does not prove",
)


def fail(message):
    raise AssertionError(message)


def field(block, name, wave):
    match = re.search(rf"^- \*\*{re.escape(name)}:\*\* (.+)$", block, re.MULTILINE)
    if not match:
        fail(f"Wave {wave} is missing the {name!r} field")
    return match.group(1)


def main():
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as source:
            catalog = source.read()
    except FileNotFoundError:
        fail("docs/FAULT-CATALOG.md is missing")

    with open(MAKEFILE_PATH, "r", encoding="utf-8") as source:
        makefile = source.read()

    headings = list(re.finditer(r"^## Wave (\d{3})\b.*$", catalog, re.MULTILINE))
    waves = [match.group(1) for match in headings]
    if waves != list(EXPECTED_TARGETS):
        fail(f"expected Waves 096-103 exactly once and in order, got {waves}")

    for index, heading in enumerate(headings):
        wave = heading.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(catalog)
        block = catalog[heading.end():end]

        values = {name: field(block, name, wave) for name in REQUIRED_FIELDS}

        for anchor in REQUIRED_CATALOG_ANCHORS[wave]:
            if anchor not in block:
                fail(f"Wave {wave} lost catalog claim anchor {anchor!r}")

        for binding in REQUIRED_MAKE_BINDINGS[wave]:
            if binding not in makefile:
                fail(f"Wave {wave} lost Make binding {binding!r}")

        targets = set(re.findall(r"`make ([a-z0-9-]+)`", values["Run"]))
        if targets != EXPECTED_TARGETS[wave]:
            fail(
                f"Wave {wave} targets are {sorted(targets)}, "
                f"expected {sorted(EXPECTED_TARGETS[wave])}"
            )
        for target in targets:
            if not re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE):
                fail(f"Wave {wave} references undefined Make target {target!r}")

        layers = set(re.findall(r"`([^`]+)`", values["Layer"]))
        if layers != EXPECTED_LAYERS[wave]:
            fail(
                f"Wave {wave} layers are {sorted(layers)}, "
                f"expected {sorted(EXPECTED_LAYERS[wave])}"
            )

        evidence = set(re.findall(r"`([^`]+)`", values["Evidence"]))
        missing_evidence = REQUIRED_EVIDENCE[wave] - evidence
        if missing_evidence:
            fail(f"Wave {wave} is missing evidence: {sorted(missing_evidence)}")
        for path in evidence:
            if not os.path.isfile(os.path.join(REPO_ROOT, path)):
                fail(f"Wave {wave} references missing evidence file {path!r}")
            if path not in makefile:
                fail(f"Wave {wave} evidence is not wired into Make: {path!r}")

        for path, anchors in REQUIRED_SOURCE_ANCHORS[wave].items():
            with open(os.path.join(REPO_ROOT, path), "r", encoding="utf-8") as source:
                evidence_source = source.read()
            for anchor in anchors:
                if anchor not in evidence_source:
                    fail(f"Wave {wave} evidence {path!r} lost source anchor {anchor!r}")

        for name in ("Expected response", "Observed response", "Does not prove"):
            if len(values[name]) < 20:
                fail(f"Wave {wave} has an underspecified {name!r} field")

    print("fault catalog covers Waves 096-103 and references live evidence")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"fault catalog check failed: {error}", file=sys.stderr)
        sys.exit(1)
