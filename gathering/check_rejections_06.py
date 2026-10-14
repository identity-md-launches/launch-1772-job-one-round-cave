#!/usr/bin/env python3
"""Exercise each line's documented rejection path; no inputs are modified."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    commands = [
        ['line-1/tools/compare-zto-snapshots/compare.py',
         'line-1/tools/compare-zto-snapshots/live-zto.json', 'line-1/tools/hash-pinned-zto/live-zto.json'],
        ['line-2/tools/rule-locator/explain.py', 'line-2/tools/json-contract/report.contract.json',
         'line-2/tools/rule-locator/report.invalid.json'],
        ['line-3/tools/payment-recheck/recheck.py', '--baseline',
         'line-3/tools/payment-recheck/current-evidence.json', '--current',
         'line-3/tools/payment-recheck/current-evidence.json'],
        ['line-4/tools/rpc-request-check/rpc_request_check.py',
         'line-4/tools/rpc-request-check/zto-envelope.json',
         'line-4/tools/rpc-request-check/account-mismatch.json', '--summary'],
        ['shared/payment-evidence/revisit.py', 'shared/payment-evidence/round05.paired.json',
         'shared/payment-evidence/round05.paired.json', 'shared/payment-evidence/example.paired-policy.json',
         'shared/payment-evidence/example.revisit-envelope.json',
         'shared/payment-evidence/example.revisit-envelope.json', '--summary'],
    ]
    rows = []
    for args in commands:
        result = subprocess.run([sys.executable, '-B', *args], capture_output=True, text=True, timeout=30)
        rows.append({'command': ['python3', '-B', *args], 'expectedExitCode': 1,
                     'exitCode': result.returncode, 'passed': result.returncode == 1,
                     'stdout': result.stdout, 'stderr': result.stderr})
    Path('gathering/rejection-checks-06.json').write_text(json.dumps(rows, indent=2) + '\n')
    print(json.dumps({'passed': all(row['passed'] for row in rows), 'checks': len(rows)}))
    return 0 if all(row['passed'] for row in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
