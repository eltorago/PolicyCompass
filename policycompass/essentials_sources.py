"""Acquire and verify the complete public Essentials publication collection.

The ZIP is a local source snapshot, not a program or a set of executable rules.
Every member is named here and verified before a parser receives its bytes.
"""
import hashlib
from html.parser import HTMLParser
import io
import json
import re
from urllib.parse import urljoin, urlsplit, unquote
import zipfile

from .contracts import PolicyError
from .documents import MAX_BYTES, checked_archive

BASE = 'https://www.cyber.gov.au'
EDITION = '2026-10-15'
CHAPTERS = {
    'essentials-it': 'chapter-it',
    'essentials-cloud': 'chapter-cloud',
    'essentials-ot': 'chapter-ot',
}
# Reading-guide order, followed by the supplementary publications.
PUBLICATIONS = (
    ('essentials-reading-guide', 'Essentials reading guide', 'guidance'),
    ('what-is-the-essentials', 'What is the Essentials?', 'guidance'),
    ('the-case-for-change', 'The case for change', 'guidance'),
    ('the-essentials-for-senior-executives', 'The Essentials for senior executives', 'guidance'),
    ('which-chapter-should-i-start-with', 'Which chapter should I start with?', 'guidance'),
    ('ai-considerations-within-the-essentials', 'AI considerations within the Essentials', 'guidance'),
    ('essentials-for-enterprise-it', 'Essentials for enterprise IT', 'chapter-it'),
    ('essentials-for-cloud', 'Essentials for cloud', 'chapter-cloud'),
    ('essentials-for-ot', 'Essentials for OT', 'chapter-ot'),
    ('transitioning-from-the-essential-eight', 'Transitioning from the Essential Eight', 'guidance'),
    ('implementation-planning-guide', 'Implementation planning guide', 'guidance'),
    ('assessment-process-guide', 'Assessment process guide', 'guidance'),
    ('frequently-asked-questions', 'Frequently asked questions', 'guidance'),
    ('essentials-glossary', 'Essentials glossary', 'guidance'),
    ('asset-scoping-guide-for-enterprise-it', 'Asset scoping guide for enterprise IT', 'guidance'),
    ('asset-scoping-guide-for-cloud', 'Asset scoping guide for cloud', 'guidance'),
    ('assessment-evidence-guide-for-enterprise-it', 'Assessment evidence guide for enterprise IT', 'evidence-it'),
)
ISM_URL = 'https://raw.githubusercontent.com/AustralianCyberSecurityCentre/ism-oscal/main/ISM_catalog.json'
PDF_LICENCE = ('CC BY 4.0, Commonwealth of Australia 2026; excludes the Coat of Arms, '
               'entity logo, third-party content and material otherwise stated.')


def _plain(value):
    return re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()


class PublicationPage(HTMLParser):
    """Read links and dates inside the publication article, excluding navigation."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.links, self.dates = [], []
        self.link = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'article':
            self.depth += 1
        if not self.depth:
            return
        if tag == 'time' and values.get('datetime'):
            self.dates.append(values['datetime'][:10])
        if tag == 'a':
            self.link = [values.get('href', ''), '']
            self.links.append(self.link)

    def handle_data(self, data):
        if self.depth and self.link is not None:
            self.link[1] += data

    def handle_endtag(self, tag):
        if tag == 'a':
            self.link = None
        if tag == 'article' and self.depth:
            self.depth -= 1


def attachment(page, title, extension):
    """Reject ambiguous downloads instead of guessing from their position."""
    title_words = _plain(title)
    pattern = r'\b' + r'\b.*\b'.join(map(re.escape, title_words.split())) + r'\b'
    candidates = set()
    for href, label in page.links:
        url = urljoin(BASE, href)
        path = urlsplit(url).path
        if path.casefold().endswith(extension) and (
                re.search(pattern, _plain(label)) or re.search(pattern, _plain(unquote(path)))):
            if extension == '.pdf' and any(word in _plain(label) for word in ('assessment workbook', 'asset scoping')) and 'scoping' not in title_words:
                continue
            candidates.add(url)
    if len(candidates) != 1:
        raise PolicyError('The Essentials publisher page has changed or lists ambiguous downloads. The current collection has been kept.', 5)
    return candidates.pop()


def _check_resource_url(url, role):
    parts = urlsplit(url)
    if (parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None, 443)
            or parts.fragment or parts.query):
        raise PolicyError('Invalid Essentials source address.', 5)
    if role == 'ism-principles':
        valid = url == ISM_URL
    else:
        valid = parts.hostname == 'www.cyber.gov.au' and parts.path.startswith('/sites/default/files/')
    if not valid:
        raise PolicyError('An Essentials source is outside its approved publisher location.', 5)


def acquire(download, cancel=None, progress=None):
    """Use the application's bounded, redirect-checked downloader for every file."""
    files, resources = {}, []
    total = 0
    options = {'cancel': cancel} if cancel else {}

    def add(name, title, role, uri, page_uri, edition):
        nonlocal total
        _check_resource_url(uri, role)
        body, final_uri = download(uri, 'ism' if role == 'ism-principles' else 'essentials-it', **options)
        _check_resource_url(final_uri, role)
        total += len(body)
        if total > 24 * 1024 * 1024:
            raise PolicyError('The Essentials collection exceeds the supported source limit.', 5)
        files[name] = body
        resources.append(dict(id=name.rsplit('.', 1)[0], filename=name, title=title, role=role,
            uri=final_uri, pageUri=page_uri, edition=edition, sha256=hashlib.sha256(body).hexdigest()))

    for slug, title, role in PUBLICATIONS:
        if cancel and cancel.is_set():
            raise KeyboardInterrupt
        if progress:
            progress('Downloading Essentials: ' + title + '…')
        page_uri = BASE + '/publication/' + slug
        body, final = download(page_uri, 'essentials-it', **options)
        if final != page_uri:
            raise PolicyError('An Essentials publication moved. Review the new source before updating.', 5)
        page = PublicationPage()
        page.feed(body.decode('utf-8'))
        if not page.dates or any(date != EDITION for date in page.dates):
            raise PolicyError('A new Essentials edition needs a reader update. The installed collection has been kept.', 5)
        add(slug + '.pdf', title, role, attachment(page, title, '.pdf'), page_uri, EDITION)
        if role == 'chapter-it':
            add('enterprise-assessment-workbook.xlsx', 'Enterprise IT assessment workbook', 'workbook',
                attachment(page, 'Assessment Workbook', '.xlsx'), page_uri, EDITION)
    add('ISM_catalog.json', 'ISM cyber security principles', 'ism-principles', ISM_URL,
        'https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/ism/ism-oscal-releases', '')
    manifest = dict(format='PolicyCompassEssentialsSources', version=1, edition=EDITION, resources=resources)
    return pack(files, manifest)


