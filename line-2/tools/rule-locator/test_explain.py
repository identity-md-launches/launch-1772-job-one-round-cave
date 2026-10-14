"""Offline regression checks; temporary inputs are confined to test/scratch/."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import types
import unittest

SOURCE = Path('line-2/tools/rule-locator/explain.py')
locator = types.ModuleType('locator_under_test')
locator.__file__ = str(SOURCE.absolute())
exec(compile(SOURCE.read_bytes(), str(SOURCE), 'exec'), locator.__dict__)
bounded = locator.bounded_module()
engine = bounded.engine_module()


class LocatorTests(unittest.TestCase):
    def check(self, contract, document):
        before = copy.deepcopy((contract, document))
        result = locator.explain(engine, contract, document)
        self.assertEqual((contract, document), before)
        original = engine.validate(document, engine.prepare(contract))
        self.assertEqual([{k: e[k] for k in ('path', 'rule', 'message')}
                          for e in result['errors']], original)
        self.assertEqual(result['error_count'], len(original))
        self.assertEqual(result['valid'], not original)
        for error in result['errors']:
            self.assertIsNot(locator.at(contract, error['contract_path']), locator.MISSING)
        return result['errors']

    def test_root_type_and_boolean_distinction(self):
        e = self.check({'type': 'integer'}, True)[0]
        self.assertEqual((e['path'], e['contract_path']), ('', '/type'))
        self.assertEqual(e['observed']['type'], 'boolean')
        self.assertEqual(e['constraint']['preview'], '"integer"')

    def test_missing_null_and_unexpected(self):
        c = {'type': 'object', 'required': ['missing'], 'additionalProperties': False,
             'properties': {'missing': {'type': 'integer'}, 'present': {'type': 'integer'}}}
        errors = self.check(c, {'present': None, 'extra': None})
        self.assertEqual([e['contract_path'] for e in errors],
                         ['/required/0', '/properties/present/type', '/additionalProperties'])
        self.assertEqual(errors[0]['observed'], {'present': False})
        self.assertEqual(errors[1]['observed']['preview'], 'null')
        self.assertTrue(errors[2]['observed']['present'])

    def test_escaped_and_empty_property_names(self):
        for key in ('', '/', '~', 'a/b~c', '~1', '0', 'snowman ☃'):
            c = {'type': 'object', 'properties': {key: {'type': 'integer'}}, 'required': [key]}
            e = self.check(c, {key: 'bad'})[0]
            self.assertEqual(locator.at(c, e['contract_path']), 'integer')
            self.assertEqual(locator.at({key: 'bad'}, e['path']), 'bad')
            self.assertEqual(self.check(c, {})[0]['contract_path'], '/required/0')

    def test_nested_required_rule_is_on_parent(self):
        c = {'type': 'array', 'items': {'type': 'object', 'required': ['a/b'],
                                      'properties': {'a/b': {'type': 'null'}}}}
        e = self.check(c, [{}])[0]
        self.assertEqual((e['path'], e['contract_path']), ('/0/a~1b', '/items/required/0'))

    def test_prefix_and_tail_have_different_rules(self):
        c = {'type': 'array', 'prefixItems': [{'type': 'string', 'minLength': 2}],
             'items': {'type': 'integer', 'minimum': 3}}
        errors = self.check(c, ['x', 2, 'bad'])
        self.assertEqual({e['path']: e['contract_path'] for e in errors},
                         {'/0': '/prefixItems/0/minLength', '/1': '/items/minimum',
                          '/2': '/items/type'})

    def test_unconstrained_tail_and_absent_prefix(self):
        c = {'type': 'array', 'prefixItems': [{'type': 'null'}]}
        self.assertEqual(self.check(c, []), [])
        self.assertEqual(self.check(c, [None, 'anything', {}]), [])

    def test_nested_unique_items_parent_rule(self):
        c = {'type': 'object', 'properties': {'a/b': {'type': 'array', 'uniqueItems': True}}}
        errors = self.check(c, {'a/b': [1, 1.0, True, 1]})
        self.assertEqual([e['path'] for e in errors], ['/a~1b/1', '/a~1b/3'])
        self.assertTrue(all(e['contract_path'] == '/properties/a~1b/uniqueItems' for e in errors))

    def test_all_supported_scalar_and_length_rules(self):
        cases = [({'type': 'number', 'minimum': 2}, 1, 'minimum'),
                 ({'type': 'integer', 'maximum': 2}, 3, 'maximum'),
                 ({'type': 'string', 'minLength': 2}, '', 'minLength'),
                 ({'type': 'string', 'maxLength': 2}, 'abc', 'maxLength'),
                 ({'type': 'string', 'pattern': '^x$'}, 'y', 'pattern'),
                 ({'type': 'string', 'enum': ['x']}, 'y', 'enum'),
                 ({'type': 'array', 'minItems': 2}, [], 'minItems'),
                 ({'type': 'array', 'maxItems': 0}, [1], 'maxItems')]
        for c, value, rule in cases:
            with self.subTest(rule=rule):
                self.assertEqual(self.check(c, value)[0]['contract_path'], '/' + rule)

    def test_nested_array_and_duplicate_complex_values(self):
        c = {'type': 'array', 'prefixItems': [{'type': 'array', 'uniqueItems': True,
              'items': {'type': 'object', 'additionalProperties': False}}]}
        errors = self.check(c, [[{'x': 1}, {'x': 1}]])
        self.assertEqual({e['contract_path'] for e in errors},
                         {'/prefixItems/0/uniqueItems', '/prefixItems/0/items/additionalProperties'})

    def test_long_previews_do_not_remove_errors(self):
        c = {'type': 'array', 'items': {'type': 'string', 'maxLength': 1}}
        errors = self.check(c, ['☃' * 500, 'x' * 500])
        self.assertEqual(len(errors), 2)
        for error in errors:
            self.assertEqual(len(error['observed']['preview']), 160)
            self.assertTrue(error['observed']['truncated'])
        for length, truncated in ((157, False), (158, False), (159, True)):
            self.assertEqual(locator.describe('a' * length)['truncated'], truncated)

    def test_preview_controls_are_escaped(self):
        d = locator.describe('\n\t\x1b☃')
        self.assertEqual(json.loads(d['preview']), '\n\t\x1b☃')
        self.assertTrue(d['preview'].isascii())
        self.assertNotIn('\n', d['preview'])

    def test_strict_pointer_resolution(self):
        self.assertIs(locator.at({}, '/absent'), locator.MISSING)
        for pointer in ('x', '/~', '/~2'):
            with self.assertRaises(ValueError):
                locator.tokens(pointer)
        for pointer in ('/01', '/-1', '/-', '/١'):
            with self.assertRaises(ValueError):
                locator.at([0, 1], pointer)
        self.assertEqual(locator.at({'01': True}, '/01'), True)

    def test_no_mutation_and_invalid_contract_refused(self):
        with self.assertRaises(ValueError):
            locator.explain(engine, {'type': 'integer', 'minimun': 1}, 0)
        self.assertEqual(self.check({'type': 'null'}, None), [])

    def test_real_saved_swarm_contract_and_zto_policy(self):
        contract = bounded.load('shared/payment-evidence/policy.contract.json')
        document = bounded.load('shared/payment-evidence/example.policy.json')
        self.assertEqual(self.check(contract, document), [])
        # In-memory damage is a rejection fixture, not a chain observation.
        damaged = dict(document, unexpected=True)
        errors = self.check(contract, damaged)
        self.assertEqual(errors[0]['contract_path'], '/additionalProperties')

    def test_cli_codes_and_input_boundaries(self):
        Path('test/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir='test/scratch') as directory:
            root = Path(directory)
            if root.is_absolute():
                root = root.relative_to(Path.cwd())
            contract = root / 'contract.json'
            document = root / 'document.json'
            contract.write_text('{"type":"integer"}')
            def run(name):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = locator.main([str(contract), str(name)])
                return code, json.loads(out.getvalue())
            document.write_text('1')
            self.assertEqual(run(document)[0], 0)
            document.write_text('true')
            self.assertEqual(run(document)[0], 1)
            for content in ('{', '{"x":1,"x":2}', 'NaN', '1e9999'):
                document.write_text(content)
                code, result = run(document)
                self.assertEqual(code, 2)
                self.assertFalse(result['valid'])
                self.assertNotIn('errors', result)
            link = root / 'link.json'
            link.symlink_to('document.json')
            for name in (link, '/outside.json', '../outside.json', '.hidden.json'):
                self.assertEqual(run(name)[0], 2)
            document.write_bytes(b' ' * 1_000_001)
            self.assertEqual(run(document)[0], 2)
            contract.write_text('{"type":"integer","bad":true}')
            document.write_text('1')
            self.assertEqual(run(document)[0], 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
