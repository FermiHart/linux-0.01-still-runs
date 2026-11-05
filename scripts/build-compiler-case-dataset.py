#!/usr/bin/env python3
"""Build a bounded, versioned reference run of the reduced compiler cases."""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_PATH = os.path.relpath(os.path.abspath(__file__), REPO_ROOT)
SOURCE_COMMIT = "86cc23d776e8c7c49061892b1ec4f93f5fb4ad9c"
DEFAULT_OUTPUT = os.path.join(REPO_ROOT, "build", "compiler-case-candidates", "v1")
PUBLISHED_OUTPUT = os.path.join(REPO_ROOT, "datasets", "compiler-cases", "v1")
BASE_FLAGS = ["-Wall", "-Wextra", "-Werror", "-std=gnu89"]
OPTS = ("O0", "O1", "O2")
CASES = (
    ("C-BUFFER-FREELIST", "buffer_freelist", "buffer_freelist.c", "fs/buffer.c"),
    ("C-BITMAP-INLINE-ASM", "bitmap_inline_asm", "bitmap_inline_asm.c", "fs/bitmap.c"),
    ("C-VSPRINTF-PERCENT-S", "vsprintf_percent_s", "vsprintf_percent_s.c", "kernel/vsprintf.c"),
)
ABIS = (
    ("hosted-x86_64-sysv", "X86_64"),
    ("hosted-i386-sysv", "I386"),
)
MULTILIB_PACKAGE_PREFIXES = (
    "lib32gcc-13-dev_",
    "lib32gcc-s1_",
    "libc6-dev_",
    "libc6-dev-i386_",
    "libc6-i386_",
)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def controlled_environment():
    return {
        "HOME": os.devnull,
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin",
        "SOURCE_DATE_EPOCH": "0",
        "TZ": "UTC",
    }


def run(command, *, cwd=REPO_ROOT, env=None, check=True):
    if env is None:
        env = controlled_environment()
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def output(command):
    return subprocess.check_output(
        command, cwd=REPO_ROOT, text=True, env=controlled_environment()
    ).strip()


def git_bytes(revision, path):
    environment = controlled_environment()
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_PAGER": "cat",
    })
    return subprocess.check_output(
        ["git", "show", f"{revision}:{path}"], cwd=REPO_ROOT, env=environment
    )


def canonical_argv(argv, compiler, multilib_root, root):
    canonical = []
    replacements = (
        (compiler, "${CC}"),
        (multilib_root, "${MULTILIB_ROOT}"),
        (root, "${DATASET_ROOT}"),
    )
    for argument in argv:
        value = argument
        for original, replacement in replacements:
            if original:
                value = value.replace(original, replacement)
        canonical.append(value)
    return canonical


def compiler_identity(compiler):
    compiler = os.path.realpath(compiler)
    version = output([compiler, "-dumpfullversion", "-dumpversion"])
    target = output([compiler, "-dumpmachine"])
    cc1 = output([compiler, "-print-prog-name=cc1"])
    cc1 = os.path.realpath(cc1)
    if not os.path.isfile(cc1):
        raise RuntimeError(f"compiler cc1 is missing: {cc1}")
    collect2 = os.path.realpath(output([compiler, "-print-prog-name=collect2"]))
    if not os.path.isfile(collect2):
        raise RuntimeError(f"compiler collect2 is missing: {collect2}")
    return {
        "id": f"CC-GCC-{version}-X86_64-LINUX-GNU",
        "family": "GCC",
        "version": version,
        "version_output": run([compiler, "--version"]).stdout.rstrip("\n"),
        "target": target,
        "executable_name": os.path.basename(compiler),
        "executable_sha256": sha256_file(compiler),
        "cc1_name": os.path.basename(cc1),
        "cc1_sha256": sha256_file(cc1),
        "collect2_name": os.path.basename(collect2),
        "collect2_sha256": sha256_file(collect2),
    }


def os_release():
    values = {}
    with open("/etc/os-release", encoding="utf-8") as source:
        for line in source:
            if "=" not in line:
                continue
            key, value = line.rstrip("\n").split("=", 1)
            values[key] = value.strip('"')
    return {"id": values.get("ID", "unknown"), "version_id": values.get("VERSION_ID", "unknown")}


