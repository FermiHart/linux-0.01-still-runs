#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Check authorship headers and provenance coverage for every public path."""

import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM_ARCHIVE = os.path.join(REPO_ROOT, "upstream", "linux-0.01.tar.gz")
UPSTREAM_SHA256 = "24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d"
MANIFEST_PATH = os.path.join(REPO_ROOT, "docs", "AUTHORSHIP-MAP.tsv")
IDENTITY_PATTERN = (
    r"F E R M I\s+(?:INFINITY|∞)\s+H A R T\s+<contact@fermihart\.com>"
)
IDENTITY_RE = re.compile(IDENTITY_PATTERN)
AUTHOR_RE = re.compile(
    rf"(?m)^[ \t]*(?:[/#;*]+[ \t]*)?Author[ \t]*:[ \t]*{IDENTITY_PATTERN}"
    r"[ \t]*(?:\*/)?[ \t]*$"
)
MAINTAINER_RE = re.compile(
    rf"(?m)^[ \t]*(?:[/#;*]+[ \t]*)?Maintainer and adaptation:[ \t]+"
    rf"{IDENTITY_PATTERN}[ \t]*(?:\*/)?[ \t]*$"
)
SPDX_RE = re.compile(
    r"(?m)^[ \t]*(?:(?:[/#;*]+[ \t]*)?SPDX-License-Identifier:[^\r\n]*"
    r"|<!--[ \t]*SPDX-License-Identifier:[^\r\n>]*-->)[ \t]*$"
)
SOURCE_SUFFIXES = (".c", ".h", ".S", ".s", ".asm", ".py", ".sh", ".ld", ".yml", ".yaml")
SOURCE_BASENAMES = {".gdbinit", "Dockerfile", "Makefile"}
THIRD_PARTY = {
    "evaluation/v1/licenses/GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt",
    "evaluation/v1/licenses/LGPL-2.1.txt",
    "kernel/vga_font8x8.h",
}
GENERATED_PATHS = {
    "upstream/SHA256SUMS",
    "upstream/linux-0.01.tar.gz",
}
HISTORICAL_DERIVED = {
    "tests/compiler-cases/bitmap_inline_asm.c",
    "tests/compiler-cases/buffer_freelist.c",
    "tests/compiler-cases/vsprintf_percent_s.c",
}
IDENTITY_PINNED_SOURCE = HISTORICAL_DERIVED | {
    "scripts/build-compiler-case-dataset.py",
    "scripts/build-patch-dataset.py",
}
MIXED_CONTENT_SOURCE = {
    "Makefile",
    "tools/mkimage.c",
    "userland/shell.c",
}
MIXED_CONTENT_DOCUMENTS = {"README.md"}
LEGAL_AGGREGATIONS = {"LICENSE"}
BEMU_PARTIAL_PATHS = {
    f"bemu/{name}" for name in """
    bemu_linux01.c cli.c cli.h console.c console.h error.h experience.h ide.c
    ide.h irq.c irq.h kernel_image.h keyboard.c keyboard.h kvm.c kvm.h loader.c
    loader.h machine.c machine.h memory.c memory.h pic.c pic.h pit.c pit.h rtc.c
    rtc.h trace.c trace.h trace_clock.c trace_clock.h uart.c uart.h
    """.split()
}
BBP_BSD_PATHS = {
    f"bbp/{name}" for name in """
    bbp_build.c bbp_build.h bbp_kernel.c bbp_kernel.h compat/stddef.h
    compat/stdint.h include/bbp/bbp.h include/bbp/bbp_crc64.h linux01_bbp.c
    linux01_bbp.h linux01_handoff.h
    """.split()
}
ALLOWED_CATEGORIES = {
    "bemu-partial-provenance",
    "generated-or-dataset",
    "identity-pinned-source",
    "legal-aggregation",
    "linux-0.01-historical",
    "modern-mixed-content",
    "modern-mixed-document",
    "modern-project",
    "third-party",
}


def tracked_paths():
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
    )
    return sorted(path for path in output.decode().split("\0") if path)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upstream_paths():
    verify_sha256(UPSTREAM_ARCHIVE, UPSTREAM_SHA256)
    with tarfile.open(UPSTREAM_ARCHIVE, "r:gz") as archive:
        paths = set()
        for member in archive.getmembers():
            if not member.isfile() or "/" not in member.name:
                continue
            paths.add(member.name.split("/", 1)[1])
        return paths


