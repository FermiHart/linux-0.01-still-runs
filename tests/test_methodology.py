#!/usr/bin/env python3
"""Validate the public methodology's structure and live references."""

import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENT_PATH = os.path.join(REPO_ROOT, "docs", "METHODOLOGY.md")
MAKEFILE_PATH = os.path.join(REPO_ROOT, "Makefile")

REQUIRED_SECTIONS = (
    "Status vocabulary",
    "Experimental environment",
    "Common run envelope",
    "RQ1 - Invalidated assumptions",
    "RQ2 - Adaptation-set minimality",
    "RQ3 - Compiler experiments",
    "RQ4 - Behavioral fidelity",
    "RQ5 - Reproducibility layers",
    "Oracle independence",
    "Evidence retention",
    "Analysis and reporting rules",
    "Threats to validity",
)

REQUIRED_PATHS = (
    "docs/RESEARCH-QUESTIONS.md",
    "docs/PORTING_LEDGER.md",
    "tests/test_boot.py",
    "tests/compiler-cases/Makefile",
    "tests/test_experience.py",
    "tests/compare_trace.py",
    "tests/test_power_cut.py",
    "scripts/verify-reproducibility.sh",
    "datasets/patches/MANIFEST.json",
    "datasets/patches/file_deltas.csv",
    "datasets/patches/adaptations.csv",
)

REQUIRED_SECTION_ANCHORS = {
    "Status vocabulary": ("`IMPLEMENTED`", "`PARTIAL`", "`PROPOSED`"),
    "Common run envelope": (
        "No aggregate RQ runner currently enforces this envelope",
        "failed and missing cells",
        "Selection of only passing commands",
    ),
    "RQ1 - Invalidated assumptions": (
        "Current status: `PARTIAL`",
        "do not bind a ledger",
        "proven invalidation only when the baseline",
        "53 source-path deltas",
        "nine unresolved ledger joins",
    ),
    "RQ2 - Adaptation-set minimality": (
        "`PARTIAL` for sufficiency and `PROPOSED` for minimality",
        "one sufficient observed configuration",
        "not a predeclared candidate universe",
        "No candidate universe, dependency graph, subset generator",
    ),
    "RQ3 - Compiler experiments": (
        "18 cells",
        "nine x86-64 cells per name",
        "not a compiler-version/ABI cross-product",
        "Publication of that dataset remains Wave 110",
    ),
    "RQ4 - Behavioral fidelity": (
        "Current status: `IMPLEMENTED` as multidimensional conformance",
        "one session per profile",
        "one alive-image audit",
        "one record and one replay",
        "mostly one execution per vector",
        "not a user study",
    ),
    "RQ5 - Reproducibility layers": (
        "exactly two independent build directories",
        "one conversion per controlled profile/input",
        "one golden-versus-replay comparison",
        "two repeats per profile/scenario",
        "each of eight scenarios for each profile runs twice",
        "Sanitized versus optimized execution is a configuration comparison, not a repeat",
        "not complete machine state",
    ),
    "Oracle independence": (
        "External independent",
        "Repository-independent implementation",
        "Production integration",
        "Production-linked white-box",
        "Self-report",
    ),
    "Evidence retention": (
        "usually overwritten or deleted",
        "zero paired RQ1 observations and zero RQ2 ablation configurations",
        "The common run envelope is therefore `PROPOSED`, not implemented",
        "Waves 108-110",
    ),
    "Analysis and reporting rules": ("No inferential statistics", "failed and missing cells"),
    "Threats to validity": ("RQ2 ablation", "complete machine replay", "third-party reproduction"),
}

EXPECTED_RQ_TARGETS = {
    "RQ1 - Invalidated assumptions": {"provenance", "audit", "doctor", "test"},
    "RQ2 - Adaptation-set minimality":
        {"test-quick", "test-bemu-loading", "test-artifact-truncation", "bbp-conformance"},
    "RQ3 - Compiler experiments":
        {"compiler-cases", "compare-assembly", "compiler-audit", "compiler-matrix"},
    "RQ4 - Behavioral fidelity":
        {"test-experiences", "test-fs-inspect", "test-trace-workflow", "fault-test"},
    "RQ5 - Reproducibility layers":
        {"verify-reproducible", "test-rtc", "compare-trace", "fault-test"},
}

FORBIDDEN_CLAIMS = (
    "complete runtime determinism is proven",
    "the minimum adaptation set is proven",
    "behaviorally identical to 1991 hardware",
)


def fail(message):
    raise AssertionError(message)


def main():
    try:
        with open(DOCUMENT_PATH, "r", encoding="utf-8") as source:
            document = source.read()
    except FileNotFoundError:
        fail("docs/METHODOLOGY.md is missing")

    with open(MAKEFILE_PATH, "r", encoding="utf-8") as source:
        makefile = source.read()

    headings = list(re.finditer(r"^## (.+)$", document, re.MULTILINE))
    sections = [heading.group(1) for heading in headings]
    for section in REQUIRED_SECTIONS:
        if section not in sections:
            fail(f"missing methodology section {section!r}")

    blocks = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        blocks[heading.group(1)] = document[heading.end():end]

    for section, anchors in REQUIRED_SECTION_ANCHORS.items():
        normalized = re.sub(r"\s+", " ", blocks[section])
        for anchor in anchors:
            if anchor not in normalized:
                fail(f"section {section!r} lost methodology boundary {anchor!r}")

    lowered = document.lower()
    for claim in FORBIDDEN_CLAIMS:
        if claim in lowered:
            fail(f"forbidden unsupported claim present: {claim!r}")

    for path in REQUIRED_PATHS:
        if f"`{path}`" not in document:
            fail(f"methodology does not cite {path!r}")
        if not os.path.isfile(os.path.join(REPO_ROOT, path)):
            fail(f"methodology references missing file {path!r}")

    targets = set(re.findall(r"`make (?:-j8 )?([a-z0-9-]+)`", document))
    if len(targets) < 12:
        fail(f"methodology references too few executable targets: {sorted(targets)}")
    for target in targets:
        if not re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE):
            fail(f"methodology references undefined Make target {target!r}")

    for section, expected in EXPECTED_RQ_TARGETS.items():
        actual = set(re.findall(r"`make ([a-z0-9-]+)`", blocks[section]))
        if actual != expected:
            fail(f"section {section!r} targets are {sorted(actual)}, expected {sorted(expected)}")

    rq5 = re.sub(r"\s+", " ", blocks["RQ5 - Reproducibility layers"])
    port_sentence = re.search(
        r"The standard workflow also excludes all IRQ events and I/O ports (.+?)\.", rq5
    )
    if port_sentence is None:
        fail("RQ5 trace-filter sentence is missing")
    trace_ports = set(re.findall(r"`(0x[0-9a-f]+)`", port_sentence.group(1)))
    expected_ports = {"0x71", "0x60", "0x61", "0x3d4", "0x3d5", "0x1f0"}
    if trace_ports != expected_ports:
        fail(f"trace filter ports are {sorted(trace_ports)}, expected {sorted(expected_ports)}")

    rq_sections = re.findall(r"^## (RQ\d+)\b", document, re.MULTILINE)
    if rq_sections != ["RQ1", "RQ2", "RQ3", "RQ4", "RQ5"]:
        fail(f"expected exactly RQ1-RQ5 methodology sections, got {rq_sections}")

    print("methodology distinguishes implemented, partial, and proposed procedures")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"methodology check failed: {error}", file=sys.stderr)
        sys.exit(1)
