#!/usr/bin/env python3
"""Validate the operational reproduction appendix and its public integration."""

import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPENDIX_PATH = os.path.join(REPO_ROOT, "docs", "REPRODUCTION.md")

REQUIRED_SECTIONS = (
    "Scope",
    "Prerequisites",
    "Clean clone",
    "Behavioral validation",
    "Two-build verification",
    "One-command artifact build",
    "Expected outputs",
    "Timing",
    "Troubleshooting",
    "Known limits",
)

REQUIRED_COMMANDS = (
    "git clone https://github.com/fermihart/linux-0.01-still-runs",
    "git rev-parse --is-shallow-repository",
    "make doctor",
    "SOURCE_DATE_EPOCH=1700000000 make reproducible artifact",
    "make -j8 ci",
    "make test-fs-persistence",
    "make verify-reproducible",
    "(cd build && sha256sum --check SHA256SUMS)",
)

REQUIRED_OUTPUTS = (
    "build/kernel.bin",
    "build/root.img",
    "build/root-1991.img",
    "build/bemu-linux01",
    "build/SHA256SUMS",
    "build/REPRODUCIBLE.sha256",
    "release/linux-0.01-still-runs-<rev>.tar.gz",
)

REQUIRED_BOUNDARIES = (
    "i386 guest/kernel",
    "Linux/x86-64 host",
    "not a port of the kernel to the x86-64 ISA",
    "no supported fallback backend",
    "one deterministic build",
    "two copied-tree builds",
    "not a self-contained source package",
    "embedded manifest is not a bundle manifest",
    "outer tarball bytes are not claimed reproducible",
    "transfer-integrity hash",
    "make toolchain does not provision hosted multilib",
    "CI removes build/REPRODUCIBLE.sha256",
    "not machine-state replay",
    "Orderly cross-process persistence is proven only",
    "independent third-party reproduction has not yet occurred",
    "no DOI or archival deposit exists yet",
    "estimates, not guarantees",
)

INTEGRATION_REFERENCES = {
    "README.md": "docs/REPRODUCTION.md",
    "docs/PAPER.md": "docs/REPRODUCTION.md",
    "docs/REPRODUCIBILITY.md": "docs/REPRODUCTION.md",
    "scripts/release-check.sh": "docs/REPRODUCTION.md",
    ".github/workflows/build.yml": "test-reproduction-appendix",
    "Makefile": "test-reproduction-appendix:",
}


def fail(message):
    raise AssertionError(message)


def section_blocks(document):
    headings = list(re.finditer(r"^## (.+)$", document, re.MULTILINE))
    blocks = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        blocks[heading.group(1)] = document[heading.end():end]
    return headings, blocks


def read(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as source:
        return source.read()


def main():
    try:
        appendix = read("docs/REPRODUCTION.md")
    except FileNotFoundError:
        fail("docs/REPRODUCTION.md is missing")

    word_count = len(re.findall(r"\b[\w'-]+\b", appendix))
    if not 900 <= word_count <= 2200:
        fail(f"reproduction appendix has {word_count} words, expected 900-2200")

    headings, blocks = section_blocks(appendix)
    actual_sections = [heading.group(1) for heading in headings]
    if actual_sections != list(REQUIRED_SECTIONS):
        fail(f"appendix sections are {actual_sections!r}, expected {list(REQUIRED_SECTIONS)!r}")

    for command in REQUIRED_COMMANDS:
        if command not in appendix:
            fail(f"appendix is missing exact command {command!r}")

    for output in REQUIRED_OUTPUTS:
        if f"`{output}`" not in appendix:
            fail(f"appendix is missing expected output {output!r}")

    normalized = re.sub(r"\s+", " ", appendix)
    for boundary in REQUIRED_BOUNDARIES:
        if boundary not in normalized:
            fail(f"appendix lost evidence boundary {boundary!r}")

    prerequisites = blocks["Prerequisites"]
    for prerequisite in ("/dev/kvm", "fsck.minix", "NASM", "multilib", "full Git history"):
        if prerequisite not in prerequisites:
            fail(f"appendix prerequisites omit {prerequisite!r}")

    timing = blocks["Timing"]
    if "measured" not in timing or "timeout" not in timing:
        fail("appendix does not distinguish measured time from timeout ceilings")

    troubleshooting = blocks["Troubleshooting"]
    for symptom in ("Permission denied", "shallow", "static PIE", "-m32", "fsck.minix"):
        if symptom not in troubleshooting:
            fail(f"appendix troubleshooting omits {symptom!r}")

    makefile = read("Makefile")
    for target in ("doctor", "reproducible", "artifact", "ci", "verify-reproducible"):
        if not re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE):
            fail(f"documented Make target {target!r} is not defined")

    doctor_match = re.search(r"^doctor:\n(?P<body>.*?)(?=^info:)", makefile, re.MULTILINE | re.DOTALL)
    if doctor_match is None:
        fail("could not inspect the make doctor implementation")
    doctor = doctor_match.group("body")
    for tool in ("tar", "gzip", "readelf", "dd", "sha256sum", "gcc"):
        if tool not in doctor:
            fail(f"make doctor does not check required reproduction tool {tool!r}")
    if (
        "gcc -m32 -no-pie" not in doctor
        or "host-i386" not in doctor
        or "#include <stdio.h>" not in doctor
    ):
        fail("make doctor does not compile and execute a hosted i386 libc/header probe")

    for path, anchor in INTEGRATION_REFERENCES.items():
        if anchor not in read(path):
            fail(f"{path} does not expose appendix integration anchor {anchor!r}")

    artifact_script = read("scripts/make-artifact.sh")
    if "docs/" not in artifact_script:
        fail("the academic tarball does not package the reproduction appendix")
    packaged_outputs = set(re.findall(r"\bbuild/([A-Za-z0-9_.-]+)", artifact_script))
    required_packaged = {
        "kernel.bin",
        "root.img",
        "root-1991.img",
        "bemu-linux01",
        "SHA256SUMS",
        "REPRODUCIBLE.sha256",
    }
    if not required_packaged <= packaged_outputs:
        fail(f"artifact script lost required outputs {sorted(required_packaged - packaged_outputs)!r}")
    for packaged_tree in ("docs/", "datasets/", "LICENSE", "README.md"):
        if packaged_tree not in artifact_script:
            fail(f"artifact script lost documented package input {packaged_tree!r}")
    if "SOURCE_DATE_EPOCH=1700000000 make reproducible artifact" not in artifact_script:
        fail("artifact failure diagnostic does not name the sufficient recovery command")
    tar_is_normalized = all(
        anchor in artifact_script for anchor in ("--sort=name", "--mtime", "--owner", "--group")
    ) and "gzip -n" in artifact_script
    if not tar_is_normalized and "outer tarball bytes are not claimed reproducible" not in appendix:
        fail("appendix does not disclose that current tar metadata is not normalized")

    if "SOURCE_DATE_EPOCH=1700000000 make reproducible artifact" not in blocks["One-command artifact build"]:
        fail("the primary one-command build is not in its operational section")
    if "make -j8 ci" not in blocks["Behavioral validation"]:
        fail("the behavioral gate is not separated from artifact construction")
    if "make verify-reproducible" not in blocks["Two-build verification"]:
        fail("the two-build comparator is not separated from make reproducible")
    if actual_sections.index("One-command artifact build") < actual_sections.index("Two-build verification"):
        fail("artifact construction must be documented after gates that clean its outputs")

    print("reproduction appendix is operational, bounded, and publicly integrated")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"reproduction appendix check failed: {error}", file=sys.stderr)
        sys.exit(1)
