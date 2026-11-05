#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Read verified historical inputs without requiring the development Git graph."""
import base64
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
INPUTS = Path('provenance/source-inputs/v1')
PATCH = 'ae458306905d4fee85121ac3c2b42e86ed099310'
COMPILER = '86cc23d776e8c7c49061892b1ec4f93f5fb4ad9c'
ROUND25 = 'e6076cb47fd27e1f6ce1b831852a1efe11de99c0'
TRACES = '14638cf9deb708680a3c58266bb4c71a865355ea'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
MAX_ARCHIVE = 16*1024*1024
MAX_EXPANDED = 64*1024*1024
MAX_FILES = 5000
_codec = None


def codec():
    global _codec
    if _codec is None:
        _codec = runpy.run_path(str(Path(__file__).with_name('check-evaluator-package.py')))
    return _codec


def safe(path):
    return (isinstance(path, str) and codec()['safe_relative'](path)
            and not any(c in path for c in ('\0', '\n', '\r', '\\'))
            and not any(p in ('.git', '.local', 'AGENTS.md') for p in path.split('/')))


def git_environment():
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_ATTR_NOSYSTEM='1', GIT_PAGER='cat', LC_ALL='C')
    return env


def git(root, *args):
    if not (Path(root)/'.git').exists():
        raise ValueError('historical inputs are not retained and this is not a Git checkout')
    return subprocess.check_output(['git', '-C', str(root), *args], env=git_environment())


def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate input-manifest field: '+key)
        result[key] = value
    return result


def tree_entries(root, revision):
    result = {}
    for line in git(root, 'ls-tree', '-rz', '--full-tree', revision).split(b'\0'):
        if not line:
            continue
        metadata, name = line.split(b'\t', 1)
        mode, kind, oid = metadata.decode().split()
        path = name.decode('utf-8')
        if kind != 'blob' or mode not in ('100644', '100755') or not safe(path):
            raise ValueError('unsupported historical source path: '+path)
        result[path] = (mode, oid)
    return result


def path_state(tree, path, read_object):
    parts = path.split('/')
    for index, wanted in enumerate(parts):
        data = read_object('tree', tree)
        at = 0
        found = None
        while at < len(data):
            space, nul = data.find(b' ', at), data.find(b'\0', at)
            if space < at or nul <= space or nul+21 > len(data):
                raise ValueError('invalid retained Git tree encoding')
            mode = data[at:space].decode('ascii')
            name = data[space+1:nul].decode('utf-8')
            oid = data[nul+1:nul+21].hex()
            at = nul+21
            if name == wanted:
                found = (mode, oid)
        if found is None:
            return None
        if index == len(parts)-1:
            return found
        if found[0] != '40000':
            return None
        tree = found[1]
    raise ValueError('empty retained path')


def walk_last_change(revision, path, read_object):
    def state(oid):
        commit = read_object('commit', oid)
        header = commit.split(b'\n\n', 1)[0].splitlines()
        if not header or not header[0].startswith(b'tree '):
            raise ValueError('retained commit lacks its tree')
        tree = header[0][5:].decode('ascii')
        parents = [line[7:].decode('ascii') for line in header if line.startswith(b'parent ')]
        if not HEX40.fullmatch(tree) or any(not HEX40.fullmatch(p) for p in parents) or len(parents) > 1:
            raise ValueError('path history requires an exact linear-parent proof')
        return path_state(tree, path, read_object), parents
    current = revision
    seen = set()
    for _ in range(128):
        if current in seen:
            raise ValueError('cyclic retained path history')
        seen.add(current)
        payload, parents = state(current)
        if not parents or state(parents[0])[0] != payload:
            return current
        current = parents[0]
    raise ValueError('retained path history exceeds its depth bound')


def capture_path_history(root, revision, path, expected):
    objects = {}
    def read_object(kind, oid):
        if oid not in objects:
            data = git(root, 'cat-file', kind, oid)
            objects[oid] = {'type': kind, 'data_b64': base64.b64encode(data).decode()}
        return base64.b64decode(objects[oid]['data_b64'])
    actual = walk_last_change(revision, path, read_object)
    if actual != expected:
        raise ValueError('captured last-change proof differs from the published observation')
    return {'revision': revision, 'path': path, 'last_change': actual, 'objects': objects}


