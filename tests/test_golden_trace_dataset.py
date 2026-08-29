#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Validate the published legacy golden-trace dataset and comparison policy."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(REPO_ROOT, "datasets", "golden-traces", "v1")
REQUIRED_FILES = {
    "README.md",
    "MANIFEST.json",
    "SHA256SUMS.txt",
    "alive-boot-console.trace",
    "alive-boot-machine.jsonl",
    "trace-event-v1.schema.json",
}
EXPECTED_PUBLICATION_SOURCE_COMMIT = "14638cf9deb708680a3c58266bb4c71a865355ea"
EXPECTED_EVENT_COUNTS = {
    "boot_start": 1,
    "io_access": 22906,
    "irq": 620,
    "input": 1,
    "shutdown": 1,
}
EXPECTED_NORMALIZED_COUNTS = {
    "boot_start": 1,
    "io_access": 609,
    "input": 1,
    "shutdown": 1,
}
EXPECTED_MISSING_IDENTITIES = {
    "capture_commit",
    "dirty_state",
    "host_kernel",
    "cpu",
    "microcode",
    "kvm_capabilities",
    "producer_binary",
    "kernel_artifact",
    "root_artifact",
    "source_date_epoch",
    "locale",
    "timezone",
    "process_exit_status",
}


def fail(message):
    raise AssertionError(message)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    fail(f"non-finite JSON value {value!r}")


def strict_json(text):
    return json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_constant,
    )


def is_integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_value(value, definition, location):
    value_type = definition.get("type")
    if value_type == "integer":
        if not is_integer(value):
            fail(f"{location} is not an integer")
        if "enum" in definition and value not in definition["enum"]:
            fail(f"{location} has unsupported value {value!r}")
        if "minimum" in definition and value < definition["minimum"]:
            fail(f"{location} is below its minimum")
        if "maximum" in definition and value > definition["maximum"]:
            fail(f"{location} exceeds its maximum")
    elif value_type == "string":
        if not isinstance(value, str):
            fail(f"{location} is not a string")
        if "enum" in definition and value not in definition["enum"]:
            fail(f"{location} has unsupported value {value!r}")
        if "pattern" in definition:
            import re
            if re.search(definition["pattern"], value) is None:
                fail(f"{location} does not match its schema pattern")
        if "maxLength" in definition and len(value) > definition["maxLength"]:
            fail(f"{location} exceeds its maximum length")
    elif value_type == "array":
        if not isinstance(value, list):
            fail(f"{location} is not an array")
        if len(value) > definition.get("maxItems", len(value)):
            fail(f"{location} has too many items")
        for index, item in enumerate(value):
            validate_value(item, definition["items"], f"{location}[{index}]")
    else:
        fail(f"unsupported validator schema type {value_type!r}")


def validate_event(event, schema, ordinal):
    if not isinstance(event, dict) or set(event) != {"ts", "type", "data"}:
        fail(f"event {ordinal} has an invalid envelope")
    if not is_integer(event["ts"]) or event["ts"] < 0:
        fail(f"event {ordinal} has an invalid logical timestamp")
    if not isinstance(event["type"], str) or not isinstance(event["data"], dict):
        fail(f"event {ordinal} has invalid type/data fields")

    definitions = schema["$defs"]
    if event["type"] not in definitions:
        fail(f"event {ordinal} has unknown type {event['type']!r}")
    payload = definitions[event["type"]]
    required = set(payload["required"])
    properties = payload["properties"]
    if set(event["data"]) != required or required != set(properties):
        fail(f"event {ordinal} payload fields do not match the schema")
    for name, definition in properties.items():
        validate_value(event["data"][name], definition, f"event {ordinal}.{name}")


def normalize(event, policy):
    if event["type"] in policy["ignore_event_types"]:
        return None
    data = event["data"].copy()
    for field in policy["drop_payload_fields"].get(event["type"], []):
        data.pop(field, None)
    if event["type"] == "io_access" and data["port"] in policy["ignore_io_ports"]:
        return None
    return {"type": event["type"], "data": data}


def git_environment():
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("GIT_"):
            environment.pop(name)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["HOME"] = os.devnull
    environment["XDG_CONFIG_HOME"] = os.devnull
    environment["LC_ALL"] = "C"
    return environment


