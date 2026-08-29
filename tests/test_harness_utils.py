#!/usr/bin/env python3
# Author: F E R M I INFINITY H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense

"""Pure-Python regressions for test harness output handling."""

import unittest

from harness_utils import extract_command_output, line_contains, sanitize_terminal


class TerminalSanitizerTests(unittest.TestCase):
    def test_removes_terminal_controls_and_string_payloads(self):
        value = (
            "readable\x1b[31m red\x1b[0m"
            "\x1b]0;osc payload\x07"
            "\x1bPdcs payload\x07still dcs\x1b\\"
            "\x9dsecond osc\x9c"
            "\x90second dcs\x9c"
            "\x00\x08\x85\nnext\tline"
        )
        self.assertEqual(sanitize_terminal(value), "readable red\nnext    line")

    def test_unterminated_control_string_does_not_leak_payload(self):
        self.assertEqual(sanitize_terminal("safe\x1b]malicious"), "safe")


class TranscriptBoundaryTests(unittest.TestCase):
    def test_echoed_input_cannot_satisfy_assertion(self):
        transcript = (
            "root@linux01:/# echo TOKENBEGIN\n"
            "TOKENBEGIN\n"
            "root@linux01:/# echo echoed-only\n"
            "actual output\n"
            "root@linux01:/# echo TOKENEND\n"
            "TOKENEND\n"
        )
        segment, _ = extract_command_output(
            transcript, "TOKENBEGIN", "TOKENEND", command="echo echoed-only",
            validate=True,
        )
        self.assertFalse(line_contains(segment, "echoed-only"))
        self.assertTrue(line_contains(segment, "actual output"))

    def test_raw_and_clean_transcripts_use_independent_offsets(self):
        raw = (
            "noise\x1b[31m\n"
            "RAWBEGIN\r\n"
            "\x1b[32mroot@linux01:/#\x1b[0m echo value\r\n"
            "value\r\n"
            "\x1b[32mroot@linux01:/#\x1b[0m echo RAWEND\r\n"
            "RAWEND\r\n"
        )
        clean = sanitize_terminal(raw)
        clean_segment, _ = extract_command_output(
            clean, "RAWBEGIN", "RAWEND", command="echo value", validate=True,
        )
        raw_segment, _ = extract_command_output(raw, "RAWBEGIN", "RAWEND")
        self.assertTrue(line_contains(clean_segment, "value"))
        self.assertIn("\x1b[32m", raw_segment)


if __name__ == "__main__":
    unittest.main()
