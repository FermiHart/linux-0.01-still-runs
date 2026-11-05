#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Source delivery regressions; retained inputs are data, never fabricated Git history."""
import hashlib
import csv
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH_REVISION = 'ae458306905d4fee85121ac3c2b42e86ed099310'


def load(name):
    path = ROOT/'scripts'/f'{name}.py'
    if not path.is_file():
        raise AssertionError(f'missing source delivery behavior: {path.name}')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HistoricInputs(unittest.TestCase):
    def setUp(self):
        self.module = load('history_inputs')
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-history-input-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root/'provenance/source-inputs/v1'
        self.module.capture(ROOT, self.directory, {
            PATCH_REVISION: {'init/main.c', 'docs/PORTING_LEDGER.md'},
        })

    def reader(self):
        return self.module.History(self.root, allow_git=False)

    def manifest(self):
        return json.loads((self.directory/'MANIFEST.json').read_text())

    def change_manifest(self, value):
        (self.directory/'MANIFEST.json').write_text(json.dumps(value)+'\n')

    def test_files_and_original_tree_bind_without_git_metadata(self):
        reader = self.reader()
        with (ROOT/'datasets/patches/file_deltas.csv').open(newline='') as stream:
            expected = next(row for row in csv.DictReader(stream) if row['path'] == 'init/main.c')
        self.assertEqual(hashlib.sha256(reader.file(PATCH_REVISION, 'init/main.c')).hexdigest(),
                         expected['port_sha256'])
        tree = json.loads((ROOT/'datasets/patches/MANIFEST.json').read_text())['port_tree']
        self.assertEqual(reader.tree(PATCH_REVISION), tree)
        self.assertIn('init/main.c', reader.entries(PATCH_REVISION, prefix='init/'))
        self.assertFalse((self.root/'.git').exists())

    def test_missing_materialized_input_never_uses_an_unstated_fallback(self):
        with self.assertRaisesRegex(ValueError, 'not retained'):
            self.reader().file(PATCH_REVISION, 'README.md')

    def test_archive_tampering_is_rejected(self):
        record = self.manifest()['revisions'][0]
        archive = self.directory/record['archive']
        data = bytearray(archive.read_bytes())
        data[len(data)//2] ^= 1
        archive.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'archive checksum'):
            self.reader().file(PATCH_REVISION, 'init/main.c')

    def test_forged_tree_descriptor_cannot_rebind_the_original_commit(self):
        manifest = self.manifest()
        manifest['revisions'][0]['entries'][0]['blob'] = '0'*40
        self.change_manifest(manifest)
        with self.assertRaisesRegex(ValueError, 'tree identity'):
            self.reader().file(PATCH_REVISION, 'init/main.c')

    def test_forged_commit_identity_is_rejected(self):
        manifest = self.manifest()
        manifest['revisions'][0]['revision'] = '0'*40
        self.change_manifest(manifest)
        with self.assertRaisesRegex(ValueError, 'commit identity'):
            self.reader().file('0'*40, 'init/main.c')

    def test_unsafe_archive_path_is_rejected_without_extraction(self):
        manifest = self.manifest()
        record = manifest['revisions'][0]
        archive = self.directory/record['archive']
        with tarfile.open(archive, 'w:gz', format=tarfile.USTAR_FORMAT) as output:
            item = tarfile.TarInfo('../escaped')
            item.size = 1
            output.addfile(item, io.BytesIO(b'x'))
        record['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.change_manifest(manifest)
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            self.reader().file(PATCH_REVISION, 'init/main.c')
        self.assertFalse((self.directory.parent/'escaped').exists())

    def test_capture_is_exclusive_and_deterministic(self):
        second = self.root/'second'
        self.module.capture(ROOT, second, {
            PATCH_REVISION: {'docs/PORTING_LEDGER.md', 'init/main.c'},
        })
        for path in self.directory.iterdir():
            self.assertEqual(path.read_bytes(), (second/path.name).read_bytes())
        before = (self.directory/'MANIFEST.json').read_bytes()
        with self.assertRaises(ValueError):
            self.module.capture(ROOT, self.directory, {PATCH_REVISION: {'init/main.c'}})
        self.assertEqual((self.directory/'MANIFEST.json').read_bytes(), before)


class TraceHistory(unittest.TestCase):
    def setUp(self):
        self.module = load('history_inputs')
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-trace-history-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT/self.module.INPUTS, self.root/self.module.INPUTS)
        self.manifest = self.root/self.module.INPUTS/'MANIFEST.json'

    def test_last_payload_change_is_proven_without_the_git_graph(self):
        history = self.module.History(self.root, allow_git=False)
        for path in ('tests/golden/boot.trace', 'tests/golden/boot.jsonl'):
            self.assertEqual(history.last_change(self.module.TRACES, path),
                             '1ccb77fef673bcd8e64fed40ee99998692377a89')

    def test_relabeling_last_change_does_not_change_the_proven_result(self):
        value = json.loads(self.manifest.read_text())
        value['path_histories'][0]['last_change'] = '0'*40
        self.manifest.write_text(json.dumps(value)+'\n')
        with self.assertRaisesRegex(ValueError, 'last-change identity'):
            self.module.History(self.root, allow_git=False).last_change(
                self.module.TRACES, value['path_histories'][0]['path'])

    def test_path_history_objects_are_hash_checked(self):
        value = json.loads(self.manifest.read_text())
        proof = value['path_histories'][0]
        proof['objects'][self.module.TRACES]['data_b64'] = 'WA=='
        self.manifest.write_text(json.dumps(value)+'\n')
        with self.assertRaisesRegex(ValueError, 'object identity'):
            self.module.History(self.root, allow_git=False).last_change(
                self.module.TRACES, proof['path'])


