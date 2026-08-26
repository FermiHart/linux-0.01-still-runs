#!/usr/bin/env python3
"""Build the versioned historical-core patch and incompatibility dataset."""

import argparse
import csv
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(REPO_ROOT, "datasets", "patches")
TARBALL_PATH = os.path.join(REPO_ROOT, "upstream", "linux-0.01.tar.gz")
GENERATOR_PATH = os.path.relpath(os.path.abspath(__file__), REPO_ROOT)
DEFAULT_PORT_COMMIT = "ae458306905d4fee85121ac3c2b42e86ed099310"
UPSTREAM_SHA256 = "24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d"
CORE_DIRECTORIES = ("init", "kernel", "mm", "fs", "lib", "include")
SOURCE_SUFFIXES = (".c", ".h", ".s", ".S")

ADAPTATION_IDS = {
    "CMOS Y2K rollover": "A-CMOS-Y2K",
    "Syscall wrappers for modern GCC": "A-SYSCALL-GCC",
    "VGA 80x50 text mode": "A-VGA-80X50",
    "Serial UART 115200 baud": "A-UART-115200",
    "Console output duplication removal": "A-CONSOLE-DEDUPE",
    "CP437 / extended VGA glyph filter": "A-CP437-FILTER",
    "Buffer-cache free-list walk": "A-BUFFER-FREELIST",
    "Bitmap `-O1` workaround": "A-BITMAP-O1",
    "`vsprintf` `%s` handling": "A-VSPRINTF-O1",
    "ATA PIO read helper and port macros": "A-ATA-PIO",
    "Colored diagnostic printk": "A-COLORED-PRINTK",
    "`PIPE_HEAD` increment macro": "A-PIPE-HEAD",
    "Filesystem patches for Minix v1 root image": "A-MINIX-ROOTFS",
    "`sys_ioctl` volatile return": "A-IOCTL-VOLATILE",
    "Memory-management compatibility": "A-MM-COMPAT",
    "Kernel assembly clobbers and constraints": "A-KERNEL-ASM",
    "Include header adjustments": "A-INCLUDE-COMPAT",
    "`lib/open.c` adjustment": "A-LIB-OPEN",
    "Validated experience environment bridge": "A-EXPERIENCE-ENV",
}


def run(command, cwd=REPO_ROOT, text=False):
    environment = git_environment() if command[0] == "git" else None
    return subprocess.check_output(command, cwd=cwd, text=text, env=environment)


def git_environment():
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("GIT_"):
            environment.pop(name)
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["GIT_PAGER"] = "cat"
    environment["HOME"] = os.devnull
    environment["XDG_CONFIG_HOME"] = os.devnull
    environment["LC_ALL"] = "C"
    return environment


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_bytes(revision, path):
    return run(["git", "show", f"{revision}:{path}"])


def git_text(revision, path):
    return git_bytes(revision, path).decode("utf-8")


def source_mode(path):
    return "100755" if os.stat(path).st_mode & stat.S_IXUSR else "100644"


def write_snapshot_file(root, path, data, mode):
    destination = os.path.join(root, path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "wb") as output:
        output.write(data)
    os.chmod(destination, 0o755 if mode == "100755" else 0o644)


def extract_upstream(destination):
    with tarfile.open(TARBALL_PATH, "r:gz") as archive:
        archive.extractall(destination, filter="data")
    return os.path.join(destination, "linux")


def upstream_snapshot(root):
    snapshot = {}
    for directory in CORE_DIRECTORIES:
        base = os.path.join(root, directory)
        for current, directories, files in os.walk(base):
            directories.sort()
            for name in sorted(files):
                path = os.path.relpath(os.path.join(current, name), root)
                if not path.endswith(SOURCE_SUFFIXES):
                    continue
                full_path = os.path.join(root, path)
                with open(full_path, "rb") as source:
                    snapshot[path] = (source.read(), source_mode(full_path))
    return snapshot


def port_snapshot(revision):
    command = ["git", "ls-tree", "-rz", "--full-tree", revision, "--", *CORE_DIRECTORIES]
    records = run(command).split(b"\0")
    snapshot = {}
    for record in records:
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, object_type, _object_hash = metadata.decode("ascii").split()
        path = encoded_path.decode("utf-8")
        if object_type != "blob" or not path.endswith(SOURCE_SUFFIXES):
            continue
        snapshot[path] = (git_bytes(revision, path), mode)
    return snapshot