def category(path, upstream, declared_category=None):
    del path, upstream
    if declared_category in ALLOWED_CATEGORIES:
        return declared_category
    return None


def required_category(path, upstream):
    if path in THIRD_PARTY:
        return "third-party"
    if path in GENERATED_PATHS:
        return "generated-or-dataset"
    if path in IDENTITY_PINNED_SOURCE:
        return "identity-pinned-source"
    if path in MIXED_CONTENT_SOURCE:
        return "modern-mixed-content"
    if path in MIXED_CONTENT_DOCUMENTS:
        return "modern-mixed-document"
    if path in LEGAL_AGGREGATIONS:
        return "legal-aggregation"
    if path in BEMU_PARTIAL_PATHS:
        return "bemu-partial-provenance"
    if path in BBP_BSD_PATHS:
        return "modern-project"
    if path in upstream and path != "Makefile":
        return "linux-0.01-historical"
    return None


def check_path_invariants(path, path_category, license_status, upstream, errors):
    required = required_category(path, upstream)
    if required is not None and path_category != required:
        errors.append(
            f"{path}: category {path_category!r} violates required category {required!r}"
        )
    if path in BBP_BSD_PATHS and license_status != "BSD-3-Clause":
        errors.append(f"{path}: known BBP path must retain BSD-3-Clause")


def source_like(path):
    return path.endswith(SOURCE_SUFFIXES) or os.path.basename(path) in SOURCE_BASENAMES


def read_content(path):
    full_path = os.path.join(REPO_ROOT, path)
    try:
        with open(full_path, encoding="utf-8", errors="replace") as source:
            return source.read()
    except (OSError, UnicodeError):
        return ""


def verify_sha256(path, expected):
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{path} hash is {actual}, expected {expected}")


def spdx_identifiers(content):
    identifiers = []
    for match in SPDX_RE.finditer(content):
        declaration = match.group(0).split("SPDX-License-Identifier:", 1)[1]
        declaration = re.sub(r"(?:\*/|-->)[ \t]*$", "", declaration).strip()
        identifiers.append(declaration)
    return identifiers


def check_header_text(path, path_category, content, errors, license_status=None):
    identifiers = spdx_identifiers(content)
    if path_category == "third-party":
        if IDENTITY_RE.search(content):
            errors.append(f"{path}: protected material falsely claims project authorship")
        if identifiers and identifiers != [license_status]:
            errors.append(f"{path}: third-party SPDX declaration does not match the manifest")
        return
    if path_category in {"generated-or-dataset", "identity-pinned-source"}:
        if IDENTITY_RE.search(content):
            errors.append(f"{path}: protected material falsely claims project authorship")
        if identifiers:
            errors.append(f"{path}: protected material falsely claims a project license")
        return
    if path_category == "linux-0.01-historical":
        if IDENTITY_RE.search(content):
            errors.append(f"{path}: historical source falsely claims project authorship")
        if identifiers:
            errors.append(f"{path}: historical source falsely claims a modern project license")
        return
    if path_category == "modern-mixed-content":
        if not AUTHOR_RE.search(content):
            errors.append(f"{path}: mixed source lacks the canonical implementation author")
        if "Mixed-content rights: see LICENSE and evaluation/v1/THIRD-PARTY-NOTICES.md" not in content:
            errors.append(f"{path}: missing the mixed-content rights pointer")
        if identifiers:
            errors.append(f"{path}: mixed source must not claim a blanket SPDX license")
        return
    if path_category in {"modern-mixed-document", "legal-aggregation"}:
        if identifiers:
            errors.append(f"{path}: mixed/legal document must not claim a blanket SPDX license")
        return
    if not source_like(path):
        return
    if path_category == "modern-project":
        expected_license = license_status or (
            "BSD-3-Clause" if path in BBP_BSD_PATHS else "Unlicense"
        )
        if not AUTHOR_RE.search(content):
            errors.append(f"{path}: modern source lacks the canonical Author identity")
        if identifiers != [expected_license]:
            errors.append(
                f"{path}: expected exactly SPDX-License-Identifier: {expected_license}"
            )
    elif path_category == "bemu-partial-provenance":
        if not MAINTAINER_RE.search(content):
            errors.append(f"{path}: bEMU source lacks the canonical maintainer/adaptation identity")
        if "bEMU-NANO provenance: see bemu/README.md" not in content:
            errors.append(f"{path}: missing the bEMU-NANO provenance pointer")
        if path == "bemu/bemu_linux01.c":
            if identifiers != ["BSD-3-Clause"]:
                errors.append(f"{path}: runner lost its existing BSD-3-Clause declaration")
        elif identifiers:
            errors.append(f"{path}: partial-provenance module must not infer a blanket SPDX license")


