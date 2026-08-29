# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Shared output handling for the bEMU test harnesses."""

import re


BEMU_PASS_RE = re.compile(
    r"^\[bemu-linux01\] RESULT: PASS after [0-9]+ KVM exits$",
    re.MULTILINE,
)
KERNEL_FAULT_RE = re.compile(
    r"^(?:Kernel panic|general protection:|double fault:|page fault:)",
    re.IGNORECASE | re.MULTILINE,
)
PROMPT_RE = r"root@linux01:[^\n]*#"


def as_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def sanitize_terminal(value):
    """Remove terminal controls and control strings without exposing payloads."""
    text = as_text(value)
    output = []
    state = "text"

    for char in text:
        code = ord(char)
        if state == "text":
            if char == "\x1b":
                state = "escape"
            elif code == 0x9D:
                state = "osc"
            elif code in (0x90, 0x98, 0x9E, 0x9F):
                state = "string"
            elif code == 0x9B:
                state = "csi"
            elif code < 0x20:
                if char == "\n":
                    output.append(char)
                elif char == "\t":
                    output.append("    ")
            elif code == 0x7F or 0x80 <= code <= 0x9F:
                continue
            else:
                output.append(char)
        elif state == "escape":
            if char == "[":
                state = "csi"
            elif char == "]":
                state = "osc"
            elif char in "PX^_":
                state = "string"
            elif 0x20 <= code <= 0x2F:
                state = "escape_intermediate"
            else:
                state = "text"
        elif state == "escape_intermediate":
            if not 0x20 <= code <= 0x2F:
                state = "text"
        elif state == "csi":
            if 0x40 <= code <= 0x7E or char in "\x18\x1a":
                state = "text"
            elif char == "\x1b":
                state = "escape"
        elif state in ("osc", "string"):
            if code == 0x9C or (state == "osc" and char == "\x07"):
                state = "text"
            elif char == "\x1b":
                state += "_escape"
        elif state in ("osc_escape", "string_escape"):
            if char == "\\" or code == 0x9C:
                state = "text"
            elif char != "\x1b":
                state = state.removesuffix("_escape")

    return "".join(output)


def diagnostic(value, limit):
    return sanitize_terminal(value)[-limit:]


def line_contains(text, value):
    """Match a literal on one output line, never across transcript boundaries."""
    return re.search(
        rf"(?m)^[^\n]*{re.escape(value)}[^\n]*$",
        text,
    ) is not None


def _marker_match(text, marker, start):
    # Raw serial lines can have one or more carriage returns around their text.
    return re.compile(
        rf"(?m)^\r*{re.escape(marker)}\r*$"
    ).search(text, start)


def extract_command_output(text, begin, end, start=0, command=None, validate=False):
    """Return command output and the next offset using full-line delimiters.

    The shell echoes the submitted command and the command that prints the end
    marker. Those input lines are excluded; the final prompt is retained so
    state-changing commands can assert their resulting directory.
    """
    begin_match = _marker_match(text, begin, start)
    if not begin_match:
        raise ValueError(f"missing begin marker {begin!r}")
    end_match = _marker_match(text, end, begin_match.end())
    if not end_match:
        raise ValueError(f"missing end marker {end!r}")

    lines = text[begin_match.end():end_match.start()].split("\n")
    while lines and not lines[0].strip("\r"):
        lines.pop(0)
    while lines and not lines[-1].strip("\r"):
        lines.pop()
    if len(lines) < 2:
        raise ValueError(f"incomplete command boundary before {end!r}")

    first_clean = sanitize_terminal(lines[0])
    last_clean = sanitize_terminal(lines[-1])
    if validate:
        if command is None:
            first_pattern = rf"^{PROMPT_RE} .+$"
        else:
            first_pattern = rf"^{PROMPT_RE} {re.escape(command)}$"
        if re.fullmatch(first_pattern, first_clean) is None:
            raise ValueError(f"unexpected command echo before {end!r}")
        if re.fullmatch(rf"{PROMPT_RE} echo {re.escape(end)}", last_clean) is None:
            raise ValueError(f"unexpected end-marker echo before {end!r}")

    raw_last = lines[-1].rstrip("\r")
    suffix = f" echo {end}"
    if not raw_last.endswith(suffix):
        raise ValueError(f"malformed end-marker echo before {end!r}")
    final_prompt = raw_last[:-len(suffix)]
    segment = "\n".join(lines[1:-1] + [final_prompt])
    # Return the marker start so it can also delimit the next command.
    return segment, end_match.start()
