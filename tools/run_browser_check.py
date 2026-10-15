"""Start an isolated app, run the Edge checks, and close its local service."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import Request, ProxyHandler, build_opener
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--work', type=Path, default=Path('data/local/browser-check'))
    parser.add_argument('--essentials-cache', type=Path,
        help='Run the Essentials workflow against an already downloaded framework cache.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    work = args.work.resolve() / uuid.uuid4().hex
    work.mkdir(parents=True)
    environment = dict(os.environ, POLICYCOMPASS_HOME=str(work/'workspace'),
        POLICYCOMPASS_FRAMEWORK_CACHE=str(work/'frameworks'), POLICYCOMPASS_LIBRARY=str(work/'empty'))
    if args.essentials_cache:
        environment['POLICYCOMPASS_FRAMEWORK_CACHE'] = str(args.essentials_cache.resolve())
    command = [str(args.exe.resolve())] if args.exe else [sys.executable, '-m', 'policycompass']
    record = work/'workspace/instance.json'
    process = subprocess.Popen([*command, 'browser', '--no-browser'], cwd=root, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        deadline = time.monotonic() + 45
        while not record.exists() and time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(process.communicate()[1].decode(errors='replace'))
            time.sleep(.2)
        if not record.exists():
            raise RuntimeError('The local app did not become ready.')
        script = 'test_essentials_browser.cjs' if args.essentials_cache else 'test_browser.cjs'
        result = subprocess.run(['node', str(root/'tools'/script), str(record), str(work/'screenshots')],
            cwd=root, env=environment, timeout=300)
        print('Browser check files: ' + str(work/'screenshots'))
        return result.returncode
    finally:
        if process.poll() is None and record.exists():
            info = json.loads(record.read_text())
            request = Request(f'http://127.0.0.1:{info["port"]}/api/quit', data=b'{}',
                headers={'Content-Type':'application/json','X-PolicyCompass-Token':info['token']})
            try:
                with build_opener(ProxyHandler({})).open(request,timeout=5) as response:
                    response.read()
            except OSError:
                pass
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
