"""References stay attributable and never turn into policy evidence."""
from copy import deepcopy
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from test_policy_review import temporary

from policycompass import corpus, references, reports
from policycompass.contracts import PolicyError, fingerprint
from policycompass.frameworks import PAGES


def source_reference(**changes):
    value = dict(frameworkId='ism', reference='ISM-0001', targetId='ism:ism-1', targetEdition='2026.09.4',
        sourceUri='https://www.cyber.gov.au/publication/assessment-evidence-guide-for-enterprise-it',
        sourceHash='a' * 64, sourceEdition='2026-10-15', sourcePage=5, kind='Publisher',
        basis='Potential evidence source, not equivalence', relationship='PotentialEvidenceFor')
    value.update(changes)
    return value


class FrameworkReferenceTests(unittest.TestCase):
    def test_selected_exact_targets_resolve_with_both_source_versions(self):
        ref = source_reference()
        rows = [dict(id='essentials-it:it.gov-01.1', frameworkReferences=[ref]), dict(id='ism:ism-1')]
        mappings = references.resolve(rows, [dict(id='ism', edition='2026.09.4', sourceHash='b' * 64)])
        self.assertEqual(len(mappings), 1)
        self.assertEqual(ref['status'], 'Edition matches')
        self.assertEqual(mappings[0]['relation'], 'MappedOnly')
        self.assertEqual(mappings[0]['sourceReference']['targetSourceHash'], 'b' * 64)
        self.assertEqual(mappings[0]['sourceReference']['sourceHash'], 'a' * 64)

    def test_unsupported_and_missing_references_remain_visible(self):
        refs = [source_reference(frameworkId='nist-800-171', targetId='nist-800-171:03.01.01'),
                source_reference(targetId='ism:ism-9999')]
        row = dict(id='source', frameworkReferences=refs)
        self.assertEqual(references.resolve([row], [dict(id='ism', edition='2026.09.4')]), [])
        self.assertEqual([r['status'] for r in refs], ['Framework not selected', 'Reference absent from selected edition'])
        self.assertEqual(len(row['frameworkReferences']), 2)

    def test_interpretations_require_matching_target_hash_and_edition(self):
        ref = source_reference(kind='PolicyCompass interpretation — needs human review', expectedTargetHash='b' * 64)
        row = dict(id='source', frameworkReferences=[ref])
        rows = [row, dict(id='ism:ism-1')]
        self.assertEqual(len(references.resolve(rows, [dict(id='ism', edition='2026.09.4', sourceHash='b' * 64)])), 1)
        self.assertEqual(references.resolve(rows, [dict(id='ism', edition='2026.09.4', sourceHash='c' * 64)]), [])
        self.assertEqual(ref['status'], 'Target source differs from reviewed version')
        ref.pop('expectedTargetHash')
        self.assertEqual(references.resolve(rows, [dict(id='ism', edition='2027.1', sourceHash='b' * 64)]), [])

    def test_relationships_do_not_modify_existing_alignment_results(self):
        finding = dict(status='Not mentioned', matches=[], matchCount=0)
        rows = [dict(id='source', alignment=deepcopy(finding), frameworkReferences=[source_reference()]),
                dict(id='ism:ism-1', alignment=deepcopy(finding))]
        before = fingerprint([r['alignment'] for r in rows])
        references.resolve(rows, [dict(id='ism', edition='2026.09.4')])
        self.assertEqual(before, fingerprint([r['alignment'] for r in rows]))

    def test_cloud_unknown_responsibility_and_scoped_phases_are_reported(self):
        row = dict(authoritativeText='Inspect outbound flows.', essentials=dict(chapter='Cloud',
            principleReference='PRO-09', principleText='Control transfers.', domains=['Boundary services'],
            phases={'Boundary services':[1]}, referenceKind='PolicyCompass locator', sharedResponsibility={'paas':None,'saas':None}))
        output = reports.essentials_text(row)
        self.assertIn('Not stated by publisher', output)
        self.assertIn('sequence, not maturity', output)

    def test_profile_references_distinguish_excluded_and_missing_targets(self):
        refs = [source_reference(), source_reference(reference='ISM-0002', targetId='ism:ism-2'),
                source_reference(reference='ISM-9999', targetId='ism:ism-9999')]
        rows = [dict(id='source', frameworkId='essentials-it', obligations=[], frameworkReferences=refs),
                dict(id='ism:ism-1', frameworkId='ism', obligations=[], ismMaturityLevels=['ML1']),
                dict(id='ism:ism-2', frameworkId='ism', obligations=[], ismMaturityLevels=[])]
        frameworks = [dict(id='ism', title='ISM', edition='2026.09.4', sourceHash='b' * 64)]
        value = dict(requirements=rows, frameworks=frameworks, mappings=references.resolve(rows, frameworks))
        result = corpus.select_ism_maturity(value, 'ML1')
        self.assertEqual([r['status'] for r in refs], ['Edition matches',
            'Reference outside selected ISM profile', 'Reference absent from selected edition'])
        self.assertEqual([(m['source'], m['target']) for m in result['mappings']], [('source', 'ism:ism-1')])
        self.assertEqual(len(result['requirements']), 2)
        self.assertEqual(refs[1]['resolvedTargetEdition'], '2026.09.4')

    def test_package_framework_selection_refreshes_reference_status(self):
        ref = source_reference()
        rows = [dict(id='source', frameworkId='essentials-it', obligations=[], frameworkReferences=[ref]),
                dict(id='ism:ism-1', frameworkId='ism', obligations=[])]
        frameworks = [dict(id='ism', title='ISM', edition='2026.09.4', sourceHash='b' * 64),
                      dict(id='essentials-it', title='Enterprise IT', edition='2026-10-15')]
        value = dict(requirements=rows, frameworks=frameworks, mappings=references.resolve(rows, frameworks))
        with patch('policycompass.packages.installed', return_value=value):
            result = corpus.load('essentials-it', corpus_version='reviewed-package')
        self.assertEqual(ref['status'], 'Framework not selected')
        self.assertNotIn('resolvedTargetEdition', ref)
        self.assertNotIn('targetSourceHash', ref)
        self.assertEqual(result['mappings'], [])

    def test_reports_preserve_variant_principle_wording_and_threat_context(self):
        technique_url = 'https://attack.mitre.org/techniques/T1078/'
        row = dict(authoritativeText='Verify suppliers.', essentials=dict(chapter='Enterprise IT',
            principleReference='GOV-11', principleText='Suppliers are independently verified.',
            evidencePrincipleText='Suppliers are verified.', domains=['Governance and culture'],
            phases={'Governance and culture':[1,2,3]}, referenceKind='Publisher action ID',
            techniques=[dict(label='Valid Accounts', url=technique_url)]))
        output = reports.essentials_text(row)
        self.assertIn('Evidence guide principle wording: Suppliers are verified.', output)
        self.assertIn('threat context, not requirements', output)
        self.assertIn('Valid Accounts', output)
        self.assertIn(technique_url, output)

    def test_prepared_principles_use_bounded_import_metadata_and_references(self):
        row = dict(id='asd-principles:gov-1', frameworkId='asd-principles', officialReference='GOV-01',
            heading='Synthetic principle', parentId=None, authoritativeText='Synthetic outcome.',
            context='', sourceLocator={'reference':'GOV-01'}, frameworkReferences=[source_reference()])
        packet = dict(framework=dict(id='asd-principles', title='ASD cyber security principles',
            edition='2026.09.4', sourceHash='a' * 64, sourceFile='ISM_catalog.json'), requirements=[row], mappings=[])
        with temporary() as folder:
            source = Path(folder) / 'sources/files/nested/ISM_catalog.json'
            source.parent.mkdir(parents=True)
            source.write_text('{}', encoding='utf-8')
            with patch.dict(os.environ, {'POLICYCOMPASS_LIBRARY':str(folder)}), \
                    patch('policycompass.documents.extract_worker', return_value=deepcopy(packet)) as worker, \
                    patch.object(corpus, '_library', side_effect=AssertionError('Legacy build must be skipped')):
                result = corpus.load('asd-principles', corpus_version=corpus.CORPUS_VERSION)
            worker.assert_called_once_with(source, framework='asd-principles')
        metadata = result['frameworks'][0]
        self.assertEqual(metadata['edition'], '2026.09.4')
        self.assertEqual(metadata['sourceHash'], packet['framework']['sourceHash'])
        self.assertEqual(metadata['sourceUri'], PAGES['asd-principles'])
        self.assertEqual(metadata['extractHash'], fingerprint(packet['requirements']))
        self.assertEqual(result['requirements'][0]['frameworkReferences'][0]['sourceHash'], 'a' * 64)
        self.assertEqual(result['requirements'][0]['frameworkReferences'][0]['status'], 'Framework not selected')
        self.assertIsNone(result['requirements'][0]['obligations'][0]['rule'])

    def test_missing_prepared_principles_offer_download_or_local_source(self):
        with temporary() as folder, patch.dict(os.environ, {'POLICYCOMPASS_LIBRARY':str(folder)}), \
                patch('policycompass.documents.extract_worker') as worker:
            with self.assertRaisesRegex(PolicyError, 'Framework updates.*ISM_catalog.json'):
                corpus.load('asd-principles', corpus_version=corpus.CORPUS_VERSION)
            worker.assert_not_called()


if __name__ == '__main__':
    unittest.main()