def capture(root, output, requests, from_git=False, histories=()):
    """Capture required bytes and their original identities, never a new commit."""
    root, output = Path(root), Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('historical input destination must be new; existing files are preserved')
    output.mkdir(parents=True)
    records = []
    history = History(root)
    for revision, paths in sorted(requests.items()):
        if not HEX40.fullmatch(revision):
            raise ValueError('input revision must be an exact SHA-1 identity')
        entries = tree_entries(root, revision) if from_git else history.entries(revision)
        commit = git(root, 'cat-file', 'commit', revision) if from_git else history.commit(revision)
        tree = git(root, 'rev-parse', revision+'^{tree}').decode().strip() if from_git else history.tree(revision)
        if codec()['git_tree'](entries) != tree:
            raise ValueError('captured tree identity does not match Git')
        archive = output/(revision+'.tar.gz')
        with archive.open('xb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=9) as zipped:
                with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                    for path in sorted(paths):
                        if not safe(path) or path not in entries:
                            raise ValueError('historical source is absent: '+path)
                        data = git(root, 'show', revision+':'+path) if from_git else history.file(revision, path)
                        if blob(data) != entries[path][1]:
                            raise ValueError('historical blob identity mismatch: '+path)
                        member = tarfile.TarInfo(path)
                        member.mode = 0o755 if entries[path][0] == '100755' else 0o644
                        member.size = len(data)
                        member.mtime = 1700000000
                        tar.addfile(member, io.BytesIO(data))
        archive.chmod(0o644)
        records.append({'revision': revision, 'tree': tree,
                        'commit_object_b64': base64.b64encode(commit).decode(),
                        'entries': [{'path': p, 'mode': m, 'blob': oid}
                                    for p, (m, oid) in sorted(entries.items())],
                        'retained': sorted(paths), 'archive': archive.name,
                        'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    proofs = []
    for revision, path, expected in histories:
        if from_git:
            proofs.append(capture_path_history(root, revision, path, expected))
        else:
            if history.last_change(revision, path) != expected:
                raise ValueError('retained last-change observation mismatch')
            proofs.append(history.path_proof(revision, path))
    manifest = output/'MANIFEST.json'
    with manifest.open('x') as stream:
        json.dump({'format': 'linux001.history-inputs.v1', 'revisions': records, 'path_histories': proofs},
                  stream, indent=2, sort_keys=True)
        stream.write('\n')
    manifest.chmod(0o644)


class History:
    def __init__(self, root=ROOT, allow_git=True):
        self.root = Path(root)
        self.directory = self.root/INPUTS
        self.allow_git = allow_git
        self.cache = {}

    def _record(self, revision):
        if not HEX40.fullmatch(revision):
            raise ValueError('historical revision must be an exact SHA-1 identity')
        if revision in self.cache:
            return self.cache[revision]
        manifest = self.directory/'MANIFEST.json'
        if not manifest.exists():
            if not self.allow_git:
                raise ValueError('historical inputs are not retained')
            return None
        if manifest.is_symlink() or manifest.stat().st_size > 2*1024*1024:
            raise ValueError('unsafe historical input manifest')
        value = json.loads(manifest.read_text(), object_pairs_hook=strict_object)
        if value.get('format') != 'linux001.history-inputs.v1':
            raise ValueError('unsupported historical input format')
        records = value.get('revisions')
        if not isinstance(records, list) or not 1 <= len(records) <= 16:
            raise ValueError('historical revision inventory is invalid')
        matches = [r for r in records if r.get('revision') == revision]
        if len(matches) != 1:
            raise ValueError('historical revision is not retained exactly once: '+revision)
        record = matches[0]
        commit = base64.b64decode(record['commit_object_b64'], validate=True)
        if hashlib.sha1(b'commit '+str(len(commit)).encode()+b'\0'+commit).hexdigest() != revision:
            raise ValueError('historical commit identity mismatch')
        tree = record['tree']
        if not HEX40.fullmatch(tree) or not commit.startswith(('tree '+tree+'\n').encode()):
            raise ValueError('historical commit/tree identity mismatch')
        entries = {}
        if not isinstance(record['entries'], list) or len(record['entries']) > MAX_FILES:
            raise ValueError('historical tree exceeds the inventory bound')
        for entry in record['entries']:
            path, mode, oid = entry['path'], entry['mode'], entry['blob']
            if not safe(path) or mode not in ('100644', '100755') or not HEX40.fullmatch(oid) or path in entries:
                raise ValueError('unsafe or duplicate historical tree entry')
            entries[path] = (mode, oid)
        try:
            computed = codec()['git_tree'](entries)
        except Exception as error:
            raise ValueError('historical tree identity is invalid') from error
        if computed != tree:
            raise ValueError('historical tree identity mismatch')
        retained = record['retained']
        if (not isinstance(retained, list) or len(retained) != len(set(retained))
                or not set(retained) <= set(entries)):
            raise ValueError('invalid retained historical path inventory')
        name = record['archive']
        if name != revision+'.tar.gz':
            raise ValueError('unsafe historical archive location')
        archive = self.directory/name
        if archive.is_symlink() or archive.stat().st_size > MAX_ARCHIVE:
            raise ValueError('unsafe or excessive historical archive')
        raw = archive.read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['archive_sha256']:
            raise ValueError('historical archive checksum mismatch')
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as zipped:
            expanded = zipped.read(MAX_EXPANDED+1)
        if len(expanded) > MAX_EXPANDED:
            raise ValueError('historical archive exceeds the expanded size bound')
        files = {}
        with tarfile.open(fileobj=io.BytesIO(expanded), mode='r:') as tar:
            for member in tar:
                if (len(files) >= MAX_FILES or not safe(member.name) or not member.isfile()
                        or member.issparse() or member.pax_headers or member.name in files):
                    raise ValueError('unsafe or duplicate historical archive member')
                if member.name not in retained:
                    raise ValueError('historical archive has an unlisted file')
                data = tar.extractfile(member).read()
                mode, oid = entries[member.name]
                if blob(data) != oid or member.mode != (0o755 if mode == '100755' else 0o644):
                    raise ValueError('historical blob identity/mode mismatch: '+member.name)
                files[member.name] = data
        if set(files) != set(retained):
            raise ValueError('historical archive is incomplete')
        result = {'tree': tree, 'commit': commit, 'entries': entries, 'files': files}
        self.cache[revision] = result
        return result

    def entries(self, revision, prefix=''):
        record = self._record(revision)
        entries = record['entries'] if record else tree_entries(self.root, revision)
        return {p: v for p, v in entries.items() if p.startswith(prefix)}

    def file(self, revision, path):
        if not safe(path):
            raise ValueError('unsafe historical source path')
        record = self._record(revision)
        if record is None:
            return git(self.root, 'show', revision+':'+path)
        if path not in record['files']:
            raise ValueError('historical file is not retained: '+path)
        return record['files'][path]

    def tree(self, revision):
        record = self._record(revision)
        return record['tree'] if record else git(self.root, 'rev-parse', revision+'^{tree}').decode().strip()

    def commit(self, revision):
        record = self._record(revision)
        return record['commit'] if record else git(self.root, 'cat-file', 'commit', revision)

    def path_proof(self, revision, path):
        value = json.loads((self.directory/'MANIFEST.json').read_text(), object_pairs_hook=strict_object)
        matches = [p for p in value.get('path_histories', []) if p.get('revision') == revision and p.get('path') == path]
        if len(matches) != 1:
            raise ValueError('last-change proof is not retained exactly once')
        return matches[0]

    def last_change(self, revision, path):
        record = self._record(revision)
        if record is None:
            return git(self.root, 'log', '-1', '--format=%H', revision, '--', path).decode().strip()
        if not safe(path) or path not in record['files']:
            raise ValueError('last-change source is not retained')
        proof = self.path_proof(revision, path)
        objects = proof['objects']
        if not isinstance(objects, dict) or not 1 <= len(objects) <= 1000:
            raise ValueError('invalid last-change object inventory')
        cache = {}
        total = 0
        def read_object(kind, oid):
            nonlocal total
            if oid in cache:
                if objects[oid]['type'] != kind:
                    raise ValueError('last-change object type mismatch')
                return cache[oid]
            if oid not in objects or objects[oid].get('type') != kind:
                raise ValueError('last-change proof is incomplete')
            data = base64.b64decode(objects[oid]['data_b64'], validate=True)
            total += len(data)
            if total > 2*1024*1024 or hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).hexdigest() != oid:
                raise ValueError('last-change object identity/size mismatch')
            cache[oid] = data
            return data
        actual = walk_last_change(revision, path, read_object)
        if actual != proof['last_change'] or set(cache) != set(objects):
            raise ValueError('last-change identity or minimal proof inventory mismatch')
        return actual


def requests(root, from_git=False):
    history = History(root)
    patch_entries = tree_entries(root, PATCH) if from_git else history.entries(PATCH)
    patch = {p for p in patch_entries if p.split('/')[0] in ('init', 'kernel', 'mm', 'fs', 'lib', 'include')
             and p.endswith(('.c', '.h', '.s', '.S'))}
    patch.update(('docs/PORTING_LEDGER.md', 'LICENSE'))
    with (Path(root)/'datasets/patches/evidence_links.csv').open(newline='') as stream:
        patch.update(r['reference'] for r in csv.DictReader(stream)
                     if r['reference_kind'] in ('test_source', 'compiler_reduction'))
    compiler = {'tests/compiler-cases/'+name+'.c' for name in
                ('buffer_freelist', 'bitmap_inline_asm', 'vsprintf_percent_s')}
    compiler.add('LICENSE')
    baseline = {p for p in (tree_entries(root, ROUND25) if from_git else history.entries(ROUND25)) if p.startswith('include/')}
    baseline.update(('fs/bitmap.c', 'fs/buffer.c', 'kernel/vsprintf.c', 'fs/fcntl.c',
                     'fs/pipe.c', 'fs/read_write.c', 'kernel/fork.c', 'mm/memory.c',
                     'userland/crt0.S', 'LICENSE'))
    traces = {'tests/golden/boot.trace', 'tests/golden/boot.jsonl', 'LICENSE'}
    return {PATCH: patch, COMPILER: compiler, ROUND25: baseline, TRACES: traces}


def trace_specs(root):
    manifest = json.loads((Path(root)/'datasets/golden-traces/v1/MANIFEST.json').read_text())
    return [(TRACES, capture['source_path_at_publication_commit'], capture['last_payload_commit'])
            for capture in manifest['captures']]


def run_generator(kind, arguments):
    name = 'build-patch-dataset.py' if kind == 'patch' else 'build-compiler-case-dataset.py'
    spec = importlib.util.spec_from_file_location('retained_generator', Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = History(Path(module.REPO_ROOT))
    module.git_bytes = history.file
    if kind == 'patch':
        module.port_snapshot = lambda revision: {
            p: (history.file(revision, p), mode) for p, (mode, _) in history.entries(revision).items()
            if p.split('/')[0] in module.CORE_DIRECTORIES and p.endswith(module.SOURCE_SUFFIXES)}
        original = module.run

        def run(command, cwd=module.REPO_ROOT, text=False):
            if command[:2] == ['git', 'rev-parse']:
                value = command[2]
                revision = value.split('^{', 1)[0]
                result = history.tree(revision) if value.endswith('^{tree}') else (
                    revision if history.entries(revision) else '')
                return result+'\n' if text else (result+'\n').encode()
            return original(command, cwd=cwd, text=text)
        module.run = run
    previous = sys.argv
    try:
        sys.argv = [name, *arguments]
        return module.main()
    finally:
        sys.argv = previous


def main():
    import argparse
    if len(sys.argv) > 1 and sys.argv[1] in ('patch', 'compiler'):
        return run_generator(sys.argv[1], sys.argv[2:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('capture', 'check'))
    parser.add_argument('--output', type=Path, default=ROOT/INPUTS)
    parser.add_argument('--from-git', action='store_true', help='explicitly capture original objects from a full checkout')
    args = parser.parse_args()
    if args.operation == 'capture':
        capture(ROOT, args.output, requests(ROOT, args.from_git), args.from_git, trace_specs(ROOT))
    else:
        history = History(ROOT, allow_git=False)
        for revision in (PATCH, COMPILER, ROUND25, TRACES):
            history.entries(revision)
        for revision, path, expected in trace_specs(ROOT):
            if history.last_change(revision, path) != expected:
                raise ValueError('published last-change identity does not match its retained proof')
        print('PASS: retained historical inputs bind to the original commit/tree/blob identities.')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, tarfile.TarError) as error:
        print('historical input failure:', error, file=sys.stderr)
        sys.exit(1)
