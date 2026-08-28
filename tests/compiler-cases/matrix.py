#!/usr/bin/env python3
"""
Build a compiler-version behavior matrix for the three -O2 sensitive cases.

The script looks for common GCC binaries on the host (gcc, gcc-11, gcc-12,
gcc-13, gcc-14, ...) and runs the harness with each one.  Results are stored in
build/matrix.json.  The matrix target ABI is x86_64; i386 is skipped for matrix
entries because not every GCC build supports -m32.
"""

import json
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HARNESS_DIR = os.path.join(REPO_ROOT, "tests", "compiler-cases")
BUILD_DIR = os.path.join(HARNESS_DIR, "build")
MATRIX_PATH = os.path.join(BUILD_DIR, "matrix.json")

CASES = ["buffer_freelist", "bitmap_inline_asm", "vsprintf_percent_s"]
OPTS = ["O0", "O1", "O2"]


def discover_compilers():
    candidates = ["gcc", "gcc-14", "gcc-13", "gcc-12", "gcc-11", "gcc-10"]
    found = []
    for c in candidates:
        path = shutil.which(c)
        if not path:
            continue
        try:
            ver = subprocess.check_output([path, "--version"], text=True)
        except Exception:
            continue
        found.append({"command": c, "path": path, "version": ver.splitlines()[0]})
    return found


def run_case(compiler, case, opt):
    bin_path = os.path.join(BUILD_DIR, f"{case}-matrix-{opt}")
    cmd = [
        compiler,
        "-Wall", "-Wextra", "-Werror", "-std=gnu89",
        f"-{opt}",
        os.path.join(HARNESS_DIR, f"{case}.c"),
        "-o", bin_path,
    ]
    try:
        subprocess.run(cmd, cwd=HARNESS_DIR, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        return {"compiled": False, "error": str(e)}

    try:
        out = subprocess.check_output([bin_path], text=True, stderr=subprocess.STDOUT)
        passed = out.strip().startswith("PASS")
        return {"compiled": True, "passed": passed, "output": out.strip()}
    except subprocess.CalledProcessError as e:
        return {"compiled": True, "passed": False, "output": e.output.strip()}


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    compilers = discover_compilers()
    if not compilers:
        print("no GCC compilers discovered", file=sys.stderr)
        return 1

    matrix = {
        "abi": "x86_64",
        "date": subprocess.check_output(
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], text=True
        ).strip(),
        "compilers": [],
    }

    for comp in compilers:
        entry = {
            "command": comp["command"],
            "path": comp["path"],
            "version": comp["version"],
            "results": {},
        }
        for case in CASES:
            entry["results"][case] = {}
            for opt in OPTS:
                entry["results"][case][opt] = run_case(comp["path"], case, opt)
        matrix["compilers"].append(entry)

    with open(MATRIX_PATH, "w") as f:
        json.dump(matrix, f, indent=2)

    print(f"matrix written to {MATRIX_PATH}")
    print(f"compilers tested: {len(compilers)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
