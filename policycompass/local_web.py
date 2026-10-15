"""Authenticated, loopback-only browser workspace and single-instance launcher.

The browser sends selected files, never filesystem paths. Files and comparisons
are confined to the user's application directory; parsers still run in bounded
worker processes. This is a local application, not a network deployment server.
"""
from contextlib import contextmanager
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
from urllib.parse import parse_qs, urlsplit, urlencode
from urllib.request import Request, ProxyHandler, build_opener
import uuid
import webbrowser

from . import ENGINE_VERSION, corpus, documents, reports, service, store, updates
from .contracts import PolicyError
from .frameworks import AUTOMATIC, NAMES, PAGES

ASSETS = Path(__file__).with_name('assets') / 'web'
MAX_UPLOAD_TOTAL = 256 * 1024 * 1024
IDLE_SECONDS = 10 * 60
UUID = re.compile(r'[a-f0-9]{32}\Z')


def home_directory():
    default = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local/share'))) / 'PolicyCompass/browser'
    return documents.local_file(os.environ.get('POLICYCOMPASS_HOME', str(default)))


def read_json(path, default):
    try:
        if path.stat().st_size > 1024 * 1024:
            return deepcopy(default)
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return deepcopy(default)


def write_json(path, value):
    stage = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        stage.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(stage, path)
    finally:
        stage.unlink(missing_ok=True)


def identifier(value):
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise PolicyError('Choose an item from this workspace.', 2)
    return value


def text_value(data, name, default='', limit=500):
    value = data.get(name, default)
    if not isinstance(value, str) or len(value) > limit:
        raise PolicyError('Invalid value for ' + name + '.', 2)
    return value.strip()


@contextmanager
def instance_lock(home):
    """An OS-owned lock survives neither a normal exit nor a crashed process."""
    home.mkdir(parents=True, exist_ok=True)
    handle = (home / 'instance.lock').open('a+b')
    locked = False
    try:
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            pass
        yield locked
    finally:
        if locked:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


