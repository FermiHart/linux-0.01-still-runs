#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Freeze and verify explicit public source bytes without shipping Git metadata."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import runpy
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MARKER = 'SOURCE-SNAPSHOT.json'
FORMAT = 'linux001.source-snapshot.v1'
MAX_FILES = 5000
MAX_FILE_BYTES = 16*1024*1024
MAX_SOURCE_BYTES = 64*1024*1024
RUNTIME_DIRS = {'.git', '.local', 'build', 'state', 'release', '__pycache__', '.cache'}
PRIVATE_NAMES = {'AGENTS.md', 'AGENT.MD', '.env', 'id_rsa', 'id_ed25519'}

LAUNCHER = ('#!/bin/sh\n'
            '# Author: F E R M I ∞ H A R T <contact@fermihart.com>\n'
            '# SPDX-License-Identifier: Unlicense\n') + '''set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
profile=${1:-alive}
session=${2:-default}
case "$profile" in
    --help|-h) echo "Usage: ./run [alive|1991] [session-name]"; exit 0 ;;
    alive) base=root.img ;;
    1991) base=root-1991.img ;;
    *) echo "Usage: ./run [alive|1991] [session-name]" >&2; exit 2 ;;
esac
if [ "$#" -gt 2 ]; then echo "Too many arguments" >&2; exit 2; fi
case "$session" in
    ''|*[!A-Za-z0-9_-]*) echo "Use letters, digits, _ or - for the session name" >&2; exit 2 ;;
esac
case "$(uname -s):$(uname -m)" in
    Linux:x86_64) ;;
    *) echo "This candidate requires a Linux x86-64 host" >&2; exit 1 ;;
esac
if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    echo "Usable /dev/kvm is required; ask your administrator for access. No permissions were changed." >&2
    exit 1
fi
python3 "$here/source/scripts/session-image.py" \\
    --build-root "$here/artifacts" --state-dir "$here/state" \\
    --prepare "$here/artifacts/$base" --output "$here/state/$profile/$session.img"
exec "$here/artifacts/bemu-linux01" --kernel "$here/artifacts/kernel.bin" \\
    --root "$here/state/$profile/$session.img" --experience "$profile"
'''

DELIVERY_README = '''# Linux 0.01 — source-bound development candidate

This candidate contains the Linux i386 guest, the Linux x86-64 bEMU runner,
both base-image profiles and their complete corresponding source. It is not the
legacy Limine/QEMU ISO, a modern distribution or an externally evaluated 1.0.

Verify the archive and independent checker with the supplied SHA-256 sidecar
before extracting or running it. The checker can validate the archive without
running the included source or binaries.

On Linux x86-64 with usable /dev/kvm, compatible glibc and Python 3.12+:

    ./run
    ./run 1991
    ./run alive work

The launcher creates a private persistent disk under state/<profile>/<name>.img
once and never replaces an existing session. In the guest, use sync then halt
for an orderly stop. Back up sessions while stopped. Base images in artifacts/
are not your personal disks. No sudo, device chmod or package installation is
performed. Review BUILD-ENVIRONMENT.json for the actual build-host/tool versions;
other host distributions and hardware durability are not qualified by this file.

Build or inspect the complete source from source/ (GCC, binutils, NASM, Make,
Python and test prerequisites are separate build-time requirements):

    cd source
    make all
    make test-host-safety
    make test-fs-persistence

source/SOURCE-SNAPSHOT.json binds the included source bytes. Historic dataset
inputs are retained locally; no old Git checkout or network lookup is needed.
Git is still a host tool for some diff/fixture checks. See source/docs/START.md
and source/docs/REPRODUCTION.md for full checks and acknowledged limits.

Read LICENSE and evaluation/THIRD-PARTY-NOTICES.md. The original Linux 0.01
source/no-fee redistribution terms remain in force; modern and third-party
components retain their own notices. Checksums establish byte consistency, not
independent publisher authentication, rights clearance or runtime confinement.
'''


def admitted(name):
    if not isinstance(name, str):
        return False
    path = Path(name)
    return (name not in ('', '.', MARKER)
            and not path.is_absolute() and str(path) == name and '..' not in path.parts
            and not any(c in name for c in ('\0', '\n', '\r', '\\'))
            and not any(p in RUNTIME_DIRS or p in PRIVATE_NAMES or p.startswith('.env.') for p in path.parts)
            and path.suffix not in ('.pem', '.key', '.p12', '.pfx'))


