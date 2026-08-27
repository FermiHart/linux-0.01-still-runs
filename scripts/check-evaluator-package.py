#!/usr/bin/env python3
"""Independently validate an extracted or archived evaluator package."""

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile


PACKAGE_RE = re.compile(r"^linux-0\.01-still-runs-evaluator-[0-9a-f]{12}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_EVALUATION = (
    "evaluation/README.md",
    "evaluation/CHECKLIST.md",
    "evaluation/CLAIM-EVIDENCE.tsv",
    "evaluation/THIRD-PARTY-NOTICES.md",
    "evaluation/licenses/LGPL-2.1.txt",
    "evaluation/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt",
)
EXPECTED_ARTIFACTS = {
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
}
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_MEMBER_COUNT = 5000
MAX_EXPANDED_BYTES = 1024 * 1024 * 1024


class PackageError(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob(path):
    digest = hashlib.sha1()
    size = os.path.getsize(path)
    digest.update(b"blob " + str(size).encode("ascii") + b"\0")
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(path):
    normalized = os.path.normpath(path)
    return (
        path == normalized
        and not os.path.isabs(path)
        and normalized not in ("", ".", "..")
        and not normalized.startswith("../")
    )


def regular_files(root):
    result = set()
    for directory, dirs, files in os.walk(root):
        dirs.sort()
        for name in dirs:
            path = os.path.join(directory, name)
            if os.path.islink(path) or not os.path.isdir(path):
                raise PackageError(f"unsupported package member: {os.path.relpath(path, root)}")
        for name in files:
            path = os.path.join(directory, name)
            if os.path.islink(path) or not os.path.isfile(path):
                raise PackageError(f"unsupported package member: {os.path.relpath(path, root)}")
            result.add(os.path.relpath(path, root))
    return result


def parse_sha256_manifest(path):
    entries = {}
    with open(path, encoding="ascii") as source:
        for line_number, raw in enumerate(source, 1):
            line = raw.rstrip("\n")
            match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
            if match is None or not safe_relative(match.group(2)):
                raise PackageError(f"invalid checksum line {line_number} in {path}")
            digest, relative = match.groups()
            if relative in entries:
                raise PackageError(f"duplicate checksum path: {relative}")
            entries[relative] = digest
    return entries


def git_tree(entries):
    root = {}
    for relative, (mode, object_id) in entries.items():
        node = root
        parts = relative.split("/")
        for part in parts[:-1]:
            existing = node.setdefault(part, {})
            if not isinstance(existing, dict):
                raise PackageError(f"source path conflicts with a file: {relative}")
            node = existing
        if parts[-1] in node:
            raise PackageError(f"duplicate source tree entry: {relative}")
        node[parts[-1]] = (mode, object_id)

    def encode(node):
        body = bytearray()
        ordered = sorted(
            node.items(),
            key=lambda item: item[0].encode("utf-8") + (b"/" if isinstance(item[1], dict) else b"\0"),
        )
        for name, value in ordered:
            if isinstance(value, dict):
                mode = "40000"
                object_id = encode(value)
            else:
                mode, object_id = value
            body.extend(mode.encode("ascii"))
            body.extend(b" ")
            body.extend(name.encode("utf-8"))
            body.extend(b"\0")
            body.extend(bytes.fromhex(object_id))
        header = b"tree " + str(len(body)).encode("ascii") + b"\0"
        return hashlib.sha1(header + body).hexdigest()

    return encode(root)


def verify_package_manifest(package):
    manifest = os.path.join(package, "SHA256SUMS")
    entries = parse_sha256_manifest(manifest)
    actual = regular_files(package) - {"SHA256SUMS"}
    if set(entries) != actual:
        missing = sorted(actual - set(entries))
        extra = sorted(set(entries) - actual)
        raise PackageError(f"package manifest inventory mismatch: unchecked={missing}, absent={extra}")
    for relative, expected in entries.items():
        if sha256(os.path.join(package, relative)) != expected:
            raise PackageError(f"package checksum mismatch: {relative}")


def verify_source(package, identity):
    manifest_path = os.path.join(package, "SOURCE-MANIFEST.tsv")
    entries = {}
    with open(manifest_path, encoding="utf-8") as source:
        for line_number, raw in enumerate(source, 1):
            fields = raw.rstrip("\n").split("\t")
            if (
                len(fields) != 3
                or fields[0] not in ("100644", "100755")
                or not HEX40_RE.fullmatch(fields[1])
                or not safe_relative(fields[2])
            ):
                raise PackageError(f"invalid source manifest line {line_number}")
            mode, object_id, relative = fields
            if relative in entries:
                raise PackageError(f"duplicate source path: {relative}")
            entries[relative] = (mode, object_id)
    source_root = os.path.join(package, "source")
    actual = regular_files(source_root)
    if set(entries) != actual:
        raise PackageError("source manifest inventory does not match exported source")
    if len(entries) != identity["source_file_count"]:
        raise PackageError("source file count does not match artifact identity")
    for relative, (mode, object_id) in entries.items():
        path = os.path.join(source_root, relative)
        if git_blob(path) != object_id:
            raise PackageError(f"source Git object mismatch: {relative}")
        expected_mode = 0o755 if mode == "100755" else 0o644
        if os.stat(path).st_mode & 0o777 != expected_mode:
            raise PackageError(f"source mode mismatch: {relative}")
    if git_tree(entries) != identity["source_tree"]:
        raise PackageError("source manifest does not reconstruct the declared Git tree")
    return entries


def verify_artifacts(package, identity):
    relative_manifest = identity["build_manifest"]
    if relative_manifest != "artifacts/SHA256SUMS":
        raise PackageError("unsupported build manifest location")
    artifact_root = os.path.join(package, "artifacts")
    entries = parse_sha256_manifest(os.path.join(package, relative_manifest))
    actual = regular_files(artifact_root) - {"SHA256SUMS", "REPRODUCIBLE.sha256"}
    if set(entries) != actual or actual != EXPECTED_ARTIFACTS:
        raise PackageError("build manifest inventory does not match packaged artifacts")
    for relative, expected in entries.items():
        if sha256(os.path.join(artifact_root, relative)) != expected:
            raise PackageError(f"build artifact checksum mismatch: {relative}")
    reproducible = os.path.join(artifact_root, "REPRODUCIBLE.sha256")
    if not os.path.isfile(reproducible):
        raise PackageError("reproducible build manifest is missing")
    if sha256(reproducible) != sha256(os.path.join(artifact_root, "SHA256SUMS")):
        raise PackageError("reproducible and build manifests differ")


def verify_modes(package, source_entries, check_directories=True):
    expected_executables = {
        os.path.join("source", relative)
        for relative, (mode, _) in source_entries.items()
        if mode == "100755"
    }
    expected_executables.update(
        {
            "artifacts/bemu-linux01",
            "artifacts/mkimage",
            "artifacts/minix-inspect",
        }
    )
    for directory, dirs, files in os.walk(package):
        for name in dirs:
            path = os.path.join(directory, name)
            actual = os.stat(path).st_mode & 0o777
            if check_directories and actual != 0o755:
                raise PackageError(
                    f"package directory mode mismatch: {os.path.relpath(path, package)} "
                    f"(expected 0755, got {actual:04o})"
                )
        for name in files:
            path = os.path.join(directory, name)
            relative = os.path.relpath(path, package)
            expected = 0o755 if relative in expected_executables else 0o644
            actual = os.stat(path).st_mode & 0o777
            if actual != expected:
                raise PackageError(
                    f"package file mode mismatch: {relative} "
                    f"(expected {expected:04o}, got {actual:04o})"
                )


def verify_identity(package):
    with open(os.path.join(package, "ARTIFACT-IDENTITY.json"), encoding="utf-8") as source:
        identity = json.load(source)
    required = {
        "format",
        "source_commit",
        "source_tree",
        "source_date_epoch",
        "source_file_count",
        "build_manifest",
        "package_manifest",
        "history_bundle",
    }
    if not required <= set(identity):
        raise PackageError(f"artifact identity lacks fields: {sorted(required - set(identity))}")
    if identity["format"] != "vesica-piscis-evaluator-v1":
        raise PackageError("unsupported evaluator package format")
    if not HEX40_RE.fullmatch(identity["source_commit"]):
        raise PackageError("invalid source commit identity")
    if not HEX40_RE.fullmatch(identity["source_tree"]):
        raise PackageError("invalid source tree identity")
    if not isinstance(identity["source_date_epoch"], int) or identity["source_date_epoch"] < 0:
        raise PackageError("invalid SOURCE_DATE_EPOCH identity")
    if not isinstance(identity["source_file_count"], int) or identity["source_file_count"] < 1:
        raise PackageError("invalid source file count")
    if identity["package_manifest"] != "SHA256SUMS":
        raise PackageError("unsupported package manifest location")
    expected_suffix = identity["source_commit"][:12]
    if os.path.basename(package) != f"linux-0.01-still-runs-evaluator-{expected_suffix}":
        raise PackageError("package directory is not named for its fixed commit")
    return identity


def verify_history_bundle(package, identity):
    relative = identity["history_bundle"]
    if relative != "repository.bundle":
        raise PackageError("unsupported history bundle location")
    bundle = os.path.join(package, relative)
    heads = subprocess.run(
        ["git", "bundle", "list-heads", bundle],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    expected = f"{identity['source_commit']} HEAD"
    if heads.returncode != 0 or expected not in heads.stdout.splitlines():
        raise PackageError("history bundle does not expose the fixed commit as HEAD")
    with tempfile.TemporaryDirectory(prefix="evaluator-bundle-check-") as temporary:
        repository = os.path.join(temporary, "repository.git")
        initialized = subprocess.run(
            ["git", "init", "--bare", "--quiet", repository],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        verified = subprocess.run(
            ["git", "-C", repository, "bundle", "verify", bundle],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if initialized.returncode != 0 or verified.returncode != 0:
            raise PackageError("history bundle pack or prerequisite verification failed")
        unbundled = subprocess.run(
            ["git", "-C", repository, "bundle", "unbundle", bundle],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        commit_tree = subprocess.run(
            ["git", "-C", repository, "rev-parse", f"{identity['source_commit']}^{{tree}}"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        connected = subprocess.run(
            ["git", "-C", repository, "fsck", "--full", "--strict", "--no-dangling", identity["source_commit"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if (
            unbundled.returncode != 0
            or commit_tree.returncode != 0
            or commit_tree.stdout.strip() != identity["source_tree"]
            or connected.returncode != 0
        ):
            raise PackageError("history bundle does not bind a complete commit to the source tree")


def verify_directory(package, check_directory_modes=True):
    package = os.path.abspath(package)
    if not os.path.isdir(package) or not PACKAGE_RE.fullmatch(os.path.basename(package)):
        raise PackageError("directory is not a versioned evaluator package")
    for relative in (
        "ARTIFACT-IDENTITY.json",
        "SOURCE-MANIFEST.tsv",
        "SHA256SUMS",
    ) + REQUIRED_EVALUATION:
        if not os.path.isfile(os.path.join(package, relative)):
            raise PackageError(f"required package file is missing: {relative}")
    identity = verify_identity(package)
    verify_package_manifest(package)
    source_entries = verify_source(package, identity)
    verify_artifacts(package, identity)
    verify_history_bundle(package, identity)
    verify_modes(package, source_entries, check_directory_modes)
    return identity


def verify_sidecar(archive):
    sidecar = archive + ".sha256"
    if not os.path.isfile(sidecar):
        raise PackageError(f"detached archive checksum is missing: {sidecar}")
    entries = parse_sha256_manifest(sidecar)
    archive_name = os.path.basename(archive)
    package_name = archive_name.removesuffix(".tar.gz")
    expected = {archive_name, package_name + ".check.py"}
    if set(entries) != expected:
        raise PackageError("detached checksum must cover the archive and independent checker")
    for relative, digest in entries.items():
        path = os.path.join(os.path.dirname(archive), relative)
        if not os.path.isfile(path) or sha256(path) != digest:
            raise PackageError(f"detached checksum mismatch: {relative}")


def verify_ustar_headers(archive):
    member_count = 0
    expanded_bytes = 0
    zero_blocks = 0
    with gzip.open(archive, "rb") as source:
        while True:
            header = source.read(512)
            if len(header) != 512:
                raise PackageError("truncated tar header")
            if header == b"\0" * 512:
                zero_blocks += 1
                if zero_blocks < 2:
                    continue
                while True:
                    trailing = source.read(1024 * 1024)
                    if not trailing:
                        return
                    expanded_bytes += len(trailing)
                    if expanded_bytes > MAX_EXPANDED_BYTES or trailing.strip(b"\0"):
                        raise PackageError("archive has excessive or nonzero trailing tar data")
            if zero_blocks:
                raise PackageError("archive has a nonzero header after tar end markers")
            member_count += 1
            if member_count > MAX_MEMBER_COUNT:
                raise PackageError("archive has too many members")
            if header[257:263] != b"ustar\0" or header[263:265] != b"00":
                raise PackageError("archive member is not encoded as POSIX ustar")
            if header[265:297].strip(b"\0") or header[297:329].strip(b"\0"):
                raise PackageError("ustar user/group names are not normalized away")
            try:
                size = int(header[124:136].rstrip(b"\0 ") or b"0", 8)
            except ValueError as error:
                raise PackageError("invalid ustar member size") from error
            expanded_bytes += 512 + ((size + 511) // 512) * 512
            if expanded_bytes > MAX_EXPANDED_BYTES:
                raise PackageError("archive expanded size exceeds the package limit")
            blocks = (size + 511) // 512
            remaining = blocks * 512
            while remaining:
                payload = source.read(min(1024 * 1024, remaining))
                if not payload:
                    raise PackageError("truncated tar member payload")
                remaining -= len(payload)


def verify_archive(archive):
    archive = os.path.abspath(archive)
    if os.path.getsize(archive) > MAX_ARCHIVE_BYTES:
        raise PackageError("archive exceeds the evaluator-package size limit")
    verify_sidecar(archive)
    with open(archive, "rb") as source:
        gzip_header = source.read(10)
    if (
        len(gzip_header) != 10
        or gzip_header[:4] != b"\x1f\x8b\x08\x00"
        or gzip_header[4:8] != b"\x00\x00\x00\x00"
    ):
        raise PackageError("gzip header retains optional fields or a timestamp")
    verify_ustar_headers(archive)
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if not members:
            raise PackageError("archive is empty")
        if len(members) > MAX_MEMBER_COUNT:
            raise PackageError("archive has too many members")
        if sum(member.size for member in members) > MAX_EXPANDED_BYTES:
            raise PackageError("archive expanded size exceeds the package limit")
        names = [member.name for member in members]
        if names != sorted(names, key=lambda name: name.encode("utf-8")):
            raise PackageError("archive members are not in lexical byte order")
        roots = {member.name.split("/", 1)[0] for member in members}
        if len(roots) != 1 or not PACKAGE_RE.fullmatch(next(iter(roots))):
            raise PackageError("archive must contain one versioned top-level directory")
        seen = set()
        for member in members:
            if member.name in seen:
                raise PackageError(f"duplicate archive member: {member.name}")
            seen.add(member.name)
            if member.pax_headers:
                raise PackageError(f"archive member uses non-ustar extension metadata: {member.name}")
            if not safe_relative(member.name) or not (member.isdir() or member.isfile()):
                raise PackageError(f"unsafe archive member: {member.name}")
            if member.uid != 0 or member.gid != 0:
                raise PackageError(f"archive ownership is not normalized: {member.name}")
            expected_mode = 0o755 if member.isdir() or member.mode & 0o111 else 0o644
            if member.mode & 0o777 != expected_mode:
                raise PackageError(f"archive mode is not normalized: {member.name}")
        with tempfile.TemporaryDirectory(prefix="evaluator-package-check-") as temporary:
            source.extractall(temporary, filter="data")
            package = os.path.join(temporary, next(iter(roots)))
            # The safe extraction filter discards directory modes. Archive
            # directory modes were already validated from tar metadata above.
            identity = verify_directory(package, check_directory_modes=False)
            for member in members:
                if member.mtime != identity["source_date_epoch"]:
                    raise PackageError(f"archive timestamp is not normalized: {member.name}")
    return identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--archive", help="tar.gz evaluator package to validate")
    group.add_argument("--directory", help="extracted evaluator package to validate")
    arguments = parser.parse_args()
    try:
        identity = (
            verify_archive(arguments.archive)
            if arguments.archive
            else verify_directory(arguments.directory)
        )
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError, PackageError) as error:
        print(f"evaluator package verification failed: {error}", file=sys.stderr)
        return 1
    print(
        "evaluator package verified: "
        f"commit={identity['source_commit']} tree={identity['source_tree']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