def check_header(path, path_category, errors, license_status=None):
    check_header_text(path, path_category, read_content(path), errors, license_status)


def attribution_for(path, path_category):
    if path_category == "linux-0.01-historical":
        return "Linux 0.01 historical source; see file-level authors and LICENSE"
    if path_category == "third-party":
        if path == "kernel/vga_font8x8.h":
            return "Joseph Gil / SeaBIOS provenance"
        if path in THIRD_PARTY:
            return "Free Software Foundation"
        return "Third-party; see file-level provenance"
    if path_category == "generated-or-dataset":
        return "NOASSERTION; see dataset or generator provenance"
    if path_category == "bemu-partial-provenance":
        return "F E R M I INFINITY H A R T; adaptation and maintenance"
    if path_category == "modern-mixed-content":
        return "F E R M I INFINITY H A R T; original implementation only"
    if path_category == "modern-mixed-document":
        return "F E R M I INFINITY H A R T; original text only"
    if path_category == "legal-aggregation":
        return "Multiple named licensors and provenance statements"
    if path_category == "identity-pinned-source":
        if path.startswith("tests/compiler-cases/"):
            return "F E R M I INFINITY H A R T; reduction derived from Linux 0.01"
        return "F E R M I INFINITY H A R T; see pinned dataset identity"
    return "F E R M I INFINITY H A R T"


def license_for(path, path_category, declared_license=None):
    if path in BBP_BSD_PATHS:
        return "BSD-3-Clause"
    if path_category == "linux-0.01-historical":
        return "LicenseRef-Linux-0.01"
    if path_category == "third-party":
        if path == "kernel/vga_font8x8.h":
            return "public-domain provenance statement"
        if path.endswith("LGPL-2.1.txt"):
            return "LGPL-2.1-or-later license text"
        if path.endswith("GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt"):
            return "GCC Runtime Library Exception 3.1 license text"
        return declared_license or "third-party; see file-level provenance"
    if path_category == "bemu-partial-provenance":
        return "BSD-3-Clause" if path == "bemu/bemu_linux01.c" else "NOASSERTION; see bemu/README.md"
    if path_category == "modern-mixed-content":
        return "mixed; see LICENSE and THIRD-PARTY-NOTICES.md"
    if path_category == "modern-mixed-document":
        return "mixed quotations; see THIRD-PARTY-NOTICES.md"
    if path_category == "legal-aggregation":
        return "aggregated terms; not a blanket license"
    if path_category in {"generated-or-dataset", "identity-pinned-source"}:
        return "see pinned manifest and notices"
    return declared_license or "Unlicense"


def expected_manifest(paths, upstream, declared_rows=None):
    declared_rows = declared_rows or {}
    rows = {}
    for path in paths:
        declared = declared_rows.get(path)
        declared_category = declared[0] if declared else None
        declared_license = declared[2] if declared else None
        path_category = category(path, upstream, declared_category)
        if path_category is None:
            continue
        rows[path] = (
            path_category,
            attribution_for(path, path_category),
            license_for(path, path_category, declared_license),
        )
    return rows


def load_manifest(errors):
    rows = {}
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as source:
            header = source.readline().rstrip("\n").split("\t")
            if header != ["path", "category", "attribution", "license_status"]:
                errors.append("docs/AUTHORSHIP-MAP.tsv: invalid header")
                return rows
            for line_number, line in enumerate(source, 2):
                fields = line.rstrip("\n").split("\t")
                if len(fields) != 4:
                    errors.append(f"docs/AUTHORSHIP-MAP.tsv:{line_number}: expected four fields")
                    continue
                path, *values = fields
                if path in rows:
                    errors.append(f"docs/AUTHORSHIP-MAP.tsv:{line_number}: duplicate {path}")
                rows[path] = tuple(values)
    except OSError as exc:
        errors.append(f"docs/AUTHORSHIP-MAP.tsv: {exc}")
    return rows


