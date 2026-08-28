#!/usr/bin/env python3
"""Validate the technical paper's structure, evidence, and public integration."""

import ast
import json
import os
import re
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPER_PATH = os.path.join(REPO_ROOT, "docs", "PAPER.md")

REQUIRED_SECTIONS = (
    "Abstract",
    "1. Introduction",
    "2. Related work",
    "3. Artifact architecture",
    "4. Experimental methodology",
    "5. Published datasets",
    "6. Results",
    "7. Fault model and bounded responses",
    "8. Discussion",
    "9. Threats to validity",
    "10. Reproducibility boundary",
    "11. Conclusion",
    "Data availability",
    "References",
)

REQUIRED_RQ_HEADINGS = (
    "RQ1 - Invalidated assumptions",
    "RQ2 - Necessary adaptation set",
    "RQ3 - Optimization and GNU89-era code",
    "RQ4 - Behavioral fidelity",
    "RQ5 - Reproducible historical experience",
)

REQUIRED_PATHS = (
    "MISSION.md",
    "ARCHITECTURE.md",
    "EXPERIENCE.md",
    "docs/RESEARCH-QUESTIONS.md",
    "docs/METHODOLOGY.md",
    "docs/AUDIT-STATEMENTS.md",
    "docs/PORTING_LEDGER.md",
    "docs/FAULT-CATALOG.md",
    "docs/OBSERVABILITY.md",
    "docs/REPRODUCIBILITY.md",
    "datasets/patches/MANIFEST.json",
    "datasets/patches/file_deltas.csv",
    "datasets/patches/adaptations.csv",
    "datasets/golden-traces/v1/MANIFEST.json",
    "datasets/golden-traces/v1/alive-boot-machine.jsonl",
    "datasets/compiler-cases/v1/MANIFEST.json",
    "datasets/compiler-cases/v1/observations.jsonl",
    "datasets/compiler-cases/v1/classifications.json",
    "tests/test_fs_persistence.py",
)

REQUIRED_RESULT_BOUNDARIES = {
    "RQ1 - Invalidated assumptions": (
        "adaptation inventory plus adapted-state conformance",
        "RQ1 invalidation procedure remains `PARTIAL`",
    ),
    "RQ2 - Necessary adaptation set": (
        "one sufficient observed configuration",
        "does not establish a minimum adaptation set",
        "sufficiency procedure is `PARTIAL`; minimality remains `PROPOSED`",
    ),
    "RQ3 - Optimization and GNU89-era code": (
        "hosted x86-64 `-O2`",
        "source-contract violation",
        "not a GCC defect",
        "compiler procedure remains `PARTIAL`",
    ),
    "RQ4 - Behavioral fidelity": (
        "multidimensional conformance",
        "no scalar fidelity score",
        "conformance procedure is `IMPLEMENTED`; retention and repetition remain `PARTIAL`",
    ),
    "RQ5 - Reproducible historical experience": (
        "not machine-state replay",
        "Orderly cross-process persistence is `IMPLEMENTED`",
        "build and fixed-vector procedures are `IMPLEMENTED`, while observable trace equivalence remains `PARTIAL`",
    ),
}

RQ_EVIDENCE_PATHS = {
    "RQ1 - Invalidated assumptions": (
        "datasets/patches/MANIFEST.json",
        "datasets/patches/file_deltas.csv",
        "datasets/patches/adaptations.csv",
    ),
    "RQ2 - Necessary adaptation set": (
        "datasets/patches/MANIFEST.json",
        "tests/test_boot.py",
    ),
    "RQ3 - Optimization and GNU89-era code": (
        "datasets/compiler-cases/v1/MANIFEST.json",
        "datasets/compiler-cases/v1/observations.jsonl",
        "datasets/compiler-cases/v1/classifications.json",
    ),
    "RQ4 - Behavioral fidelity": (
        "EXPERIENCE.md",
        "tests/test_experience.py",
    ),
    "RQ5 - Reproducible historical experience": (
        "datasets/golden-traces/v1/MANIFEST.json",
        "tests/test_power_cut.py",
        "tests/test_fs_persistence.py",
        "docs/REPRODUCIBILITY.md",
    ),
}

INTEGRATION_REFERENCES = {
    "README.md": "docs/PAPER.md",
    "MISSION.md": "docs/PAPER.md",
    "docs/RESEARCH-QUESTIONS.md": "docs/PAPER.md",
    "docs/METHODOLOGY.md": "docs/PAPER.md",
    "scripts/release-check.sh": "docs/PAPER.md",
    ".github/workflows/build.yml": "test-paper",
    "Makefile": "test-paper:",
}

