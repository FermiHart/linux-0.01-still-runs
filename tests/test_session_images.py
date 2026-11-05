#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Root-image lifecycle regressions; synthetic bytes are not boot evidence."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SessionImages(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-sessions-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copy2(ROOT/'Makefile', self.root/'Makefile')
        shutil.copytree(ROOT/'scripts', self.root/'scripts')
        (self.root/'build').mkdir()
        self.legacy = self.root/'build/root.img'
        self.legacy.write_bytes(b'SYNTHETIC legacy guest data')

    def make(self, *args):
        return subprocess.run(['make', '--no-print-directory', 'NO_COLOR=1', 'BUILD=build', *args],
                              cwd=self.root, capture_output=True, text=True, timeout=30)

    def helper(self, *args):
        return subprocess.run(['python3', str(ROOT/'scripts/session-image.py'),
                               '--build-root', str(self.root/'build'),
                               '--state-dir', str(self.root/'state'), *map(str, args)],
                              capture_output=True, text=True, timeout=10)

    def test_clean_preserves_legacy_disk_outside_build(self):
        before = self.legacy.read_bytes()
        result = self.make('clean')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root/'state/alive/default.img').read_bytes(), before)
        self.assertFalse(self.legacy.exists())

    def test_rebuild_failure_keeps_legacy_disk_and_recovery(self):
        before = self.legacy.read_bytes()
        tools = self.root/'tools'
        tools.mkdir()
        (tools/'mkimage.c').write_text('/* synthetic dependency */\n')
        os.utime(tools/'mkimage.c', (1, 1))
        (self.root/'bemu').mkdir()
        (self.root/'bemu/experience.h').write_text('/* synthetic dependency */\n')
        os.utime(self.root/'bemu/experience.h', (1, 1))
        for name in ('shell', 'update', 'hello', 'yes', 'pathcheck', 'cat'):
            (self.root/f'build/{name}.bin').write_bytes(b'SYNTHETIC program')
        forge = self.root/'build/mkimage'
        forge.write_text('#!/bin/sh\necho fixture-forge-failed >&2\nexit 1\n')
        forge.chmod(0o755)
        os.utime(self.legacy, (1, 1))
        result = self.make('build/root.img', 'USERLAND_BINS=')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('fixture-forge-failed', result.stdout+result.stderr)
        self.assertEqual(self.legacy.read_bytes(), before)
        self.assertEqual((self.root/'state/alive/default.img').read_bytes(), before)

    def test_existing_session_is_never_overwritten(self):
        session = self.root/'state/alive/default.img'
        session.parent.mkdir(parents=True)
        session.write_bytes(b'SYNTHETIC current user session')
        result = self.helper('--preserve-build', self.root/'build')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(session.read_bytes(), b'SYNTHETIC current user session')
        digest = hashlib.sha256(self.legacy.read_bytes()).hexdigest()
        self.assertEqual((self.root/f'state/recovered/root.img.{digest}.img').read_bytes(),
                         self.legacy.read_bytes())

    def test_prepare_is_exclusive_and_refuses_build_owned_state(self):
        target = self.root/'state/alive/work.img'
        first = self.helper('--prepare', self.legacy, '--output', target)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.legacy.write_bytes(b'SYNTHETIC changed base')
        second = self.helper('--prepare', self.legacy, '--output', target)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(target.read_bytes(), b'SYNTHETIC legacy guest data')
        bad = self.helper('--prepare', self.legacy, '--output', self.root/'build/session.img')
        self.assertNotEqual(bad.returncode, 0)
        self.assertFalse((self.root/'build/session.img').exists())

    def test_unchanged_generated_base_needs_no_recovery(self):
        digest = hashlib.sha256(self.legacy.read_bytes()).hexdigest()
        Path(str(self.legacy)+'.base-sha256').write_text(digest+'\n')
        result = self.helper('--preserve-build', self.root/'build')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root/'state/recovered').exists())

    def test_prepare_rejects_existing_symlink_without_touching_target(self):
        victim = self.root/'victim'
        victim.write_bytes(b'keep me')
        target = self.root/'state/alive/work.img'
        target.parent.mkdir(parents=True)
        target.symlink_to(victim)
        result = self.helper('--prepare', self.legacy, '--output', target)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('session image refused', result.stderr)
        self.assertEqual(victim.read_bytes(), b'keep me')

    def test_prepare_rejects_hardlink_alias_of_base(self):
        target = self.root/'state/alive/work.img'
        target.parent.mkdir(parents=True)
        os.link(self.legacy, target)
        result = self.helper('--prepare', self.legacy, '--output', target)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('session image refused', result.stderr)
        self.assertEqual(self.legacy.read_bytes(), b'SYNTHETIC legacy guest data')

    def test_clean_aborts_if_state_would_be_deleted(self):
        before = self.legacy.read_bytes()
        result = self.make('clean', 'STATE=build/state')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.legacy.read_bytes(), before)

    def test_historical_legacy_session_is_separate(self):
        historical = self.root/'build/root-1991.img'
        historical.write_bytes(b'SYNTHETIC historical user data')
        result = self.make('clean')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root/'state/1991/default.img').read_bytes(),
                         b'SYNTHETIC historical user data')

    def test_cleanup_refuses_recovery_redirected_back_into_build(self):
        (self.root/'state').mkdir()
        (self.root/'state/recovered').symlink_to(self.root/'build')
        before = self.legacy.read_bytes()
        result = self.make('clean')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.legacy.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
