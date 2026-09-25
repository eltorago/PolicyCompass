"""Regression checks for the application extraction, independent of publisher data."""
import json
from copy import deepcopy
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
from test_policy_alignment import BASELINE
from policycompass import corpus, documents, packages, service, store, updates
from policycompass.config import setting
from policycompass.contracts import canonical, fingerprint


class StandaloneTests(unittest.TestCase):
    def test_cli_version_and_standalone_core_import(self):
        result = subprocess.run([sys.executable, '-m', 'policycompass', '--version'],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('PolicyCompass '))
        from framework_core.build import build
        library, _ = build(False, source_root=ROOT/'absent-sources',
                           corpus_root=ROOT/'absent-corpus', framework_keys=['ism'])
        self.assertIn('ism', library.frameworks)
        self.assertTrue(callable(build))

    def test_assets_resolve_in_the_application_package(self):
        self.assertTrue(corpus.training_rules())
        self.assertEqual(json.loads(packages.TRUST_FILE.read_text())['keys'], {})
        from policycompass.wa_parser import parse
        self.assertTrue(callable(parse))

    def test_configuration_and_separate_cache(self):
        with patch.dict(os.environ, {}, clear=True), patch('pathlib.Path.home', return_value=ROOT):
            self.assertEqual(setting('LIBRARY', 'fallback'), 'fallback')
            self.assertEqual(updates.cache_root().parts[-2:], ('PolicyCompass', 'frameworks'))
            self.assertEqual(packages.installation_root().parts[-2:], ('PolicyCompass', 'corpus'))
        with patch.dict(os.environ, {'POLICYCOMPASS_LIBRARY': 'prepared-library'}, clear=True):
            self.assertEqual(setting('LIBRARY', 'fallback'), 'prepared-library')
        from framework_core.sources import source_directory
        with patch.dict(os.environ, {'POLICYCOMPASS_SOURCES': str(ROOT/'prepared-sources')}, clear=True):
            self.assertEqual(source_directory(), (ROOT/'prepared-sources').resolve())

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
            saved = directory/'comparison.policycompass'

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

    def test_existing_comparison_can_be_copied_to_current_extension(self):
        with temporary() as directory:
            source = directory/'policy.txt'
            source.write_text('MFA protects remote access.', encoding='utf-8')
            with patch.object(corpus, 'load', return_value=deepcopy(BASELINE)):
                run = service.analyse([source], scope='Synthetic saved-file migration')
            saved = directory/'comparison.policycompass'
            store.save(saved, run)
            previous = directory/'comparison.previous'
            saved.rename(previous)
            original = previous.read_bytes()
            self.assertEqual(store.load(previous)['run'], run)
            store.snapshot(previous, saved)
            self.assertEqual(store.load(saved)['run'], run)
            self.assertEqual(previous.read_bytes(), original)

    def test_signed_package_install_uses_current_extension(self):
        import base64
        import hashlib
        import zipfile
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        with temporary() as directory:
            key = Ed25519PrivateKey.generate()
            trust = directory/'keys.json'
            trust.write_text(json.dumps({'keys': {'test': {'publicKey': base64.b64encode(key.public_key().public_bytes_raw()).decode()}}}))
            data = deepcopy(BASELINE)
            data['status'] = 'Synthetic test'
            data['rulesHash'] = fingerprint([r['obligations'] for r in data['requirements']])
            payload = canonical(data).encode()
            manifest = canonical(dict(schemaVersion='1.0', version=data['version'], engineMajor=0,
                files={'corpus.json': hashlib.sha256(payload).hexdigest()}, reviewRecord='Synthetic test')).encode()
            signature = canonical(dict(keyId='test', algorithm='Ed25519', signature=base64.b64encode(key.sign(manifest)).decode()))
            archive = directory/'download.previous'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('manifest.json', manifest)
                output.writestr('corpus.json', payload)
                output.writestr('signature.json', signature)
            installed = directory/'installed'
            with patch.object(packages, 'TRUST_FILE', trust), patch.object(packages, 'installation_root', return_value=installed):
                packages.install(archive)
                self.assertTrue((installed/(data['version'] + '.policycompasspack')).is_file())
                self.assertEqual(packages.installed(data['version']), data)


if __name__ == '__main__':
    unittest.main()