def check_manifest_paths(paths, actual, errors):
    missing = sorted(set(paths) - set(actual))
    extra = sorted(set(actual) - set(paths))
    if missing:
        errors.append(f"docs/AUTHORSHIP-MAP.tsv: missing paths {missing}")
    if extra:
        errors.append(f"docs/AUTHORSHIP-MAP.tsv: unknown paths {extra}")


def compare_manifest_rows(expected, actual, errors):
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        errors.append(f"docs/AUTHORSHIP-MAP.tsv: missing paths {missing}")
    if extra:
        errors.append(f"docs/AUTHORSHIP-MAP.tsv: unknown paths {extra}")
    for path in sorted(set(expected) & set(actual)):
        if actual[path] != expected[path]:
            errors.append(
                f"docs/AUTHORSHIP-MAP.tsv: {path} is {actual[path]!r}, expected {expected[path]!r}"
            )


def check_pinned_source_hashes(errors, repo_root=REPO_ROOT):
    manifests = (
        os.path.join(repo_root, "datasets", "patches", "MANIFEST.json"),
        os.path.join(repo_root, "datasets", "compiler-cases", "v1", "MANIFEST.json"),
    )
    declared_paths = set()
    for manifest_path in manifests:
        with open(manifest_path, encoding="utf-8") as source:
            manifest = json.load(source)
        generator = manifest["generator_path"]
        declared_paths.add(generator)
        check_declared_sha256(
            os.path.join(repo_root, generator), manifest["generator_sha256"],
            errors, f"{generator}: bytes differ from the published generator identity",
        )
        for record in manifest.get("sources", []):
            path = record["repository_path"]
            declared_paths.add(path)
            check_declared_sha256(
                os.path.join(repo_root, path), record["sha256"],
                errors, f"{path}: bytes differ from the published source identity",
            )
    if declared_paths != IDENTITY_PINNED_SOURCE:
        missing = sorted(IDENTITY_PINNED_SOURCE - declared_paths)
        extra = sorted(declared_paths - IDENTITY_PINNED_SOURCE)
        errors.append(
            "published identity paths do not match the protected set: "
            f"missing={missing}, extra={extra}"
        )


def check_declared_sha256(path, expected, errors, message):
    try:
        verify_sha256(path, expected)
    except (OSError, ValueError):
        errors.append(message)


def check_documents(errors):
    required = {
        "AUTHORS.md": "F E R M I ∞ H A R T <contact@fermihart.com>",
        "docs/AUTHORSHIP.md": "Files are not attributed by directory inference",
        "README.md": "Authorship and provenance",
        "LICENSE": "Modern project attribution",
    }
    for path, marker in required.items():
        full_path = os.path.join(REPO_ROOT, path)
        try:
            with open(full_path, encoding="utf-8") as source:
                content = source.read()
        except OSError:
            errors.append(f"{path}: missing")
            continue
        if marker not in content:
            errors.append(f"{path}: missing required marker {marker!r}")


def main():
    errors = []
    counts = collections.Counter()
    try:
        upstream = upstream_paths()
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(f"FAIL: upstream provenance cannot be trusted: {exc}", file=sys.stderr)
        return 1
    paths = tracked_paths()
    actual = load_manifest(errors)
    check_manifest_paths(paths, actual, errors)
    expected = expected_manifest(paths, upstream, actual)
    if "--emit-manifest" in sys.argv[1:]:
        print("path\tcategory\tattribution\tlicense_status")
        for path in sorted(expected):
            print(path, *expected[path], sep="\t")
        return 0
    compare_manifest_rows(expected, actual, errors)
    check_pinned_source_hashes(errors)
    for path in paths:
        declared = actual.get(path)
        declared_category = declared[0] if declared else None
        path_category = category(path, upstream, declared_category)
        if path_category is None:
            errors.append(f"{path}: no authorship/provenance category")
            continue
        license_status = declared[2] if declared else None
        check_path_invariants(path, path_category, license_status, upstream, errors)
        counts[path_category] += 1
        check_header(path, path_category, errors, license_status)
    check_documents(errors)

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        print(f"authorship coverage failed with {len(errors)} error(s)", file=sys.stderr)
        return 1

    summary = ", ".join(f"{name}={counts[name]}" for name in sorted(counts))
    print(f"authorship coverage passed: {len(paths)} paths ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