def find_program(name):
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"required program is missing: {name}")
    return os.path.realpath(path)


def tool_identity(name):
    path = find_program(name)
    process = run([path, "--version"])
    first_line = (process.stdout or process.stderr).splitlines()[0]
    return {
        "name": os.path.basename(path),
        "version_output_first_line": first_line,
        "executable_sha256": sha256_file(path),
    }


def package_identities(package_dir):
    entries = []
    names = sorted(os.listdir(package_dir))
    for prefix in MULTILIB_PACKAGE_PREFIXES:
        matches = [name for name in names if name.startswith(prefix) and name.endswith(".deb")]
        if len(matches) != 1:
            raise RuntimeError(f"expected one {prefix}*.deb in {package_dir}, found {matches}")
        name = matches[0]
        entries.append({"name": name, "sha256": sha256_file(os.path.join(package_dir, name))})
    return sorted(entries, key=lambda entry: entry["name"])


def extract_packages(package_dir, entries, root):
    dpkg_deb = find_program("dpkg-deb")
    for entry in entries:
        process = run(
            [dpkg_deb, "--extract", os.path.join(package_dir, entry["name"]), root],
            check=False,
        )
        if process.returncode:
            raise RuntimeError(f"failed to extract {entry['name']}: {process.stderr}")
    os.symlink("usr/lib32", os.path.join(root, "lib32"))
    os.makedirs(os.path.join(root, "lib"), exist_ok=True)
    os.symlink("../usr/lib32/ld-linux.so.2", os.path.join(root, "lib", "ld-linux.so.2"))


def i386_flags(multilib_root):
    return [
        f"--sysroot={multilib_root}",
        "-isystem", os.path.join(multilib_root, "usr", "include"),
        "-isystem", os.path.join(multilib_root, "usr", "include", "x86_64-linux-gnu"),
        f"-B{os.path.join(multilib_root, 'usr', 'lib32')}/",
        f"-B{os.path.join(multilib_root, 'usr', 'lib', 'gcc', 'x86_64-linux-gnu', '13', '32')}/",
        f"-L{os.path.join(multilib_root, 'usr', 'lib32')}",
        f"-L{os.path.join(multilib_root, 'usr', 'lib', 'gcc', 'x86_64-linux-gnu', '13', '32')}",
        "-m32",
        "-no-pie",
    ]


def readelf_value(binary, label):
    text = run([find_program("readelf"), "-h", binary]).stdout
    for line in text.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key == label:
            return value.strip()
    raise RuntimeError(f"readelf did not report {label} for {binary}")


def interpreter(binary):
    text = run([find_program("readelf"), "-l", binary]).stdout
    marker = "Requesting program interpreter: "
    for line in text.splitlines():
        if marker in line:
            return line.split(marker, 1)[1].rstrip("]")
    raise RuntimeError(f"readelf did not report an interpreter for {binary}")


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")


def normalize_assembly(path, multilib_root):
    with open(path, "rb") as source:
        content = source.read()
    normalized = content.replace(multilib_root.encode("utf-8"), b"${MULTILIB_ROOT}")
    normalized = b"\n".join(line.rstrip(b" \t") for line in normalized.splitlines()) + b"\n"
    with open(path, "wb") as destination:
        destination.write(normalized)


