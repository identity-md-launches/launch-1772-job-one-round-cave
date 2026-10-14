#!/usr/bin/env python3
"""Verify and compare two portable hash-pinned ZTO observations, offline."""
import argparse
import json
from pathlib import Path
import runpy
import sys

P = runpy.run_path(str(Path(__file__).resolve().parents[1] /
                      'hash-pinned-zto' / 'pinned.py'))


class ComparisonError(ValueError):
    pass


def compare(before, after):
    # Verify both complete transcripts, including their requests, before comparing.
    a, b = P['validate_bundle'](before), P['validate_bundle'](after)
    distance = b['block_number'] - a['block_number']
    same_hash = a['block_hash'].lower() == b['block_hash'].lower()
    if distance < 0:
        raise ComparisonError('after block precedes before block; swap the inputs')
    if distance == 0 and not same_hash:
        raise ComparisonError('conflicting block hashes at the same height')
    if distance != 0 and same_hash:
        raise ComparisonError('one block hash is associated with different heights')
    if a['decimals'] != b['decimals']:
        raise ComparisonError('token decimals changed; amounts are not comparable')
    delta = int(b['total_supply_raw']) - int(a['total_supply_raw'])
    if distance == 0 and delta:
        raise ComparisonError('conflicting supply observations for the same block')
    places = a['decimals']
    digits = str(abs(delta)).rjust(places + 1, '0')
    human = digits if places == 0 else digits[:-places] + '.' + digits[-places:]
    if delta < 0:
        human = '-' + human
    return {
        'schema': 'line1-zto-snapshot-comparison-v1',
        'chain_id': 1, 'zto_address': a['zto_address'],
        'before': a, 'after': b, 'block_distance': distance,
        'same_block': distance == 0,
        'supply_changed': delta != 0, 'supply_delta_raw': str(delta),
        'supply_delta_tokens': human, 'decimals': places,
        'before_bundle_sha256': P['digest'](before),
        'after_bundle_sha256': P['digest'](after),
        'evidence': 'Validated provider observations, not a state or ancestry proof; '
                    'timestamps do not establish ordering or freshness.'}


def load(path):
    return P['B']['parse_json'](P['SAFE']['read_bytes'](path, P['MAX_BYTES']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before', help='earlier hash-pinned bundle, visible workspace path')
    parser.add_argument('after', help='later hash-pinned bundle, visible workspace path')
    args = parser.parse_args(argv)
    try:
        result = compare(load(args.before), load(args.after))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, P['B']['SnapshotError'], RecursionError) as exc:
        print('compare-zto-snapshots: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