def regular_bytes(path):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o7000:
        raise ValueError('source member is not a regular safe file: '+str(path))
    if before.st_size > MAX_FILE_BYTES:
        raise ValueError('source member exceeds the size bound: '+str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        data = stream.read(MAX_FILE_BYTES+1)
        after = os.fstat(stream.fileno())
    if len(data) > MAX_FILE_BYTES or (
            before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
        raise ValueError('source changed during snapshot: '+str(path))
    return ('100755' if before.st_mode & 0o111 else '100644'), data


def identity(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate source metadata field: '+key)
        result[key] = value
    return result


def actual_files(root, allow_runtime=False, listed=frozenset()):
    result = set()
    for directory, dirs, files in os.walk(root):
        if allow_runtime:
            dirs[:] = [d for d in dirs if d not in RUNTIME_DIRS]
            files = [f for f in files if f not in PRIVATE_NAMES and not (
                str((Path(directory)/f).relative_to(root)) not in listed
                and Path(f).suffix in ('.o', '.d', '.a', '.bin', '.elf', '.iso', '.pyc', '.tmp', '.log'))]
        for name in dirs:
            if (Path(directory)/name).is_symlink():
                raise ValueError('source directory is a symlink')
        for name in files:
            path = Path(directory)/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('unsupported source member: '+str(path))
            result.add(str(path.relative_to(root)))
    return result


def verify(root, allow_runtime=False):
    root = Path(root).resolve()
    mode, data = regular_bytes(root/MARKER)
    if mode != '100644':
        raise ValueError('source metadata must not be executable')
    manifest = json.loads(data, object_pairs_hook=unique_object)
    if set(manifest) != {'format', 'source_id', 'files'} or manifest['format'] != FORMAT:
        raise ValueError('unsupported source snapshot identity')
    rows = manifest['files']
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_FILES:
        raise ValueError('source inventory exceeds its count bound')
    names = []
    total = 0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'path', 'mode', 'sha256', 'size'}:
            raise ValueError('invalid source inventory record')
        name = row['path']
        if (not admitted(name) or row['mode'] not in ('100644', '100755')
                or not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256'])
                or type(row['size']) is not int or not 0 <= row['size'] <= MAX_FILE_BYTES):
            raise ValueError('unsafe source inventory record')
        names.append(name)
        total += row['size']
        actual_mode, payload = regular_bytes(root/name)
        if (actual_mode != row['mode'] or len(payload) != row['size']
                or hashlib.sha256(payload).hexdigest() != row['sha256']):
            raise ValueError('source snapshot member mismatch: '+name)
    if total > MAX_SOURCE_BYTES or names != sorted(set(names)):
        raise ValueError('source inventory is excessive, duplicated or unordered')
    if manifest['source_id'] != identity(rows):
        raise ValueError('source snapshot identity mismatch')
    if actual_files(root, allow_runtime, set(names)) != set(names) | {MARKER}:
        raise ValueError('source snapshot contains absent or unlisted members')
    return manifest


def public_paths(root):
    root = Path(root).resolve()
    if (root/'.git').exists():
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        raw = subprocess.check_output(
            ['git', '-C', str(root), 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], env=env)
        names = sorted(set(os.fsdecode(p) for p in raw.split(b'\0') if p) - {MARKER})
    else:
        names = [row['path'] for row in verify(root, allow_runtime=True)['files']]
    if len(names) > MAX_FILES or any(not admitted(name) for name in names):
        raise ValueError('public source list contains a private or unsupported path')
    return names


def freeze(source, output):
    source, output = Path(source).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('source output must be new; existing files are never removed')
    if output.resolve().is_relative_to(source):
        raise ValueError('source output must be outside the source tree')
    payloads = {}
    rows = []
    total = 0
    names = public_paths(source)
    reviewed = source/'docs/AUTHORSHIP-MAP.tsv'
    if reviewed.is_file():
        with reviewed.open(newline='') as stream:
            declarations = [row['path'] for row in csv.DictReader(stream, delimiter='\t')]
        if len(declarations) != len(set(declarations)) or set(declarations) != set(names):
            raise ValueError('public inputs differ from the reviewed authorship inventory; run make test-authorship')
    for name in names:
        mode, data = regular_bytes(source/name)
        total += len(data)
        if total > MAX_SOURCE_BYTES:
            raise ValueError('source snapshot exceeds its total size bound')
        payloads[name] = data
        rows.append({'path': name, 'mode': mode, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)})
    if not rows:
        raise ValueError('cannot export an empty source snapshot')
    manifest = {'format': FORMAT, 'source_id': identity(rows), 'files': rows}
    output.mkdir(parents=True)
    for row in rows:
        path = output/row['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(payloads[row['path']])
        path.chmod(0o755 if row['mode'] == '100755' else 0o644)
    with (output/MARKER).open('x') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    (output/MARKER).chmod(0o644)
    verify(output)
    return manifest


def package(source, release, epoch=1700000000, cc='gcc', host_cc='cc'):
    """Build the existing artifact inventory from a fresh, content-bound source."""
    if type(epoch) is not int or not 0 <= epoch <= 8589934591:
        raise ValueError('SOURCE_DATE_EPOCH is outside the ustar timestamp range')
    source, release = Path(source).resolve(), Path(release).resolve()
    checker_path = Path(__file__).with_name('check-evaluator-package.py')
    contract = runpy.run_path(str(checker_path))
    work = Path(tempfile.mkdtemp(prefix='linux001-candidate-build-'))
    complete = False

    def write(path, data, executable=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        path.chmod(0o755 if executable else 0o644)

    def tool(command, arguments):
        executable = shutil.which(command)
        if not executable:
            raise ValueError('required build tool is unavailable: '+command)
        result = subprocess.run([command, *arguments], capture_output=True, text=True, check=True)
        return {'command': Path(command).name,
                'version': result.stdout.splitlines()[0],
                'executable_sha256': contract['sha256'](executable)}

    try:
        frozen = work/'frozen'
        snapshot = freeze(source, frozen)
        source_id = snapshot['source_id']
        name = 'linux-0.01-snapshot-candidate-'+source_id[:12]
        outputs = [release/(name+suffix) for suffix in ('.tar.gz', '.check.py', '.tar.gz.sha256')]
        if any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError('candidate output already exists; existing evidence is never replaced')
        env = {k: v for k, v in os.environ.items()
               if not k.startswith('GIT_') and k not in ('MAKEFLAGS', 'MAKELEVEL', 'MAKEOVERRIDES')}
        env.update(SOURCE_DATE_EPOCH=str(epoch), LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')
        command = ['make', '-j2', 'reproducible', 'BUILD=build', 'CC='+cc, 'HOSTCC='+host_cc]
        with (work/'build.log').open('wb') as log:
            subprocess.run(command, cwd=frozen, env=env, stdin=subprocess.DEVNULL,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        root = work/name
        delivered = freeze(frozen, root/'source')
        if delivered != snapshot:
            raise ValueError('build mutated the declared source inputs')
        artifacts = root/'artifacts'
        artifacts.mkdir()
        for filename in sorted(contract['EXPECTED_ARTIFACTS'] | {'SHA256SUMS', 'REPRODUCIBLE.sha256'}):
            original = frozen/'build'/filename
            info = original.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > 128*1024*1024:
                raise ValueError('unsafe or excessive build output: '+filename)
            shutil.copyfile(original, artifacts/filename)
            (artifacts/filename).chmod(0o755 if filename in ('bemu-linux01', 'mkimage', 'minix-inspect') else 0o644)
        source_entries = {}
        for relative in sorted(actual_files(root/'source')):
            path = root/'source'/relative
            mode = '100755' if path.stat().st_mode & 0o111 else '100644'
            source_entries[relative] = (mode, contract['git_blob'](str(path)))
        lines = ''.join(f'{mode}\t{oid}\t{path}\n' for path, (mode, oid) in source_entries.items())
        write(root/'SOURCE-MANIFEST.tsv', lines.encode())
        artifact_identity = {'format': 'linux001.snapshot-candidate.v1', 'source_id': source_id,
                             'source_tree': contract['git_tree'](source_entries),
                             'source_date_epoch': epoch, 'source_file_count': len(source_entries),
                             'build_manifest': 'artifacts/SHA256SUMS', 'package_manifest': 'SHA256SUMS'}
        write(root/'ARTIFACT-IDENTITY.json', (json.dumps(artifact_identity, indent=2, sort_keys=True)+'\n').encode())
        write(root/'LICENSE', (frozen/'LICENSE').read_bytes())
        for relative in contract['REQUIRED_EVALUATION']:
            original = frozen/relative.replace('evaluation/', 'evaluation/v1/', 1)
            write(root/relative, original.read_bytes())
        write(root/'run', LAUNCHER.encode(), executable=True)
        write(root/'README.md', DELIVERY_README.encode())
        environment = {'system': platform.system(), 'machine': platform.machine(),
                       'libc': list(platform.libc_ver()), 'source_date_epoch': epoch,
                       'cc': tool(cc, ['--version']), 'host_cc': tool(host_cc, ['--version']),
                       'make': tool('make', ['--version']), 'python': platform.python_version()}
        write(root/'BUILD-ENVIRONMENT.json', (json.dumps(environment, indent=2, sort_keys=True)+'\n').encode())
        names = sorted(actual_files(root))
        checksums = ''.join(contract['sha256'](str(root/p))+'  '+p+'\n' for p in names)
        write(root/'SHA256SUMS', checksums.encode())
        for path in [root, *root.rglob('*')]:
            if path.is_dir():
                path.chmod(0o755)
        contract['verify_directory'](str(root))
        archive = work/(name+'.tar.gz')
        with archive.open('xb') as raw:
            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0, compresslevel=9) as zipped:
                with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as tar:
                    paths = [root, *root.rglob('*')]
                    for path in sorted(paths, key=lambda p: str(p.relative_to(work)).encode()):
                        member = tar.gettarinfo(str(path), str(path.relative_to(work)))
                        member.uid = member.gid = 0
                        member.uname = member.gname = ''
                        member.mtime = epoch
                        member.pax_headers = {}
                        if path.is_file():
                            with path.open('rb') as stream:
                                tar.addfile(member, stream)
                        else:
                            tar.addfile(member)
        checker = work/(name+'.check.py')
        shutil.copyfile(checker_path, checker)
        checker.chmod(0o755)
        sidecar = work/(name+'.tar.gz.sha256')
        write(sidecar, (contract['sha256'](str(archive))+'  '+archive.name+'\n'
                        +contract['sha256'](str(checker))+'  '+checker.name+'\n').encode())
        contract['verify_archive'](str(archive))
        subprocess.run([sys.executable, '-I', str(checker), '--archive', str(archive)],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        release.mkdir(parents=True, exist_ok=True)
        for original, destination in zip((archive, checker, sidecar), outputs):
            fd, temporary = tempfile.mkstemp(prefix='.candidate-publish-', dir=release)
            try:
                with os.fdopen(fd, 'wb') as stream, original.open('rb') as input_file:
                    shutil.copyfileobj(input_file, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, 0o755 if destination.suffix == '.py' else 0o644)
                os.link(temporary, destination)
            finally:
                os.unlink(temporary)
        complete = True
        print('PASS: source-bound candidate built and independently checked:', outputs[0])
        return outputs[0]
    except contract['PackageError'] as error:
        raise ValueError('candidate verification failed: '+str(error)) from error
    finally:
        if complete:
            shutil.rmtree(work)
        else:
            print('Candidate build evidence retained at', work, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('export', 'verify', 'package'))
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-runtime', action='store_true')
    parser.add_argument('--release-dir', type=Path, default=ROOT/'release')
    parser.add_argument('--epoch', type=int, default=os.environ.get('SOURCE_DATE_EPOCH', '1700000000'))
    parser.add_argument('--cc', default=os.environ.get('CC', 'gcc'))
    parser.add_argument('--host-cc', default=os.environ.get('HOSTCC', 'cc'))
    args = parser.parse_args()
    try:
        if args.operation == 'export':
            if args.output is None:
                raise ValueError('export requires --output')
            manifest = freeze(args.source, args.output)
        elif args.operation == 'verify':
            manifest = verify(args.source, args.allow_runtime)
        else:
            package(args.source, args.release_dir, args.epoch, args.cc, args.host_cc)
            return
        print(f"PASS: {len(manifest['files'])} source files; source_id={manifest['source_id']}")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'source snapshot refused: {error}\n')


if __name__ == '__main__':
    main()
