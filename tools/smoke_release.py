"""Exercise the frozen core from a fresh workspace, with no Python path or publisher files."""
import argparse
import http.client
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlencode
import uuid
import zipfile


def catalogue():
    return json.dumps({'catalog': {'uuid': '00000000-0000-0000-0000-000000000001',
        'metadata': {'title': 'Information Security Manual — synthetic release check', 'version': 'test-1'},
        'controls': [{'id':'ism-9999', 'title':'Evidence retention', 'parts':[{'id':'statement',
            'name':'statement', 'prose':'Synthetic policy evidence is retained.'}]}]}}).encode('utf-8')


def tiny_pdf():
    stream = b'BT /F1 12 Tf 50 750 Td (Synthetic policy evidence is retained.) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    body = bytearray(b'%PDF-1.4\n'); offsets = []
    for number, item in enumerate(objects, 1):
        offsets.append(len(body)); body.extend(f'{number} 0 obj\n'.encode() + item + b'\nendobj\n')
    start = len(body)
    body.extend(b'xref\n0 6\n0000000000 65535 f \n')
    body.extend(''.join(f'{offset:010} 00000 n \n' for offset in offsets).encode())
    body.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
    return bytes(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--work', type=Path, default=Path('data/local/release-check'))
    args = parser.parse_args()
    folder = args.work.resolve() / uuid.uuid4().hex
    folder.mkdir(parents=True)
    executable = args.exe.resolve()
    environment = {k:v for k,v in os.environ.items() if not k.startswith(('PYTHON', 'POLICYCOMPASS_'))}
    environment.update(POLICYCOMPASS_HOME=str(folder/'browser'), POLICYCOMPASS_FRAMEWORK_CACHE=str(folder/'frameworks'),
                       POLICYCOMPASS_LIBRARY=str(folder/'empty-library'))
    process = subprocess.Popen([str(executable), 'browser', '--no-browser'], cwd=folder, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    session = None
    def request(path, body=None):
        headers = {'X-PolicyCompass-Token':session['token']}
        if isinstance(body, dict):
            headers['Content-Type'] = 'application/json'; body = json.dumps(body).encode()
        connection = http.client.HTTPConnection('127.0.0.1', session['port'], timeout=30)
        try:
            connection.request('POST' if body is not None else 'GET', path, body, headers)
            response = connection.getresponse(); content = response.read()
            if response.status != 200:
                raise AssertionError(f'HTTP {response.status}: {content[:1000]!r}')
            return json.loads(content) if response.getheader('Content-Type', '').startswith('application/json') else content
        finally:
            connection.close()
    def upload(name, data, kind):
        return request('/api/upload?' + urlencode(dict(name=name, kind=kind)), data)['id']
    def wait_job():
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            job = request('/api/status')['job']
            if job['status'] != 'running':
                assert job['status'] == 'succeeded', job
                return job['result']
            time.sleep(.2)
        raise AssertionError('Packaged operation timed out.')
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError('Frozen app stopped: ' + process.communicate()[1].decode(errors='replace'))
            try:
                session = json.loads((folder/'browser/instance.json').read_text())
                break
            except (OSError, ValueError):
                time.sleep(.2)
        assert session, 'The frozen app did not start.'
        assert not request('/api/status')['installed']['availableFrameworks']
        assert b'PolicyCompass' in request('/')
        assert b'function renderResults' in request('/app.js')
        second = subprocess.run([str(executable), 'browser', '--no-browser'], cwd=folder, env=environment,
            capture_output=True, timeout=20, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert second.returncode == 0, second.stderr
        assert json.loads((folder/'browser/instance.json').read_text()) == session, 'A second server was started.'
        source = upload('fixture.json', catalogue(), 'framework')
        request('/api/update', dict(frameworks=['ism'], upload=source))
        assert wait_job()['updates'][0]['status'] == 'Updated'
        text = b'Synthetic policy evidence is retained.'
        docx = folder/'policy.docx'
        with zipfile.ZipFile(docx, 'w') as archive:
            archive.writestr('[Content_Types].xml', '<Types/>')
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Synthetic policy evidence is retained.</w:t></w:r></w:p></w:body></w:document>')
        archive_path = folder/'policies.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            archive.writestr('nested/policy.md', b'# Retention\n\n' + text)
        files = [('policy.txt', text), ('policy.docx', docx.read_bytes()), ('policy.pdf', tiny_pdf()), ('policies.zip', archive_path.read_bytes())]
        uploads = [upload(name, data, 'policy') for name, data in files]
        request('/api/compare', dict(uploads=uploads, frameworks=['ism'], scope='Frozen release check', name='Release check'))
        key = wait_job()['comparisonId']
        comparison = request('/api/comparison?' + urlencode(dict(id=key)))
        assert comparison['report']['summary']['counts']['Mentioned'] == 1
        assert len(comparison['report']['documents']) == 4
        assert all(doc['status'] == 'Ready' for doc in comparison['report']['documents']), comparison['report']['documents']
        for format in ('html','csv','markdown','json'):
            assert request('/api/export?' + urlencode(dict(id=key,format=format)))
        saved = request('/api/assessment?' + urlencode(dict(id=key)))
        imported = upload('copy.policycompass', saved, 'assessment')
        request('/api/import', dict(upload=imported))
        copy = wait_job()['comparisonId']
        assert request('/api/comparison?' + urlencode(dict(id=copy)))['report']['runId'] == comparison['report']['runId']
        assert len(request('/api/library')) == 2
        assert not list((folder/'browser/uploads').iterdir())
        request('/api/quit', {})
        process.wait(timeout=30)
        assert process.returncode == 0
        assert not (folder/'browser/instance.json').exists()
        print('Packaged checks passed: startup, instance reuse, framework import, TXT/DOCX/PDF/ZIP parsing, comparison, save/import, four report formats and shutdown.')
    finally:
        if process.poll() is None:
            try:
                if session:
                    request('/api/quit', {})
                process.wait(timeout=30)
            except Exception:
                process.kill(); process.wait()


if __name__ == '__main__':
    main()
