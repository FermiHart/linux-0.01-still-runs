#!/usr/bin/env python3
"""Validate the published reduced compiler-case dataset."""

import hashlib
import json
import os
import re
import subprocess


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(REPO_ROOT, "datasets", "compiler-cases", "v1")
SOURCE_COMMIT = "86cc23d776e8c7c49061892b1ec4f93f5fb4ad9c"
CASES = {
    "C-BUFFER-FREELIST": "buffer_freelist.c",
    "C-BITMAP-INLINE-ASM": "bitmap_inline_asm.c",
    "C-VSPRINTF-PERCENT-S": "vsprintf_percent_s.c",
}
ABIS = {"hosted-x86_64-sysv", "hosted-i386-sysv"}
OPTS = {"O0", "O1", "O2"}
TOP_LEVEL_FILES = {
    "README.md",
    "MANIFEST.json",
    "SHA256SUMS.txt",
    "classifications.json",
    "environment.json",
    "observations.jsonl",
    "assembly",
    "binaries",
    "sources",
}
EXPECTED_COMPILER_HASHES = {
    "executable_sha256": "1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26",
    "cc1_sha256": "5d1679131184e2de4435b426eb264bf13472fe026db8e5c6bc97445814e8e2f4",
    "collect2_sha256": "4d1f341ae5b763b513258ee2812422a45e063c30a2f1924a0cf63d3699f3a158",
}
EXPECTED_PACKAGES = {
    "lib32gcc-13-dev_13.3.0-6ubuntu2~24.04.1_amd64.deb":
        "0850e0555c86f2ce7a954158eb47df42d7645bfa4f12f29ea2df76459c930ac0",
    "lib32gcc-s1_14.2.0-4ubuntu2~24.04.1_amd64.deb":
        "1802dc75345ccce457b44110a3819ca74ff8c33fc62394a78d0e59a11c0cf770",
    "libc6-dev-i386_2.39-0ubuntu8.8_amd64.deb":
        "b560b6f53e60ef83320c2c170d890074dcb4bdd077dcea03ff98a030ae9c635e",
    "libc6-dev_2.39-0ubuntu8.8_amd64.deb":
        "bb8741966e7c1d2e2c0b84bb311717a0908fb563d9b2247b7212710e3cd88b94",
    "libc6-i386_2.39-0ubuntu8.8_amd64.deb":
        "7c373e63a02bda5d8da4363a899c24622b1234f658b5fca78a9a4d8b1017b079",
}


def fail(message):
    raise AssertionError(message)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(name):
    with open(os.path.join(DATASET_DIR, name), encoding="utf-8") as source:
        return json.load(source)


def relative_files():
    files = set()
    for current, directories, names in os.walk(DATASET_DIR):
        directories.sort()
        for name in sorted(names):
            files.add(os.path.relpath(os.path.join(current, name), DATASET_DIR))
    return files


def expected_argv(row, assembly=False):
    source = f"sources/{CASES[row['case_id']]}"
    argv = ["${CC}", "-Wall", "-Wextra", "-Werror", "-std=gnu89"]
    if row["abi_id"] == "hosted-i386-sysv":
        argv.extend([
            "--sysroot=${MULTILIB_ROOT}",
            "-isystem", "${MULTILIB_ROOT}/usr/include",
            "-isystem", "${MULTILIB_ROOT}/usr/include/x86_64-linux-gnu",
            "-B${MULTILIB_ROOT}/usr/lib32/",
            "-B${MULTILIB_ROOT}/usr/lib/gcc/x86_64-linux-gnu/13/32/",
            "-L${MULTILIB_ROOT}/usr/lib32",
            "-L${MULTILIB_ROOT}/usr/lib/gcc/x86_64-linux-gnu/13/32",
            "-m32", "-no-pie",
        ])
    argv.append(f"-{row['optimization']}")
    if assembly:
        argv.extend(["-S", "-fverbose-asm", "-o", row["assembly_path"], source])
    else:
        argv.extend(["-o", row["binary_path"], source])
    return argv


def expected_run_argv(row):
    if row["abi_id"] == "hosted-x86_64-sysv":
        return [f"./{row['binary_path']}"]
    return [
        "${MULTILIB_ROOT}/usr/lib32/ld-linux.so.2",
        "--library-path",
        "${MULTILIB_ROOT}/usr/lib32",
        f"${{DATASET_ROOT}}/{row['binary_path']}",
    ]