class CleanSource(unittest.TestCase):
    def setUp(self):
        self.module = load('source_snapshot')
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-source-export-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.root = self.work/'project'
        self.root.mkdir()
        (self.root/'main.c').write_text('/* SYNTHETIC public source */\n')
        (self.root/'.gitignore').write_text('.local/\nAGENTS.md\nbuild/\nstate/\nrelease/\n')
        for name in ('.local', 'build', 'state', 'release'):
            (self.root/name).mkdir()
            (self.root/name/'private-fixture').write_text('SYNTHETIC private material')
        (self.root/'AGENTS.md').write_text('SYNTHETIC private instructions')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', 'add', '--', 'main.c', '.gitignore'], cwd=self.root, check=True)

    def test_export_contains_only_explicit_public_inputs_and_reverifies_without_git(self):
        destination = self.work/'export'
        manifest = self.module.freeze(self.root, destination)
        self.assertEqual({p.name for p in destination.iterdir()},
                         {'main.c', '.gitignore', 'SOURCE-SNAPSHOT.json'})
        self.assertEqual(self.module.verify(destination)['source_id'], manifest['source_id'])
        self.assertEqual(set(self.module.public_paths(destination)), {'main.c', '.gitignore'})
        self.assertEqual((destination/'main.c').read_bytes(), (self.root/'main.c').read_bytes())

    def test_no_clobber_and_no_output_inside_source(self):
        destination = self.work/'existing'
        destination.mkdir()
        (destination/'owned').write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.module.freeze(self.root, destination)
        self.assertEqual((destination/'owned').read_bytes(), b'keep')
        with self.assertRaises(ValueError):
            self.module.freeze(self.root, self.root/'nested-export')
        self.assertFalse((self.root/'nested-export').exists())

    def test_mutation_and_extra_public_members_fail_closed(self):
        destination = self.work/'export'
        self.module.freeze(self.root, destination)
        (destination/'extra.txt').write_text('unlisted')
        with self.assertRaises(ValueError):
            self.module.verify(destination)
        (destination/'extra.txt').unlink()
        (destination/'main.c').write_text('modified')
        with self.assertRaises(ValueError):
            self.module.verify(destination)

    def test_symlink_and_tracked_private_paths_are_rejected(self):
        (self.root/'link.c').symlink_to(self.root/'main.c')
        with self.assertRaises(ValueError):
            self.module.freeze(self.root, self.work/'bad-link')
        (self.root/'link.c').unlink()
        subprocess.run(['git', 'add', '-f', '--', 'AGENTS.md'], cwd=self.root, check=True)
        with self.assertRaises(ValueError):
            self.module.freeze(self.root, self.work/'bad-private')

    def test_build_outputs_do_not_change_the_frozen_source_identity(self):
        destination = self.work/'export'
        first = self.module.freeze(self.root, destination)
        (destination/'build').mkdir()
        (destination/'build/runtime.log').write_text('SYNTHETIC generated output')
        self.assertEqual(self.module.verify(destination, allow_runtime=True)['source_id'],
                         first['source_id'])
        with self.assertRaises(ValueError):
            self.module.verify(destination)
        second = self.module.freeze(destination, self.work/'second')
        self.assertEqual(first, second)

    def test_project_authorship_inventory_prevents_unreviewed_inputs(self):
        (self.root/'docs').mkdir()
        manifest = self.root/'docs/AUTHORSHIP-MAP.tsv'
        manifest.write_text('path\tcategory\tattribution\tlicense_status\n'
                            '.gitignore\tfixture\tfixture\tfixture\n'
                            'main.c\tfixture\tfixture\tfixture\n'
                            'docs/AUTHORSHIP-MAP.tsv\tfixture\tfixture\tfixture\n')
        subprocess.run(['git', 'add', '--', 'docs/AUTHORSHIP-MAP.tsv'], cwd=self.root, check=True)
        (self.root/'unreviewed.txt').write_text('SYNTHETIC unreviewed input')
        with self.assertRaisesRegex(ValueError, 'reviewed authorship inventory'):
            self.module.freeze(self.root, self.work/'unreviewed-export')
        self.assertFalse((self.work/'unreviewed-export').exists())