def write_readme(path):
    text = """# Reduced compiler cases v1

This directory is the versioned reference-run dataset for the three reduced
`-O2`-sensitive patterns investigated in Waves 075-083. It retains the exact
source snapshots, one GCC 13.3.0 observation grid, compiler-generated assembly,
hosted executables, process output, classifications, and environment identities.

## Observation grid

The reference run contains 18 cells: three reductions, `-O0`/`-O1`/`-O2`, and
two hosted GNU/Linux process ABIs (`x86_64` SysV and `i386` SysV). Seventeen
cells pass. Only `bitmap_inline_asm` at `x86_64 -O2` fails, with exit status 1
and the retained `bit 0 not visible` diagnostic.

The i386 programs were compiled against the five Debian/Ubuntu package archives
identified in `environment.json` and executed through the identified i386 glibc
loader. `${CC}`, `${MULTILIB_ROOT}`, and `${DATASET_ROOT}` in argv arrays are
path bindings; replacing them with the identified compiler, extracted package
root, and dataset root reconstructs the actual process argv without retaining
ephemeral absolute paths.

## Evidence boundaries

This is one compiler identity, not a compiler-version matrix. Both ABIs are
hosted GNU/Linux process ABIs, not the freestanding Linux 0.01 kernel ABI. The
dataset does not prove that any `-O1` workaround is necessary or minimal, does
not establish a GCC bug, and does not reproduce the unobserved historical
symptoms for `buffer_freelist` or `vsprintf_percent_s`.

Comments inside the source snapshots are inherited investigation hypotheses,
not evidence-linked conclusions. In particular, the bitmap source comment that
the asm does not mention memory is inaccurate: its memory operand is input-only,
and its statement about full-kernel effects is untested by this dataset. The
bounded conclusions are in `classifications.json`; where the run does not
establish a proposition, the dataset uses `NOT_ESTABLISHED` rather than a
boolean `false`.

## Files

- `MANIFEST.json`: identity, scope, counts, source provenance, and non-claims.
- `environment.json`: compiler, tools, host, ABI runtime, and package identities.
- `observations.jsonl`: normalized argv, return codes, stdout/stderr, and payload hashes.
- `classifications.json`: bounded conclusions linked to observation IDs.
- `sources/`: exact reductions from the pinned source commit.
- `assembly/`: full compiler-generated assembly for every cell, with the
  ephemeral multilib-root prefix replaced by `${MULTILIB_ROOT}` in comments and
  trailing horizontal whitespace removed.
- `binaries/`: the exact hosted executables that produced the retained outputs.
- `SHA256SUMS.txt`: every non-self-referential file in this directory.

Regenerate a candidate outside this immutable publication with:

```sh
python3 scripts/build-compiler-case-dataset.py \
  --compiler /usr/bin/gcc-13 \
  --multilib-packages /path/to/package-archives
```
"""
    with open(path, "w", encoding="utf-8") as destination:
        destination.write(text)