class Workspace:
    def __init__(self, home):
        self.home = documents.local_file(home)
        self.library = self.home / 'comparisons'
        self.library.mkdir(parents=True, exist_ok=True)
        self.staging = self.home / 'uploads'
        self.staging.mkdir(exist_ok=True)
        # Only the instance holding the OS lock constructs the workspace.
        # Clear incomplete browser uploads from an earlier session.
        for folder in self.staging.iterdir():
            if folder.is_dir() and UUID.fullmatch(folder.name):
                self.remove_upload_directory(folder)
        self.uploads = {}
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.thread = None
        self.job = dict(status='idle', message='Ready', result=None, kind=None)
        self.stopping = False
        self.last_request = time.monotonic()
        raw = read_json(self.home / 'settings.json', {})
        self.settings = self.clean_settings(raw if isinstance(raw, dict) else {})
        self.frameworks = None
        self.framework_error = None
        self.refresh_frameworks()

    @staticmethod
    def clean_settings(data):
        selected = data.get('frameworks', ['wa-csp'])
        if not isinstance(selected, list) or not selected or any(not isinstance(k, str) or k not in NAMES for k in selected):
            selected = ['wa-csp']
        level = data.get('ismMaturity', '')
        if level not in ('', 'ML1', 'ML2', 'ML3') or 'ism' not in selected:
            level = ''
        retention = data.get('retention', 'extracted')
        if retention not in ('extracted', 'evidence'):
            retention = 'extracted'
        organisation = data.get('organisation', '')
        if not isinstance(organisation, str):
            organisation = ''
        return dict(frameworks=list(dict.fromkeys(selected)), ismMaturity=level,
                    organisation=organisation.strip()[:500], retention=retention)

    def refresh_frameworks(self):
        try:
            result = corpus.installed()
            with self.lock:
                self.frameworks, self.framework_error = result, None
        except (PolicyError, OSError):
            with self.lock:
                self.framework_error = 'Frameworks could not be read. Saved comparisons can still be opened.'
                self.frameworks = dict(availableFrameworks=[], availabilityErrors={})

    def status(self):
        with self.lock:
            return deepcopy(dict(version=ENGINE_VERSION, job=self.job, settings=self.settings,
                installed=self.frameworks, frameworkError=self.framework_error,
                frameworks=[dict(id=k, title=v, automatic=k in AUTOMATIC, source=PAGES[k]) for k, v in NAMES.items()],
                home=str(self.home), stopping=self.stopping))

    def comparison_path(self, key):
        return documents.local_file(self.library / (identifier(key) + '.policycompass'))

    def list_comparisons(self):
        index = read_json(self.home / 'library.json', {})
        if not isinstance(index, dict):
            index = {}
        return sorted([dict(value, id=key) for key, value in index.items()
            if isinstance(key, str) and UUID.fullmatch(key) and isinstance(value, dict)
            and self.comparison_path(key).is_file()], key=lambda row: str(row.get('updatedAt', '')), reverse=True)

    def remember(self, key, state):
        with self.lock:
            index = {row.pop('id'): row for row in self.list_comparisons()}
            run = state['run']
            index[key] = dict(name=run['name'], updatedAt=service.now(), organisation=run.get('organisation', ''),
                              runs=len(state['history']), frameworks=[f['title'] for f in run['versions']['frameworks']])
            write_json(self.home / 'library.json', index)

    def state(self, key, run=None):
        if run is not None and (not isinstance(run, str) or len(run) > 100):
            raise PolicyError('Choose a saved run.', 2)
        return store.load(self.comparison_path(key), run or None)

    def comparison(self, key, run=None):
        state = self.state(key, run)
        return dict(id=key, report=reports.model(state), history=state['history'], metadata=state['metadata'])

    def remove_upload_directory(self, folder):
        target = documents.local_file(folder).resolve()
        if target.parent != self.staging.resolve() or not UUID.fullmatch(target.name):
            raise PolicyError('Invalid temporary upload directory.')
        shutil.rmtree(target)

    def receive(self, stream, name, kind, length):
        allowed = {'policy': documents.INPUT_FORMATS, 'assessment': ('.policycompass',),
                   'framework': ('.pdf', '.xlsx', '.json', '.html', '.zip')}
        if (kind not in allowed or not name or len(name) > 200 or re.search(r'[\\/:\x00-\x1f<>"|?*]', name)
                or name.endswith(('.', ' ')) or re.match(r'(?i)^(?:con|prn|aux|nul|com[0-9¹²³]|lpt[0-9¹²³])(?:\.|$)', name)):
            raise PolicyError('Choose a supported file with a normal filename.', 2)
        if Path(name).suffix.lower() not in allowed[kind]:
            raise PolicyError('This file type is not supported for that import.', 2)
        limit = store.MAX_FILE if kind == 'assessment' else documents.MAX_BYTES
        if not 0 < length <= limit:
            raise PolicyError(f'The selected file must be between 1 byte and {limit // 1024 // 1024} MiB.', 2)
        with self.lock:
            if self.stopping or self.job['status'] == 'running':
                raise PolicyError('Wait for the current operation before adding files.', 6)
            if len(self.uploads) >= 250 or sum(x['size'] for x in self.uploads.values()) + length > MAX_UPLOAD_TOTAL:
                raise PolicyError('The upload limit has been reached. Remove unused files or compare a smaller set.', 2)
            key = uuid.uuid4().hex
            folder = self.staging / key
            folder.mkdir()
            path = folder / name
            self.uploads[key] = dict(path=path, name=name, kind=kind, size=length, ready=False)
        try:
            remaining = length
            with path.open('xb') as target:
                while remaining:
                    block = stream.read(min(65536, remaining))
                    if not block:
                        raise PolicyError('The file transfer was interrupted. Select the file again.', 2)
                    target.write(block)
                    remaining -= len(block)
            with self.lock:
                self.uploads[key]['ready'] = True
            return dict(id=key, name=name, size=length)
        except BaseException:
            self.discard([key])
            raise

    def upload_paths(self, keys, kind):
        if not isinstance(keys, list) or not 1 <= len(keys) <= 250 or any(not isinstance(k, str) for k in keys):
            raise PolicyError('Select files before continuing.', 2)
        if len(set(keys)) != len(keys):
            raise PolicyError('A file was selected more than once.', 2)
        result = []
        for key in keys:
            upload = self.uploads.get(identifier(key))
            if not upload or not upload['ready'] or upload['kind'] != kind:
                raise PolicyError('A selected file is no longer available. Select it again.', 2)
            result.append(upload['path'])
        return result

    def discard(self, keys):
        with self.lock:
            for key in keys:
                item = self.uploads.pop(identifier(key), None)
                if item:
                    self.remove_upload_directory(item['path'].parent)

    def progress(self, message):
        with self.lock:
            self.job['message'] = message

    def start(self, kind, action):
        with self.lock:
            if self.stopping or self.job['status'] == 'running':
                raise PolicyError('Wait for the current operation to finish, or cancel it.', 6)
            self.cancel = threading.Event()
            self.job = dict(id=uuid.uuid4().hex, kind=kind, status='running', message='Starting…', result=None)
            def work():
                try:
                    result = action()
                    with self.lock:
                        self.job.update(status='succeeded', message='Complete', result=result)
                except KeyboardInterrupt:
                    with self.lock:
                        self.job.update(status='cancelled', message='Cancelled. Previously saved work is unchanged.')
                except Exception as error:
                    with self.lock:
                        self.job.update(status='failed', message=str(error) if isinstance(error, PolicyError) else
                            'The operation could not finish. Check the file format, available space and folder permissions.')
            self.thread = threading.Thread(target=work, name='policycompass-job')
            self.thread.start()
            return deepcopy(self.job)

    def compare(self, data):
        keys = data.get('uploads')
        paths = self.upload_paths(keys, 'policy')
        selected = data.get('frameworks')
        if not isinstance(selected, list) or not selected or any(not isinstance(k, str) or k not in NAMES for k in selected):
            raise PolicyError('Choose one or more frameworks.', 2)
        name = text_value(data, 'name', 'Framework comparison') or 'Framework comparison'
        scope = text_value(data, 'scope', limit=4000)
        if not scope:
            raise PolicyError('Describe which documents this comparison covers.', 2)
        organisation = text_value(data, 'organisation')
        approval = data.get('documentStatus', 'unknown')
        retention = data.get('retention', 'extracted')
        if approval not in ('approved', 'draft', 'unknown', 'superseded') or retention not in ('extracted', 'evidence'):
            raise PolicyError('Choose a document status and text retention option.', 2)
        level = data.get('ismMaturity') or None
        if level and (level not in ('ML1', 'ML2', 'ML3') or 'ism' not in selected):
            raise PolicyError('Choose ISM before using its Essential Eight filter.', 2)
        key = data.get('comparisonId') or uuid.uuid4().hex
        destination = self.comparison_path(key)
        if data.get('comparisonId'):
            self.state(key)
        def action():
            try:
                run = service.analyse(paths, name=name, scope=scope, organisation=organisation,
                    framework=selected[0], also=selected[1:], approval=approval, retention=retention,
                    ism_maturity=level, cancel=self.cancel, progress=self.progress)
                if self.cancel.is_set():
                    raise KeyboardInterrupt
                self.progress('Saving the comparison…')
                store.save(destination, run)
                state = store.load(destination)
                self.remember(key, state)
                with self.lock:
                    self.settings = self.clean_settings(data)
                    write_json(self.home / 'settings.json', self.settings)
                return dict(comparisonId=key, runId=run['runId'])
            finally:
                self.discard(keys)
        return self.start('compare', action)

    def import_comparison(self, data):
        keys = [data.get('upload')]
        source = self.upload_paths(keys, 'assessment')[0]
        key = uuid.uuid4().hex
        def action():
            try:
                self.progress('Checking the saved comparison…')
                store.load(source)
                if self.cancel.is_set():
                    raise KeyboardInterrupt
                store.snapshot(source, self.comparison_path(key))
                self.remember(key, store.load(self.comparison_path(key)))
                return dict(comparisonId=key)
            finally:
                self.discard(keys)
        return self.start('import', action)

    def update_frameworks(self, data):
        selected = data.get('frameworks')
        if not isinstance(selected, list) or not selected or any(not isinstance(k, str) or k not in NAMES for k in selected):
            raise PolicyError('Choose frameworks to download or import.', 2)
        key = data.get('upload')
        source = self.upload_paths([key], 'framework')[0] if key else None
        if source and len(selected) != 1:
            raise PolicyError('Choose one framework for the selected file.', 2)
        if not source and 'aescsf' in selected:
            raise PolicyError('Download the AESCSF Core workbook from AEMO, then import it here.', 2)
        def action():
            try:
                results = updates.update(selected, source, progress=self.progress, cancel=self.cancel)
                return dict(updates=results)
            finally:
                if key:
                    self.discard([key])
                self.refresh_frameworks()
        return self.start('update', action)

    def close(self):
        self.stopping = True
        self.cancel.set()
        if self.thread:
            self.thread.join()
        self.discard(list(self.uploads))


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace):
        self.workspace = workspace
        self.token = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(12)
        super().__init__(('127.0.0.1', 0), Handler)
        self.origin = 'http://127.0.0.1:' + str(self.server_port)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(15)
        return request, address

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        # Never include policy text, session credentials or file paths in logs.
        pass