def pack(files, manifest):
    """Deterministic archive: unchanged publisher bytes produce an unchanged hash."""
    stream = io.BytesIO()
    entries = dict(files, **{'manifest.json': json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode('utf-8')})
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, entries[name])
    raw = stream.getvalue()
    if len(raw) > MAX_BYTES:
        raise PolicyError('The Essentials source snapshot exceeds 16 MiB.', 5)
    return raw


def unpack(raw):
    """Never extract archive paths onto disk or trust an embedded source digest."""
    if len(raw) > MAX_BYTES:
        raise PolicyError('The Essentials source snapshot exceeds 16 MiB.', 5)
    expected = {slug + '.pdf': role for slug, _, role in PUBLICATIONS}
    expected.update({'enterprise-assessment-workbook.xlsx': 'workbook', 'ISM_catalog.json': 'ism-principles'})
    with checked_archive(raw) as archive:
        if set(archive.namelist()) != set(expected) | {'manifest.json'}:
            raise PolicyError('The Essentials snapshot must contain the complete publication collection.', 5)
        if archive.getinfo('manifest.json').file_size > 65536:
            raise PolicyError('Essentials source manifest is too large.', 5)
        manifest = json.loads(archive.read('manifest.json'))
        if (manifest.get('format') != 'PolicyCompassEssentialsSources' or manifest.get('version') != 1
                or manifest.get('edition') != EDITION or len(manifest.get('resources', [])) != len(expected)):
            raise PolicyError('Unsupported Essentials source snapshot.', 5)
        files = {}
        for item in manifest['resources']:
            name = item.get('filename')
            if name in files or name not in expected or item.get('role') != expected[name]:
                raise PolicyError('Duplicate or unexpected Essentials source.', 5)
            _check_resource_url(item['uri'], item['role'])
            if item.get('id') != name.rsplit('.', 1)[0]:
                raise PolicyError('Invalid Essentials source identifier.', 5)
            if item['role'] not in ('ism-principles', 'workbook'):
                slug = name.removesuffix('.pdf')
                definition = next(entry for entry in PUBLICATIONS if entry[0] == slug)
                if item.get('pageUri') != BASE + '/publication/' + slug or item.get('title') != definition[1]:
                    raise PolicyError('Essentials source metadata does not match its publication.', 5)
            if item['role'] != 'ism-principles' and item.get('edition') != EDITION:
                raise PolicyError('Essentials source editions are inconsistent.', 5)
            body = archive.read(name)
            if hashlib.sha256(body).hexdigest() != item['sha256']:
                raise PolicyError('An Essentials source does not match its recorded fingerprint.', 5)
            if name.endswith('.pdf') and not body.startswith(b'%PDF-'):
                raise PolicyError('An Essentials publication is not a PDF.', 5)
            files[name] = body
    return files, manifest