def build_observations(root, compiler, compiler_id, multilib_root, environment):
    observations = []
    compiler_env = controlled_environment()
    for case_id, short_name, source_name, _core_path in CASES:
        source_rel = os.path.join("sources", source_name)
        for abi_id, abi_tag in ABIS:
            abi_flags = [] if abi_id == "hosted-x86_64-sysv" else i386_flags(multilib_root)
            for opt in OPTS:
                observation_id = f"OBS-GCC13-{short_name.replace('_', '-').upper()}-{abi_tag}-{opt}"
                binary_rel = os.path.join("binaries", f"{observation_id}.bin")
                assembly_rel = os.path.join("assembly", f"{observation_id}.s")
                compile_argv = [compiler, *BASE_FLAGS, *abi_flags, f"-{opt}", "-o", binary_rel, source_rel]
                compiled = run(compile_argv, cwd=root, env=compiler_env, check=False)
                if compiled.returncode:
                    raise RuntimeError(
                        f"{observation_id} compile failed ({compiled.returncode}): {compiled.stderr}"
                    )
                assembly_argv = [
                    compiler, *BASE_FLAGS, *abi_flags, f"-{opt}", "-S", "-fverbose-asm",
                    "-o", assembly_rel, source_rel,
                ]
                assembled = run(assembly_argv, cwd=root, env=compiler_env, check=False)
                if assembled.returncode:
                    raise RuntimeError(
                        f"{observation_id} assembly compile failed ({assembled.returncode}): {assembled.stderr}"
                    )
                binary = os.path.join(root, binary_rel)
                assembly = os.path.join(root, assembly_rel)
                normalize_assembly(assembly, multilib_root)
                with open(binary, "rb") as compiled_binary:
                    if multilib_root.encode("utf-8") in compiled_binary.read():
                        raise RuntimeError(f"{observation_id} binary embeds the ephemeral multilib root")
                if abi_id == "hosted-x86_64-sysv":
                    run_argv = [os.path.join(".", binary_rel)]
                else:
                    loader = os.path.join(multilib_root, "usr", "lib32", "ld-linux.so.2")
                    library = os.path.join(multilib_root, "usr", "lib32")
                    run_argv = [loader, "--library-path", library, binary]
                executed = run(run_argv, cwd=root, env=compiler_env, check=False)
                observations.append({
                    "observation_id": observation_id,
                    "case_id": case_id,
                    "compiler_id": compiler_id,
                    "abi_id": abi_id,
                    "optimization": opt,
                    "compile_argv": canonical_argv(compile_argv, compiler, multilib_root, root),
                    "compile_rc": compiled.returncode,
                    "compile_stdout": compiled.stdout,
                    "compile_stderr": compiled.stderr,
                    "assembly_compile_argv": canonical_argv(
                        assembly_argv, compiler, multilib_root, root
                    ),
                    "assembly_compile_rc": assembled.returncode,
                    "assembly_compile_stdout": assembled.stdout,
                    "assembly_compile_stderr": assembled.stderr,
                    "run_argv": canonical_argv(run_argv, compiler, multilib_root, root),
                    "run_rc": executed.returncode,
                    "run_stdout": executed.stdout,
                    "run_stderr": executed.stderr,
                    "outcome": "PASS" if executed.returncode == 0 else "FAIL",
                    "binary_path": binary_rel,
                    "binary_sha256": sha256_file(binary),
                    "binary_size": os.path.getsize(binary),
                    "assembly_path": assembly_rel,
                    "assembly_sha256": sha256_file(assembly),
                    "assembly_normalization": (
                        "replace ephemeral multilib-root prefix with ${MULTILIB_ROOT}; "
                        "strip trailing horizontal whitespace"
                    ),
                    "elf_class": readelf_value(binary, "Class"),
                    "elf_machine": readelf_value(binary, "Machine"),
                    "elf_interpreter": interpreter(binary),
                })
    return observations


def classifications(observations):
    observation_ids = {}
    for row in observations:
        observation_ids.setdefault(row["case_id"], []).append(row["observation_id"])
    return {
        "schema_version": 1,
        "cases": [
            {
                "case_id": "C-BUFFER-FREELIST",
                "classification": "HISTORICAL_HYPOTHESIS_NOT_REPRODUCED",
                "gcc_bug_status": "NOT_ESTABLISHED",
                "source_contract_status": "NOT_ESTABLISHED",
                "rationale": (
                    "All six retained cells pass. This reduction does not reproduce the "
                    "historical symptom and does not establish why the full kernel used -O1."
                ),
                "observation_ids": observation_ids["C-BUFFER-FREELIST"],
            },
            {
                "case_id": "C-BITMAP-INLINE-ASM",
                "classification": "SOURCE_CONTRACT_VIOLATION_OBSERVED",
                "gcc_bug_status": "NOT_SUPPORTED",
                "source_contract_status": "SUPPORTED_FOR_REDUCED_X86_64_O2_CASE",
                "rationale": (
                    "The x86_64 -O2 cell alone observes a stale value after inline asm whose "
                    "memory operand is declared input-only. This supports a source constraint "
                    "violation in the reduction, not a GCC defect or kernel-level necessity claim."
                ),
                "observation_ids": observation_ids["C-BITMAP-INLINE-ASM"],
            },
            {
                "case_id": "C-VSPRINTF-PERCENT-S",
                "classification": "HISTORICAL_HYPOTHESIS_NOT_REPRODUCED",
                "gcc_bug_status": "NOT_ESTABLISHED",
                "source_contract_status": "NOT_ESTABLISHED",
                "rationale": (
                    "All six retained cells pass. This single-string hosted reduction does not "
                    "reproduce the historical full-printk symptom or exclude other contexts."
                ),
                "observation_ids": observation_ids["C-VSPRINTF-PERCENT-S"],
            },
        ],
    }


