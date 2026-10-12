"""Check the windowed shortcut launcher while recording its browser URL harmlessly."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, ProxyHandler, build_opener
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launcher', type=Path, required=True)
    parser.add_argument('--work', type=Path, default=Path('data/local/launcher-check'))
    args = parser.parse_args()
    work = args.work.resolve() / uuid.uuid4().hex
    work.mkdir(parents=True)
    captured = work / 'browser-url.txt'
    recorder = work / 'record_browser.py'
    recorder.write_text('import pathlib, sys\npathlib.Path(' + repr(str(captured)) + ').write_text(sys.argv[1], encoding="utf-8")\n', encoding='utf-8')
    # A test browser command records the URL. It never opens the user's browser.
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    environment = {k:v for k,v in os.environ.items() if not k.startswith(('PYTHON', 'POLICYCOMPASS_'))}
    environment.update(POLICYCOMPASS_HOME=str(work/'workspace'), POLICYCOMPASS_FRAMEWORK_CACHE=str(work/'frameworks'),
        POLICYCOMPASS_LIBRARY=str(work/'empty'), BROWSER=f'"{pythonw.as_posix()}" "{recorder.as_posix()}" %s')
    process = subprocess.Popen([str(args.launcher.resolve())], cwd=work, env=environment,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    session = None
    def api(path, body=None):
        request = Request(f'http://127.0.0.1:{session["port"]}' + path, data=body,
            headers={'X-PolicyCompass-Token':session['token'], 'Content-Type':'application/json'})
        with build_opener(ProxyHandler({})).open(request,timeout=5) as response:
            return json.loads(response.read())
    try:
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline and not captured.exists():
            time.sleep(.2)
        assert captured.exists(), 'The windowed launcher did not open the browser.'
        session = json.loads((work/'workspace/instance.json').read_text())
        url = urlsplit(captured.read_text(encoding='utf-8'))
        assert url.hostname == '127.0.0.1' and url.port == session['port']
        assert parse_qs(url.fragment)['session'] == [session['token']]
        assert api('/api/status')['version']
        process.wait(timeout=20)
        assert process.returncode == 0
        second = subprocess.run([str(args.launcher.resolve())], cwd=work, env=environment,
            timeout=25, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        assert second.returncode == 0
        assert json.loads((work/'workspace/instance.json').read_text()) == session
        api('/api/quit', b'{}')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and (work/'workspace/instance.json').exists():
            time.sleep(.2)
        assert not (work/'workspace/instance.json').exists()
        print('Windowed launcher checks passed: default startup, browser URL, instance reuse and shutdown.')
    finally:
        if (work/'workspace/instance.json').exists():
            session = json.loads((work/'workspace/instance.json').read_text())
            try:
                api('/api/quit', b'{}')
            except OSError:
                pass
        if process.poll() is None:
            process.terminate(); process.wait(timeout=10)


if __name__ == '__main__':
    main()
