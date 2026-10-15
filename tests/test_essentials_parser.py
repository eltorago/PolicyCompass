"""Synthetic parser checks; optional live sources are never committed as fixtures."""
import io
import unittest
from unittest.mock import patch
import zipfile

from policycompass import essentials_parser as parser
from policycompass.contracts import PolicyError


def pdf_bytes(pages):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    font_ref = writer._add_object(font)
    for commands in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font_ref})})
        stream = DecodedStreamObject()
        stream.set_data('\n'.join(commands).encode('ascii'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


def text(x, y, value, size=9):
    value = value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return f'BT /F1 {size} Tf {x} {y} Td ({value}) Tj ET'


def table(x, y, widths, rows, height=24):
    commands = []
    for i in range(len(rows)+1):
        commands.append(f'{x} {y-i*height} m {x+sum(widths)} {y-i*height} l S')
    current = x
    for width in [*widths, 0]:
        commands.append(f'{current} {y} m {current} {y-len(rows)*height} l S')
        current += width
    for ri, row in enumerate(rows):
        current = x
        for width, cell in zip(widths, row):
            commands.append(text(current+4, y-ri*height-16, cell, 8))
            current += width
    return commands


def synthetic_evidence():
    """All 58 IDs, with one reference table split over two pages."""
    pages, seen = [], set()
    references = [['ISM (excl. E8)', 'ISM-0001'], ['E8', 'N/A'], ['CSF', 'GV.OC-01'],
                  ['800-171r3', '03.15.01'], ['AESCSF', 'PROGRAM-2a']]
    for index, action in enumerate(parser.IT_ACTIONS):
        principle = action.split('.')[1]
        commands = []
        y = 750
        if principle not in seen:
            commands.extend([text(40, y, principle+' - Synthetic principle'), text(40, y-18, 'Principle: Synthetic security outcome.')])
            y -= 40
            seen.add(principle)
        commands.extend([text(40, y, action), text(40, y-20, 'Action: Retain synthetic records.'),
                         text(40, y-40, 'Domains: Governance and culture; Mitigated Techniques: N/A;'),
                         text(40, y-60, 'Indicators of Good Practice')])
        commands += table(40, y-80, [170, 170, 170], [['Not effective', 'Partially effective', 'Fully effective'],
                                                    ['NE-1: No records.', 'PE-1: Some records.', 'FE-1: Records retained.']])
        commands += table(40, y-160, [140, 370], [['Framework', 'References'], *(references[:2] if index==0 else references)])
        pages.append(commands)
        if index == 0:
            pages.append(table(40, 750, [140, 370], [['Framework', 'References'], *references[2:]]))
    return pdf_bytes(pages)


def workbook(extra=None):
    names = ['How to use', 'Domain Summary', 'Principle Summary', 'Existing E8 Controls',
             *parser.CAPABILITIES, *parser.DOMAINS, 'Data']
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    entries = {'xl/workbook.xml': ('<workbook xmlns="'+ns+'"><sheets>'+''.join(
        f'<sheet name="{name}" sheetId="{i}"/>' for i,name in enumerate(names, 1))+'</sheets></workbook>').encode(),
        'xl/worksheets/sheet1.xml': ('<worksheet xmlns="'+ns+'"><sheetData><row><c><f>WEBSERVICE(&quot;https://invalid.test/&quot;)</f></c></row></sheetData></worksheet>').encode()}
    entries.update(extra or {})
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return stream.getvalue()


class EssentialsParserTests(unittest.TestCase):
    def test_striped_rows_without_vertical_borders_are_preserved(self):
        commands = [text(40, 750, 'Visibility and response'), '0.8 g 40 678 530 22 re f 0 g',
                    text(45, 685, 'Principle'), text(205, 685, 'Action')]
        values = [('IDE-01 - Asset identification', 'Retain inventory.'),
                  ('IDE-02 - Business criticality', 'Identify critical services.'),
                  ('', 'Record their dependencies.'), ('RES-03 - Incident response', 'Use response procedures.')]
        for i, row in enumerate(values):
            y = 678-i*48
            if i % 2 == 0:
                commands += [f'0.9 g 40 {y-48} 530 48 re f 0 g', f'200 {y} m 200 {y-48} l S']
            commands += [text(45, y-26, row[0], 8), text(205, y-26, row[1], 8)]
        for y in [700, 678, 630, 582, 534, 486]:
            commands.append(f'40 {y} m 570 {y} l S')
        commands.append('200 700 m 200 678 l S')
        with patch.dict(parser.EXPECTED, {'chapter-ot': (4, 3, (0, 4, 0))}):
            result = parser._matrix(pdf_bytes([commands]), 'chapter-ot')
        self.assertEqual([r['principle'] for r in result], ['IDE-01', 'IDE-02', 'IDE-02', 'RES-03'])
        self.assertEqual(result[-1]['text'], 'Use response procedures.')

    def test_reference_table_continuation_keeps_its_original_action(self):
        raw = synthetic_evidence()
        with parser._open_pdf(raw) as pdf:
            pages = []
            for page in pdf.pages:
                pages.append(page.extract_text())
                page.close()
        actions, definitions = parser._evidence(raw, pages)
        first = actions[parser.IT_ACTIONS[0]]
        second = actions[parser.IT_ACTIONS[1]]
        self.assertEqual(len(actions), 58)
        self.assertEqual(len(definitions), 28)
        self.assertEqual(first['referencePages']['ISM (excl. E8)'], 1)
        self.assertEqual(first['referencePages']['CSF'], 2)
        self.assertEqual(second['referencePages']['CSF'], 3)

    def test_cloud_unknown_responsibility_is_not_filled_from_other_rows(self):
        header = ['Principle','Cloud actions','PaaS shared responsibility','SaaS shared responsibility','MITRE ATT&CK','Identity services']
        values = ['PRO-09 - Content filtering', 'Inspect outbound flows.', '', '', '', '']
        with self.assertRaises(PolicyError):
            parser._matrix_row(header, values, None, 'Technical domains', {'page':1}, [])
        values[-1] = '✔'
        result, _ = parser._matrix_row(header, values, None, 'Technical domains', {'page':1}, [])
        self.assertEqual(result['responsibility'], {'paas': None, 'saas': None})
        values[2] = 'Unknown'
        with self.assertRaises(PolicyError):
            parser._matrix_row(header, values, None, 'Technical domains', {'page':1}, [])

    def test_enterprise_join_accepts_reviewed_variant_and_rejects_semantic_drift(self):
        chapter = 'Identify unsecured keys and secrets.'
        parser._join_action('IT.PRO-13.3', chapter, 'Identify and remediate unsecured keys and secrets.')
        for wrong in ['Identify and publish unsecured keys and secrets.', 'Do not identify unsecured keys and secrets.']:
            with self.subTest(wrong=wrong), self.assertRaises(PolicyError):
                parser._join_action('IT.PRO-13.3', chapter, wrong)
        with self.assertRaises(PolicyError):
            parser._join_action('IT.PRO-13.4', chapter, 'Identify and remediate unsecured keys and secrets.')

    def test_phase_order_retains_ot_difference_and_capabilities(self):
        self.assertEqual(parser._phases('chapter-it', ['Identity services'])['Identity services'], [1])
        self.assertEqual(parser._phases('chapter-ot', ['Identity services'])['Identity services'], [2])
        self.assertEqual(parser._phases('chapter-ot', ['Critical processes and services'])['Critical processes and services'], [1])
        self.assertEqual(parser._phases('chapter-cloud', list(parser.CAPABILITIES)), {d:[1,2,3] for d in parser.CAPABILITIES})

    def test_workbook_formulas_are_counted_without_execution(self):
        info = parser._workbook(workbook())
        self.assertEqual(info['sheetCount'], 13)
        self.assertEqual(info['formulaCount'], 1)
        for extra in [{'xl/vbaProject.bin': b'macro'}, {'xl/test.xml': b'<!DOCTYPE x [<!ENTITY y "z">]><x/>'}]:
            with self.subTest(extra=list(extra)), self.assertRaises(PolicyError):
                parser._workbook(workbook(extra))

    def test_source_groups_and_external_framework_references_remain_distinct(self):
        source = {'uri':'https://www.cyber.gov.au/source.pdf','sha256':'a'*64,'edition':'2026-10-15'}
        evidence = {'references': {'ISM (excl. E8)':'ISM-0041','E8':'ISM-0041','800-171r3':'03.15.01'},
                    'referencePages': {'ISM (excl. E8)': 5, 'E8': 5, '800-171r3': 6}}
        refs = parser._references(evidence, source)
        self.assertEqual(len(refs), 3)
        self.assertEqual(refs[0]['targetId'], refs[1]['targetId'])
        self.assertNotEqual(refs[0]['sourceGroup'], refs[1]['sourceGroup'])
        self.assertEqual(refs[-1]['frameworkId'], 'nist-800-171')
        self.assertEqual(refs[-1]['sourcePage'], 6)
        self.assertTrue(all(r['relationship']=='PotentialEvidenceFor' for r in refs))
        evidence['references']['800-171r3'] = 'see unrelated document'
        with self.assertRaises(PolicyError):
            parser._references(evidence, source)

    def test_wrong_publication_cover_is_rejected(self):
        with self.assertRaises(PolicyError):
            parser._resource_text(pdf_bytes([[text(40,750,'Unrelated publication')]]), 'Essentials reading guide')


if __name__ == '__main__':
    unittest.main()
