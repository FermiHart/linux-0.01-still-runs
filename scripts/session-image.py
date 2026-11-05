#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Keep user-owned guest sessions outside the disposable build tree."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile


def regular(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('unsafe session destination or source: '+str(path))
    return info


def digest(path):
    regular(path)
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def copy_new(source, destination):
    """Publish a complete private copy, never replace an existing session."""
    regular(source)
    if destination.exists() or destination.is_symlink():
        regular(destination)
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.session-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as output, source.open('rb') as input_file:
            before = os.fstat(input_file.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('source is not a regular image')
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
            after = os.fstat(input_file.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('source changed during preservation; stop the guest first')
        try:
            os.link(name, destination)
        except FileExistsError:
            regular(destination)
            return False
        sync_directory(destination.parent)
        return True
    finally:
        os.unlink(name)


def outside_build(path, build_root):
    if path.resolve().is_relative_to(build_root.resolve()):
        raise ValueError('persistent state must be outside the build tree')


def preserve(build, state, build_root):
    outside_build(state, build_root)
    for name, profile in (('root.img', 'alive'), ('root-1991.img', '1991')):
        source = build/name
        if not source.exists() and not source.is_symlink():
            continue
        checksum = digest(source)
        receipt = Path(str(source)+'.base-sha256')
        if receipt.is_file() and receipt.read_text().strip() == checksum:
            continue
        recovery = state/'recovered'/f'{name}.{checksum}.img'
        outside_build(recovery, build_root)
        if not recovery.resolve().is_relative_to(state.resolve()):
            raise ValueError('recovery must remain inside the selected state directory')
        copy_new(source, recovery)
        if digest(recovery) != checksum:
            raise ValueError('existing recovery does not match its identity: '+str(recovery))
        session = state/profile/'default.img'
        outside_build(session, build_root)
        if not session.resolve().is_relative_to(state.resolve()):
            raise ValueError('session must remain inside the selected state directory')
        copy_new(recovery, session)
        print('Preserved legacy guest image:', recovery)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument('--preserve-build', type=Path)
    operation.add_argument('--prepare', type=Path)
    operation.add_argument('--mark-base', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        if args.preserve_build:
            preserve(args.preserve_build, args.state_dir, args.build_root)
        elif args.prepare:
            if args.output is None:
                raise ValueError('--prepare requires --output')
            outside_build(args.state_dir, args.build_root)
            outside_build(args.output, args.build_root)
            if not args.output.resolve().is_relative_to(args.state_dir.resolve()):
                raise ValueError('session must be inside the selected state directory')
            if args.output.exists() and os.path.samefile(args.prepare, args.output):
                raise ValueError('session aliases its build-owned base')
            copy_new(args.prepare, args.output)
            print('Persistent guest session:', args.output)
        else:
            checksum = digest(args.mark_base)
            receipt = Path(str(args.mark_base)+'.base-sha256')
            fd, name = tempfile.mkstemp(prefix='.base-identity-', dir=receipt.parent)
            try:
                with os.fdopen(fd, 'w') as stream:
                    stream.write(checksum+'\n')
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, receipt)
                sync_directory(receipt.parent)
            finally:
                if os.path.exists(name):
                    os.unlink(name)
    except (OSError, ValueError) as error:
        parser.exit(1, f'session image refused: {error}\n')


if __name__ == '__main__':
    main()
