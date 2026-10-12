"""Real HTTP checks for the local browser boundary and saved comparison flows."""
from contextlib import ExitStack
import http.client
import io
import json
import os
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from test_policy_review import temporary
from test_framework_updates import fixture
from policycompass import updates
from policycompass.contracts import PolicyError
from policycompass.local_web import Workspace, LocalServer, instance_lock, existing_instance, write_json


class LocalWebTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = self.stack.enter_context(temporary())
        self.stack.enter_context(patch.dict(os.environ, {
            'POLICYCOMPASS_LIBRARY': str(self.root / 'empty'),
            'POLICYCOMPASS_FRAMEWORK_CACHE': str(self.root / 'frameworks'),
            'POLICYCOMPASS_HOME': str(self.root / 'browser'),
        }))
        self.app = Workspace(self.root / 'browser')
        self.server = LocalServer(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)
        self.app.close()

    def request(self, path, body=None, headers=None, authenticated=True, method=None):
        values = {'X-PolicyCompass-Token': self.server.token} if authenticated else {}
        if isinstance(body, dict):
            body = json.dumps(body).encode()
            values['Content-Type'] = 'application/json'
        values.update(headers or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        try:
            connection.request(method or ('POST' if body is not None else 'GET'), path, body, values)
            response = connection.getresponse()
            raw = response.read()
            data = json.loads(raw) if response.getheader('Content-Type', '').startswith('application/json') else raw
            return response.status, dict(response.getheaders()), data
        finally:
            connection.close()

    def upload(self, name, body, kind='policy'):
        status, _, value = self.request('/api/upload?' + urlencode(dict(name=name, kind=kind)), body)
        self.assertEqual(status, 200, value)
        return value['id']

    def completed(self):
        self.app.thread.join(30)
        self.assertFalse(self.app.thread.is_alive())
        result = self.app.status()['job']
        self.assertEqual(result['status'], 'succeeded', result)
        return result['result']

    def install_fixture(self):
        key = self.upload('catalogue.json', fixture(), 'framework')
        status, _, value = self.request('/api/update', dict(frameworks=['ism'], upload=key))
        self.assertEqual(status, 200, value)
        result = self.completed()
        self.assertEqual(result['updates'][0]['status'], 'Updated', result)

    def compare(self, previous=None):
        key = self.upload('access.txt', b'Synthetic policy evidence is retained.')
        data = dict(uploads=[key], frameworks=['ism'], scope='Selected access policy', name='Browser test',
                    organisation='Test organisation', comparisonId=previous)
        status, _, value = self.request('/api/compare', data)
        self.assertEqual(status, 200, value)
        return self.completed()['comparisonId']

    def test_api_requires_session_and_rejects_other_hosts_and_origins(self):
        for path in ('/api/status', '/api/library', '/api/comparison?id=anything'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path, authenticated=False)[0], 403)
                self.assertEqual(self.request(path, headers={'X-PolicyCompass-Token':'wrong'})[0], 403)
        for headers in ({'Host':'evil.example'}, {'Origin':'https://evil.example'},
                        {'Origin':'null'}, {'Sec-Fetch-Site':'cross-site'},
                        {'Origin':'http://127.0.0.1:1'}):
            self.assertEqual(self.request('/api/quit', {}, headers=headers)[0], 403)
        self.assertFalse(self.app.stopping)
        self.assertEqual(self.request('/api/status', headers={'Origin':self.server.origin})[0], 200)
        self.assertEqual(self.server.server_address[0], '127.0.0.1')

    def test_static_assets_do_not_expose_disk_or_session(self):
        for path in ('/', '/app.js', '/app.css', '/favicon.svg'):
            status, headers, content = self.request(path, authenticated=False)
            self.assertEqual(status, 200)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertNotIn(self.server.token.encode(), content)
        for path in ('/../instance.json', '/assets/../../README.md', '/instance.json', '/uploads', '/api/unknown'):
            self.assertEqual(self.request(path)[0], 404)

    def test_upload_paths_sizes_and_windows_devices_are_rejected(self):
        for name in ('../policy.txt', 'C:\\policy.txt', 'a/b.txt', 'policy.txt:stream', 'NUL.txt', 'CON', 'a.txt ', 'a.txt.', 'app.exe'):
            with self.subTest(name=name):
                self.assertEqual(self.request('/api/upload?' + urlencode(dict(name=name, kind='policy')), b'test')[0], 400)
        self.assertEqual(self.request('/api/upload?name=p.txt&kind=policy', b'', headers={'Content-Length':str(17*1024*1024)})[0], 400)
        self.assertEqual(self.request('/api/upload?name=p.txt&kind=policy', b'', headers={'Transfer-Encoding':'chunked'})[0], 411)
        with self.assertRaises(PolicyError):
            self.app.receive(io.BytesIO(b'short'), 'short.txt', 'policy', 10)
        self.assertEqual(self.app.uploads, {})
        self.assertEqual(list(self.app.staging.iterdir()), [])

    def test_compare_save_history_reopen_export_and_import(self):
        self.install_fixture()
        first = self.compare()
        _, _, comparison = self.request('/api/comparison?' + urlencode(dict(id=first)))
        self.assertEqual(comparison['report']['summary']['counts']['Mentioned'], 1)
        self.assertEqual(len(comparison['history']), 1)
        original_run = comparison['report']['runId']
        doc = comparison['report']['documents'][0]
        _, _, extracted = self.request('/api/document?' + urlencode(dict(id=first, document=doc['id'])))
        self.assertIn('Synthetic policy evidence', extracted['passages'][0]['text'])
        self.assertNotIn('path', extracted)
        self.assertEqual(self.app.uploads, {})
        self.assertEqual(list(self.app.staging.iterdir()), [])
        self.assertEqual(self.compare(first), first)
        _, _, previous = self.request('/api/comparison?' + urlencode(dict(id=first, run=original_run)))
        self.assertEqual(previous['report']['runId'], original_run)
        self.assertTrue(previous['metadata']['historical'])
        self.assertEqual(len(previous['history']), 2)
        for format in ('html', 'csv', 'markdown', 'json'):
            status, headers, report = self.request('/api/export?' + urlencode(dict(id=first, run=original_run, format=format)))
            self.assertEqual(status, 200, report)
            self.assertIn('attachment;', headers['Content-Disposition'])
            if format == 'json':
                self.assertEqual(report['runId'], original_run)
        self.assertEqual(self.request('/api/export?' + urlencode(dict(id=first, format='exe')))[0], 400)
        status, _, content = self.request('/api/assessment?' + urlencode(dict(id=first)))
        self.assertEqual(status, 200)
        self.assertTrue(content.startswith(b'SQLite format 3\x00'))
        imported = self.upload('from-another-folder.policycompass', content, 'assessment')
        self.assertEqual(self.request('/api/import', dict(upload=imported))[0], 200)
        new_id = self.completed()['comparisonId']
        self.assertNotEqual(new_id, first)
        self.assertEqual(len(self.app.state(new_id)['history']), 2)
        self.assertEqual(len(self.app.list_comparisons()), 2)
        restored = Workspace(self.app.home)
        self.assertEqual(restored.settings['frameworks'], ['ism'])
        self.assertEqual(restored.settings['organisation'], 'Test organisation')

    def test_failed_import_leaves_existing_library_unchanged(self):
        key = self.upload('bad.policycompass', b'not a comparison', 'assessment')
        self.request('/api/import', dict(upload=key))
        self.app.thread.join(10)
        self.assertEqual(self.app.job['status'], 'failed')
        self.assertEqual(self.app.list_comparisons(), [])
        self.assertEqual(self.app.uploads, {})
        self.assertEqual(list(self.app.library.iterdir()), [])

    def test_cancel_preserves_saved_runs_and_rejects_simultaneous_work(self):
        self.install_fixture()
        key = self.compare()
        previous = self.app.comparison_path(key).read_bytes()
        selected = self.upload('revision.txt', b'Revised wording.')
        started = threading.Event()
        def wait_for_cancel(*args, **kwargs):
            started.set()
            kwargs['cancel'].wait(10)
            raise KeyboardInterrupt
        with patch('policycompass.service.analyse', side_effect=wait_for_cancel):
            data = dict(uploads=[selected], frameworks=['ism'], scope='New revision', comparisonId=key)
            self.assertEqual(self.request('/api/compare', data)[0], 200)
            self.assertTrue(started.wait(5))
            self.assertEqual(self.request('/api/compare', data)[0], 409)
            self.assertEqual(self.request('/api/discard', dict(uploads=[selected]))[0], 409)
            self.assertEqual(self.request('/api/cancel', {})[0], 200)
            self.app.thread.join(10)
        self.assertEqual(self.app.job['status'], 'cancelled')
        self.assertEqual(self.app.comparison_path(key).read_bytes(), previous)
        self.assertEqual(self.app.uploads, {})

    def test_invalid_ids_cannot_open_or_overwrite_arbitrary_files(self):
        for identifier in ('../../README', 'C:/Windows', 'x'*32, '', '../'*12):
            self.assertEqual(self.request('/api/comparison?' + urlencode(dict(id=identifier)))[0], 400)
        self.assertEqual(self.request('/api/compare', dict(uploads=['../../README'], frameworks=['ism'], scope='Test'))[0], 400)
        self.assertEqual(self.request('/api/compare', dict(uploads='README.md', frameworks=['ism'], scope='Test'))[0], 400)
        self.assertEqual(self.request('/api/update', dict(frameworks=['aescsf']))[0], 400)

    def test_instance_lock_releases_and_second_launch_reuses_same_service(self):
        home = self.app.home
        with instance_lock(home) as acquired:
            self.assertTrue(acquired)
            with instance_lock(home) as second:
                self.assertFalse(second)
            write_json(home/'instance.json', dict(port=self.server.server_port, token=self.server.token))
            with patch('policycompass.local_web.webbrowser.open') as opened:
                self.assertTrue(existing_instance(home))
                url = opened.call_args.args[0]
                self.assertTrue(url.startswith(self.server.origin + '/#session='))
                self.assertNotIn('?', url)
        with instance_lock(home) as again:
            self.assertTrue(again)

    def test_cancelled_framework_download_makes_no_network_request(self):
        cancel = threading.Event(); cancel.set()
        with patch('policycompass.updates.build_opener', side_effect=AssertionError('No network expected')):
            with self.assertRaises(KeyboardInterrupt):
                updates.download(updates.ISM_CATALOG, 'ism', cancel)
            with self.assertRaises(KeyboardInterrupt):
                updates.update(['ism'], cancel=cancel)


if __name__ == '__main__':
    unittest.main()