class SnapshotDistribution(unittest.TestCase):
    def setUp(self):
        self.module = load('source_snapshot')
        self.checker = load('check-evaluator-package')
        self.temporary = tempfile.TemporaryDirectory(prefix='linux001-distribution-test-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.root = self.work/'synthetic-source'
        (self.root/'scripts').mkdir(parents=True)
        (self.root/'evaluation/v1/licenses').mkdir(parents=True)
        (self.root/'LICENSE').write_text('SYNTHETIC legal fixture, not a release license\n')
        shutil.copy2(ROOT/'scripts/session-image.py', self.root/'scripts/session-image.py')
        for path in self.checker.REQUIRED_EVALUATION:
            target = self.root/path.replace('evaluation/', 'evaluation/v1/', 1)
            target.write_text('SYNTHETIC notice fixture\n')
        (self.root/'.gitignore').write_text('build/\nstate/\nrelease/\n')
        (self.root/'fixture.py').write_text('''import hashlib
from pathlib import Path
root=Path('build');root.mkdir(exist_ok=True)
names=%r
for name in names:
    path=root/name;path.write_text('SYNTHETIC artifact '+name+'\\n')
    path.chmod(0o755 if name in ('bemu-linux01','mkimage','minix-inspect') else 0o644)
manifest=''.join(hashlib.sha256((root/n).read_bytes()).hexdigest()+'  '+n+'\\n' for n in sorted(names))
for name in ('SHA256SUMS','REPRODUCIBLE.sha256'):(root/name).write_text(manifest)
''' % sorted(self.checker.EXPECTED_ARTIFACTS))
        (self.root/'Makefile').write_text('reproducible:\n\tpython3 fixture.py\n')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', 'add', '--', 'LICENSE', '.gitignore', 'fixture.py',
                        'Makefile', 'scripts', 'evaluation'], cwd=self.root, check=True)

    def build(self, directory):
        return self.module.package(self.root, directory, epoch=1700000000,
                                   cc='/usr/bin/gcc', host_cc='/usr/bin/gcc')

    def test_candidate_is_deterministic_self_contained_and_has_no_fabricated_commit(self):
        first = self.build(self.work/'a')
        second = self.build(self.work/'b')
        self.assertEqual(Path(first).read_bytes(), Path(second).read_bytes())
        identity = self.checker.verify_archive(str(first))
        self.assertEqual(identity['format'], 'linux001.snapshot-candidate.v1')
        self.assertNotIn('source_commit', identity)
        self.assertNotIn('history_bundle', identity)
        with tarfile.open(first) as archive:
            names = [m.name for m in archive]
            self.assertFalse(any('/.git/' in n or '/.local/' in n or 'repository.bundle' in n for n in names))
            self.assertTrue(any(n.endswith('/run') for n in names))
            self.assertTrue(any(n.endswith('/source/SOURCE-SNAPSHOT.json') for n in names))
        detached = str(first).removesuffix('.tar.gz')+'.check.py'
        result = subprocess.run(['python3', '-I', detached, '--archive', str(first)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_existing_candidate_outputs_are_not_replaced(self):
        archive = Path(self.build(self.work/'release'))
        before = archive.read_bytes()
        with self.assertRaises(ValueError):
            self.build(self.work/'release')
        self.assertEqual(archive.read_bytes(), before)

    def test_launcher_refuses_invalid_profile_before_creating_state(self):
        archive = self.build(self.work/'release')
        with tarfile.open(archive) as payload:
            payload.extractall(self.work/'unpacked', filter='data')
        package = next((self.work/'unpacked').iterdir())
        result = subprocess.run([str(package/'run'), 'wrong-profile'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((package/'state').exists())

    def test_candidate_rejects_fabricated_history_and_rehashed_notice_drift(self):
        archive = self.build(self.work/'release')
        with tarfile.open(archive) as payload:
            payload.extractall(self.work/'unpacked', filter='data')
        package = next((self.work/'unpacked').iterdir())
        identity_path = package/'ARTIFACT-IDENTITY.json'
        original = identity_path.read_bytes()
        identity = json.loads(original)
        identity['source_commit'] = '0'*40
        identity_path.write_text(json.dumps(identity)+'\n')
        with self.assertRaises(self.checker.PackageError):
            self.checker.verify_directory(str(package))
        identity_path.write_bytes(original)
        (package/'LICENSE').write_text('SYNTHETIC changed duplicated license')
        paths = sorted(self.checker.regular_files(str(package)) - {'SHA256SUMS'})
        (package/'SHA256SUMS').write_text(''.join(
            self.checker.sha256(str(package/p))+'  '+p+'\n' for p in paths))
        with self.assertRaisesRegex(self.checker.PackageError, 'license differs'):
            self.checker.verify_directory(str(package))

    def test_special_unix_mode_bits_are_not_normalized_away_by_verification(self):
        archive = Path(self.build(self.work/'release'))
        tampered = self.work/'tampered'
        tampered.mkdir()
        target = tampered/archive.name
        with tarfile.open(archive) as original, target.open('wb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as output:
                    for member in original:
                        if member.name.count('/') == 1 and member.name.endswith('/README.md'):
                            member.mode |= 0o4000
                        output.addfile(member, original.extractfile(member) if member.isfile() else None)
        checker = Path(str(archive).removesuffix('.tar.gz')+'.check.py')
        shutil.copyfile(checker, tampered/checker.name)
        Path(str(target)+'.sha256').write_text(
            self.checker.sha256(str(target))+'  '+target.name+'\n'
            +self.checker.sha256(str(tampered/checker.name))+'  '+checker.name+'\n')
        with self.assertRaisesRegex(self.checker.PackageError, 'mode'):
            self.checker.verify_archive(str(target))


if __name__ == '__main__':
    unittest.main()
