#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Host orchestration regressions with clearly synthetic executables, never KVM."""
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FuzzSafety(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-script-tests-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        (self.work/'scripts').mkdir()
        (self.work/'build').mkdir()
        (self.work/'bin').mkdir()
        shutil.copy2(ROOT/'scripts/fuzz-bemu.sh', self.work/'scripts/fuzz-bemu.sh')
        self.disk = self.work/'build/root.img'
        self.disk.write_bytes(b'SYNTHETIC original disk\n'*64)
        (self.work/'build/kernel.bin').write_bytes(b'SYNTHETIC kernel\n'*1024)
        self.executable(self.work/'build/bemu-linux01', '''#!/usr/bin/python3
import os, sys
from pathlib import Path
args=sys.argv[1:]
if '--nope' in args or ('--max-exits' in args and args[args.index('--max-exits')+1]=='0'):
    sys.exit(int(os.environ.get('SYNTHETIC_CLI_RC','2')))
if '--kernel' in args and args[args.index('--kernel')+1]=='/nonexistent':sys.exit(1)
if '--root' in args:
    with Path(args[args.index('--root')+1]).open('ab') as disk:disk.write(b'SYNTHETIC guest write')
sys.exit(1)
''')
        self.executable(self.work/'bin/timeout', '''#!/usr/bin/python3
import os, sys
if 'SYNTHETIC_TIMEOUT_RC' in os.environ:sys.exit(int(os.environ['SYNTHETIC_TIMEOUT_RC']))
args=sys.argv[1:]
while args and args[0].startswith('-'):args.pop(0)
args.pop(0)
os.execv(args[0],args)
''')

    def executable(self, path, source):
        path.write_text(source)
        path.chmod(0o755)

    def run_fuzz(self, **extra):
        env = dict(os.environ, PATH=str(self.work/'bin')+':'+os.environ['PATH'], **extra)
        env.pop('BUILD', None)
        return subprocess.run(['/bin/bash', 'scripts/fuzz-bemu.sh'], cwd=self.work,
                              env=env, capture_output=True, text=True, timeout=30)

    def test_all_guest_writes_use_disposable_images(self):
        before = self.disk.read_bytes()
        result = self.run_fuzz()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual(self.disk.read_bytes(), before)

    def test_timeout_and_launch_errors_are_failures(self):
        for status in ('124', '125', '126', '127', '137', '139'):
            with self.subTest(status=status):
                result = self.run_fuzz(SYNTHETIC_TIMEOUT_RC=status)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertNotIn('all 15 cases handled cleanly', result.stdout)

    def test_invalid_cli_success_is_not_accepted(self):
        result = self.run_fuzz(SYNTHETIC_CLI_RC='0')
        self.assertNotEqual(result.returncode, 0, result.stdout)


class StaticAnalysisAvailability(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-analysis-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        (self.work/'scripts').mkdir()
        (self.work/'bin').mkdir()
        shutil.copy2(ROOT/'scripts/static-analysis.sh', self.work/'scripts/static-analysis.sh')
        (self.work/'bin/dirname').symlink_to(shutil.which('dirname'))

    def tool(self, name, status=0):
        path = self.work/'bin'/name
        path.write_text(f'#!/bin/sh\nexit {status}\n')
        path.chmod(0o755)

    def run_analysis(self):
        return subprocess.run(['/bin/bash', 'scripts/static-analysis.sh'], cwd=self.work,
                              env=dict(os.environ, PATH=str(self.work/'bin')),
                              capture_output=True, text=True, timeout=10)

    def test_missing_analyzers_are_not_success(self):
        result = self.run_analysis()
        self.assertEqual(result.returncode, 77, result.stdout+result.stderr)
        self.assertIn('SKIP', result.stdout)
        self.assertNotIn('passed', result.stdout)

    def test_partial_availability_is_reported_and_full_run_can_pass(self):
        self.tool('cppcheck')
        partial = self.run_analysis()
        self.assertEqual(partial.returncode, 77, partial.stdout)
        self.tool('clang-tidy')
        complete = self.run_analysis()
        self.assertEqual(complete.returncode, 0, complete.stdout)
        self.assertIn('PASS', complete.stdout)

    def test_real_analyzer_failure_dominates_missing_tool(self):
        self.tool('cppcheck', 9)
        result = self.run_analysis()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn('FAIL', result.stdout+result.stderr)


class ProvenanceSafety(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-provenance-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        shutil.copytree(ROOT/'scripts', self.work/'scripts')
        (self.work/'upstream').mkdir()
        for name in ('linux-0.01.tar.gz', 'SHA256SUMS'):
            shutil.copy2(ROOT/'upstream'/name, self.work/'upstream'/name)
        (self.work/'docs').mkdir()
        shutil.copy2(ROOT/'docs/PORTING_LEDGER.md', self.work/'docs/PORTING_LEDGER.md')
        with tarfile.open(ROOT/'upstream/linux-0.01.tar.gz') as archive:
            original = archive.extractfile('linux/init/main.c').read()
        for directory in ('init', 'kernel', 'mm', 'fs', 'lib', 'include'):
            (self.work/directory).mkdir()
            (self.work/'upstream/extracted/linux'/directory).mkdir(parents=True)
        (self.work/'init/main.c').write_bytes(original+b'\n/* SYNTHETIC changed body */\n')
        (self.work/'upstream/extracted/linux/init/main.c').write_bytes(original)

    def run_provenance(self):
        env = dict(os.environ)
        env.pop('BUILD', None)
        return subprocess.run(['/bin/bash', 'scripts/provenance.sh'], cwd=self.work,
                              env=env, capture_output=True, text=True, timeout=20)

    def test_missing_ledger_declaration_is_not_reported_as_complete(self):
        ledger = self.work/'docs/PORTING_LEDGER.md'
        ledger.write_text(ledger.read_text().replace('**Files**: `init/main.c`',
                                                    '**Files**: `init/unrelated.c`'))
        result = self.run_provenance()
        report = (self.work/'build/PROVENANCE.txt').read_text()
        self.assertNotEqual(result.returncode, 0, report)
        self.assertIn('UNRESOLVED init/main.c', report)
        self.assertNotIn('All changed files are referenced', report)

    def test_exact_declared_path_is_identified_without_a_git_revision_trick(self):
        result = self.run_provenance()
        report = (self.work/'build/PROVENANCE.txt').read_text()
        self.assertIn('EXACT init/main.c', report)
        # The deliberately sparse fixture deletes other historical source paths;
        # those must be counted rather than silently disappearing from the audit.
        self.assertIn('DELETED', report)


class ReproducibilityIsolation(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-repro-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.repo = self.work/'repo'
        (self.repo/'scripts').mkdir(parents=True)
        (self.work/'bin').mkdir()
        (self.work/'tmp').mkdir()
        shutil.copy2(ROOT/'scripts/verify-reproducibility.sh',
                     self.repo/'scripts/verify-reproducibility.sh')
        shutil.copy2(ROOT/'scripts/source_snapshot.py', self.repo/'scripts/source_snapshot.py')
        (self.repo/'Makefile').write_text('# SYNTHETIC build fixture\n')
        (self.repo/'.gitignore').write_text('build/\n.local/\nstate/\nrelease/\n')
        for directory in ('.local', 'state', 'release', 'build'):
            (self.repo/directory).mkdir()
            (self.repo/directory/'private-fixture').write_text('SYNTHETIC private data\n')
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', 'add', '--', 'Makefile', '.gitignore',
                        'scripts/verify-reproducibility.sh', 'scripts/source_snapshot.py'], cwd=self.repo, check=True)
        make = self.work/'bin/make'
        make.write_text('''#!/usr/bin/python3
import os,sys
from pathlib import Path
if os.environ.get('SYNTHETIC_PUBLIC_ONLY'):
    if any(Path(p).exists() for p in ('.git','.local','state','release','build/private-fixture')):sys.exit(12)
Path('build').mkdir(exist_ok=True)
content=os.getcwd() if os.environ.get('SYNTHETIC_DIFFERENT_BUILDS') else 'SYNTHETIC stable result'
Path('build/SHA256SUMS').write_text(content+'\\n')
''')
        make.chmod(0o755)

    def run_repro(self, **extra):
        env = dict(os.environ, PATH=str(self.work/'bin')+':'+os.environ['PATH'],
                   TMPDIR=str(self.work/'tmp'), **extra)
        return subprocess.run(['/bin/bash', 'scripts/verify-reproducibility.sh'],
                              cwd=self.repo, env=env, capture_output=True, text=True, timeout=30)

    def test_shared_temp_manifests_are_never_touched(self):
        sentinels = [self.work/'tmp'/f'repro-{name}.sha256' for name in ('a', 'b')]
        for path in sentinels:
            path.write_bytes(b'user-owned sentinel')
        result = self.run_repro()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        for path in sentinels:
            self.assertEqual(path.read_bytes(), b'user-owned sentinel')

    def test_only_public_source_inputs_are_copied(self):
        result = self.run_repro(SYNTHETIC_PUBLIC_ONLY='1')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_different_results_really_fail(self):
        result = self.run_repro(SYNTHETIC_DIFFERENT_BUILDS='1')
        self.assertNotEqual(result.returncode, 0, result.stdout+result.stderr)


class ArchSetupSafety(unittest.TestCase):
    def test_arch_setup_never_performs_an_implicit_system_upgrade(self):
        with tempfile.TemporaryDirectory(prefix='linux001-arch-test-') as directory:
            root = Path(directory)
            (root/'tools').mkdir()
            (root/'bin').mkdir()
            shutil.copy2(ROOT/'tools/setup-toolchain.sh', root/'tools/setup-toolchain.sh')
            for name in ('dirname', 'mktemp', 'uname', 'rm'):
                (root/'bin'/name).symlink_to(shutil.which(name))
            for name in ('pacman', 'sudo'):
                path = root/'bin'/name
                path.write_text('#!/bin/sh\necho "$*" >> "$SYNTHETIC_PACKAGE_LOG"\nexit 0\n')
                path.chmod(0o755)
            log = root/'package-commands'
            result = subprocess.run(['/bin/bash', 'tools/setup-toolchain.sh'], cwd=root,
                                    env=dict(os.environ, PATH=str(root/'bin'),
                                             SYNTHETIC_PACKAGE_LOG=str(log)),
                                    capture_output=True, text=True, timeout=10)
            self.assertFalse(log.exists(), log.read_text() if log.exists() else '')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('pacman -Syu', result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