def write_checksums(root):
    paths = []
    for current, directories, names in os.walk(root):
        directories.sort()
        for name in sorted(names):
            path = os.path.join(current, name)
            relative = os.path.relpath(path, root)
            if relative != "SHA256SUMS.txt":
                paths.append(relative)
    with open(os.path.join(root, "SHA256SUMS.txt"), "w", encoding="ascii") as destination:
        for relative in sorted(paths):
            destination.write(f"{sha256_file(os.path.join(root, relative))}  {relative}\n")


def build_dataset(output_dir, compiler, package_dir, publish, replace):
    output_dir = os.path.realpath(os.path.abspath(output_dir))
    published_output = os.path.realpath(PUBLISHED_OUTPUT)
    common_path = os.path.commonpath([output_dir, published_output])
    overlaps_publication = common_path in {output_dir, published_output}
    if overlaps_publication and not publish:
        raise RuntimeError("refusing to write the published dataset without --publish")
    if os.path.exists(output_dir) and not replace:
        raise RuntimeError(f"refusing to overwrite existing dataset: {output_dir}")
    if replace and overlaps_publication and not publish:
        raise RuntimeError("refusing to replace the published dataset without --publish")

    compiler = os.path.realpath(compiler)
    compiler_record = compiler_identity(compiler)
    if compiler_record["version"] != "13.3.0" or compiler_record["target"] != "x86_64-linux-gnu":
        raise RuntimeError("the v1 reference run requires GCC 13.3.0 targeting x86_64-linux-gnu")

    os.makedirs(os.path.dirname(output_dir), exist_ok=True)
    temporary = tempfile.mkdtemp(prefix="compiler-case-v1-", dir=os.path.dirname(output_dir))
    try:
        multilib_root = os.path.join(temporary, ".multilib-root")
        os.makedirs(multilib_root)
        package_records = package_identities(package_dir)
        extract_packages(package_dir, package_records, multilib_root)
        for required in (
            os.path.join(multilib_root, "usr", "include", "stdio.h"),
            os.path.join(multilib_root, "usr", "lib32", "libc.so.6"),
            os.path.join(multilib_root, "usr", "lib32", "ld-linux.so.2"),
            os.path.join(multilib_root, "usr", "lib", "gcc", "x86_64-linux-gnu", "13", "32", "libgcc.a"),
        ):
            if not os.path.isfile(required):
                raise RuntimeError(f"extracted multilib packages lack required file: {required}")
        for directory in ("sources", "assembly", "binaries"):
            os.makedirs(os.path.join(temporary, directory))
        source_hashes = {}
        source_records = []
        for case_id, _short_name, source_name, core_path in CASES:
            repository_path = f"tests/compiler-cases/{source_name}"
            content = git_bytes(SOURCE_COMMIT, repository_path)
            with open(os.path.join(temporary, "sources", source_name), "wb") as destination:
                destination.write(content)
            source_hashes[source_name] = sha256_bytes(content)
            source_records.append({
                "case_id": case_id,
                "path": f"sources/{source_name}",
                "repository_path": repository_path,
                "historical_core_path": core_path,
                "sha256": source_hashes[source_name],
                "embedded_comment_status": "inherited_hypothesis_not_dataset_conclusion",
            })

        x86_libc = "/lib/x86_64-linux-gnu/libc.so.6"
        x86_loader = os.path.realpath("/lib64/ld-linux-x86-64.so.2")
        i386_libc = os.path.join(multilib_root, "usr", "lib32", "libc.so.6")
        i386_loader = os.path.join(multilib_root, "usr", "lib32", "ld-linux.so.2")
        environment = {
            "schema_version": 1,
            "compiler": compiler_record,
            "host": {
                "architecture": platform.machine(),
                "kernel_release": platform.release(),
                "operating_system": os_release(),
            },
            "tools": {
                name: tool_identity(name)
                for name in ("as", "dpkg-deb", "ld", "readelf", "objdump")
            },
            "abis": [
                {
                    "id": "hosted-x86_64-sysv",
                    "execution_model": "hosted GNU/Linux process",
                    "elf_class": "ELF64",
                    "elf_machine": "Advanced Micro Devices X86-64",
                    "loader_name": os.path.basename(x86_loader),
                    "loader_sha256": sha256_file(x86_loader),
                    "libc_name": os.path.basename(x86_libc),
                    "libc_sha256": sha256_file(x86_libc),
                },
                {
                    "id": "hosted-i386-sysv",
                    "execution_model": "hosted GNU/Linux process",
                    "elf_class": "ELF32",
                    "elf_machine": "Intel 80386",
                    "loader_name": os.path.basename(i386_loader),
                    "loader_sha256": sha256_file(i386_loader),
                    "libc_name": os.path.basename(i386_libc),
                    "libc_sha256": sha256_file(i386_libc),
                },
            ],
            "multilib_packages": package_records,
            "multilib_root_derivation": (
                "dpkg-deb --extract in sorted name order plus canonical /lib32 and "
                "/lib/ld-linux.so.2 symlinks"
            ),
            "path_binding_contract": {
                "${CC}": "compiler executable identified by compiler.executable_sha256",
                "${MULTILIB_ROOT}": "root produced by extracting the five identified package archives",
                "${DATASET_ROOT}": "root of this dataset directory",
            },
        }
        write_json(os.path.join(temporary, "environment.json"), environment)
        observations = build_observations(
            temporary, compiler, compiler_record["id"], multilib_root, environment
        )
        with open(os.path.join(temporary, "observations.jsonl"), "w", encoding="utf-8") as destination:
            for row in observations:
                destination.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        write_json(os.path.join(temporary, "classifications.json"), classifications(observations))
        write_readme(os.path.join(temporary, "README.md"))

        failures = [row for row in observations if row["outcome"] == "FAIL"]
        manifest = {
            "schema_version": 1,
            "dataset_id": "linux-0.01-reduced-compiler-cases-v1",
            "source_commit": SOURCE_COMMIT,
            "generator_path": GENERATOR_PATH,
            "generator_sha256": sha256_file(os.path.join(REPO_ROOT, GENERATOR_PATH)),
            "reference_scope": "one compiler identity x two hosted ABIs",
            "case_count": len(CASES),
            "abi_count": len(ABIS),
            "optimization_count": len(OPTS),
            "observation_count": len(observations),
            "compiler_identity_count": 1,
            "unique_compiler_version_count": 1,
            "pass_count": len(observations) - len(failures),
            "fail_count": len(failures),
            "assembly_normalization": (
                "replace ephemeral multilib-root prefix with ${MULTILIB_ROOT}; "
                "strip trailing horizontal whitespace"
            ),
            "sources": source_records,
            "non_claims": [
                "not_a_compiler_version_matrix",
                "not_a_freestanding_kernel_abi_run",
                "not_proof_that_o1_is_minimal_or_necessary",
                "not_proof_of_a_gcc_bug",
                "not_a_reproduction_of_unobserved_historical_symptoms",
                "not_a_complete_archive_of_every_host_build_input",
            ],
        }
        write_json(os.path.join(temporary, "MANIFEST.json"), manifest)
        shutil.rmtree(multilib_root)
        write_checksums(temporary)
        if os.path.exists(output_dir):
            if not replace:
                raise RuntimeError(f"output appeared during generation; refusing overwrite: {output_dir}")
            backup = output_dir + ".previous"
            if os.path.exists(backup):
                shutil.rmtree(backup)
            os.replace(output_dir, backup)
            try:
                os.replace(temporary, output_dir)
            except Exception:
                os.replace(backup, output_dir)
                raise
            shutil.rmtree(backup)
        else:
            os.replace(temporary, output_dir)
        temporary = None
    finally:
        if temporary and os.path.isdir(temporary):
            shutil.rmtree(temporary)
    print(f"compiler-case dataset written to {output_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default="/usr/bin/gcc-13")
    parser.add_argument("--multilib-packages", required=True)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        build_dataset(
            args.output,
            args.compiler,
            os.path.abspath(args.multilib_packages),
            args.publish,
            args.replace,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"build-compiler-case-dataset: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
