"""Regression checks for the application extraction, independent of publisher data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_policy_review import temporary
from test_framework_updates import fixture
from policycompass import corpus, documents, packages, updates
from policycompass.config import setting


class StandaloneTests(unittest.TestCase):
    def test_cli_version_and_core_import_without_wacc(self):
        result = subprocess.run([sys.executable, '-m', 'policycompass', '--version'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('PolicyCompass '))
        from framework_core.build import build
        library, _ = build(False, source_root=ROOT/'absent-sources',
                           corpus_root=ROOT/'absent-corpus', framework_keys=['ism'])
        self.assertIn('ism', library.frameworks)
        self.assertNotIn('wacc', sys.modules)

    def test_assets_resolve_in_the_application_package(self):
        self.assertTrue(corpus.training_rules())
        self.assertEqual(json.loads(packages.TRUST_FILE.read_text())['keys'], {})
        from policycompass.wa_parser import parse
        self.assertTrue(callable(parse))

    def test_configuration_precedence_and_separate_cache(self):
        with patch.dict(os.environ, {}, clear=True), patch('pathlib.Path.home', return_value=ROOT):
            self.assertEqual(setting('LIBRARY', 'fallback'), 'fallback')
            self.assertEqual(updates.cache_root().parts[-2:], ('PolicyCompass', 'frameworks'))
            self.assertEqual(packages.installation_root().parts[-2:], ('PolicyCompass', 'corpus'))
        with patch.dict(os.environ, {'WACC_LIBRARY': 'legacy'}, clear=True):
            self.assertEqual(setting('LIBRARY', 'fallback'), 'legacy')
            with patch.dict(os.environ, {'POLICYCOMPASS_LIBRARY': 'new'}):
                self.assertEqual(setting('LIBRARY', 'fallback'), 'new')

    def test_renamed_extraction_worker_preserves_source_locator(self):
        with temporary() as directory:
            source = directory/'policy.md'
            source.write_text('Remote access requires multi-factor authentication.', encoding='utf-8')
            result = documents.extract_worker(source)
            self.assertEqual(result['status'], 'Ready')
            self.assertIn('multi-factor', result['passages'][0]['text'])
            self.assertTrue(result['passages'][0]['locator'])

    def test_fresh_library_import_compare_reopen_and_report(self):
        with temporary() as directory:
            environment = dict(os.environ, POLICYCOMPASS_LIBRARY=str(directory/'empty'),
                               POLICYCOMPASS_FRAMEWORK_CACHE=str(directory/'cache'))
            source = directory/'ism.json'
            source.write_bytes(fixture())
            policy = directory/'policy.txt'
            policy.write_text('Synthetic policy evidence is retained.', encoding='utf-8')
            saved = directory/'comparison.wacc'

            def cli(*args):
                result = subprocess.run([sys.executable, '-m', 'policycompass', *map(str, args)],
                                        cwd=ROOT, env=environment, capture_output=True, text=True,
                                        encoding='utf-8')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return result.stdout

            imported = json.loads(cli('corpus', 'update', '--framework', 'ism', '--import-file', source, '--format', 'json'))
            self.assertEqual(imported['updates'][0]['status'], 'Updated')
            compared = json.loads(cli('compare', policy, '--framework', 'ism', '--scope', 'Synthetic standalone test',
                                      '--assessment', saved, '--format', 'json'))
            self.assertEqual(compared['summary']['counts']['Mentioned'], 1)
            self.assertTrue(json.loads(cli('validate', saved, '--format', 'json'))['valid'])
            report = directory/'report.html'
            cli('report', saved, '--framework', 'ism', '--format', 'html', '--output', report)
            self.assertIn('PolicyCompass', report.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
