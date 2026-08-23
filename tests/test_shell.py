#!/usr/bin/env python3
"""bEMU shell smoke tests for linux-0.01-still-runs."""

import argparse
import os
import re
import shutil
import secrets
import subprocess
import sys
import tempfile

from harness_utils import (
    BEMU_PASS_RE,
    KERNEL_FAULT_RE,
    diagnostic,
    extract_command_output,
    line_contains,
    sanitize_terminal,
)


KEYS = {
    " ": "spc",
    "/": "slash",
    ".": "dot",
    "-": "minus",
    "+": "plus",
    ">": "shift-dot",
    ";": "semicolon",
}


COMMANDS = [
    ("hello", ["Hello from C userland"], []),
    ("/bin/hello", ["Hello from C userland"], []),
    ("help", ["built-in commands"], []),
    ("echo oi", ["oi"], []),
    ("nope", ["nope: not found"], []),
    ("uname", ["linux .0"], []),
    ("uname -a", ["nodename", "machine"], []),
    ("history", ["hello"], []),
    ("ls", ["bin", "etc", "home", "tmp"], []),
    ("ls -la", ["drwx", "tmp"], []),
    ("ls -la /dev", ["tty0"], []),
    ("ls -la bin", ["shell", "hello", "yes"], []),
    ("whoami", ["root"], []),
    ("mount", ["/dev/hd1 on / type minix"], []),
    ("df", ["Filesystem", "/dev/hd1"], []),
    ("ps aux", ["USER  PID   PPID  STAT  TTY    TIME  COMMAND", "shell"], []),
    ("cat /etc/fstab", ["/dev/hd1 / minix rw"], []),
    ("cat /etc/motd", ["There is a specific feeling", "Welcome to 1991"], []),
    ("cd etc", ["fermihart@linux01:/etc$"], []),
    ("pwd", ["/etc"], []),
    ("cd ..", ["fermihart@linux01:/$"], []),
    ("pwd", ["/"], []),
    ("cd", ["fermihart@linux01:/home/fermihart$"], []),
    ("pwd", ["/home/fermihart"], []),
    ("ls", ["fermihart@linux01:/home/fermihart$"], [], ["bin  dev  etc"]),
    ("ls -la", [".", ".."], [], ["README", "motd"]),
    ("cd /", ["fermihart@linux01:/$"], []),
    ("cd tmp", ["fermihart@linux01:/tmp$"], []),
    ("mkdir core", [], []),
    ("cd core", ["fermihart@linux01:/tmp/core$"], []),
    ("pwd", ["/tmp/core"], []),
    ("touch empty", [], []),
    ("ls", ["empty"], []),
    ("echo alpha beta > a", [], []),
    ("cp a b", [], []),
    ("cat b", ["alpha beta"], []),
    ("mv b c", [], []),
    ("cat c", ["alpha beta"], []),
    ("ln c hard", [], []),
    ("rm c", [], []),
    ("cat hard", ["alpha beta"], []),
    ("head hard", ["alpha beta"], []),
    ("wc hard", ["1 2 11"], []),
    ("grep beta hard", ["alpha beta"], []),
    ("cd ..", ["fermihart@linux01:/tmp$"], []),
    ("rmdir core", [], []),
    ("cd /", ["fermihart@linux01:/$"], []),
    ("date", [":"], []),
    ("cal", ["Su Mo Tu We Th Fr Sa"], []),
    ("uptime", ["load average"], []),
    ("fortune", ["--"], []),
    ("true", [], []),
    ("false", [], []),
    ("linus", ["comp.os.minix"], []),
]

INTERACTIVE = [
    ("tab-complete whoami", ["w", "h", "o", "tab", "ret"], ["root"]),
    ("tab-complete /etc/motd", ["c", "a", "t", "spc", "slash", "e", "t", "c", "slash", "m", "tab", "ret"], ["There is a specific feeling"]),
    ("tab-complete path", ["c", "a", "t", "spc", "slash", "e", "t", "c", "slash", "f", "tab", "ret"], ["/dev/hd1 / minix rw"]),
    ("history up", ["e", "c", "h", "o", "spc", "h", "i", "s", "t", "ret", "up", "ret"], ["hist"]),
    ("history down", ["e", "c", "h", "o", "spc", "o", "l", "d", "ret", "e", "c", "h", "o", "spc", "n", "e", "w", "ret", "up", "up", "down", "ret"], ["new"]),
    ("backspace", ["e", "c", "h", "o", "spc", "g", "o", "o", "x", "backspace", "d", "ret"], ["good"]),
    ("ctrl-u", ["n", "o", "i", "s", "e", "ctrl-u", "e", "c", "h", "o", "spc", "c", "l", "e", "a", "n", "ret"], ["clean"]),
    ("left-insert", ["e", "c", "h", "o", "spc", "a", "c", "left", "b", "ret"], ["abc"]),
    ("ctrl-a-e", ["z", "z", "ctrl-a", "e", "c", "h", "o", "spc", "ctrl-e", "ret"], ["zz"]),
    ("ctrl-k", ["e", "c", "h", "o", "spc", "k", "e", "e", "p", "t", "r", "a", "s", "h", "left", "left", "left", "left", "left", "ctrl-k", "ret"], ["keep"]),
    ("ctrl-w", ["e", "c", "h", "o", "spc", "d", "r", "o", "p", "spc", "w", "o", "r", "d", "ctrl-w", "ret"], ["drop"]),
    ("ctrl-y", ["e", "c", "h", "o", "spc", "y", "a", "n", "k", "ctrl-w", "ctrl-y", "ret"], ["yank"]),
]