def main():
    if not os.path.isdir(DATASET_DIR):
        fail("datasets/compiler-cases/v1 is missing")
    if set(os.listdir(DATASET_DIR)) != TOP_LEVEL_FILES:
        fail("compiler-case dataset has an unexpected top-level inventory")

    manifest = load_json("MANIFEST.json")
    expected_manifest = {
        "schema_version": 1,
        "dataset_id": "linux-0.01-reduced-compiler-cases-v1",
        "source_commit": SOURCE_COMMIT,
        "case_count": 3,
        "abi_count": 2,
        "optimization_count": 3,
        "observation_count": 18,
        "compiler_identity_count": 1,
        "unique_compiler_version_count": 1,
        "pass_count": 17,
        "fail_count": 1,
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            fail(f"manifest {field!r} is {manifest.get(field)!r}, expected {expected!r}")
    if manifest.get("reference_scope") != "one compiler identity x two hosted ABIs":
        fail("manifest does not bound the reference-run scope")
    if manifest.get("assembly_normalization") != (
        "replace ephemeral multilib-root prefix with ${MULTILIB_ROOT}; "
        "strip trailing horizontal whitespace"
    ):
        fail("manifest does not declare the sole assembly normalization")
    required_non_claims = {
        "not_a_compiler_version_matrix",
        "not_a_freestanding_kernel_abi_run",
        "not_proof_that_o1_is_minimal_or_necessary",
        "not_proof_of_a_gcc_bug",
        "not_a_reproduction_of_unobserved_historical_symptoms",
        "not_a_complete_archive_of_every_host_build_input",
    }
    if set(manifest.get("non_claims", [])) != required_non_claims:
        fail("manifest non-claims are incomplete")
    generator_path = os.path.join(REPO_ROOT, manifest.get("generator_path", ""))
    if not os.path.isfile(generator_path) or sha256(generator_path) != manifest.get("generator_sha256"):
        fail("manifest generator identity does not match the live generator")

    source_dir = os.path.join(DATASET_DIR, "sources")
    if set(os.listdir(source_dir)) != set(CASES.values()):
        fail("dataset must publish exactly the three reduced sources")
    for source_name in CASES.values():
        path = f"tests/compiler-cases/{source_name}"
        expected = subprocess.check_output(["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=REPO_ROOT)
        with open(os.path.join(source_dir, source_name), "rb") as source:
            if source.read() != expected:
                fail(f"published source does not match {SOURCE_COMMIT}:{path}")
    source_records = manifest.get("sources", [])
    if {record.get("case_id") for record in source_records} != set(CASES):
        fail("manifest source records do not cover the exact cases")
    for record in source_records:
        source_name = CASES[record["case_id"]]
        if record.get("path") != f"sources/{source_name}":
            fail(f"manifest source path is stale for {record['case_id']}")
        if record.get("sha256") != sha256(os.path.join(source_dir, source_name)):
            fail(f"manifest source hash is stale for {record['case_id']}")
        if record.get("embedded_comment_status") != (
            "inherited_hypothesis_not_dataset_conclusion"
        ):
            fail(f"manifest source caveat is missing for {record['case_id']}")

    environment = load_json("environment.json")
    compiler = environment.get("compiler", {})
    if compiler.get("id") != "CC-GCC-13.3.0-X86_64-LINUX-GNU":
        fail("reference compiler lacks a stable identity")
    for field in (
        "version", "target", "executable_sha256", "cc1_sha256", "collect2_sha256"
    ):
        if not compiler.get(field):
            fail(f"compiler identity lacks {field}")
    if compiler.get("version") != "13.3.0" or compiler.get("target") != "x86_64-linux-gnu":
        fail("reference compiler version/target changed")
    for field, expected in EXPECTED_COMPILER_HASHES.items():
        if compiler.get(field) != expected:
            fail(f"reference compiler {field} changed")
    if not re.fullmatch(r"[0-9a-f]{64}", compiler["executable_sha256"]):
        fail("compiler executable hash is invalid")
    if environment.get("host", {}).get("architecture") != "x86_64":
        fail("reference host architecture is not explicit")
    abi_records = environment.get("abis", [])
    if {record.get("id") for record in abi_records} != ABIS:
        fail("environment does not identify both hosted ABIs")
    for record in abi_records:
        for field in ("elf_class", "elf_machine", "libc_sha256", "loader_sha256"):
            if not record.get(field):
                fail(f"ABI {record.get('id')} lacks {field}")
        if record.get("execution_model") != "hosted GNU/Linux process":
            fail(f"ABI {record.get('id')} is mislabeled as a kernel execution")
    package_records = environment.get("multilib_packages", [])
    packages = {record.get("name"): record.get("sha256") for record in package_records}
    if packages != EXPECTED_PACKAGES or len(package_records) != len(EXPECTED_PACKAGES):
        fail("i386 sysroot package provenance is incomplete")
    if environment.get("multilib_root_derivation") != (
        "dpkg-deb --extract in sorted name order plus canonical /lib32 and "
        "/lib/ld-linux.so.2 symlinks"
    ):
        fail("i386 sysroot derivation is not explicit")

    observations = []
    with open(os.path.join(DATASET_DIR, "observations.jsonl"), encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            try:
                observations.append(json.loads(line))
            except json.JSONDecodeError as error:
                fail(f"observations.jsonl line {number} is invalid: {error}")
    expected_cells = {
        (case_id, abi, opt) for case_id in CASES for abi in ABIS for opt in OPTS
    }
    actual_cells = {
        (row.get("case_id"), row.get("abi_id"), row.get("optimization"))
        for row in observations
    }
    if len(observations) != 18 or actual_cells != expected_cells:
        fail("observations do not cover the exact 3 x 2 x 3 reference grid")
    if len({row.get("observation_id") for row in observations}) != 18:
        fail("observation IDs are not unique")

    failures = []
    expected_outputs = {
        "C-BUFFER-FREELIST": "PASS: free-list loop behaves as intended\n",
        "C-BITMAP-INLINE-ASM": "PASS: bit operations are visible after inline asm\n",
        "C-VSPRINTF-PERCENT-S": "PASS: %s formatting reads the correct argument slot\n",
    }
    for row in observations:
        observation_id = row["observation_id"]
        if row.get("compiler_id") != compiler["id"]:
            fail(f"{observation_id} has an unknown compiler identity")
        if row.get("compile_rc") != 0:
            fail(f"{observation_id} did not compile")
        if row.get("compile_argv") != expected_argv(row):
            fail(f"{observation_id} compiler argv does not exactly match its cell")
        if row.get("assembly_compile_argv") != expected_argv(row, assembly=True):
            fail(f"{observation_id} assembly argv does not exactly match its cell")
        if row.get("run_argv") != expected_run_argv(row):
            fail(f"{observation_id} run argv does not exactly match its ABI")
        if row.get("compile_stdout") != "" or row.get("compile_stderr") != "":
            fail(f"{observation_id} has unexpected compiler diagnostics")
        if row.get("assembly_compile_rc") != 0:
            fail(f"{observation_id} assembly did not compile")
        if row.get("assembly_normalization") != manifest["assembly_normalization"]:
            fail(f"{observation_id} assembly normalization is not declared")
        if row.get("assembly_compile_stdout") != "" or row.get("assembly_compile_stderr") != "":
            fail(f"{observation_id} assembly compile has unexpected diagnostics")
        if row.get("outcome") not in {"PASS", "FAIL"}:
            fail(f"{observation_id} has an unknown outcome")
        if row["outcome"] == "FAIL":
            failures.append(row)
        binary_rel = row.get("binary_path", "")
        assembly_rel = row.get("assembly_path", "")
        binary = os.path.join(DATASET_DIR, binary_rel)
        assembly = os.path.join(DATASET_DIR, assembly_rel)
        if not os.path.isfile(binary) or sha256(binary) != row.get("binary_sha256"):
            fail(f"{observation_id} binary is missing or has the wrong hash")
        if os.path.getsize(binary) != row.get("binary_size"):
            fail(f"{observation_id} binary size is stale")
        if not os.path.isfile(assembly) or os.path.getsize(assembly) < 100:
            fail(f"{observation_id} assembly is missing or empty")
        if sha256(assembly) != row.get("assembly_sha256"):
            fail(f"{observation_id} assembly hash is stale")
        elf_header = subprocess.check_output(["readelf", "-h", binary], text=True)
        expected_class = "ELF64" if row["abi_id"] == "hosted-x86_64-sysv" else "ELF32"
        if f"Class:                             {expected_class}" not in elf_header:
            fail(f"{observation_id} binary does not match its ABI label")
        if row.get("elf_class") != expected_class:
            fail(f"{observation_id} recorded ELF class is stale")
        expected_machine = "Advanced Micro Devices X86-64" if expected_class == "ELF64" else "Intel 80386"
        if row.get("elf_machine") != expected_machine or expected_machine not in elf_header:
            fail(f"{observation_id} recorded ELF machine is stale")
        expected_interpreter = "/lib64/ld-linux-x86-64.so.2" if expected_class == "ELF64" else "/lib/ld-linux.so.2"
        if row.get("elf_interpreter") != expected_interpreter:
            fail(f"{observation_id} recorded ELF interpreter is stale")
        elf_program_headers = subprocess.check_output(["readelf", "-l", binary], text=True)
        if f"Requesting program interpreter: {expected_interpreter}" not in elf_program_headers:
            fail(f"{observation_id} binary interpreter does not match its record")
        if row["outcome"] == "PASS":
            if row.get("run_rc") != 0 or row.get("run_stdout") != expected_outputs[row["case_id"]]:
                fail(f"{observation_id} PASS output/status is inconsistent")
            if row.get("run_stderr") != "":
                fail(f"{observation_id} PASS has unexpected stderr")
        if row["abi_id"] == "hosted-x86_64-sysv":
            rerun = subprocess.run([binary], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if (
                rerun.returncode != row.get("run_rc")
                or rerun.stdout != row.get("run_stdout")
                or rerun.stderr != row.get("run_stderr")
            ):
                fail(f"{observation_id} retained x86_64 executable no longer reproduces its output")
    if len(failures) != 1:
        fail(f"reference run has {len(failures)} failures, expected one")
    failure = failures[0]
    if (
        failure["case_id"], failure["abi_id"], failure["optimization"], failure["run_rc"]
    ) != ("C-BITMAP-INLINE-ASM", "hosted-x86_64-sysv", "O2", 1):
        fail("the sole retained divergence is not bitmap/x86_64/O2 rc=1")
    if "bit 0 not visible" not in failure.get("run_stderr", ""):
        fail("the retained divergence lost its observable output")

    classifications = load_json("classifications.json")
    case_records = classifications.get("cases", [])
    if {record.get("case_id") for record in case_records} != set(CASES):
        fail("classifications do not cover the exact three cases")
    for record in case_records:
        if isinstance(record.get("gcc_bug_status"), bool) or isinstance(
            record.get("source_contract_status"), bool
        ):
            fail(f"{record.get('case_id')} collapses an evidential state to a boolean")
        if record.get("gcc_bug_status") not in {"NOT_SUPPORTED", "NOT_ESTABLISHED"}:
            fail(f"{record.get('case_id')} overstates a GCC-bug conclusion")
        linked = set(record.get("observation_ids", []))
        expected = {row["observation_id"] for row in observations if row["case_id"] == record["case_id"]}
        if linked != expected:
            fail(f"{record.get('case_id')} classification is not linked to all observations")

    files = relative_files()
    checksums = {}
    with open(os.path.join(DATASET_DIR, "SHA256SUMS.txt"), encoding="ascii") as source:
        for line in source:
            digest, name = line.rstrip("\n").split("  ", 1)
            checksums[name] = digest
    if set(checksums) != files - {"SHA256SUMS.txt"}:
        fail("SHA256SUMS.txt does not cover every non-self-referential dataset file")
    for name, digest in checksums.items():
        if sha256(os.path.join(DATASET_DIR, name)) != digest:
            fail(f"checksum mismatch for {name}")

    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", os.path.join(DATASET_DIR, failures[0]["binary_path"])],
        cwd=REPO_ROOT,
    )
    if ignored.returncode == 0:
        fail("published compiler-case binaries are ignored by Git")

    forbidden = (b"/tmp/", REPO_ROOT.encode("utf-8"))
    for name in files:
        if name.endswith((".json", ".jsonl", ".md", ".txt", ".c", ".s")):
            with open(os.path.join(DATASET_DIR, name), "rb") as source:
                content = source.read()
            if any(marker in content for marker in forbidden):
                fail(f"{name} leaks an ephemeral absolute path")

    required_public_references = {
        "MISSION.md": "datasets/compiler-cases/v1/",
        "README.md": "datasets/compiler-cases/v1/",
        "docs/METHODOLOGY.md": "datasets/compiler-cases/v1/observations.jsonl",
        "docs/RESEARCH-QUESTIONS.md": "datasets/compiler-cases/v1/MANIFEST.json",
        "docs/SBOM.md": "datasets/compiler-cases/v1/",
    }
    for path, reference in required_public_references.items():
        with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as source:
            if reference not in source.read():
                fail(f"{path} does not cite the published compiler-case dataset")
    with open(os.path.join(REPO_ROOT, "Makefile"), encoding="utf-8") as source:
        makefile = source.read()
    if "test-compiler-case-dataset:" not in makefile:
        fail("Makefile does not expose the compiler-case dataset gate")
    with open(os.path.join(REPO_ROOT, "scripts", "make-artifact.sh"), encoding="utf-8") as source:
        if "datasets" not in source.read():
            fail("artifact packaging does not include the published datasets")

    print("compiler-case dataset valid: 3 cases, 18 observations, 17 PASS, 1 FAIL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