def initialize_diff_repository(root, upstream):
    environment = git_environment()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, env=environment)
    for path, (data, mode) in upstream.items():
        write_snapshot_file(root, path, data, mode)
    subprocess.run(["git", "add", *CORE_DIRECTORIES], cwd=root, check=True, env=environment)
    subprocess.run(
        [
            "git", "-c", "user.name=dataset", "-c", "user.email=dataset.invalid",
            "commit", "-qm", "pinned upstream snapshot",
        ],
        cwd=root,
        check=True,
        env=environment,
    )


def install_port_snapshot(root, upstream, port):
    for path in sorted(set(upstream) - set(port)):
        os.remove(os.path.join(root, path))
    for path, (data, mode) in port.items():
        write_snapshot_file(root, path, data, mode)
    added = sorted(set(port) - set(upstream))
    if added:
        subprocess.run(
            ["git", "add", "-N", "--", *added],
            cwd=root,
            check=True,
            env=git_environment(),
        )


def git_patch(root, paths):
    if not paths:
        return b""
    process = subprocess.run(
        [
            "git", "diff", "--binary", "--full-index", "--no-ext-diff", "--no-renames",
            "--no-color", "--diff-algorithm=myers", "--unified=3", "--src-prefix=a/",
            "--dst-prefix=b/", "HEAD", "--", *paths,
        ],
        cwd=root,
        stdout=subprocess.PIPE,
        check=True,
        env=git_environment(),
    )
    return process.stdout


def diff_counts(root, path):
    output = run(
        ["git", "diff", "--no-renames", "--numstat", "HEAD", "--", path],
        cwd=root,
        text=True,
    )
    if not output.strip():
        return 0, 0
    added, deleted, _name = output.rstrip("\n").split("\t", 2)
    return int(added), int(deleted)


def field(block, name):
    marker = f"- **{name}**:"
    lines = block.splitlines()
    captured = []
    active = False
    for line in lines:
        if line.startswith(marker):
            captured.append(line[len(marker):].strip())
            active = True
        elif active and line.startswith("  "):
            captured.append(line.strip())
        elif active:
            break
    if not captured:
        raise ValueError(f"ledger entry lacks {name}: {block[:80]!r}")
    return " ".join(captured)


def normalize_title(title):
    return title.replace("×", "x")


def parse_ledger(text):
    entry_area = text.split("## Entries", 1)[1].split("## Test traceability", 1)[0]
    headings = list(__import__("re").finditer(r"^### (.+)$", entry_area, __import__("re").MULTILINE))
    entries = []
    prefix_lines = text[:text.index("## Entries") + len("## Entries")].count("\n")
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(entry_area)
        title = heading.group(1)
        key = normalize_title(title)
        if key not in ADAPTATION_IDS:
            raise ValueError(f"ledger title has no stable ID: {title}")
        block = entry_area[heading.end():end]
        line_start = prefix_lines + entry_area[:heading.start()].count("\n") + 1
        line_end = prefix_lines + entry_area[:end].count("\n")
        entries.append({
            "adaptation_id": ADAPTATION_IDS[key],
            "title": title,
            "change_summary": field(block, "Change"),
            "files": field(block, "Files"),
            "categories": field(block, "Category").replace(" / ", ";"),
            "ledger_evidence": field(block, "Evidence"),
            "ledger_test": field(block, "Test"),
            "ledger_status": field(block, "Status").split(" ", 1)[0],
            "ledger_line_start": str(line_start),
            "ledger_line_end": str(line_end),
        })
    if len(entries) != 19:
        raise ValueError(f"expected 19 ledger entries, found {len(entries)}")
    return entries


def rq1_claim_level(adaptation_id):
    if adaptation_id in {"A-BUFFER-FREELIST", "A-VSPRINTF-O1"}:
        return "historical_hypothesis_not_reproduced"
    if adaptation_id == "A-BITMAP-O1":
        return "source_contract_reproduced_without_retained_run"
    return "adapted_conformance_only"


def pattern_matches(pattern, path):
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if "/**/" in pattern:
        return fnmatch.fnmatchcase(path, pattern.replace("/**/", "/"))
    return False


