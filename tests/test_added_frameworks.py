"""Synthetic publisher fixtures for framework imports and versioned comparisons."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_policy_review import temporary
from test_framework_updates import fixture
from policycompass import corpus, documents, framework_import, reports, service, store, updates
from policycompass.cli import parser, execute
from policycompass.contracts import PolicyError
from policycompass.frameworks import AUTOMATIC, NAMES


def workbook(sheet, rows, extra=None):
    output = BytesIO()
    cells = []
    for i, row in enumerate(rows, 1):
        cells.append('<row>' + ''.join('<c r="%s%d" t="inlineStr"><is><t>%s</t></is></c>' %
            (chr(65+j), i, escape(str(value))) for j, value in enumerate(row)) + '</row>')
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets></workbook>' % escape(sheet))
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(cells) + '</sheetData></worksheet>')
        for name, value in (extra or {}).items():
            z.writestr(name, value)
    return output.getvalue()


def csf_fixture():
    return workbook('CSF 2.0', [
        ['The NIST Cybersecurity Framework 2.0'],
        ['Function', 'Category', 'Subcategory', 'Implementation Examples', 'Informative References'],
        ['GOVERN (GV): Synthetic governance outcomes'],
        ['', 'Policy (GV.PO): Synthetic policy category'],
        ['', '', 'GV.PO-01: Synthetic backup restoration is tested quarterly.'],
        ['', '', 'GV.PO-99: [Withdrawn: Moved to GV.PO-01]']])


def aescsf_fixture():
    return workbook('AESCSF synthetic v2', [
        ['Domain', 'Objective ID', 'Objective', 'Practice ID', 'Practice', 'Maturity Indicator Level', 'Security Profile', 'Australian References'],
        ['TEST', 'TEST-1', 'Synthetic objective', 'TEST-1a', 'Synthetic backup restoration is tested quarterly.', 'MIL1', 'SP1', 'Security Control: ISM-9999']])


def ism_fixture():
    data = json.loads(fixture())
    controls = data['catalog']['controls']
    controls[0]['props'] = [{'name': 'essential-eight-applicability', 'value': level} for level in ('ML1', 'ML2', 'ML3')]
    extra = deepcopy(controls[0]); extra['id'] = 'ism-9998'; extra['props'] = []
    controls.append(extra)
    return json.dumps(data).encode()


def nist_fixture(version='5.2.0'):
    data = json.loads(fixture(version))
    data['catalog']['metadata']['title'] = 'NIST SP 800-53 synthetic test catalogue'
    controls = data['catalog']['controls']
    controls[0]['id'] = 'ac-1'
    child = deepcopy(controls[0]); child['id'] = 'ac-1.1'
    controls[0]['controls'] = [child]
    retired = deepcopy(child); retired['id'] = 'ac-2'; retired['props'] = [{'name': 'status', 'value': 'withdrawn'}]
    controls.append(retired)
    return json.dumps(data).encode()


def wa_pdf(path, year=2026):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    pages = [
        [(50, 740, 16, 'Western Australian Government'), (50, 710, 16, 'Cyber Security Policy'), (50, 680, 16, str(year))],
        [(50, 740, 14, 'Contents'), (50, 710, 12, '1. Govern ..................3'),
         (50, 685, 12, '1.1 Responsibilities ..................3'),
         (50, 660, 12, '3. Protect ..................3'), (50, 635, 12, '3.1 Essential Controls ..................3')],
        [(50, 740, 28, '1. Govern'), (50, 700, 14, '1.1 Responsibilities'), (80, 670, 12, 'a. Synthetic roles are assigned.'),
         (50, 625, 28, '3. Protect'), (80, 595, 12, 'Synthetic controls are due by December 2028.'),
         (50, 565, 14, '3.1 Essential Controls'), (80, 535, 12, 'Synthetic conditions apply.'),
         (80, 505, 13, '3.1.1 Synthetic patching'), (80, 475, 12, 'a. Synthetic applications are patched.'),
         (105, 450, 12, 'i. A nested condition stays with its parent.'),
         (80, 420, 12, 'b. Synthetic scans run weekly.'),
         (50, 365, 28, 'Annual Implementation Reporting'), (50, 335, 12, 'This separate guidance must not enter a requirement.'),
         (50, 80, 9, '7 A footnote must not enter a requirement.'),
         (50, 40, 8, str(year) + ' WA Government Cyber Security Policy | 3')]]
    writer = PdfWriter()
    for entries in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'):NameObject('/Font'), NameObject('/Subtype'):NameObject('/Type1'), NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        content = '\n'.join('BT /F1 %d Tf %d %d Td (%s) Tj ET' % (size, x, y, text) for x,y,size,text in entries)
        stream = DecodedStreamObject(); stream.set_data(content.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as output:
        writer.write(output)


class AddedFrameworkTests(unittest.TestCase):
    def test_choices_and_default_batch_match_requested_scope(self):
        self.assertEqual(set(NAMES), {'wa-csp','ism','aescsf','asd-strategies','csf','pspf','nist-800-53'})
        self.assertEqual(set(AUTOMATIC), set(NAMES)-{'aescsf'})
        for key in NAMES:
            self.assertEqual(parser().parse_args(['corpus','update','--framework',key]).update_frameworks,[key])

    def test_wa_discovery_prefers_2026_and_excludes_overview_and_draft(self):
        html = b'<a href="/2024.pdf">WA Government Cyber Security Policy 2024</a><a href="/2026.pdf">2026 WA Cyber Security Policy</a><a href="/overview.pdf">WA Cyber Security Policy overview 2028</a><a href="/draft.pdf">2029 WA Cyber Security Policy draft</a>'
        with patch.object(updates, 'download', return_value=(html, updates.PAGES['wa-csp'])):
            self.assertEqual(updates.discover('wa-csp'), 'https://www.wa.gov.au/2026.pdf')

    def test_pspf_discovery_selects_requirements_not_guidelines(self):
        html=b'<a href="/pspf-release-2026-guidelines.pdf">Guidelines</a><a href="/pspf-release-2026-list-requirements.pdf">Requirements</a>'
        with patch.object(updates,'download',return_value=(html,updates.PAGES['pspf'])):
            self.assertTrue(updates.discover('pspf').endswith('list-requirements.pdf'))

    def test_new_download_boundaries(self):
        for key,url in [('nist-800-53','https://raw.githubusercontent.com/other/catalog.json'), ('csf','https://evil.example/file.xlsx'), ('pspf','http://www.protectivesecurity.gov.au/a.pdf')]:
            with self.subTest(key=key), self.assertRaises(PolicyError):
                updates.approved_url(url,key)

    def test_csf_import_counts_subcategories_only(self):
        with temporary() as root:
            path=root/'csf.xlsx';path.write_bytes(csf_fixture())
            value=documents.extract_worker(path,framework='csf')
            self.assertEqual([r['officialReference'] for r in value['requirements']],['GV.PO-01'])
            self.assertEqual(value['framework']['edition'],'2.0')
            self.assertIn('Synthetic policy category',value['requirements'][0]['context'])

    def test_csf_rejects_macro_and_entity_workbooks(self):
        with temporary() as root:
            for extra in [{'xl/vbaProject.bin':b'fake'}, {'xl/test.xml':b'<!DOCTYPE x [<!ENTITY a "b">]><x/>'}]:
                path=root/'bad.xlsx';path.write_bytes(workbook('CSF 2.0',[],extra))
                with self.assertRaises(PolicyError):framework_import.parse('csf',path)

    def test_nist_import_preserves_enhancements_and_excludes_withdrawn(self):
        with temporary() as root:
            path=root/'nist.json';path.write_bytes(nist_fixture())
            value=documents.extract_worker(path,framework='nist-800-53')
            self.assertEqual({r['id'] for r in value['requirements']},{'nist-800-53:ac-1','nist-800-53:ac-1.1'})
            self.assertEqual(value['framework']['edition'],'5.2.0')

    def test_nist_rejects_wrong_catalogue_and_duplicate_ids(self):
        with temporary() as root:
            path=root/'nist.json';path.write_bytes(fixture())
            with self.assertRaises(PolicyError):framework_import.parse('nist-800-53',path)
            value=json.loads(nist_fixture());value['catalog']['controls'].append(deepcopy(value['catalog']['controls'][0]))
            path.write_text(json.dumps(value))
            with self.assertRaises(PolicyError):framework_import.parse('nist-800-53',path)

    def test_asd_strategies_worker_keeps_ratings_and_rejects_changed_edition(self):
        from framework_core.loaders.extended import STRATEGY_TITLES
        html = ['<h1>Strategies to mitigate cyber security incidents (February 2017)</h1><table>']
        for i, title in enumerate(STRATEGY_TITLES):
            if i % 8 == 0:
                html.append('<tr><td>Mitigation strategies - synthetic category %d</td></tr>' % (i//8))
            html.append('<tr><td>%s</td><td>%s. Synthetic test description.</td><td>Low</td><td>Low</td><td>Low</td></tr>' % ('Essential' if i < 8 else 'Good', title))
        html.append('</table>')
        with temporary() as root:
            path=root/'strategies.html';path.write_text(''.join(html),encoding='utf-8')
            value=documents.extract_worker(path,framework='asd-strategies')
            self.assertEqual(len(value['requirements']),37)
            self.assertEqual(sum('rating: Essential' in r['context'] for r in value['requirements']),8)
            path.write_text(''.join(html).replace('February 2017','October 2026'),encoding='utf-8')
            with self.assertRaises(PolicyError):documents.extract_worker(path,framework='asd-strategies')

    def test_ism_maturity_uses_original_ids_and_survives_save_and_export(self):
        with temporary() as root, patch.dict(os.environ,{'POLICYCOMPASS_FRAMEWORK_CACHE':str(root/'cache')}):
            path=root/'ism.json';path.write_bytes(ism_fixture())
            self.assertEqual(updates.update(['ism'],path)[0]['status'],'Updated')
            source=root/'policy.txt';source.write_text('Synthetic policy evidence is retained.')
            run=service.analyse([source],framework='ism',also=['ism'],scope='Synthetic',ism_maturity='ML2')
            self.assertEqual([r['id'] for r in run['requirements']],['ism:ism-9999'])
            self.assertEqual(run['versions']['frameworks'][0]['profile'],'ML2')
            saved=root/'test.policycompass';store.save(saved,run);state=store.load(saved)
            self.assertEqual(state['run'],run)
            for format in ('json','html','markdown','csv'):
                self.assertIn('ML2',reports.render(state,format))
            import jsonschema
            jsonschema.validate(run,json.loads((ROOT/'schemas/policy/run.schema.json').read_text()))

    def test_maturity_filter_fails_without_tags_or_ism(self):
        with temporary() as root, patch.dict(os.environ,{'POLICYCOMPASS_FRAMEWORK_CACHE':str(root/'cache')}):
            path=root/'ism.json';path.write_bytes(fixture());updates.update(['ism'],path)
            with self.assertRaisesRegex(PolicyError,'no Essential Eight maturity tags'):corpus.load('ism',ism_maturity='ML1')
            with self.assertRaises(PolicyError):corpus.select_ism_maturity({'frameworks':[{'id':'csf'}]},'ML1')

    def test_pspf_excludes_retired_and_recommended_rows_preserves_applicability(self):
        from policycompass.pspf_parser import parse
        headers=['Req Number','Release 26 Requirement','Domain','Section','Applicability','Start Date','Decision','Question Mandatory']
        table=[['PSPF Release 2026 (July 2026) - List of Requirements'],headers,
            ['1','Synthetic retained text','GOV','Governance','All entities','01/07/2026','Retain','Not Mandatory'],
            ['2','Synthetic retired text','GOV','Governance','All entities','','Retire','Mandatory'],
            ['PSPF Recommended Approach'],['3','Synthetic guidance','GOV','Governance','','','Retain','']]
        pdf=SimpleNamespace(pages=[SimpleNamespace(extract_tables=lambda:[table])])
        with patch('pdfplumber.open') as opened:
            opened.return_value.__enter__.return_value=pdf
            metadata,rows=parse('unused.pdf')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['officialReference'],'Req 1')
        self.assertIn('All entities',rows[0]['context'])
        self.assertEqual(rows[0]['sourceLocator']['page'],1)

    def test_wa_2026_worker_preserves_nested_references_and_conditions(self):
        with temporary() as root:
            path=root/'wa.pdf';wa_pdf(path)
            value=documents.extract_worker(path,framework='wa-csp')
            rows={r['officialReference']:r for r in value['requirements']}
            self.assertEqual(set(rows),{'1.1a','3.1','3.1.1a','3.1.1b'})
            self.assertIn('nested condition',rows['3.1.1a']['authoritativeText'])
            self.assertIn('December 2028',rows['3.1.1a']['context'])
            self.assertNotIn('footnote',json.dumps(rows))
            self.assertNotIn('separate guidance',json.dumps(rows))
            self.assertTrue(value['framework']['edition'].endswith('2026'))
            self.assertTrue(all(a['rule'] is None for r in corpus._imported_rows(value) for a in r['obligations']))

    def test_wa_unknown_edition_is_rejected(self):
        with temporary() as root:
            path=root/'wa.pdf';wa_pdf(path,2028)
            with self.assertRaises(PolicyError):documents.extract_worker(path,framework='wa-csp')

    def test_new_framework_can_download_compare_and_export_offline_afterwards(self):
        with temporary() as root, patch.dict(os.environ,{'POLICYCOMPASS_FRAMEWORK_CACHE':str(root/'cache'),'POLICYCOMPASS_LIBRARY':str(root/'empty')}):
            with patch.object(updates,'download',return_value=(csf_fixture(),updates.DIRECT_DOWNLOADS['csf'])):
                self.assertEqual(updates.update(['csf'])[0]['status'],'Updated')
            source=root/'policy.txt';source.write_text('Synthetic backup restoration is tested quarterly.')
            with patch.object(updates,'download',side_effect=AssertionError('Comparison must be offline')):
                run=service.analyse([source],framework='csf',scope='Synthetic')
                self.assertEqual(run['requirements'][0]['alignment']['status'],'Mentioned')
                self.assertIn('csf', {f['id'] for f in corpus.installed()['availableFrameworks']})

    def test_update_does_not_change_saved_framework_snapshot(self):
        with temporary() as root, patch.dict(os.environ,{'POLICYCOMPASS_FRAMEWORK_CACHE':str(root/'cache')}):
            path=root/'nist.json';path.write_bytes(nist_fixture('5.1.0'));updates.update(['nist-800-53'],path)
            source=root/'policy.txt';source.write_text('Synthetic policy evidence is retained.')
            run=service.analyse([source],framework='nist-800-53',scope='Synthetic')
            saved=root/'history.policycompass';store.save(saved,run)
            path.write_bytes(nist_fixture('5.2.0'));updates.update(['nist-800-53'],path)
            self.assertEqual(store.load(saved)['run'],run)
            self.assertEqual(corpus.load('nist-800-53')['frameworks'][0]['edition'],'5.2.0')

    def test_aescsf_any_filename_import_and_failed_replacement(self):
        with temporary() as root, patch.dict(os.environ,{'POLICYCOMPASS_FRAMEWORK_CACHE':str(root/'cache')}):
            path=root/'My downloaded core workbook.xlsx';path.write_bytes(aescsf_fixture())
            result=updates.update(['aescsf'],path)
            self.assertEqual(result[0]['status'],'Updated',result)
            original=corpus.load('aescsf')
            self.assertEqual(len(original['requirements']),1)
            path.write_bytes(csf_fixture())
            self.assertEqual(updates.update(['aescsf'],path)[0]['status'],'Failed')
            self.assertEqual(corpus.load('aescsf'),original)

    def test_aescsf_button_does_not_depend_on_download_checkboxes(self):
        import tkinter as tk
        from policycompass.desktop import Desktop
        root=tk.Tk();root.withdraw()
        try:
            app=Desktop(root)
            with patch('policycompass.desktop.filedialog.askopenfilename',return_value='chosen.xlsx') as choose, patch('policycompass.desktop.threading.Thread') as thread, patch.object(updates,'update',return_value=[]) as update:
                thread.side_effect=lambda target,**_:SimpleNamespace(start=target)
                app.update_frameworks(True,'aescsf')
                self.assertEqual(update.call_args.args,(['aescsf'],'chosen.xlsx'))
                self.assertEqual(choose.call_args.kwargs['filetypes'],[('AESCSF Core workbook','*.xlsx')])
        finally:
            for callback in root.tk.call('after','info'):root.after_cancel(callback)
            root.destroy()


if __name__ == '__main__':
    unittest.main()
