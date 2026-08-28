#!/usr/bin/env python3
"""Validate the Wave 113 evaluator-package contract and verifier."""

import hashlib
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALUATION_FILES = (
    "evaluation/v1/README.md",
    "evaluation/v1/CHECKLIST.md",
    "evaluation/v1/CLAIM-EVIDENCE.tsv",
    "evaluation/v1/THIRD-PARTY-NOTICES.md",
    "evaluation/v1/licenses/LGPL-2.1.txt",
    "evaluation/v1/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt",
)
TOOLS = (
    "scripts/check-evaluator-package.py",
    "scripts/capture-evaluator-environment.sh",
    "scripts/verify-artifact-reproducibility.sh",
)
LICENSE_HASHES = {
    "evaluation/v1/licenses/LGPL-2.1.txt":
        "dc626520dcd53a22f727af3ee42c770e56c97a64fe3adb063799d8ab032fe551",
    "evaluation/v1/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt":
        "28e85c5aa4af9b4f1dfe6b4817aa3eefb3eaaee7fd735045016f29ccf50276a1",
}
ARTIFACT_NAMES = (
    "kernel.elf",
    "kernel.bin",
    "root.img",
    "root-1991.img",
    "bemu-linux01",
    "mkimage",
    "minix-inspect",
    "shell.bin",
    "update.bin",
    "hello.bin",
    "yes.bin",
    "pathcheck.bin",
    "cat.bin",
)


def fail(message):
    raise AssertionError(message)


def read(path):
    with open(os.path.join(REPO_ROOT, path), encoding="utf-8") as source:
        return source.read()


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob(path):
    with open(path, "rb") as source:
        data = source.read()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as destination:
        destination.write(data)
    os.chmod(path, 0o644)


def manifest_lines(root, excluded):
    paths = []
    for directory, _, files in os.walk(root):
        for name in files:
            relative = os.path.relpath(os.path.join(directory, name), root)
            if relative not in excluded:
                paths.append(relative)
    return "".join(f"{sha256(os.path.join(root, path))}  {path}\n" for path in sorted(paths))


def build_archive(package, checker):
    archive = package + ".tar.gz"
    detached_checker = package + ".check.py"
    shutil.copyfile(checker, detached_checker)

    def normalize(member):
        member.uid = 0
        member.gid = 0
        member.uname = ""
        member.gname = ""
        member.mtime = 1700000000
        member.mode = 0o755 if member.isdir() or member.mode & 0o111 else 0o644
        return member

    with open(archive, "wb") as destination:
        with gzip.GzipFile(
            filename="", mode="wb", compresslevel=9, mtime=0, fileobj=destination
        ) as compressed:
            with tarfile.open(
                fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT
            ) as output:
                output.add(package, arcname=os.path.basename(package), filter=normalize)
    write(
        archive + ".sha256",
        f"{sha256(archive)}  {os.path.basename(archive)}\n"
        f"{sha256(detached_checker)}  {os.path.basename(detached_checker)}\n",
    )
    return archive