def make_adaptation_rows(entries):
    rows = []
    for entry in entries:
        rows.append({
            "adaptation_id": entry["adaptation_id"],
            "title": entry["title"],
            "change_summary": entry["change_summary"],
            "categories": entry["categories"],
            "ledger_status": entry["ledger_status"],
            "interpretation_status": "historical_summary_without_paired_raw_output",
            "rq1_claim_level": rq1_claim_level(entry["adaptation_id"]),
            "rq2_role": "not_in_predeclared_universe",
            "ledger_line_start": entry["ledger_line_start"],
            "ledger_line_end": entry["ledger_line_end"],
        })
    return rows


def make_join_rows(entries, deltas):
    import re

    delta_by_path = {row["path"]: row for row in deltas}
    rows = []
    joined_paths = set()
    for entry in entries:
        declarations = re.findall(r"`([^`]+)`", entry["files"])
        for declaration in declarations:
            is_glob = any(character in declaration for character in "*?[")
            if is_glob:
                matches = sorted(path for path in delta_by_path if pattern_matches(declaration, path))
            else:
                matches = [declaration]
            for path in matches:
                delta = delta_by_path.get(path)
                relation = "build_rule" if path == "Makefile" else "source_change"
                if delta and delta["change_type"] == "added":
                    relation = "added_source"
                rows.append({
                    "adaptation_id": entry["adaptation_id"],
                    "path": path,
                    "delta_id": delta["delta_id"] if delta else "",
                    "relation": relation,
                    "join_basis": "declared_glob" if is_glob else "explicit_path",
                    "semantic_attribution": "broad" if is_glob else "exact",
                })
                if delta:
                    joined_paths.add(path)
    for path in sorted(set(delta_by_path) - joined_paths):
        rows.append({
            "adaptation_id": "",
            "path": path,
            "delta_id": delta_by_path[path]["delta_id"],
            "relation": "source_change",
            "join_basis": "none",
            "semantic_attribution": "unresolved",
        })
    return sorted(rows, key=lambda row: (row["path"], row["adaptation_id"]))


def evidence_class(reference):
    if reference.startswith("tests/compiler-cases/"):
        return "repository_independent_implementation", "versioned_oracle_definition"
    if reference in {"tests/test_shell.py", "tests/test_experience.py"}:
        return "self_report", "versioned_oracle_definition"
    if reference.startswith("tests/"):
        return "production_integration", "versioned_oracle_definition"
    if reference.startswith("make "):
        return "production_integration", "generated_unretained"
    return "historical_interpretation", "versioned_summary_without_raw_output"


def make_evidence_rows(entries):
    import re

    rows = []
    for entry in entries:
        references = [
            reference for reference in re.findall(r"`([^`]+)`", entry["ledger_test"])
            if reference.startswith("tests/") or reference.startswith("make ")
        ]
        if not references:
            references = [""]
        for index, reference in enumerate(references, 1):
            oracle_class, retention = evidence_class(reference)
            if reference.startswith("make "):
                reference_kind = "make_target"
            elif reference.startswith("tests/compiler-cases/"):
                reference_kind = "compiler_reduction"
            elif reference.startswith("tests/"):
                reference_kind = "test_source"
            else:
                reference_kind = "historical_statement"
            rows.append({
                "evidence_id": f"E-{entry['adaptation_id'][2:]}-{index:02d}",
                "adaptation_id": entry["adaptation_id"],
                "ledger_test": entry["ledger_test"],
                "reference": reference,
                "reference_kind": reference_kind,
                "oracle_class": oracle_class,
                "retention": retention,
                "observation_id": "",
                "raw_output_sha256": "",
            })
    return rows


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def dataset_readme(manifest):
    return f"""# Historical-Core Patch and Incompatibility Dataset

This versioned dataset compares the pinned Linux 0.01 tarball with port commit
`{manifest['port_commit']}`. It publishes source deltas and ledger
interpretations for RQ1/RQ2; it does not retroactively create execution logs.

## Contents

- `historical-core.patch`: deterministic Git-format patch for 53 source paths.
- `file_deltas.csv`: hashes, modes, line counts and per-path patch hashes.
- `adaptations.csv`: 19 stable IDs derived from `docs/PORTING_LEDGER.md`.
- `adaptation_files.csv`: explicit/glob joins and nine unresolved path deltas.
- `evidence_links.csv`: retained oracle definitions and evidence gaps.
- `MANIFEST.json` and `SHA256SUMS.txt`: immutable source identities and checksums.

Run `make patch-dataset` to reproduce the tracked files and
`make test-patch-dataset` to verify them against both pinned snapshots.

## Interpretation Boundary

The patch and hashes are newly retained observations. Ledger prose is a
versioned historical interpretation. Test source defines an oracle but is not a
retained execution result; generated outputs marked `generated_unretained` were
not preserved with observation IDs or raw-output hashes.

Consequently this release contains zero paired baseline/adapted observations
meeting the RQ1 invalidation criterion and zero RQ2 ablation configurations. It
supports inspection of one observed sufficient port, not a claim of causal
invalidation, necessity, inclusion-minimality or a minimum adaptation set.
"""


