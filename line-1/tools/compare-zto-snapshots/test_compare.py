"""Offline adversarial checks; mutations are synthetic rejection fixtures only."""
import copy
import contextlib
import io
import json
from pathlib import Path
import runpy
import unittest

C = runpy.run_path(str(Path(__file__).with_name('compare.py')))
P = C['P']
SAMPLE = 'line-1/tools/hash-pinned-zto/live-zto.json'


def reseal(bundle):
    for read in bundle['reads']:
        read['response_sha256'] = P['digest'](read['response'])
    bundle['reads_sha256'] = P['digest'](bundle['reads'])
    return bundle


def later(bundle, delta=0):
    b = copy.deepcopy(bundle)
    number = hex(int(b['reads'][1]['response']['result']['number'], 16) + 1)
    # This fabricated identity is only for unit testing, never saved as evidence.
    new_hash = '0x' + 'ab' * 32
    for index in (1, 4):
        b['reads'][index]['response']['result']['number'] = number
        b['reads'][index]['response']['result']['hash'] = new_hash
    for index in (2, 3):
        b['reads'][index]['params'][1]['blockHash'] = new_hash
    b['reads'][4]['params'][0] = number
    raw = int(b['reads'][2]['response']['result'], 16) + delta
    b['reads'][2]['response']['result'] = '0x' + format(raw, '064x')
    return reseal(b)


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.a = C['load'](SAMPLE)

    def test_real_self_comparison_and_immutability(self):
        original = copy.deepcopy(self.a)
        result = C['compare'](self.a, self.a)
        self.assertEqual(result['supply_delta_raw'], '0')
        self.assertTrue(result['same_block'])
        self.assertEqual(self.a, original)

    def test_later_unchanged(self):
        result = C['compare'](self.a, later(self.a))
        self.assertEqual(result['block_distance'], 1)
        self.assertFalse(result['supply_changed'])

    def test_signed_exact_delta(self):
        for delta, human in [(1, '0.000000000000000001'),
                             (-1, '-0.000000000000000001')]:
            result = C['compare'](self.a, later(self.a, delta))
            self.assertEqual(result['supply_delta_tokens'], human)
            self.assertEqual(result['supply_delta_raw'], str(delta))

    def test_reverse_order(self):
        with self.assertRaises(C['ComparisonError']):
            C['compare'](later(self.a), self.a)

    def test_same_height_hash_conflict(self):
        b = later(self.a)
        for i in (1, 4):
            b['reads'][i]['response']['result']['number'] = self.a['reads'][1]['response']['result']['number']
        b['reads'][4]['params'][0] = self.a['reads'][4]['params'][0]
        with self.assertRaises(C['ComparisonError']):
            C['compare'](self.a, reseal(b))

    def test_hash_reused_at_other_height(self):
        b = later(self.a)
        old = self.a['reads'][1]['response']['result']['hash']
        for i in (1, 4):
            b['reads'][i]['response']['result']['hash'] = old
        for i in (2, 3):
            b['reads'][i]['params'][1]['blockHash'] = old
        with self.assertRaises(C['ComparisonError']):
            C['compare'](self.a, reseal(b))

    def test_same_block_supply_conflict(self):
        b = copy.deepcopy(self.a)
        b['reads'][2]['response']['result'] = '0x' + '00' * 32
        with self.assertRaises(C['ComparisonError']):
            C['compare'](self.a, reseal(b))

    def test_changed_decimals(self):
        b = later(self.a)
        b['reads'][3]['response']['result'] = '0x' + format(6, '064x')
        with self.assertRaises(C['ComparisonError']):
            C['compare'](self.a, reseal(b))

    def test_checksum_and_request_tampering(self):
        for path in ('response', 'params'):
            b = copy.deepcopy(self.a)
            if path == 'response':
                b['reads'][2]['response']['result'] = '0x' + '00' * 32
            else:
                b['reads'][2]['params'][0]['to'] = '0x' + '00' * 20
            with self.assertRaises(ValueError):
                C['compare'](self.a, b)

    def test_cli_and_boundary(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(C['main']([SAMPLE, SAMPLE]), 0)
        self.assertTrue(json.loads(output.getvalue())['same_block'])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(C['main'](['../outside.json', SAMPLE]), 1)

    def test_timestamp_does_not_control_order(self):
        b = later(self.a)
        b['captured_at_utc'] = '2000-01-01T00:00:00+00:00'
        self.assertEqual(C['compare'](self.a, b)['block_distance'], 1)


if __name__ == '__main__':
    unittest.main()
