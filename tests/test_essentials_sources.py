"""Collection downloads stay complete, bounded and tied to their publisher bytes."""
from copy import deepcopy
import hashlib
import io
import json
import threading
import unittest
import zipfile
from unittest.mock import patch

from policycompass import essentials_sources as sources, updates
from policycompass.contracts import PolicyError


def synthetic_downloads():
    result = {}
    for slug, title, role in sources.PUBLICATIONS:
        url = sources.BASE + '/sites/default/files/2026-10/' + slug + '.pdf'
        label = 'ASD Essentials series Reading guide' if slug == 'essentials-reading-guide' else title
        links = '<a href="' + url + '">' + label + ' pdf</a>'
        result[url] = ('%PDF-1.4\nSynthetic source ' + slug).encode()
        if role == 'chapter-it':
            workbook_url = sources.BASE + '/sites/default/files/2026-10/workbook.xlsx'
            links += '<a href="' + workbook_url + '">Assessment Workbook xlsx</a>'
            result[workbook_url] = b'Synthetic workbook (acquisition only)'
        result[sources.BASE + '/publication/' + slug] = (
            '<nav><a href="https://evil.example/ad.pdf">' + title + '</a></nav>'
            '<article><time datetime="2026-10-15T12:00:00Z"></time>' + links + '</article>').encode()
    result[sources.ISM_URL] = b'{"synthetic":"principles, acquisition only"}'
    return result


class EssentialsSourcesTests(unittest.TestCase):
    def download(self, url, framework, **kwargs):
        updates.approved_url(url, framework)
        return self.downloads[url], url

    def setUp(self):
        self.downloads = synthetic_downloads()

    def test_complete_deterministic_collection_and_fingerprints(self):
        raw = sources.acquire(self.download)
        self.assertEqual(raw, sources.acquire(self.download))
        files, manifest = sources.unpack(raw)
        self.assertEqual(len(files), 19)
        self.assertEqual(sum(name.endswith('.pdf') for name in files), 17)
        for resource in manifest['resources']:
            self.assertEqual(resource['sha256'], hashlib.sha256(files[resource['filename']]).hexdigest())

    def test_missing_changed_or_ambiguous_publication_is_rejected(self):
        page = sources.BASE + '/publication/essentials-reading-guide'
        original = self.downloads[page]
        self.downloads[page] = original.replace(b'2026-10-15', b'2026-11-15')
        with self.assertRaises(PolicyError):
            sources.acquire(self.download)
        self.downloads[page] = original.replace(b'</article>', b'<a href="/sites/default/files/other.pdf">Essentials reading guide pdf</a></article>')
        with self.assertRaises(PolicyError):
            sources.acquire(self.download)

    def test_partial_and_tampered_snapshots_are_rejected(self):
        files, manifest = sources.unpack(sources.acquire(self.download))
        missing = deepcopy(files)
        missing.pop('essentials-for-cloud.pdf')
        with self.assertRaises(PolicyError):
            sources.unpack(sources.pack(missing, manifest))
        files['essentials-for-cloud.pdf'] += b'changed'
        with self.assertRaises(PolicyError):
            sources.unpack(sources.pack(files, manifest))

    def test_publisher_addresses_and_cancellation(self):
        for url in ('https://evil.example/a.pdf', 'http://www.cyber.gov.au/sites/default/files/a.pdf',
                    'https://www.cyber.gov.au:444/sites/default/files/a.pdf',
                    'https://www.cyber.gov.au/sites/default/files/a.pdf?redirect=elsewhere'):
            with self.subTest(url=url), self.assertRaises(PolicyError):
                sources._check_resource_url(url, 'chapter-it')
        event = threading.Event()
        event.set()
        with self.assertRaises(KeyboardInterrupt):
            sources.acquire(self.download, cancel=event)

    def test_unexpected_members_and_duplicate_resource_roles_are_rejected(self):
        files, manifest = sources.unpack(sources.acquire(self.download))
        files['unexpected.txt'] = b'never read'
        with self.assertRaises(PolicyError):
            sources.unpack(sources.pack(files, manifest))
        files.pop('unexpected.txt')
        manifest['resources'][1] = deepcopy(manifest['resources'][0])
        with self.assertRaises(PolicyError):
            sources.unpack(sources.pack(files, manifest))


if __name__ == '__main__':
    unittest.main()
