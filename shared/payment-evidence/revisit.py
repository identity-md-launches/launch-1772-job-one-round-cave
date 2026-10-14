#!/usr/bin/env python3
"""Revisit paired payment evidence and compare captured client requests offline."""
import argparse
import json
from pathlib import Path
import sys

from corroborate import corroborate, request_for_pair, MAX_OUTPUT_BYTES
from check import contracts, load, module, typed

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
import rpc_request_check as envelope

recheck = module('revisit_checkpoint', 'vendor/payment-recheck/recheck.py')
locator = module('revisit_rule_locator', 'vendor/rule-locator/explain.py')


def revisit(baseline, current, policy, intended, client, summary=False):
    """Require progress from EACH provider, current agreement and exact binding.

    Policy and intended envelope are independent caller inputs. Neither current
    evidence nor a saved acceptance flag can approve a policy or public account.
    """
    for value in (baseline, current, policy, intended, client):
        typed.validate_tree(value)
    explanation = locator.explain(contracts, load(
        Path(__file__).resolve().parent / 'policy.contract.json'), policy)
    if not explanation['valid']:
        return {'accepted': False, 'state': 'policy_error', 'policyExplanation': explanation}
    before, _ = request_for_pair(baseline, policy)
    if before['accepted'] is not True:
        raise ValueError('baseline must have two agreeing, accepted payment observations')
    # Parsing and comparing never invokes the captured method. No transport exists.
    _, intended_data, _ = envelope.unpack(intended)
    _, client_data, _ = envelope.unpack(client)
    client_binding = envelope.check(intended, client)
    current_binding = corroborate(current, policy, intended_data, client_data, summary)
    changes = []
    for old, new in zip(baseline['providers'], current['providers']):
        # Both request_for_pair calls enforce exact provider count, source/order,
        # structures and independently supplied policy before this zip is used.
        single_old = {'version': 1, 'policy': policy, 'reads': old['reads']}
        single_new = {'version': 1, 'policy': policy, 'reads': new['reads']}
        change = recheck.compare(single_old, single_new)
        changes.append({'source': old['source'], **change})
    continued = all(item['accepted'] is True for item in changes)
    accepted = continued and current_binding['accepted'] and client_binding['accepted']
    result = {
        'accepted': accepted, 'state': 'continued' if accepted else 'review_required',
        'bothProvidersAdvancedWithoutAlerts': continued,
        'currentPaymentAndRequestAccepted': current_binding['accepted'],
        'accountAndEncodingMatch': client_binding['accepted'],
        'providerRechecks': changes, 'currentBinding': current_binding,
        'envelopeBinding': client_binding, 'policyExplanation': explanation,
        'evidenceMode': 'offline historical observations; source labels are unauthenticated',
        'authorization': 'Captured request bytes only; no account ownership, consent, signing or sending.',
        'evidenceLimit': 'Height progress is not wall-clock freshness, consensus proof or independent provider ownership.'}
    # Bound the complete result before summary removes diagnostics.
    if len(json.dumps(result, ensure_ascii=True, indent=2).encode()) > MAX_OUTPUT_BYTES:
        raise ValueError('revisit exceeds 100000-byte output limit')
    if summary:
        result['envelopeBinding'].pop('differences', None)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', help='previous accepted paired transcript')
    parser.add_argument('current', help='new paired transcript; both heads must advance')
    parser.add_argument('policy', help='independently chosen policy, unchanged in both pairs')
    parser.add_argument('intended', help='independently reviewed captured-request envelope')
    parser.add_argument('client', help='actual captured-request envelope; never dispatched')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = revisit(*(load(getattr(args, name)) for name in
                           ('baseline', 'current', 'policy', 'intended', 'client')), args.summary)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0 if result['accepted'] else 2 if result['state'] == 'policy_error' else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({'accepted': False, 'state': 'input_error', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