FORBIDDEN_CLAIMS = (
    "proves full runtime determinism",
    "proves the minimum adaptation set",
    "behaviorally identical to 1991 hardware",
    "proves a gcc bug",
    "independently reproduced by a third party",
)


def fail(message):
    raise AssertionError(message)


def section_blocks(document):
    headings = list(re.finditer(r"^## (.+)$", document, re.MULTILINE))
    blocks = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        blocks[heading.group(1)] = document[heading.end():end]
    return headings, blocks


def result_blocks(results):
    headings = list(re.finditer(r"^### (RQ\d+ - .+)$", results, re.MULTILINE))
    blocks = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(results)
        blocks[heading.group(1)] = results[heading.end():end]
    return headings, blocks


def load_json(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as source:
        return json.load(source)


def assigned_value(statements, name):
    for statement in statements:
        if not isinstance(statement, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in statement.targets):
            return statement.value
    fail(f"could not derive {name!r} from executable evidence")


def case_mutation_count(statement, forbidden_count):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return 0
    call = statement.value
    if not isinstance(call.func, ast.Attribute) or not isinstance(call.func.value, ast.Name):
        return 0
    if call.func.value.id != "cases":
        return 0
    if call.func.attr == "insert":
        return 1
    if call.func.attr != "extend" or len(call.args) != 1:
        return 0
    argument = call.args[0]
    if isinstance(argument, (ast.List, ast.Tuple)):
        return len(argument.elts)
    if isinstance(argument, ast.GeneratorExp):
        iterator = argument.generators[0].iter
        if isinstance(iterator, ast.Name) and iterator.id == "FORBIDDEN_GUEST_COMMANDS":
            return forbidden_count
    fail("test_experience.py changed its cases construction; update the paper evidence derivation")


def experience_case_counts():
    path = os.path.join(REPO_ROOT, "tests", "test_experience.py")
    with open(path, encoding="utf-8") as source:
        tree = ast.parse(source.read(), path)
    forbidden = assigned_value(tree.body, "FORBIDDEN_GUEST_COMMANDS")
    if not isinstance(forbidden, ast.Tuple):
        fail("FORBIDDEN_GUEST_COMMANDS is not a fixed tuple")
    main = next(
        (node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"),
        None,
    )
    if main is None:
        fail("tests/test_experience.py has no main function")
    cases = assigned_value(main.body, "cases")
    if not isinstance(cases, ast.List):
        fail("experience cases are not initialized as a fixed list")
    alive_count = len(cases.elts)
    historical_extra = 0
    for statement in main.body:
        if isinstance(statement, ast.If):
            comparison = ast.unparse(statement.test)
            if "args.experience == '1991'" in comparison:
                historical_extra += sum(
                    case_mutation_count(item, len(forbidden.elts)) for item in statement.body
                )
            continue
        alive_count += case_mutation_count(statement, len(forbidden.elts))
    return alive_count, alive_count + historical_extra


def power_cut_run_count():
    path = os.path.join(REPO_ROOT, "tests", "test_power_cut.py")
    with open(path, encoding="utf-8") as source:
        tree = ast.parse(source.read(), path)
    scenarios = assigned_value(tree.body, "SCENARIOS")
    if not isinstance(scenarios, ast.Tuple):
        fail("power-cut scenarios are not a fixed tuple")
    parse_args = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "parse_args"
    )
    default_images = None
    for node in ast.walk(parse_args):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "args"
                and target.attr == "images"
            ):
                default_images = len(node.value.elts)
    run_profile = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_profile"
    )
    repeats = None
    for node in ast.walk(run_profile):
        if (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and node.target.id == "repeat"
            and isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and len(node.iter.args) == 1
            and isinstance(node.iter.args[0], ast.Constant)
        ):
            repeats = node.iter.args[0].value
    if default_images is None or repeats is None:
        fail("could not derive the power-cut profile/repeat matrix")
    return len(scenarios.elts) * default_images * repeats


