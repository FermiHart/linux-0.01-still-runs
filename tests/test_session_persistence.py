#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Prove make-run sessions survive a real clean/rebuild in both profiles."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from test_fs_persistence import inspect_payload, fsck_image
from harness_utils import BEMU_PASS_RE, KERNEL_FAULT_RE, sanitize_terminal

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make', default='make')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix='linux001-session-proof-'))
    print('Session lifecycle evidence:', work, flush=True)
    state = work/'state'
    environment = dict(os.environ)
    environment.pop('BUILD', None)
    records = []

    def run(label, targets, script=None):
        command = [args.make, '--no-print-directory', 'NO_COLOR=1',
                   'BUILD=build', 'STATE='+str(state), *targets]
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment,
                                    input=script.encode() if script is not None else None,
                                    stdin=subprocess.DEVNULL if script is None else None,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=args.timeout)
        except subprocess.TimeoutExpired as error:
            (work/(label+'.log')).write_bytes(error.stdout or b'')
            records.append({'command': command, 'status': 'TIMEOUT',
                            'log': label+'.log'})
            (work/'commands.json').write_text(json.dumps(records, indent=2)+'\n')
            raise
        (work/(label+'.log')).write_bytes(result.stdout)
        records.append({'command': command, 'exit_status': result.returncode,
                        'log': label+'.log'})
        (work/'commands.json').write_text(json.dumps(records, indent=2)+'\n')
        if result.returncode:
            raise RuntimeError(f'{label}: command exited {result.returncode}; see retained log')
        return sanitize_terminal(result.stdout)

    payloads = {}
    images = {}
    for profile in ('alive', '1991'):
        payload = 'SESSION_'+profile+'_'+secrets.token_hex(8).upper()
        payloads[profile] = payload
        text = run(profile+'-create', ['run', 'SESSION=qualification', 'EXPERIENCE='+profile],
                   'mkdir /tmp/d01p\n'+f'echo {payload} > /tmp/d01p/proof\nsync\nhalt\n')
        if not BEMU_PASS_RE.search(text) or KERNEL_FAULT_RE.search(text):
            raise RuntimeError(profile+': guest did not finish normally')
        image = state/profile/'qualification.img'
        images[profile] = (image, digest(image), image.stat().st_ino)

    run('clean', ['clean'])
    for image, checksum, inode in images.values():
        if digest(image) != checksum or image.stat().st_ino != inode:
            raise RuntimeError('clean changed a persistent session')
    run('rebuild', ['all', 'build/minix-inspect'])
    for profile, (image, checksum, inode) in images.items():
        if digest(image) != checksum or image.stat().st_ino != inode:
            raise RuntimeError('rebuild replaced a persistent session')
        text = run(profile+'-read', ['run', 'SESSION=qualification', 'EXPERIENCE='+profile],
                   'cat /tmp/d01p/proof\nsync\nhalt\n')
        if payloads[profile] not in text or not BEMU_PASS_RE.search(text):
            raise RuntimeError(profile+': second process did not read persisted payload')
        oracle_args = argparse.Namespace(minix_inspect=str(ROOT/'build/minix-inspect'),
                                         fsck='fsck.minix', timeout=args.timeout)
        inspect_payload(oracle_args, profile, str(image), payloads[profile])
        fsck_image(oracle_args, profile, str(image), str(work/(profile+'.minix')))
    print('PASS: both make-run sessions retain bytes/inodes across clean/rebuild; '
          'fresh KVM processes and two read-only oracles verify the payloads.')


if __name__ == '__main__':
    main()