def generate(output_dir, revision):
    if sha256_file(TARBALL_PATH) != UPSTREAM_SHA256:
        raise ValueError("upstream tarball hash mismatch")
    revision = run(["git", "rev-parse", f"{revision}^{{commit}}"], text=True).strip()
    ledger_text = git_text(revision, "docs/PORTING_LEDGER.md")
    entries = parse_ledger(ledger_text)

    with tempfile.TemporaryDirectory(prefix="patch-dataset-") as temporary:
        upstream_root = extract_upstream(os.path.join(temporary, "upstream"))
        upstream = upstream_snapshot(upstream_root)
        port = port_snapshot(revision)
        diff_root = os.path.join(temporary, "diff")
        os.makedirs(diff_root)
        initialize_diff_repository(diff_root, upstream)
        install_port_snapshot(diff_root, upstream, port)

        changed_paths = []
        rows = []
        for path in sorted(set(upstream) | set(port)):
            upstream_data, upstream_mode = upstream.get(path, (b"", ""))
            port_data, port_mode = port.get(path, (b"", ""))
            if upstream_data == port_data and upstream_mode == port_mode:
                continue
            if path not in upstream:
                change_type = "added"
            elif path not in port:
                change_type = "deleted"
            elif upstream_data == port_data:
                change_type = "mode_only"
            else:
                change_type = "modified"
            changed_paths.append(path)
            patch = git_patch(diff_root, [path])
            added, deleted = diff_counts(diff_root, path)
            rows.append({
                "delta_id": f"D:{path}",
                "path": path,
                "change_type": change_type,
                "upstream_sha256": sha256_bytes(upstream_data) if path in upstream else "",
                "port_sha256": sha256_bytes(port_data) if path in port else "",
                "upstream_mode": upstream_mode,
                "port_mode": port_mode,
                "added_lines": str(added),
                "deleted_lines": str(deleted),
                "hunk_count": str(patch.count(b"@@ ")),
                "patch_sha256": sha256_bytes(patch),
            })

        if len(rows) != 53:
            raise ValueError(f"expected 53 historical-core deltas, found {len(rows)}")
        full_patch = git_patch(diff_root, changed_paths)
        subprocess.run(
            ["git", "apply", "--reverse", "--check", "--whitespace=nowarn", "-"],
            cwd=diff_root,
            input=full_patch,
            check=True,
            env=git_environment(),
        )

    os.makedirs(output_dir, exist_ok=True)
    adaptation_rows = make_adaptation_rows(entries)
    join_rows = make_join_rows(entries, rows)
    evidence_rows = make_evidence_rows(entries)
    unresolved_count = sum(1 for row in join_rows if not row["adaptation_id"])

    manifest = {
        "schema_version": 1,
        "dataset_id": "linux-0.01-historical-core-patches-v1",
        "publication_date": "2026-08-26",
        "upstream_path": "upstream/linux-0.01.tar.gz",
        "upstream_sha256": UPSTREAM_SHA256,
        "port_commit": revision,
        "port_tree": run(["git", "rev-parse", f"{revision}^{{tree}}"], text=True).strip(),
        "ledger_path": "docs/PORTING_LEDGER.md",
        "ledger_sha256": sha256_bytes(ledger_text.encode("utf-8")),
        "generator_path": GENERATOR_PATH,
        "generator_sha256": sha256_file(os.path.join(REPO_ROOT, GENERATOR_PATH)),
        "historical_core_directories": list(CORE_DIRECTORIES),
        "historical_core_path_count": len(rows),
        "adaptation_count": len(adaptation_rows),
        "unresolved_path_count": unresolved_count,
        "paired_observation_count": 0,
        "rq2_ablation_configuration_count": 0,
        "historical_core_patch_sha256": sha256_bytes(full_patch),
    }

    write_csv(
        os.path.join(output_dir, "file_deltas.csv"),
        [
            "delta_id", "path", "change_type", "upstream_sha256", "port_sha256",
            "upstream_mode", "port_mode", "added_lines", "deleted_lines", "hunk_count",
            "patch_sha256",
        ],
        rows,
    )
    write_csv(
        os.path.join(output_dir, "adaptations.csv"),
        [
            "adaptation_id", "title", "change_summary", "categories", "ledger_status",
            "interpretation_status", "rq1_claim_level", "rq2_role", "ledger_line_start",
            "ledger_line_end",
        ],
        adaptation_rows,
    )
    write_csv(
        os.path.join(output_dir, "adaptation_files.csv"),
        ["adaptation_id", "path", "delta_id", "relation", "join_basis", "semantic_attribution"],
        join_rows,
    )
    write_csv(
        os.path.join(output_dir, "evidence_links.csv"),
        [
            "evidence_id", "adaptation_id", "ledger_test", "reference", "reference_kind",
            "oracle_class", "retention", "observation_id", "raw_output_sha256",
        ],
        evidence_rows,
    )
    with open(os.path.join(output_dir, "historical-core.patch"), "wb") as output:
        output.write(full_patch)
    with open(os.path.join(output_dir, "README.md"), "w", encoding="utf-8") as output:
        output.write(dataset_readme(manifest))
    with open(os.path.join(output_dir, "MANIFEST.json"), "w", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2, sort_keys=True)
        output.write("\n")

    checksum_names = (
        "README.md", "MANIFEST.json", "adaptations.csv", "adaptation_files.csv",
        "evidence_links.csv", "file_deltas.csv", "historical-core.patch",
    )
    with open(os.path.join(output_dir, "SHA256SUMS.txt"), "w", encoding="ascii") as output:
        for name in checksum_names:
            output.write(f"{sha256_file(os.path.join(output_dir, name))}  {name}\n")