def evidence_result_anchors():
    patches = load_json("datasets/patches/MANIFEST.json")
    compiler = load_json("datasets/compiler-cases/v1/MANIFEST.json")
    traces = load_json("datasets/golden-traces/v1/MANIFEST.json")
    machine = next(capture for capture in traces["captures"] if capture["format"] == "jsonl")
    alive_count, historical_count = experience_case_counts()
    return {
        "RQ1 - Invalidated assumptions": (
            f"{patches['historical_core_path_count']} historical-core path deltas",
            f"{patches['adaptation_count']} adaptation IDs",
            f"{patches['unresolved_path_count']} unresolved joins",
            f"{patches['paired_observation_count']} paired baseline/adapted observations",
        ),
        "RQ2 - Necessary adaptation set": (
            f"{patches['rq2_ablation_configuration_count']} ablation configurations",
        ),
        "RQ3 - Optimization and GNU89-era code": (
            f"{compiler['observation_count']} cells",
            f"{compiler['pass_count']} PASS and {compiler['fail_count']} FAIL",
        ),
        "RQ4 - Behavioral fidelity": (
            f"{alive_count} command segments",
            f"{historical_count} command segments",
        ),
        "RQ5 - Reproducible historical experience": (
            f"{machine['event_count']:,} raw events",
            f"{machine['filtered_event_count']:,}",
            f"{machine['normalized_event_count']} retained events",
            f"{traces['inputs'][0]['byte_count']} input bytes",
            f"{power_cut_run_count()} image runs",
        ),
    }


def main():
    try:
        with open(PAPER_PATH, encoding="utf-8") as source:
            paper = source.read()
    except FileNotFoundError:
        fail("docs/PAPER.md is missing")

    if len(paper.split()) < 3500:
        fail("technical paper is too short to be complete")

    headings, blocks = section_blocks(paper)
    actual_sections = [heading.group(1) for heading in headings]
    if actual_sections != list(REQUIRED_SECTIONS):
        fail(f"paper sections are {actual_sections!r}, expected {list(REQUIRED_SECTIONS)!r}")

    abstract_words = re.findall(r"\b[\w'-]+\b", blocks["Abstract"])
    if not 150 <= len(abstract_words) <= 250:
        fail(f"abstract has {len(abstract_words)} words, expected 150-250")

    rq_headings, rq_blocks = result_blocks(blocks["6. Results"])
    actual_rqs = [heading.group(1) for heading in rq_headings]
    if actual_rqs != list(REQUIRED_RQ_HEADINGS):
        fail(f"paper result headings are {actual_rqs!r}, expected {list(REQUIRED_RQ_HEADINGS)!r}")

    derived_anchors = evidence_result_anchors()
    for heading, anchors in REQUIRED_RESULT_BOUNDARIES.items():
        normalized = re.sub(r"\s+", " ", rq_blocks[heading])
        for anchor in anchors + derived_anchors[heading]:
            if anchor not in normalized:
                fail(f"paper result {heading!r} lost evidence boundary {anchor!r}")
        for path in RQ_EVIDENCE_PATHS[heading]:
            if f"`{path}`" not in rq_blocks[heading]:
                fail(f"paper result {heading!r} does not cite {path!r}")

    for path in REQUIRED_PATHS:
        if f"`{path}`" not in paper:
            fail(f"paper does not cite repository evidence {path!r}")
        if not os.path.isfile(os.path.join(REPO_ROOT, path)):
            fail(f"paper references missing repository evidence {path!r}")

    lowered = paper.lower()
    for claim in FORBIDDEN_CLAIMS:
        if claim in lowered:
            fail(f"paper contains forbidden unsupported claim {claim!r}")

    references = blocks["References"]
    external_links = re.findall(r"https://[^\s)>]+", references)
    if len(external_links) < 6:
        fail("paper needs at least six external references")
    if "Linux 0.01" not in references or "KVM" not in references:
        fail("paper references do not identify the historical object and execution substrate")

    for path, anchor in INTEGRATION_REFERENCES.items():
        with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as source:
            content = source.read()
        if anchor not in content:
            fail(f"{path} does not expose paper integration anchor {anchor!r}")

    artifact_script = os.path.join(REPO_ROOT, "scripts", "make-artifact.sh")
    with open(artifact_script, encoding="utf-8") as source:
        artifact = source.read()
    if "archive --format=tar" not in artifact or "source/evaluation/v1" not in artifact:
        fail("the evaluator package does not export tracked evidence and its package guide")

    print("technical paper is complete, evidence-linked, and publicly integrated")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"paper check failed: {error}", file=sys.stderr)
        sys.exit(1)
