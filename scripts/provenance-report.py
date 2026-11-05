#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Report live historical-source coverage using the pinned dataset contract."""
import argparse
import os
from pathlib import Path
import re
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def live_ledger(contract, text):
    # v1's pinned parser intentionally accepts exactly its original 19 entries.
    # Frame the live ledger here, retaining its canonical field and join rules.
    area = text.split('## Entries', 1)[1].split('## Test traceability', 1)[0]
    headings = list(re.finditer(r'^### (.+)$', area, re.MULTILINE))
    if not headings:
        raise ValueError('ledger has no adaptation entries')
    entries = []
    for index, heading in enumerate(headings):
        end = headings[index+1].start() if index+1 < len(headings) else len(area)
        block = area[heading.end():end]
        fields = {name: contract['field'](block, name) for name in
                  ('Change', 'Files', 'Category', 'Evidence', 'Test', 'Status')}
        title = contract['normalize_title'](heading.group(1))
        identifier = contract['ADAPTATION_IDS'].get(title, 'live-ledger:'+title)
        entries.append({'adaptation_id': identifier, 'files': fields['Files']})
    return entries


def report():
    contract = runpy.run_path(str(ROOT/'scripts/build-patch-dataset.py'))
    if contract['sha256_file'](contract['TARBALL_PATH']) != contract['UPSTREAM_SHA256']:
        raise ValueError('upstream archive SHA-256 mismatch')
    for directory in contract['CORE_DIRECTORIES']:
        for path in (ROOT/directory).rglob('*'):
            if path.is_symlink():
                raise ValueError('source snapshot contains a symlink: '+str(path))
    with tempfile.TemporaryDirectory(prefix='linux001-provenance-') as work:
        upstream = contract['upstream_snapshot'](contract['extract_upstream'](work))
    current = contract['upstream_snapshot'](str(ROOT))
    deltas = []
    lines = [
        'Historical-source provenance: live working-tree bytes',
        'Upstream SHA-256: '+contract['UPSTREAM_SHA256'],
        'Scope: canonical historical-core directories and source suffixes.',
        'Declared path coverage is not semantic attribution, necessity or rights clearance.',
        '',
    ]
    for path in sorted(set(upstream) | set(current)):
        before, after = upstream.get(path), current.get(path)
        if before == after:
            continue
        kind = 'added' if before is None else 'deleted' if after is None else 'modified'
        deltas.append({'path': path, 'change_type': kind, 'delta_id': 'working:'+path})
        checksum = contract['sha256_bytes'](after[0]) if after else '-'
        lines.append(f'{kind.upper()} {path} sha256={checksum}')
    ledger = live_ledger(contract, (ROOT/'docs/PORTING_LEDGER.md').read_text())
    joins = contract['make_join_rows'](ledger, deltas)
    changed = {delta['path'] for delta in deltas}
    unresolved = []
    lines += ['', 'Ledger path coverage (canonical explicit-path/glob rules):']
    for path in sorted(changed):
        relevant = [join for join in joins if join['path'] == path]
        declared = [join for join in relevant if join['adaptation_id']]
        if not declared:
            unresolved.append(path)
            lines.append('UNRESOLVED '+path)
        else:
            exact = any(join['semantic_attribution'] == 'exact' for join in declared)
            identifiers = ','.join(sorted({join['adaptation_id'] for join in declared}))
            lines.append(('EXACT ' if exact else 'BROAD ')+path+' '+identifiers)
    status = 'PARTIAL' if unresolved else 'PATH_COVERAGE_COMPLETE'
    lines += ['', f'{status}: {len(deltas)} source deltas; {len(unresolved)} unresolved paths.',
              'Broad declarations remain broad; this report never promotes them to exact attribution.']
    return '\n'.join(lines)+'\n', bool(unresolved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        text, partial = report()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix='.provenance-', dir=args.output.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, args.output)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print(text.splitlines()[-2])
        print(args.output)
        if partial:
            parser.exit(1)
    except (OSError, ValueError, IndexError, KeyError) as error:
        parser.exit(1, f'provenance failed: {error}\n')


if __name__ == '__main__':
    main()