def check_dataset(revision):
    with tempfile.TemporaryDirectory(prefix="patch-dataset-check-") as temporary:
        generated = os.path.join(temporary, "patches")
        generate(generated, revision)
        expected_names = sorted(os.listdir(generated))
        actual_names = sorted(os.listdir(DATASET_DIR)) if os.path.isdir(DATASET_DIR) else []
        if actual_names != expected_names:
            raise ValueError(f"tracked dataset files are {actual_names}, expected {expected_names}")
        for name in expected_names:
            with open(os.path.join(generated, name), "rb") as source:
                expected = source.read()
            with open(os.path.join(DATASET_DIR, name), "rb") as source:
                actual = source.read()
            if actual != expected:
                raise ValueError(f"tracked dataset is stale: {name}")
    print("tracked patch dataset is reproducible")


def manifest_revision():
    path = os.path.join(DATASET_DIR, "MANIFEST.json")
    if not os.path.isfile(path):
        return DEFAULT_PORT_COMMIT
    with open(path, encoding="utf-8") as source:
        revision = json.load(source)["port_commit"]
    if revision != DEFAULT_PORT_COMMIT:
        raise ValueError(
            f"dataset v1 port commit is {revision}, expected {DEFAULT_PORT_COMMIT}"
        )
    return revision


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", default=DATASET_DIR)
    parser.add_argument("--revision", default=None)
    arguments = parser.parse_args()
    revision = arguments.revision or manifest_revision()
    if arguments.check:
        check_dataset(revision)
    else:
        generate(os.path.abspath(arguments.output), revision)
        print(f"patch dataset written to {os.path.abspath(arguments.output)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.CalledProcessError, KeyError) as error:
        print(f"patch dataset generation failed: {error}", file=sys.stderr)
        sys.exit(1)
