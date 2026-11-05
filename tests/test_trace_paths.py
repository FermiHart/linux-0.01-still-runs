#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Pre-KVM trace admission and input/evidence preservation regressions."""
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT/Path(os.environ.get('BUILD', 'build'))


class TracePaths(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-trace-paths-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.kernel = self.work/'kernel.bin'
        self.disk = self.work/'root.img'
        self.kernel.write_bytes(b'SYNTHETIC invalid kernel; never execute')
        self.disk.write_bytes(b'SYNTHETIC user disk contents')

    def run_bemu(self, trace):
        return subprocess.run([str(BUILD/'bemu-linux01'), '--kernel', str(self.kernel),
                               '--root', str(self.disk), '--trace-file', str(trace)],
                              capture_output=True, timeout=10)

    def test_inputs_and_all_existing_aliases_are_preserved(self):
        before = {p: p.read_bytes() for p in (self.kernel, self.disk)}
        for original in before:
            for kind in ('direct', 'symlink', 'hardlink'):
                with self.subTest(original=original.name, kind=kind):
                    alias = self.work/(original.name+'.'+kind)
                    if kind == 'direct':
                        alias = original
                    elif kind == 'symlink':
                        alias.symlink_to(original)
                    else:
                        os.link(original, alias)
                    result = self.run_bemu(alias)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(original.read_bytes(), before[original])

    def test_existing_trace_even_empty_is_not_implicitly_replaced(self):
        for payload in (b'', b'previous evidence\n'):
            with self.subTest(payload=payload):
                trace = self.work/'evidence.jsonl'
                trace.write_bytes(payload)
                inode = trace.stat().st_ino
                result = self.run_bemu(trace)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'trace', result.stderr)
                self.assertEqual(trace.read_bytes(), payload)
                self.assertEqual(trace.stat().st_ino, inode)

    def test_new_trace_has_private_permissions_and_valid_events(self):
        trace = self.work/'new.jsonl'
        result = subprocess.run([str(BUILD/'test-trace-producer'),
                                 '--emit-schema-fixture', str(trace)],
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(trace.stat().st_mode), 0o600)
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        self.assertEqual(events[0]['type'], 'boot_start')
        self.assertEqual(events[-1]['type'], 'shutdown')


if __name__ == '__main__':
    unittest.main()
