#!/usr/bin/env python3
"""Offline JSON contracts with bounded, no-follow workspace file reads (POSIX)."""
import argparse
import json
import math
import os
import stat
import sys
import types
from pathlib import Path

MAX_BYTES = 1_000_000


def read_bytes(name, limit=MAX_BYTES):
    """Traverse relative paths by directory descriptors; never follow symlinks."""
    if not isinstance(name, str) or not name or name.startswith('/'):
        raise ValueError('input must be a relative workspace path')
    parts = name.split('/')
    if any(not p or p.startswith('.') for p in parts):
        raise ValueError('empty, hidden and parent path components are refused')
    if type(limit) is not int or not 0 <= limit <= MAX_BYTES:
        raise ValueError('invalid byte limit')
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'):
        raise ValueError('POSIX no-follow directory reads are required')
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    file_fd = None
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=directory)
        metadata = os.fstat(file_fd)
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError('input must be a regular file')
        if metadata.st_size > limit:
            raise ValueError(f'input exceeds {limit} bytes')
        chunks = []
        remaining = limit + 1
        while remaining:
            block = os.read(file_fd, min(65536, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        data = b''.join(chunks)
        if len(data) > limit:
            raise ValueError(f'input exceeds {limit} bytes')
        return data
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(directory)


def load(name):
    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError('duplicate JSON property: ' + key)
            result[key] = value
        return result

    def finite(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('JSON number must be finite')
        return value

    def reject(text):
        raise ValueError('invalid JSON constant: ' + text)

    return json.loads(read_bytes(name).decode('utf-8'), object_pairs_hook=pairs,
                      parse_float=finite, parse_constant=reject)


def engine_module():
    # The sibling source is trusted code; use the same file boundary to load it.
    source = Path(__file__).absolute().parent.parent / 'json-contract' / 'check.py'
    try:
        relative = source.relative_to(Path.cwd()).as_posix()
    except ValueError:
        raise ValueError('run inside a workspace containing both tool folders')
    module = types.ModuleType('bounded_json_contract_engine')
    module.__file__ = str(source)
    exec(compile(read_bytes(relative), str(source), 'exec'), module.__dict__)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='trusted contract, relative workspace path')
    parser.add_argument('documents', nargs='+', help='relative workspace JSON paths')
    args = parser.parse_args(argv)
    if len(args.documents) > 256:
        print(json.dumps({'error': 'at most 256 documents per invocation'}))
        return 2
    try:
        engine = engine_module()
        contract = engine.prepare(load(args.contract))
        rows = []
        failed = unreadable = 0
        for name in args.documents:
            try:
                errors = engine.validate(load(name), contract)
                failed += bool(errors)
                rows.append({'file': name, 'valid': not errors, 'errors': errors})
            except (ValueError, OSError, RecursionError) as exc:
                unreadable += 1
                rows.append({'file': name, 'valid': False, 'errors': [], 'error': str(exc)})
        print(json.dumps({'valid': not (failed or unreadable),
                          'summary': {'checked': len(rows),
                                      'passed': len(rows) - failed - unreadable,
                                      'failed': failed, 'unreadable': unreadable},
                          'files': rows}, indent=2))
        return 2 if unreadable else (1 if failed else 0)
    except (ValueError, OSError, RecursionError) as exc:
        print(json.dumps({'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