def parse_args():
    parser = argparse.ArgumentParser(description="Linux 0.01 bEMU shell tests")
    parser.add_argument("--bemu", default="build/bemu-linux01")
    parser.add_argument("--kernel", default="build/kernel.bin")
    parser.add_argument("--img", default="build/root.img")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    return parser.parse_args()


def interactive_text(keys):
    special = {
        "tab": "\t", "ret": "\n", "up": "\x1b[A", "down": "\x1b[B",
        "left": "\x1b[D", "right": "\x1b[C",
        "backspace": "\x7f",
        "ctrl-a": "\x01", "ctrl-e": "\x05", "ctrl-k": "\x0b",
        "ctrl-u": "\x15", "ctrl-w": "\x17", "ctrl-y": "\x19",
        "spc": " ", "slash": "/", "dot": ".", "minus": "-",
        "plus": "+", "semicolon": ";",
    }
    return "".join(special.get(key, key) for key in keys)


def build_script(include_interactive):
    cases = []
    nonce = secrets.token_hex(6).upper()
    begin = f"BEMU{nonce}START"
    chunks = [f"echo {begin}\n"]
    for item in COMMANDS:
        command, expected, raw_expected = item[:3]
        forbidden = item[3] if len(item) > 3 else []
        end = f"BEMU{nonce}{len(cases):02d}END"
        chunks.extend((command, "\n", f"echo {end}\n"))
        cases.append((command, expected, raw_expected, forbidden, begin, end, command))
        begin = end
    if include_interactive:
        for name, keys, expected in INTERACTIVE:
            end = f"BEMU{nonce}{len(cases):02d}END"
            chunks.extend((interactive_text(keys), f"echo {end}\n"))
            cases.append((name, expected, [], [], begin, end, None))
            begin = end
    return "".join(chunks), cases


def main():
    args = parse_args()
    for path in (args.bemu, args.kernel, args.img):
        if not os.path.exists(path):
            print(f"missing artifact: {diagnostic(path, 1000)}; run make all first")
            return 1

    script, cases = build_script(args.interactive)
    final_marker = cases[-1][5]
    with tempfile.TemporaryDirectory(prefix="linux001-shell-") as temp_dir:
        root_copy = os.path.join(temp_dir, "root.img")
        shutil.copyfile(args.img, root_copy)
        command = [
            args.bemu, "--kernel", args.kernel, "--root", root_copy,
            "--keys", script, "--expect", final_marker,
        ]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            print(f"bEMU shell test timed out after {args.timeout}s")
            if args.verbose and exc.stdout:
                print(diagnostic(exc.stdout, 4000))
            return 1
        except OSError as exc:
            print(f"failed to run bEMU: {diagnostic(exc, 1000)}")
            return 1

    raw_output = result.stdout
    output = sanitize_terminal(raw_output)
    if result.returncode or BEMU_PASS_RE.search(output) is None:
        print(f"bEMU failed with status {result.returncode}")
        if args.verbose:
            print(output[-4000:])
        return 1
    if KERNEL_FAULT_RE.search(output):
        print("kernel fault during shell test")
        if args.verbose:
            print(output[-4000:])
        return 1

    print("Starting shell smoke tests...")
    clean_cursor = 0
    raw_cursor = 0
    for name, expected, raw_expected, forbidden, begin, end, command_echo in cases:
        try:
            segment, clean_cursor = extract_command_output(
                output, begin, end, clean_cursor, command_echo, validate=True,
            )
            raw_segment, raw_cursor = extract_command_output(
                raw_output, begin, end, raw_cursor,
            )
        except ValueError as exc:
            print(f"  {name}: {exc}")
            if args.verbose:
                print(diagnostic(output[clean_cursor:], 3000))
            return 1
        missing = [value for value in expected if not line_contains(segment, value)]
        raw_missing = [value for value in raw_expected if value not in raw_segment]
        unexpected = [value for value in forbidden if line_contains(segment, value)]
        if missing or raw_missing or unexpected:
            print(f"  {name}: missing={missing + raw_missing} unexpected={unexpected}")
            if args.verbose:
                print(segment[-2000:])
            return 1
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