def verifier_fixture(root):
    repository = os.path.join(root, "repository")
    subprocess.run(["git", "init", "--quiet", repository], check=True)
    repository_readme = os.path.join(repository, "README.md")
    write(repository_readme, "fixed source\n")
    os.chmod(repository_readme, 0o644)
    subprocess.run(["git", "-C", repository, "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            repository,
            "-c",
            "user.name=Evaluator Fixture",
            "-c",
            "user.email=fixture.invalid",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
        check=True,
    )
    commit = subprocess.check_output(
        ["git", "-C", repository, "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", repository, "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    package = os.path.join(root, f"linux-0.01-still-runs-evaluator-{commit[:12]}")
    source_path = os.path.join(package, "source", "README.md")
    write(source_path, "fixed source\n")
    os.chmod(source_path, 0o644)
    for name in ARTIFACT_NAMES:
        write(os.path.join(package, "artifacts", name), f"fixed {name}\n")
    for relative in EVALUATION_FILES:
        packaged = relative.replace("evaluation/v1/", "evaluation/", 1)
        write(os.path.join(package, packaged), f"fixture for {relative}\n")
    subprocess.run(
        [
            "git",
            "-C",
            repository,
            "-c",
            "pack.threads=1",
            "bundle",
            "create",
            os.path.join(package, "repository.bundle"),
            "HEAD",
        ],
        check=True,
    )
    write(
        os.path.join(package, "SOURCE-MANIFEST.tsv"),
        f"100644\t{git_blob(source_path)}\tREADME.md\n",
    )
    artifact_manifest = "".join(
        f"{sha256(os.path.join(package, 'artifacts', name))}  {name}\n"
        for name in ARTIFACT_NAMES
    )
    write(os.path.join(package, "artifacts", "SHA256SUMS"), artifact_manifest)
    write(os.path.join(package, "artifacts", "REPRODUCIBLE.sha256"), artifact_manifest)
    identity = {
        "format": "vesica-piscis-evaluator-v1",
        "source_commit": commit,
        "source_tree": tree,
        "source_date_epoch": 1700000000,
        "source_file_count": 1,
        "build_manifest": "artifacts/SHA256SUMS",
        "package_manifest": "SHA256SUMS",
        "history_bundle": "repository.bundle",
    }
    write(
        os.path.join(package, "ARTIFACT-IDENTITY.json"),
        json.dumps(identity, sort_keys=True, indent=2) + "\n",
    )
    write(
        os.path.join(package, "SHA256SUMS"),
        manifest_lines(package, {"SHA256SUMS"}),
    )
    os.chmod(package, 0o755)
    for directory, dirs, files in os.walk(package):
        os.chmod(directory, 0o755)
        for name in dirs:
            os.chmod(os.path.join(directory, name), 0o755)
        for name in files:
            os.chmod(os.path.join(directory, name), 0o644)
    for name in ("bemu-linux01", "mkimage", "minix-inspect"):
        os.chmod(os.path.join(package, "artifacts", name), 0o755)
    return package


def main():
    for path in EVALUATION_FILES + TOOLS:
        if not os.path.isfile(os.path.join(REPO_ROOT, path)):
            fail(f"evaluator package component is missing: {path}")
    for path, expected in LICENSE_HASHES.items():
        if sha256(os.path.join(REPO_ROOT, path)) != expected:
            fail(f"canonical license text changed: {path}")

    builder = read("scripts/make-artifact.sh")
    required_builder_anchors = (
        "status --porcelain",
        "--is-shallow-repository",
        "archive --format=tar",
        "ARTIFACT-IDENTITY.json",
        "SOURCE-MANIFEST.tsv",
        "pack.threads=1",
        "make -C",
        "SHA256SUMS",
        "--sort=name",
        "--format=ustar",
        "--mtime",
        "--owner=0",
        "--group=0",
        "--numeric-owner",
        "gzip -n",
        ".tar.gz.sha256",
        ".check.py",
    )
    for anchor in required_builder_anchors:
        if anchor not in builder:
            fail(f"artifact builder lacks evaluator-package control {anchor!r}")
    for output in (
        "kernel.elf",
        "kernel.bin",
        "root.img",
        "root-1991.img",
        "bemu-linux01",
        "mkimage",
        "minix-inspect",
        "shell.bin",
        "update.bin",
        "hello.bin",
        "yes.bin",
        "pathcheck.bin",
        "cat.bin",
    ):
        if output not in builder:
            fail(f"artifact builder omits reproducible output {output!r}")

    makefile = read("Makefile")
    for target in (
        "artifact-check",
        "verify-artifact-reproducible",
        "test-evaluator-package",
    ):
        if not re.search(rf"^{re.escape(target)}\s*:", makefile, re.MULTILINE):
            fail(f"Makefile lacks evaluator-package target {target!r}")
    test_body = re.search(r"^test:.*?(?=^[A-Za-z0-9_.%/-]+\s*:)", makefile, re.MULTILINE | re.DOTALL)
    if test_body is None or "test-evaluator-package" not in test_body.group(0):
        fail("full test aggregate does not run test-evaluator-package")
    workflow = read(".github/workflows/build.yml")
    if "make test-evaluator-package" not in workflow:
        fail("hosted workflow does not run the evaluator-package contract")
    if (
        "SOURCE_DATE_EPOCH=1700000000 make artifact" not in workflow
        or '.check.py" --archive' not in workflow
    ):
        fail("hosted workflow does not construct and independently check the evaluator package")

    claims = read("evaluation/v1/CLAIM-EVIDENCE.tsv")
    if not claims.startswith("claim_id\tbounded_claim\tcommand\tevidence\tnon_claim\n"):
        fail("claim map lacks the versioned five-column header")
    if len([line for line in claims.splitlines()[1:] if line.strip()]) < 5:
        fail("claim map must operationalize at least five bounded claims")

    notices = read("evaluation/v1/THIRD-PARTY-NOTICES.md")
    for boundary in (
        "Linux 0.01",
        "may not distribute this for a fee",
        "SeaBIOS",
        "glibc",
        "GCC Runtime Library Exception",
        "not a blanket license",
        "bEMU-NANO",
    ):
        if boundary not in notices:
            fail(f"third-party notices omit {boundary!r}")

    checklist = read("evaluation/v1/CHECKLIST.md")
    for command in (
        "sha256sum --check",
        "check-evaluator-package.py",
        "capture-evaluator-environment.sh",
        "make doctor",
        "make -j8 ci",
        "make verify-reproducible",
    ):
        if command not in checklist:
            fail(f"evaluator checklist omits command {command!r}")
    for boundary in (
        "independent third-party reproduction has not yet occurred",
        "no DOI or archival deposit exists yet",
        "not machine-state replay",
    ):
        if boundary not in checklist:
            fail(f"evaluator checklist omits non-claim {boundary!r}")

    checker = os.path.join(REPO_ROOT, "scripts", "check-evaluator-package.py")
    with tempfile.TemporaryDirectory(prefix="evaluator-package-test-") as temporary:
        package = verifier_fixture(temporary)
        valid = subprocess.run(
            [sys.executable, checker, "--directory", package],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if valid.returncode != 0:
            fail(f"package verifier rejected a valid fixture: {valid.stderr.strip()}")
        archive = build_archive(package, checker)
        valid_archive = subprocess.run(
            [sys.executable, checker, "--archive", archive],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if valid_archive.returncode != 0:
            fail(
                "package verifier rejected a valid archive: "
                f"{valid_archive.stderr.strip()}"
            )
        with gzip.open(archive, "rb") as source:
            archive_data = source.read()
        with open(archive, "wb") as destination:
            with gzip.GzipFile(
                filename="", mode="wb", compresslevel=9, mtime=0, fileobj=destination
            ) as compressed:
                compressed.write(archive_data + b"nonzero trailing tar data")
        detached_checker = package + ".check.py"
        write(
            archive + ".sha256",
            f"{sha256(archive)}  {os.path.basename(archive)}\n"
            f"{sha256(detached_checker)}  {os.path.basename(detached_checker)}\n",
        )
        trailing_data = subprocess.run(
            [sys.executable, checker, "--archive", archive],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if trailing_data.returncode == 0 or "trailing tar data" not in trailing_data.stderr:
            fail("package verifier accepted nonzero data after the tar end markers")
        readme = os.path.join(package, "evaluation", "README.md")
        os.chmod(readme, 0o755)
        wrong_mode = subprocess.run(
            [sys.executable, checker, "--directory", package],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if wrong_mode.returncode == 0 or "mode mismatch" not in wrong_mode.stderr:
            fail("package verifier accepted an executable evaluator document")
        os.chmod(readme, 0o644)
        write(os.path.join(package, "unchecked.txt"), "not in the package manifest\n")
        invalid = subprocess.run(
            [sys.executable, checker, "--directory", package],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if invalid.returncode == 0 or "inventory" not in invalid.stderr:
            fail("package verifier did not reject an unchecked regular file")
        os.remove(os.path.join(package, "unchecked.txt"))
        os.remove(os.path.join(package, "artifacts", "cat.bin"))
        reduced = [name for name in ARTIFACT_NAMES if name != "cat.bin"]
        reduced_manifest = "".join(
            f"{sha256(os.path.join(package, 'artifacts', name))}  {name}\n"
            for name in reduced
        )
        write(os.path.join(package, "artifacts", "SHA256SUMS"), reduced_manifest)
        write(os.path.join(package, "artifacts", "REPRODUCIBLE.sha256"), reduced_manifest)
        write(os.path.join(package, "SHA256SUMS"), manifest_lines(package, {"SHA256SUMS"}))
        incomplete = subprocess.run(
            [sys.executable, checker, "--directory", package],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if incomplete.returncode == 0 or "build manifest inventory" not in incomplete.stderr:
            fail("package verifier accepted an incomplete selected build-output set")

    print("evaluator package contract, notices, checklist, and verifier are complete")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as error:
        print(f"evaluator package check failed: {error}", file=sys.stderr)
        sys.exit(1)