class Handler(BaseHTTPRequestHandler):
    server_version = 'PolicyCompass'
    sys_version = ''

    def log_message(self, *args):
        pass

    def respond(self, status, body, content_type='application/json; charset=utf-8', filename=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header('Connection', 'close')
        if filename:
            self.send_header('Content-Disposition', 'attachment; filename="' + filename + '"')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def authorised(self, api):
        if self.headers.get_all('Host', []) != [urlsplit(self.server.origin).netloc]:
            self.respond(403, dict(error='This address is not allowed. Open PolicyCompass using its shortcut.'))
            return False
        origins = self.headers.get_all('Origin', [])
        if origins and origins != [self.server.origin]:
            self.respond(403, dict(error='Requests from other websites are not allowed.'))
            return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.respond(403, dict(error='Open PolicyCompass using its shortcut.'))
            return False
        if api:
            tokens = self.headers.get_all('X-PolicyCompass-Token', [])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0], self.server.token):
                self.respond(403, dict(error='This session has ended. Reopen PolicyCompass using its shortcut.'))
                return False
            self.server.workspace.last_request = time.monotonic()
        return True

    def do_GET(self):
        self.handle_action(False)

    def do_POST(self):
        self.handle_action(True)

    def handle_action(self, post):
        try:
            # Buffer only small, fixed-length bodies before an early rejection.
            # Closing a Windows socket with unread request bytes can reset it
            # before the browser receives the error. Large uploads still require
            # authorisation before their content is read; all sockets are timed.
            small_body = None
            declared = self.headers.get_all('Content-Length', [])
            if (post and not self.headers.get('Transfer-Encoding') and len(declared) == 1
                    and declared[0].isdigit() and len(declared[0]) <= 5 and int(declared[0]) <= 65536):
                small_body = self.rfile.read(int(declared[0]))
            parsed = urlsplit(self.path)
            path = parsed.path
            if parsed.scheme or parsed.netloc or len(self.path) > 8192:
                self.respond(400, dict(error='Invalid request.'))
                return
            api = path.startswith('/api/')
            if not self.authorised(api):
                return
            if not api:
                files = {'/': ('index.html', 'text/html; charset=utf-8'),
                         '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                         '/app.css': ('app.css', 'text/css; charset=utf-8'),
                         '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
                if post or path not in files:
                    self.respond(404, dict(error='Page not found.'))
                    return
                name, mime = files[path]
                self.respond(200, (ASSETS / name).read_bytes(), mime)
                return
            query = parse_qs(parsed.query, max_num_fields=25)
            value = lambda key: query.get(key, [None])[0]
            app = self.server.workspace
            if post:
                lengths = self.headers.get_all('Content-Length', [])
                if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not lengths[0].isdigit():
                    self.respond(411, dict(error='A fixed request length is required.'))
                    return
                length = int(lengths[0])
                if path == '/api/upload':
                    stream = io.BytesIO(small_body) if small_body is not None else self.rfile
                    result = app.receive(stream, value('name'), value('kind'), length)
                else:
                    if length > 65536 or self.headers.get_content_type() != 'application/json':
                        self.respond(413, dict(error='Use a small JSON request.'))
                        return
                    raw = small_body if small_body is not None else self.rfile.read(length)
                    if len(raw) != length:
                        raise PolicyError('The request was interrupted.', 2)
                    data = json.loads(raw)
                    if not isinstance(data, dict):
                        raise PolicyError('A JSON object is required.', 2)
                    if path == '/api/compare':
                        result = app.compare(data)
                    elif path == '/api/import':
                        result = app.import_comparison(data)
                    elif path == '/api/update':
                        result = app.update_frameworks(data)
                    elif path == '/api/cancel':
                        app.cancel.set()
                        result = dict(message='Cancelling. An active network request may take a moment to stop.')
                    elif path == '/api/discard':
                        with app.lock:
                            if app.job['status'] == 'running':
                                raise PolicyError('Wait for the current operation to finish.', 6)
                            keys = data.get('uploads')
                            if not isinstance(keys, list) or len(keys) > 250:
                                raise PolicyError('Choose files to remove.', 2)
                            app.discard(keys)
                        result = dict(ok=True)
                    elif path == '/api/settings':
                        with app.lock:
                            settings = app.clean_settings(data)
                            write_json(app.home / 'settings.json', settings)
                            app.settings = settings
                        result = settings
                    elif path == '/api/quit':
                        app.stopping = True
                        app.cancel.set()
                        result = dict(message='PolicyCompass is closing. You can close this tab.')
                        threading.Thread(target=self.server.shutdown, daemon=True).start()
                    else:
                        self.respond(404, dict(error='Operation not found.'))
                        return
                self.respond(200, result)
                return
            if path == '/api/status':
                self.respond(200, app.status())
            elif path == '/api/library':
                self.respond(200, app.list_comparisons())
            elif path == '/api/comparison':
                self.respond(200, app.comparison(value('id'), value('run')))
            elif path == '/api/document':
                state = app.state(value('id'), value('run'))
                doc = next((d for d in state['run']['documents'] if d['id'] == value('document')), None)
                if doc is None:
                    raise PolicyError('Document not found in this comparison.', 2)
                self.respond(200, {k: v for k, v in doc.items() if k != 'path'})
            elif path == '/api/export':
                format = value('format')
                types = {'html': ('text/html; charset=utf-8', 'html'), 'json': ('application/json', 'json'),
                         'markdown': ('text/markdown; charset=utf-8', 'md'), 'csv': ('text/csv; charset=utf-8', 'csv')}
                if format not in types:
                    raise PolicyError('Choose HTML, CSV, Markdown or JSON.', 2)
                state = app.state(value('id'), value('run'))
                content = reports.render(state, format, value('full') != 'false', query.get('framework'))
                mime, suffix = types[format]
                self.respond(200, content.encode('utf-8'), mime, 'PolicyCompass-report.' + suffix)
            elif path == '/api/assessment':
                key = identifier(value('id'))
                folder = app.staging / uuid.uuid4().hex
                folder.mkdir()
                try:
                    target = folder / 'comparison.policycompass'
                    store.snapshot(app.comparison_path(key), target)
                    self.respond(200, target.read_bytes(), 'application/octet-stream', 'PolicyCompass-comparison.policycompass')
                finally:
                    app.remove_upload_directory(folder)
            else:
                self.respond(404, dict(error='Operation not found.'))
        except PolicyError as error:
            self.respond(409 if error.code == 6 else 400, dict(error=str(error)))
        except (ValueError, TypeError, KeyError, RecursionError):
            self.respond(400, dict(error='The request was not understood. Check the selected options.'))
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            self.close_connection = True
        except Exception:
            self.respond(500, dict(error='The operation could not finish. Check local folder permissions and available space.'))


def browser_url(origin, token):
    return origin + '/#' + urlencode({'session': token})


def existing_instance(home, open_browser=True):
    for _ in range(100):
        record = read_json(home / 'instance.json', {})
        if isinstance(record, dict):
            port, token = record.get('port'), record.get('token')
            if isinstance(port, int) and 1 <= port <= 65535 and isinstance(token, str) and len(token) == 43:
                origin = f'http://127.0.0.1:{port}'
                try:
                    request = Request(origin + '/api/status', headers={'X-PolicyCompass-Token': token})
                    with build_opener(ProxyHandler({})).open(request, timeout=.5) as response:
                        body = json.loads(response.read(1024 * 1024))
                    if not body.get('version') or body.get('stopping'):
                        raise ValueError('The previous instance is closing.')
                    if open_browser:
                        webbrowser.open(browser_url(origin, token))
                    return True
                except (OSError, ValueError):
                    pass
        time.sleep(.1)
    raise PolicyError('PolicyCompass is still starting or closing. Wait a moment and open it again.', 6)


def launch(open_browser=True):
    home = home_directory()
    with instance_lock(home) as owned:
        if not owned:
            return existing_instance(home, open_browser)
        app = Workspace(home)
        server = LocalServer(app)
        record = home / 'instance.json'
        write_json(record, dict(port=server.server_port, token=server.token, version=ENGINE_VERSION))
        def watch():
            while not app.stopping:
                time.sleep(2)
                if time.monotonic() - app.last_request > IDLE_SECONDS and app.job['status'] != 'running':
                    app.stopping = True
                    server.shutdown()
                    return
        threading.Thread(target=watch, daemon=True).start()
        if open_browser:
            threading.Thread(target=webbrowser.open, args=(browser_url(server.origin, server.token),), daemon=True).start()
        try:
            server.serve_forever(poll_interval=.2)
        finally:
            server.server_close()
            app.close()
            record.unlink(missing_ok=True)
    return True
