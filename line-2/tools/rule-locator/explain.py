#!/usr/bin/env python3
"""Locate JSON violations in both the document and its explicit contract, offline."""
import argparse
import json
from pathlib import Path
import sys
import types


def bounded_module():
    # Bootstrap only the fixed, trusted sibling; user inputs use its no-follow reader.
    source = Path(__file__).absolute().parent.parent / 'bounded-contract' / 'check.py'
    relative = source.relative_to(Path.cwd()).as_posix()
    if any(not p or p.startswith('.') for p in relative.split('/')):
        raise ValueError('run inside the workspace containing the sibling tools')
    # Open each component without following links, including the trusted bootstrap.
    import os
    import stat
    directory = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaf = None
    try:
        parts = relative.split('/')
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=directory)
        if not stat.S_ISREG(os.fstat(leaf).st_mode):
            raise ValueError('trusted sibling must be a regular file')
        chunks, remaining = [], 1_000_001
        while remaining:
            chunk = os.read(leaf, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        code = b''.join(chunks)
        if len(code) > 1_000_000:
            raise ValueError('trusted sibling exceeds byte limit')
    finally:
        if leaf is not None:
            os.close(leaf)
        os.close(directory)
    module = types.ModuleType('repair_bounded_contract')
    module.__file__ = str(source)
    exec(compile(code, str(source), 'exec'), module.__dict__)
    return module



MISSING = object()
PREVIEW_CHARS = 160


def tokens(pointer):
    if pointer == '':
        return []
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('invalid JSON Pointer')
    parts = pointer[1:].split('/')
    for part in parts:
        i = 0
        while i < len(part):
            if part[i] == '~':
                if i + 1 == len(part) or part[i+1] not in '01':
                    raise ValueError('invalid JSON Pointer escape')
                i += 1
            i += 1
    return [part.replace('~1', '/').replace('~0', '~') for part in parts]


def at(value, pointer):
    """Resolve an engine pointer; absence is distinct from JSON null."""
    for part in tokens(pointer):
        if isinstance(value, dict):
            if part not in value:
                return MISSING
            value = value[part]
        elif isinstance(value, list):
            if not part.isascii() or not part.isdecimal() or str(int(part)) != part:
                raise ValueError('invalid array index in JSON Pointer')
            index = int(part)
            if index >= len(value):
                return MISSING
            value = value[index]
        else:
            raise ValueError('JSON Pointer traverses a scalar')
    return value


def describe(value):
    """Bound each value preview, never silently truncate the diagnostic list."""
    if value is MISSING:
        return {'present': False}
    kind = {dict: 'object', list: 'array', str: 'string', int: 'integer',
            float: 'number', bool: 'boolean', type(None): 'null'}[type(value)]
    result = {'present': True, 'type': kind}
    if isinstance(value, (str, list, dict)):
        result['length'] = len(value)
    # iterencode avoids building a full serialization of a large container.
    chunks, size = [], 0
    for chunk in json.JSONEncoder(ensure_ascii=True, allow_nan=False,
                                  separators=(',', ':')).iterencode(value):
        room = PREVIEW_CHARS + 1 - size
        chunks.append(chunk[:room])
        size += min(len(chunk), room)
        if size > PREVIEW_CHARS:
            break
    encoded = ''.join(chunks)
    result['preview'] = encoded[:PREVIEW_CHARS]
    result['truncated'] = len(encoded) > PREVIEW_CHARS
    return result


def rule_pointer(engine, contract, error):
    """Find the actual rule, including parent rules and prefix/tail array rules."""
    parts = tokens(error['path'])
    rule = error['rule']
    parent_rule = rule in ('required', 'additionalProperties', 'uniqueItems')
    if parent_rule and not parts:
        raise ValueError('parent rule diagnostic has no child path')
    walk = parts[:-1] if parent_rule else parts
    node, location = contract, ''
    for part in walk:
        if node['type'] == 'object':
            node = node['properties'][part]
            location = engine.pointer(engine.pointer(location, 'properties'), part)
        elif node['type'] == 'array':
            index = int(part)
            prefix = node.get('prefixItems', [])
            if index < len(prefix):
                node = prefix[index]
                location = engine.pointer(engine.pointer(location, 'prefixItems'), index)
            else:
                node = node['items']
                location = engine.pointer(location, 'items')
        else:
            raise ValueError('diagnostic descends through a scalar contract')
    location = engine.pointer(location, rule)
    if rule == 'required':
        location = engine.pointer(location, node['required'].index(parts[-1]))
    if at(contract, location) is MISSING:
        raise ValueError('diagnostic does not resolve to a contract rule')
    return location


def explain(engine, contract, document):
    # The existing engine alone decides validity, order and diagnostic multiplicity.
    engine.prepare(contract)
    errors = engine.validate(document, contract)
    detailed = []
    for error in errors:
        location = rule_pointer(engine, contract, error)
        detailed.append({**error, 'contract_path': location,
                         'constraint': describe(at(contract, location)),
                         'observed': describe(at(document, error['path']))})
    return {'valid': not errors, 'error_count': len(errors), 'errors': detailed}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', help='trusted structural contract, relative workspace path')
    parser.add_argument('document', help='JSON document, relative workspace path')
    args = parser.parse_args(argv)
    try:
        bounded = bounded_module()
        engine = bounded.engine_module()
        contract = bounded.load(args.contract)
        document = bounded.load(args.document)
        result = explain(engine, contract, document)
        print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
        return 0 if result['valid'] else 1
    except (ValueError, OSError, RecursionError, KeyError, IndexError) as exc:
        print(json.dumps({'valid': False, 'error': str(exc)}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    sys.exit(main())
