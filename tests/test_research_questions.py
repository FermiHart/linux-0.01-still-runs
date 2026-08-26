#!/usr/bin/env python3
"""Validate the public research questions and their evidence references."""

import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENT_PATH = os.path.join(REPO_ROOT, "docs", "RESEARCH-QUESTIONS.md")
MAKEFILE_PATH = os.path.join(REPO_ROOT, "Makefile")
MISSION_PATH = os.path.join(REPO_ROOT, "MISSION.md")

EXPECTED_QUESTIONS = {
    "RQ1": "Which Linux 0.01 assumptions fail in the documented modern execution environment?",
    "RQ2": "What minimum adaptation set is necessary and sufficient to reach the declared execution boundary?",
    "RQ3": "How do compiler version, target ABI, and optimization level affect the reduced GNU89-era cases?",
    "RQ4": "How can behavioral fidelity be measured as explicit dimensions in executable software archaeology?",
    "RQ5": "Which parts of the historical operating-system experience are reproducible under controlled inputs?",
}

EXPECTED_TARGETS = {
    "RQ1": {"provenance", "audit", "doctor", "test"},
    "RQ2": {"test-quick", "test-bemu-loading", "test-artifact-truncation", "bbp-conformance"},
    "RQ3": {"compiler-cases", "compare-assembly", "compiler-audit", "compiler-matrix"},
    "RQ4": {"test-experiences", "test-fs-inspect", "test-trace-workflow", "fault-test"},
    "RQ5": {"verify-reproducible", "test-rtc", "compare-trace", "fault-test"},
}

REQUIRED_EVIDENCE = {
    "RQ1": {"docs/PORTING_LEDGER.md", "docs/AUDIT-STATEMENTS.md"},
    "RQ2": {"docs/PORTING_LEDGER.md", "tests/test_boot.py"},
    "RQ3": {"tests/compiler-cases/README.md", "tests/compiler-cases/CLASSIFICATION.md"},
    "RQ4": {"EXPERIENCE.md", "tests/test_experience.py", "docs/FAULT-CATALOG.md"},
    "RQ5": {"docs/REPRODUCIBILITY.md", "tests/compare_trace.py", "tests/test_power_cut.py"},
}

REQUIRED_FIELDS = (
    "Question",
    "Scope",
    "Run",
    "Evidence",
    "Measures",
    "Answer criterion",
    "Limits",
)

REQUIRED_LIMIT_ANCHORS = {
    "RQ1": "current reports do not retain complete host identity",
    "RQ2": "no complete ablation matrix",
    "RQ3": "no full compiler-version/ABI cross-product",
    "RQ4": "no scalar fidelity score",
    "RQ5": "does not prove full event-by-event runtime determinism",
}

MISSION_QUESTION_ANCHORS = (
    "Which assumptions in Linux 0.01 became invalid",
    "What is the minimum set of adaptations required",
    "How do modern compiler optimizations interact",
    "How can we measure behavioral fidelity",
    "Can a historical operating-system experience be reproduced deterministically",
)


def fail(message):
    raise AssertionError(message)


def field(block, name, rq):
    match = re.search(rf"^- \*\*{re.escape(name)}:\*\* (.+)$", block, re.MULTILINE)
    if not match:
        fail(f"{rq} is missing the {name!r} field")
    return match.group(1)


def main():
    try:
        with open(DOCUMENT_PATH, "r", encoding="utf-8") as source:
            document = source.read()
    except FileNotFoundError:
        fail("docs/RESEARCH-QUESTIONS.md is missing")

    with open(MAKEFILE_PATH, "r", encoding="utf-8") as source:
        makefile = source.read()
    with open(MISSION_PATH, "r", encoding="utf-8") as source:
        mission = source.read()

    for anchor in MISSION_QUESTION_ANCHORS:
        if anchor not in mission:
            fail(f"MISSION.md lost canonical question {anchor!r}")
    if "docs/RESEARCH-QUESTIONS.md" not in mission:
        fail("MISSION.md does not link the operational research questions")
    if "Wave 107 will consolidate the experimental" not in document:
        fail("the Wave 107 methodology boundary is missing")

    headings = list(re.finditer(r"^## (RQ\d+)\b.*$", document, re.MULTILINE))
    ids = [heading.group(1) for heading in headings]
    if ids != list(EXPECTED_QUESTIONS):
        fail(f"expected RQ1-RQ5 exactly once and in order, got {ids}")

    for index, heading in enumerate(headings):
        rq = heading.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        block = document[heading.end():end]
        values = {name: field(block, name, rq) for name in REQUIRED_FIELDS}

        if values["Question"] != EXPECTED_QUESTIONS[rq]:
            fail(f"{rq} changed its canonical question")

        targets = set(re.findall(r"`make ([a-z0-9-]+)`", values["Run"]))
        if targets != EXPECTED_TARGETS[rq]:
            fail(f"{rq} targets are {sorted(targets)}, expected {sorted(EXPECTED_TARGETS[rq])}")
        for target in targets:
            if not re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE):
                fail(f"{rq} references undefined Make target {target!r}")

        evidence = set(re.findall(r"`([^`]+)`", values["Evidence"]))
        if not REQUIRED_EVIDENCE[rq].issubset(evidence):
            fail(f"{rq} is missing required evidence paths")
        for path in evidence:
            if not os.path.isfile(os.path.join(REPO_ROOT, path)):
                fail(f"{rq} references missing evidence file {path!r}")

        for name in ("Scope", "Measures", "Answer criterion", "Limits"):
            if len(values[name]) < 30:
                fail(f"{rq} has an underspecified {name!r} field")
        if REQUIRED_LIMIT_ANCHORS[rq] not in values["Limits"]:
            fail(f"{rq} lost its key epistemic limit")

    print("research questions RQ1-RQ5 are scoped to live evidence")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"research-question check failed: {error}", file=sys.stderr)
        sys.exit(1)
