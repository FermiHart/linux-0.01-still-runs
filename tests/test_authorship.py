#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Validate public authorship and path-level provenance coverage."""

import os
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO_ROOT, "scripts", "check-authorship.py")
REQUIRED = (
    os.path.join(REPO_ROOT, "AUTHORS.md"),
    os.path.join(REPO_ROOT, "docs", "AUTHORSHIP.md"),
)


def load_checker():
    spec = importlib.util.spec_from_file_location("authorship_checker", CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_policy_rejection(
        checker, path, category, content, marker, license_status=None):
    errors = []
    checker.check_header_text(path, category, content, errors, license_status)
    if not any(marker in error for error in errors):
        raise AssertionError(f"{category} fixture was not rejected: {errors}")


def copy_pinned_fixture(root, checker):
    for relative in checker.IDENTITY_PINNED_SOURCE:
        destination = os.path.join(root, relative)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(os.path.join(REPO_ROOT, relative), destination)
    for relative in (
        "datasets/patches/MANIFEST.json",
        "datasets/compiler-cases/v1/MANIFEST.json",
    ):
        destination = os.path.join(root, relative)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(os.path.join(REPO_ROOT, relative), destination)


def main():
    missing = [os.path.relpath(path, REPO_ROOT) for path in REQUIRED if not os.path.isfile(path)]
    if missing:
        raise AssertionError(f"missing public authorship documents: {missing}")
    if not os.path.isfile(CHECKER):
        raise AssertionError("scripts/check-authorship.py is missing")

    checker = load_checker()
    identity = "F E R M I INFINITY H A R T <contact@fermihart.com>"
    require_policy_rejection(
        checker, "kernel/sched.c", "linux-0.01-historical",
        f"/* Author: {identity}\n * SPDX-License-Identifier: Unlicense\n */\n",
        "historical source falsely claims project authorship",
    )
    require_policy_rejection(
        checker, "kernel/sched.c", "linux-0.01-historical",
        "/* SPDX-License-Identifier: MIT */\n",
        "historical source falsely claims a modern project license",
    )
    require_policy_rejection(
        checker, "kernel/vga_font8x8.h", "third-party",
        f"/* Author: {identity}\n */\n",
        "protected material falsely claims project authorship",
    )
    require_policy_rejection(
        checker, "datasets/example.c", "generated-or-dataset",
        "/* SPDX-License-Identifier: BSD-3-Clause */\n",
        "protected material falsely claims a project license",
    )
    require_policy_rejection(
        checker, "userland/shell.c", "modern-mixed-content",
        f"/* Author: {identity}\n"
        " * Mixed-content rights: see LICENSE and evaluation/v1/THIRD-PARTY-NOTICES.md\n"
        " * SPDX-License-Identifier: BSD-3-Clause\n */\n",
        "must not claim a blanket SPDX license",
    )
    require_policy_rejection(
        checker, "bemu/cli.c", "bemu-partial-provenance",
        f"/* Maintainer and adaptation: {identity}\n"
        " * bEMU-NANO provenance: see bemu/README.md\n"
        " * SPDX-License-Identifier: BSD-3-Clause\n */\n",
        "must not infer a blanket SPDX license",
    )
    require_policy_rejection(
        checker, "README.md", "modern-mixed-document",
        "# SPDX-License-Identifier: MIT\n",
        "must not claim a blanket SPDX license",
    )
    require_policy_rejection(
        checker, "LICENSE", "legal-aggregation",
        "legal prose\n" * 35 + "SPDX-License-Identifier: Unlicense\n",
        "must not claim a blanket SPDX license",
    )
    require_policy_rejection(
        checker, "README.md", "modern-mixed-document",
        "<!-- SPDX-License-Identifier: MIT -->\n",
        "must not claim a blanket SPDX license",
    )
    require_policy_rejection(
        checker, "kernel/sched.c", "linux-0.01-historical",
        "/* SPDX-License-Identifier: MIT OR Apache-2.0 */\n",
        "historical source falsely claims a modern project license",
    )
    require_policy_rejection(
        checker, "tools/example.py", "modern-project",
        f"# Author: {identity}\n# SPDX-License-Identifier: Unlicense\n"
        "# SPDX-License-Identifier: MIT\n",
        "expected exactly SPDX-License-Identifier: Unlicense",
    )
    require_policy_rejection(
        checker, "tools/example.py", "modern-project",
        f"# Not authored by {identity}\n# SPDX-License-Identifier: Unlicense\n",
        "lacks the canonical Author identity",
    )
    require_policy_rejection(
        checker, "bemu/example.c", "bemu-partial-provenance",
        f"/* Not maintained by {identity}\n"
        " * bEMU-NANO provenance: see bemu/README.md\n */\n",
        "lacks the canonical maintainer/adaptation identity",
    )
    if checker.category("tests/imported.c", set()) is not None:
        raise AssertionError("new paths must not inherit a directory classification")
    if checker.category("tests/imported.c", set(), "third-party") != "third-party":
        raise AssertionError("an explicit manifest category was not honored")
    if checker.category("bemu/vendor.c", set(), "third-party") != "third-party":
        raise AssertionError("a directory prefix overrode an explicit category")
    if checker.required_category("bemu/vendor.c", set()) is not None:
        raise AssertionError("an unknown bEMU path inherited a required category")
    if checker.required_category("bemu/cli.c", set()) != "bemu-partial-provenance":
        raise AssertionError("a known bEMU path lost its exact category invariant")
    vendor_errors = []
    checker.check_header_text(
        "bemu/vendor.c",
        "third-party",
        "/* SPDX-License-Identifier: MIT */\n",
        vendor_errors,
        "MIT",
    )
    if vendor_errors:
        raise AssertionError(f"declared third-party SPDX was rejected: {vendor_errors}")
    require_policy_rejection(
        checker,
        "bemu/vendor.c",
        "third-party",
        "/* SPDX-License-Identifier: Apache-2.0 */\n",
        "does not match the manifest",
        license_status="MIT",
    )
    bbp_new_errors = []
    checker.check_header_text(
        "bbp/new.c",
        "modern-project",
        f"/* Author: {identity}\n * SPDX-License-Identifier: Unlicense\n */\n",
        bbp_new_errors,
        "Unlicense",
    )
    if bbp_new_errors:
        raise AssertionError(f"new BBP path inherited a directory license: {bbp_new_errors}")
    if checker.license_for("bbp/new.c", "modern-project", "Unlicense") != "Unlicense":
        raise AssertionError("new BBP path ignored its explicit manifest license")
    if checker.license_for("bbp/bbp_build.c", "modern-project", "Unlicense") != "BSD-3-Clause":
        raise AssertionError("known BBP path lost its exact BSD invariant")
    for bbp_path in sorted(checker.BBP_BSD_PATHS):
        bbp_reclassification_errors = []
        checker.check_path_invariants(
            bbp_path,
            "third-party",
            "MIT",
            set(),
            bbp_reclassification_errors,
        )
        if not any("required category" in error for error in bbp_reclassification_errors):
            raise AssertionError(
                f"known BBP reclassification was not rejected: "
                f"{bbp_path}: {bbp_reclassification_errors}"
            )
        if not any("retain BSD-3-Clause" in error for error in bbp_reclassification_errors):
            raise AssertionError(
                f"known BBP license mutation was not rejected: "
                f"{bbp_path}: {bbp_reclassification_errors}"
            )
    manifest_errors = []
    checker.compare_manifest_rows(
        {"README.md": ("modern-mixed-document", "author", "mixed")},
        {},
        manifest_errors,
    )
    if not any("missing paths" in error for error in manifest_errors):
        raise AssertionError(f"missing manifest row was not rejected: {manifest_errors}")
    for pinned_path in sorted(checker.IDENTITY_PINNED_SOURCE):
        with tempfile.TemporaryDirectory() as fixture_root:
            copy_pinned_fixture(fixture_root, checker)
            with open(os.path.join(fixture_root, pinned_path), "ab") as fixture:
                fixture.write(b"altered")
            pinned_errors = []
            checker.check_pinned_source_hashes(pinned_errors, fixture_root)
            if not any("bytes differ" in error for error in pinned_errors):
                raise AssertionError(
                    f"altered pinned source was not rejected: {pinned_path}: {pinned_errors}"
                )
    with tempfile.TemporaryDirectory() as fixture_root:
        copy_pinned_fixture(fixture_root, checker)
        manifest_path = os.path.join(
            fixture_root, "datasets", "compiler-cases", "v1", "MANIFEST.json"
        )
        with open(manifest_path, encoding="utf-8") as source:
            manifest = json.load(source)
        redirected = "datasets/compiler-cases/v1/sources/buffer_freelist.c"
        redirected_path = os.path.join(fixture_root, redirected)
        os.makedirs(os.path.dirname(redirected_path), exist_ok=True)
        shutil.copy2(
            os.path.join(REPO_ROOT, redirected),
            redirected_path,
        )
        manifest["sources"][0]["repository_path"] = redirected
        with open(manifest_path, "w", encoding="utf-8") as destination:
            json.dump(manifest, destination)
        pinned_errors = []
        checker.check_pinned_source_hashes(pinned_errors, fixture_root)
        if not any("published identity paths" in error for error in pinned_errors):
            raise AssertionError(f"redirected pinned path was not rejected: {pinned_errors}")

    result = subprocess.run(
        [sys.executable, CHECKER],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout.strip())
    if "authorship coverage passed" not in result.stdout:
        raise AssertionError("authorship checker did not emit its success marker")
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
