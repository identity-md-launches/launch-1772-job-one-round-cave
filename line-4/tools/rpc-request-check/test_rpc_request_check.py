import copy
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from rpc_request_check import check, main, unpack
from typed_digest import TypedDataError

ROOT = Path(__file__).parent
EXAMPLE = json.loads((ROOT / 'zto-envelope.json').read_text())


class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.client = copy.deepcopy(EXAMPLE)

    def test_historical_digest(self):
        r = check(EXAMPLE, self.client)
        self.assertTrue(r['accepted'])
        self.assertEqual(r['client']['digest'], '0xf33e2506e5c103f98dbfe3feb6d4b87d55f1fad4e423dbaa8462465ff4ab9774')

    def test_public_account_not_in_digest(self):
        self.client['params'][0] = '0xd782bdea4ef02a0bd391eb9089470c8080f0a68e'
        r = check(EXAMPLE, self.client)
        self.assertTrue(r['digestMatches'])
        self.assertFalse(r['accountMatches'])
        self.assertFalse(r['accepted'])

    def test_case_equivalence(self):
        self.client['params'][0] = '0x' + self.client['params'][0][2:].upper()
        self.assertTrue(check(EXAMPLE, self.client)['accepted'])

    def test_amount_change(self):
        d = json.loads(self.client['params'][1])
        d['message']['minimumRaw'] = str(int(d['message']['minimumRaw']) + 1)
        self.client['params'][1] = json.dumps(d)
        r = check(EXAMPLE, self.client)
        self.assertFalse(r['accepted'])
        self.assertEqual(r['differenceCount'], 2)

    def test_transport_metadata(self):
        self.client.update(jsonrpc='2.0', id=73)
        self.assertTrue(check(EXAMPLE, self.client)['accepted'])
        self.client['id'] = 'another request'
        self.assertTrue(check(EXAMPLE, self.client)['accepted'])

    def test_reject_methods(self):
        for method in ['personal_sign', 'eth_sign', 'eth_signTypedData', 'eth_signTypedData_v3', 'eth_sendTransaction']:
            with self.subTest(method=method), self.assertRaises(TypedDataError):
                unpack({**self.client, 'method': method})

    def test_reject_params(self):
        for params in [[], self.client['params'] + [None], list(reversed(self.client['params'])),
                       [self.client['params'][0], json.loads(self.client['params'][1])],
                       [self.client['params'][0], 'null'], [self.client['params'][0], '[]']]:
            with self.subTest(params=params), self.assertRaises(ValueError):
                check(EXAMPLE, {**self.client, 'params': params})

    def test_reject_wrapper(self):
        for wrapper in [[self.client], {**self.client, 'extra': True},
                        {**self.client, 'id': 1}, {**self.client, 'jsonrpc': '2.0'},
                        {**self.client, 'jsonrpc': '1.0', 'id': 1},
                        {**self.client, 'jsonrpc': '2.0', 'id': True},
                        {**self.client, 'jsonrpc': '2.0', 'id': None}]:
            with self.subTest(wrapper=wrapper), self.assertRaises(TypedDataError):
                unpack(wrapper)

    def test_duplicate_nested_keys(self):
        self.client['params'][1] = '{"types":{},"types":{}}'
        with self.assertRaisesRegex(TypedDataError, 'duplicate'):
            unpack(self.client)

    def test_nested_float(self):
        self.client['params'][1] = '{"value":1.5}'
        with self.assertRaises(TypedDataError):
            unpack(self.client)

    def test_bounds(self):
        for text in [' ' * 65537, '[' * 49 + '0' + ']' * 49, '"\\ud800"']:
            self.client['params'][1] = text
            with self.assertRaises(ValueError):
                unpack(self.client)

    def test_cyclic_api(self):
        self.client['params'].append(self.client)
        with self.assertRaises(TypedDataError):
            unpack(self.client)

    def test_input_unchanged(self):
        original = copy.deepcopy(EXAMPLE)
        check(EXAMPLE, self.client)
        self.assertEqual(EXAMPLE, original)

    def test_cli_match_summary(self):
        path = str(ROOT / 'zto-envelope.json')
        for options in [[], ['--summary']]:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([path, path] + options), 0)
            r = json.loads(output.getvalue())
            self.assertTrue(r['accepted'])
            self.assertEqual('differences' in r, not bool(options))

    def test_cli_rejection(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(ROOT / 'zto-envelope.json'),
                                   str(ROOT / 'account-mismatch.json')]), 1)

    def test_cli_invalid_path(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['../outside.json', str(ROOT / 'zto-envelope.json')]), 2)

    def test_complete_report_cap(self):
        with patch('rpc_request_check.MAX_REPORT_BYTES', 100):
            with self.assertRaisesRegex(TypedDataError, 'report limit'):
                check(EXAMPLE, self.client)


if __name__ == '__main__':
    unittest.main()
