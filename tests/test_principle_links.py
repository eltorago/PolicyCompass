import copy
import json
from pathlib import Path
import unittest

from policycompass import principle_links, references
from test_policy_review import temporary


ASSET = Path(principle_links.__file__).parent / 'assets' / 'essentials-topic-links.json'


class PrincipleLinkTests(unittest.TestCase):
    def setUp(self):
        self.asset = json.loads(ASSET.read_text(encoding='utf-8'))
        source = self.asset['source']
        self.metadata = dict(id='asd-principles', edition=source['edition'], sourceHash=source['sourceHash'])

    def rows(self):
        return [dict(id=uid, frameworkId='asd-principles', authoritativeText='Independent principle outcome.')
                for uid in sorted({link['principleId'] for link in self.asset['links']})]

    def test_reviewed_links_retain_attribution_versions_and_independent_text(self):
        rows = self.rows()
        before = copy.deepcopy(rows)
        self.assertIs(principle_links.enrich(rows, self.metadata), rows)
        refs = [reference for row in rows for reference in row['frameworkReferences']]
        self.assertEqual(len(refs), 94)
        self.assertEqual(len({(r['principleId'], r['targetId']) for r in self.asset['links']}), 94)
        for old, row in zip(before, rows):
            self.assertEqual({key: row[key] for key in old}, old)
        for reference in refs:
            target = self.asset['targets'][reference['frameworkId']]
            self.assertEqual(reference['kind'], principle_links.KIND)
            self.assertEqual(reference['relationship'], 'TopicOverlap')
            self.assertEqual(reference['expectedTargetHash'], target['sourceHash'])
            self.assertEqual(reference['targetEdition'], target['edition'])
            self.assertEqual(reference['sourceHash'], self.asset['source']['sourceHash'])
            self.assertTrue(reference['basis'])
        self.assertIn(principle_links.REVIEW_NOTICE, self.metadata['notices'])

    def test_repeat_enrichment_preserves_publisher_references_without_duplicates(self):
        rows = self.rows()
        publisher = {'kind': 'Publisher', 'relationship': 'EvidenceSource', 'sourceHash': self.metadata['sourceHash']}
        rows[0]['frameworkReferences'] = [publisher]
        principle_links.enrich(rows, self.metadata)
        once = copy.deepcopy((rows, self.metadata))
        principle_links.enrich(rows, self.metadata)
        self.assertEqual((rows, self.metadata), once)
        self.assertIn(publisher, rows[0]['frameworkReferences'])

    def test_changed_source_hash_or_edition_withholds_and_removes_old_interpretations(self):
        for field, changed in [('sourceHash', '0' * 64), ('edition', '2027.01')]:
            with self.subTest(field=field):
                rows, metadata = self.rows(), copy.deepcopy(self.metadata)
                principle_links.enrich(rows, metadata)
                metadata[field] = changed
                principle_links.enrich(rows, metadata)
                self.assertFalse(any(row.get('frameworkReferences') for row in rows))
                self.assertEqual(metadata['notices'], [principle_links.SOURCE_CHANGED])

    def test_unselected_or_changed_target_does_not_produce_a_mapping(self):
        rows = self.rows()
        principle_links.enrich(rows, self.metadata)
        row = rows[0]
        reference = row['frameworkReferences'][0]
        row['frameworkReferences'] = [reference]
        target_row = {'id': reference['targetId'], 'frameworkId': reference['frameworkId']}
        target_metadata = dict(id=reference['frameworkId'], edition=reference['targetEdition'],
                               sourceHash=reference['expectedTargetHash'])
        self.assertEqual(references.resolve([row], [self.metadata]), [])
        self.assertEqual(reference['status'], 'Framework not selected')
        self.assertEqual(len(references.resolve([row, target_row], [self.metadata, target_metadata])), 1)
        for field, changed in [('sourceHash', '0' * 64), ('edition', 'Unreviewed edition')]:
            with self.subTest(field=field):
                modified = dict(target_metadata, **{field: changed})
                self.assertEqual(references.resolve([row, target_row], [self.metadata, modified]), [])

    def test_principle_links_are_not_inherited_by_chapter_actions(self):
        rows = [dict(id='essentials-it:it.pro-13.4', frameworkId='essentials-it',
                     essentials={'principleId': 'PRO-13'}, authoritativeText='A narrower action.')]
        metadata = dict(self.metadata, id='essentials-it')
        before = copy.deepcopy((rows, metadata))
        principle_links.enrich(rows, metadata)
        self.assertEqual((rows, metadata), before)


class PspfRowBoundaryTests(unittest.TestCase):
    def test_text_crossing_retired_row_border_does_not_leak_into_next_requirement(self):
        from pypdf import PdfWriter
        from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
        import pdfplumber
        from policycompass.pspf_parser import parse, _tables

        with temporary() as folder:
            path = Path(folder) / 'row-border.pdf'
            content = []
            def line(x1, y1, x2, y2):
                content.append(f'{x1} {y1} m {x2} {y2} l S')
            def text(x, y, value, size=8):
                value = value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
                content.append(f'BT /F1 {size} Tf {x} {y} Td ({value}) Tj ET')
            xs = [20, 60, 410, 450, 550, 640, 710, 780, 880]
            ys = [390, 370, 350, 290, 260, 230]
            for y in ys:
                line(xs[0], y, xs[-1], y)
            for x in (xs[0], xs[-1]):
                line(x, ys[-1], x, ys[0])
            for x in xs[1:-1]:
                line(x, ys[-1], x, 370)
            text(23, 378, 'PSPF Release 2026 (July 2026) - List of Requirements')
            headers = ['Req Number', 'Release 26 Requirement', 'Domain', 'Section', 'Applicability',
                       'Start Date', 'Decision', 'Question Mandatory']
            for x, value in zip(xs, headers):
                text(x + 2, 360, value, 6)
            for number, statement, y, decision in [
                ('92', 'Retired social media rule.', 330, 'Retire'),
                ('93', 'Use mitigations for legacy systems.', 273, 'Retain'),
                ('94', 'Protect other assets.', 243, 'Retain')]:
                values = [number, statement, 'TECH', 'Lifecycle', 'All entities', '1/07/2026', decision, 'Mandatory']
                for x, value in zip(xs, values):
                    text(x + 2, y, value)
            # Its top is above the row border, but its midpoint is below it.
            text(62, 285, 'Remove retired application.', 10)
            writer = PdfWriter()
            page = writer.add_blank_page(width=900, height=450)
            font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                                     NameObject('/BaseFont'): NameObject('/Helvetica')})
            page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data('\n'.join(content).encode('ascii'))
            page[NameObject('/Contents')] = writer._add_object(stream)
            writer.write(path)
            with pdfplumber.open(path) as opened:
                raw = next(row for table in opened.pages[0].extract_tables() for row in table if row[0] == '93')
                self.assertIn('Remove retired application.', raw[1])
                corrected = next(row for table in _tables(opened.pages[0], None) for row in table if row[0] == '92')
                self.assertIn('Remove retired application.', corrected[1])
            _, rows = parse(path)
            by_id = {row['id']: row for row in rows}
            self.assertEqual(set(by_id), {'pspf:req 93', 'pspf:req 94'})
            self.assertEqual(by_id['pspf:req 93']['authoritativeText'], 'Use mitigations for legacy systems.')
            self.assertEqual(by_id['pspf:req 94']['authoritativeText'], 'Protect other assets.')


if __name__ == '__main__':
    unittest.main()
