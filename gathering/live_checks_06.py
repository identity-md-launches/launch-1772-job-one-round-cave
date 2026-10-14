#!/usr/bin/env python3
"""One-shot ZTO public read trials, with injectable read-only job transport."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def save(relative, value):
    encoded = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    if len(encoded) > 100000:
        raise ValueError('evidence exceeds deliverable byte limit')
    (ROOT / relative).write_bytes(encoded)


def main(read=None, rpc_factory=None):
    if Path.cwd().resolve() != ROOT:
        raise ValueError('run from repository root')
    pinned = module('gathering_pinned06', 'line-1/tools/hash-pinned-zto/pinned.py')
    comparison = module('gathering_compare06', 'line-1/tools/compare-zto-snapshots/compare.py')
    recheck = module('gathering_recheck06', 'line-3/tools/payment-recheck/recheck.py')
    rows = []
    try:
        bundle, info = pinned.capture(timeout=8, read=read)
        save('gathering/hash-pinned-round06.json', bundle)
        previous = comparison.load('line-1/tools/compare-zto-snapshots/live-zto.json')
        changed = comparison.compare(previous, bundle)
        save('gathering/snapshot-comparison-06.json', changed)
        rows.append({'trial': 'fresh hash-pinned ZTO supply and historical comparison',
                     'exitCode': 0, 'source': pinned.SOURCE, 'result': info,
                     'blockDistance': changed['block_distance'],
                     'supplyDeltaRaw': changed['supply_delta_raw']})
    except (ValueError, OSError, RecursionError):
        rows.append({'trial': 'fresh hash-pinned ZTO supply', 'exitCode': 2,
                     'source': pinned.SOURCE, 'error': 'Read or replay validation failed; no value inferred.'})
    baseline = recheck.w.load_workspace_json('line-3/tools/payment-recheck/current-evidence.json')
    result = recheck.collect(baseline, rpc_factory=rpc_factory or recheck.s.RPC)
    if 'currentSample' in result:
        save('gathering/payment-observation-06.json', result.pop('currentSample'))
    save('gathering/payment-recheck-06.json', result)
    rows.append({'trial': 'fresh single-provider ZTO payment recheck',
                 'exitCode': recheck.exit_code(result), 'source': recheck.s.RPC_URL,
                 'result': result})
    save('gathering/live-check-results-06.json', rows)
    for row in rows:
        print(row['trial'], row['exitCode'])
    return 0 if all(row['exitCode'] == 0 for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
