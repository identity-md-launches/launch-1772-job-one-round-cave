"""Integration checks; modified observations are in-memory rejection fixtures."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import revisit as r
from corroborate import request_for_pair
from check import load

HERE = Path(__file__).resolve().parent


def inputs():
    names = ('example.paired.json', 'round05.paired.json',
             'example.paired-policy.json', 'example.revisit-envelope.json')
    a, b, p, e = (load(HERE / name) for name in names)
    return a, b, p, e, copy.deepcopy(e)


def request_for(sample, policy, account):
    _, data = request_for_pair(sample, policy)
    return {'method': 'eth_signTypedData_v4',
            'params': [account, json.dumps(data, separators=(',', ':'))]}


class RevisitTests(unittest.TestCase):
    def test_actual_historical_pairs_and_immutability(self):
        args = inputs()
        untouched = copy.deepcopy(args)
        result = r.revisit(*args)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['state'], 'continued')
        self.assertEqual(result['providerRechecks'][0]['alerts'], [])
        self.assertEqual(args, untouched)

    def test_same_heads_reject_even_when_payment_and_envelopes_match(self):
        a, b, p, e, c = inputs()
        result = r.revisit(b, b, p, e, c)
        self.assertFalse(result['accepted'])
        self.assertTrue(result['currentPaymentAndRequestAccepted'])
        self.assertTrue(all(x['alerts'] == ['head_unchanged'] for x in result['providerRechecks']))

    def test_one_provider_cannot_be_dropped(self):
        args = list(inputs())
        args[1]['providers'].pop()
        with self.assertRaises(ValueError): r.revisit(*args)

    def test_one_provider_cannot_remain_at_baseline(self):
        a, b, p, e, _ = inputs()
        b['providers'][1] = copy.deepcopy(a['providers'][1])
        e = request_for(b, p, e['params'][0])
        result = r.revisit(a, b, p, e, e)
        self.assertTrue(result['currentPaymentAndRequestAccepted'])
        self.assertFalse(result['accepted'])
        self.assertEqual(result['providerRechecks'][1]['alerts'], ['head_unchanged'])

    def test_baseline_policy_cannot_be_relaxed(self):
        args = list(inputs())
        args[2]['minimum_raw'] = '1'
        with self.assertRaisesRegex(ValueError, 'policy'): r.revisit(*args)

    def test_structural_policy_error_has_exact_rule_location(self):
        args = list(inputs())
        args[2]['confirmations'] = True
        result = r.revisit(*args)
        self.assertEqual(result['state'], 'policy_error')
        error = result['policyExplanation']['errors'][0]
        self.assertEqual(error['path'], '/confirmations')
        self.assertEqual(error['contract_path'], '/properties/confirmations/type')
        self.assertFalse(result['accepted'])

    def test_account_change_detected_despite_same_digest(self):
        a, b, p, e, c = inputs()
        c['params'][0] = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
        result = r.revisit(a, b, p, e, c)
        self.assertTrue(result['currentPaymentAndRequestAccepted'])
        self.assertTrue(result['envelopeBinding']['digestMatches'])
        self.assertFalse(result['accountAndEncodingMatch'])
        self.assertFalse(result['accepted'])

    def test_reviewed_and_client_changed_together_cannot_change_evidence(self):
        a, b, p, e, _ = inputs()
        data = json.loads(e['params'][1])
        data['message']['minimumRaw'] = '1'
        e['params'][1] = json.dumps(data)
        result = r.revisit(a, b, p, e, e)
        self.assertTrue(result['accountAndEncodingMatch'])
        self.assertFalse(result['currentPaymentAndRequestAccepted'])
        self.assertFalse(result['accepted'])

    def test_same_amount_new_sender_in_both_providers_needs_review(self):
        a, b, p, e, _ = inputs()
        # Public IMD address here is a deliberately altered event sender fixture.
        for provider in b['providers']:
            for read in provider['reads']:
                if read['method'] == 'eth_getTransactionReceipt':
                    for event in read['result']['logs']:
                        if event['address'].lower() == r.recheck.w.TOKENS['ZTO']:
                            event['topics'][1] = '0x' + '0' * 24 + 'd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7'
        e = request_for(b, p, e['params'][0])
        result = r.revisit(a, b, p, e, e)
        self.assertTrue(result['currentPaymentAndRequestAccepted'])
        self.assertFalse(result['accepted'])
        self.assertTrue(all('payment_events_changed' in x['alerts'] for x in result['providerRechecks']))

    def test_false_zero_request_type_and_extra_flags_rejected(self):
        for mode in ('params', 'flag', 'version', 'unused'):
            args = list(inputs())
            if mode == 'params':
                next(x for x in args[1]['providers'][0]['reads']
                     if x['method'] == 'eth_getBlockByNumber')['params'][1] = 0
            if mode == 'flag': args[1]['accepted'] = True
            if mode == 'version': args[1]['version'] = True
            if mode == 'unused': args[1]['providers'][0]['reads'].append(copy.deepcopy(args[1]['providers'][0]['reads'][-1]))
            with self.subTest(mode=mode), self.assertRaises(ValueError): r.revisit(*args)

    def test_transport_ids_ignored_and_case_equivalent(self):
        a, b, p, e, c = inputs()
        c.update(jsonrpc='2.0', id='different transport id')
        c['params'][0] = '0x' + c['params'][0][2:].upper()
        self.assertTrue(r.revisit(a, b, p, e, c)['accepted'])

    def test_unaccepted_baseline_never_becomes_checkpoint(self):
        a, b, p, e, c = inputs()
        for provider in a['providers']:
            for read in provider['reads']:
                if read['method'] == 'eth_getTransactionReceipt': read['result']['status'] = '0x0'
        with self.assertRaises(ValueError): r.revisit(a, b, p, e, c)

    def test_full_summary_and_output_bound(self):
        args = inputs()
        full, summary = r.revisit(*args), r.revisit(*args, summary=True)
        self.assertEqual(full['accepted'], summary['accepted'])
        self.assertNotIn('differences', summary['envelopeBinding'])
        with patch.object(r, 'MAX_OUTPUT_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'output limit'): r.revisit(*args, summary=True)

    def test_cli_accept_reject_and_unsafe_input(self):
        paths = [str((HERE / name).relative_to(Path.cwd())) for name in (
            'example.paired.json', 'round05.paired.json', 'example.paired-policy.json',
            'example.revisit-envelope.json', 'example.revisit-envelope.json')]
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(r.main(paths + ['--summary']), 0)
        paths[0] = paths[1]
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(r.main(paths), 1)
        paths[0] = '../outside.json'
        with contextlib.redirect_stdout(io.StringIO()): self.assertEqual(r.main(paths), 2)


if __name__ == '__main__':
    unittest.main()