def main():
    git_env = git_environment()
    if not os.path.isdir(DATASET_DIR):
        fail("datasets/golden-traces/v1 is missing")
    if set(os.listdir(DATASET_DIR)) != REQUIRED_FILES:
        fail("golden-trace dataset file set is incomplete")

    with open(os.path.join(DATASET_DIR, "MANIFEST.json"), encoding="utf-8") as source:
        manifest = strict_json(source.read())
    with open(os.path.join(DATASET_DIR, "trace-event-v1.schema.json"), encoding="utf-8") as source:
        schema = strict_json(source.read())

    if manifest.get("manifest_schema_version") != 1:
        fail("unsupported golden-trace manifest schema")
    if manifest.get("dataset_id") != "linux-0.01-golden-traces-v1":
        fail("unexpected golden-trace dataset ID")
    if manifest.get("publication_source_commit") != EXPECTED_PUBLICATION_SOURCE_COMMIT:
        fail("manifest does not pin the Wave 108 publication source")
    if manifest.get("captures_share_run_id") is not False:
        fail("manifest incorrectly joins the console and machine captures")
    for claim in (
        "machine_state_replay",
        "full_runtime_determinism",
        "physical_hardware_equivalence",
        "both_profiles_covered",
    ):
        if manifest.get("claims", {}).get(claim) is not False:
            fail(f"manifest overstates {claim}")

    schema_info = manifest["event_schema"]
    if schema_info["id"] != "bemu-trace-event-v1":
        fail("unexpected event schema ID")
    if sha256_file(os.path.join(DATASET_DIR, schema_info["path"])) != schema_info["sha256"]:
        fail("event schema hash mismatch")
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("event schema does not declare JSON Schema 2020-12")
    expected_types = {
        "boot_start", "kvm_exit", "io_access", "irq", "timer", "input",
        "syscall", "interrupt", "process", "shutdown",
    }
    if set(schema.get("$defs", {})) != expected_types:
        fail("event schema does not define the exact producer event types")
    if schema.get("required") != ["ts", "type", "data"] or schema.get("additionalProperties") is not False:
        fail("event schema does not enforce the exact envelope")
    root_properties = schema.get("properties", {})
    if schema.get("type") != "object" or set(root_properties) != {"ts", "type", "data"}:
        fail("event schema root is not the exact event object")
    if root_properties["ts"] != {"type": "integer", "minimum": 0}:
        fail("event schema root timestamp constraint drifted")
    if root_properties["type"] != {"type": "string", "enum": [
        "boot_start", "kvm_exit", "io_access", "irq", "timer", "input",
        "syscall", "interrupt", "process", "shutdown",
    ]}:
        fail("event schema root type constraint drifted")
    if root_properties["data"] != {"type": "object"}:
        fail("event schema root data constraint drifted")
    branches = {
        branch.get("properties", {}).get("type", {}).get("const"):
        branch.get("properties", {}).get("data", {}).get("$ref")
        for branch in schema.get("oneOf", [])
    }
    expected_branches = {event_type: f"#/$defs/{event_type}" for event_type in expected_types}
    if branches != expected_branches or len(schema.get("oneOf", [])) != len(expected_types):
        fail("event schema oneOf branches do not bind every type to its payload")

    captures = manifest.get("captures", [])
    if [capture.get("trace_id") for capture in captures] != [
        "T-ALIVE-BOOT-CONSOLE-001",
        "T-ALIVE-BOOT-MACHINE-001",
    ]:
        fail("manifest lost the two stable capture IDs")
    for capture in captures:
        if capture.get("profile") != "alive":
            fail(f"capture {capture['trace_id']} has the wrong profile")
        if capture.get("capture_provenance_status") != "incomplete_historical":
            fail(f"capture {capture['trace_id']} overstates provenance")
        if set(capture.get("missing_identities", [])) != EXPECTED_MISSING_IDENTITIES:
            fail(f"capture {capture['trace_id']} lost explicit missing identities")
        path = os.path.join(DATASET_DIR, capture["path"])
        if sha256_file(path) != capture["sha256"] or os.path.getsize(path) != capture["byte_count"]:
            fail(f"capture {capture['trace_id']} identity mismatch")
        historical = subprocess.check_output(
            [
                "git", "show",
                f"{EXPECTED_PUBLICATION_SOURCE_COMMIT}:{capture['source_path_at_publication_commit']}",
            ],
            cwd=REPO_ROOT,
            env=git_env,
        )
        with open(path, "rb") as source:
            if source.read() != historical:
                fail(f"capture {capture['trace_id']} differs from its pinned Git source")
        last_change = subprocess.check_output(
            [
                "git", "log", "-1", "--format=%H", EXPECTED_PUBLICATION_SOURCE_COMMIT,
                "--", capture["source_path_at_publication_commit"],
            ],
            cwd=REPO_ROOT,
            env=git_env,
            text=True,
        ).strip()
        if capture.get("last_payload_commit") != last_change:
            fail(f"capture {capture['trace_id']} has incorrect last-change provenance")

    console = captures[0]
    console_path = os.path.join(DATASET_DIR, console["path"])
    with open(console_path, "rb") as source:
        console_bytes = source.read()
    if console_bytes.count(b"\n") != console["physical_line_count"]:
        fail("console physical line count mismatch")
    if console_bytes.count(b"\x1b") != console["escape_byte_count"]:
        fail("console escape-byte count mismatch")
    for marker in (b"GOLDEN_BOOT_MARKER", b"PASS after 6294 KVM exits"):
        if marker not in console_bytes:
            fail(f"console trace lost marker {marker!r}")

    machine = captures[1]
    machine_path = os.path.join(DATASET_DIR, machine["path"])
    with open(machine_path, "rb") as source:
        machine_bytes = source.read()
    if not machine_bytes.endswith(b"\n"):
        fail("machine trace lacks final LF")
    events = []
    previous_ts = -1
    for ordinal, encoded_line in enumerate(machine_bytes.splitlines(), 1):
        event = strict_json(encoded_line.decode("utf-8"))
        validate_event(event, schema, ordinal)
        if event["ts"] < previous_ts:
            fail(f"event {ordinal} moves logical time backwards")
        previous_ts = event["ts"]
        events.append(event)
    if events[0]["type"] != "boot_start" or events[-1]["type"] != "shutdown":
        fail("machine trace does not start at boot and end at shutdown")

    counts = {}
    for event in events:
        counts[event["type"]] = counts.get(event["type"], 0) + 1
    if counts != EXPECTED_EVENT_COUNTS or counts != machine["event_type_counts"]:
        fail(f"machine event counts are {counts}")
    if len(events) != machine["event_count"]:
        fail("machine event count mismatch")
    if events[0]["ts"] != machine["logical_ts_min"] or events[-1]["ts"] != machine["logical_ts_max"]:
        fail("machine logical timestamp range mismatch")

    inputs = {item["input_id"]: item for item in manifest["inputs"]}
    for join in machine["input_joins"]:
        event = events[join["event_ordinal"] - 1]
        item = inputs[join["input_id"]]
        if event["type"] != "input" or event["data"]["source"] != item["source"]:
            fail("input join does not point to the declared source event")
        raw = bytes.fromhex(event["data"]["hex"])
        if len(raw) != event["data"]["bytes"] or len(raw) != item["byte_count"]:
            fail("input byte count does not match its hex payload")
        if raw.hex() != item["hex"] or sha256_bytes(raw) != item["sha256"]:
            fail("input identity mismatch")

    policy = manifest["comparison_policy"]
    if policy != {
        "id": "observable-compare-v1",
        "drop_top_level_fields": ["ts"],
        "drop_payload_fields": {"kvm_exit": ["exit_count"], "shutdown": ["exits"]},
        "ignore_event_types": ["irq"],
        "ignore_io_ports": [113, 96, 97, 980, 981, 496],
        "ordering": "positional",
        "payload_comparison": "exact",
        "canonical_serialization": "UTF-8 compact sorted-key JSON Lines with LF",
    }:
        fail("comparison policy drifted from observable-compare-v1")
    normalized = [item for item in (normalize(event, policy) for event in events) if item]
    normalized_counts = {}
    removal_counts = {"event_type:irq": 0}
    removal_counts.update({f"io_port:{port}": 0 for port in policy["ignore_io_ports"]})
    for event in events:
        if event["type"] in policy["ignore_event_types"]:
            removal_counts[f"event_type:{event['type']}"] += 1
        elif event["type"] == "io_access" and event["data"]["port"] in policy["ignore_io_ports"]:
            removal_counts[f"io_port:{event['data']['port']}"] += 1
    serialized = bytearray()
    for event in normalized:
        normalized_counts[event["type"]] = normalized_counts.get(event["type"], 0) + 1
        serialized.extend(
            json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        )
        serialized.extend(b"\n")
    if (
        len(normalized) != machine["normalized_event_count"]
        or normalized_counts != EXPECTED_NORMALIZED_COUNTS
        or normalized_counts != machine["normalized_event_type_counts"]
    ):
        fail("normalized event counts do not match the publication")
    if removal_counts != machine["filter_removal_counts"]:
        fail("filter removal counts do not match the publication")
    if sha256_bytes(serialized) != machine["normalized_sha256"]:
        fail("normalized trace hash mismatch")
    if len(events) - len(normalized) != machine["filtered_event_count"]:
        fail("filtered event count mismatch")

    checksums = {}
    with open(os.path.join(DATASET_DIR, "SHA256SUMS.txt"), encoding="ascii") as source:
        for line in source:
            digest, name = line.rstrip("\n").split("  ", 1)
            checksums[name] = digest
    if set(checksums) != REQUIRED_FILES - {"SHA256SUMS.txt"}:
        fail("dataset checksums do not cover every non-self-referential file")
    for name, digest in checksums.items():
        if sha256_file(os.path.join(DATASET_DIR, name)) != digest:
            fail(f"dataset checksum mismatch for {name}")

    build_dir = os.environ.get("BUILD", "build")
    if not os.path.isabs(build_dir):
        build_dir = os.path.join(REPO_ROOT, build_dir)
    producer = os.path.join(build_dir, "test-trace-producer")
    if not os.path.isfile(producer):
        fail("build/test-trace-producer is missing; use make test-golden-trace-dataset")
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as fixture_file:
        fixture_path = fixture_file.name
    try:
        subprocess.run(
            [producer, "--emit-schema-fixture", fixture_path],
            cwd=REPO_ROOT,
            check=True,
        )
        fixture_types = set()
        with open(fixture_path, encoding="utf-8") as source:
            for ordinal, line in enumerate(source, 1):
                event = strict_json(line)
                validate_event(event, schema, ordinal)
                fixture_types.add(event["type"])
        if fixture_types != expected_types:
            fail("production emitter fixture does not cover every schema event type")
    finally:
        os.unlink(fixture_path)

    with open(os.path.join(REPO_ROOT, "Makefile"), encoding="utf-8") as source:
        makefile = source.read()
    with open(os.path.join(REPO_ROOT, "tests", "test_compare_trace.py"), encoding="utf-8") as source:
        comparator_test = source.read()
    with open(os.path.join(REPO_ROOT, "tests", "golden_trace.py"), encoding="utf-8") as source:
        console_capture = source.read()
    with open(os.path.join(REPO_ROOT, "tests", "golden_trace_jsonl.py"), encoding="utf-8") as source:
        machine_capture = source.read()
    if "test-golden-trace-dataset:" not in makefile or "alive-boot-machine.jsonl" not in makefile:
        fail("Makefile does not bind the published golden-trace dataset")
    for option in ("irq", "0x71", "0x60", "0x61", "0x3d4", "0x3d5", "0x1f0"):
        if f'"{option}"' not in comparator_test:
            fail(f"runtime comparator test lost policy option {option}")
    if "build/golden-candidates/" not in console_capture or "build/golden-candidates/" not in machine_capture:
        fail("capture tools can overwrite the published observations")
    for script, output in (
        ("tests/golden_trace.py", captures[0]["path"]),
        ("tests/golden_trace_jsonl.py", captures[1]["path"]),
    ):
        published_path = os.path.join(DATASET_DIR, output)
        original_hash = sha256_file(published_path)
        result = subprocess.run(
            [sys.executable, script, "--output", published_path],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if result.returncode == 0 or "refusing to overwrite" not in result.stdout:
            fail(f"{script} does not reject a published output path")
        if sha256_file(published_path) != original_hash:
            fail(f"{script} modified a published observation")

    print("golden traces are published with bounded provenance and comparison policy")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, ValueError, UnicodeError, subprocess.CalledProcessError) as error:
        print(f"golden-trace dataset check failed: {error}", file=sys.stderr)
        sys.exit(1)
