"""Demo policy retrieval and independent regressions for conservative matching."""
from copy import deepcopy
from pathlib import Path
import sys
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from policycompass import alignment, documents
from test_policy_alignment import document, requirement


# Original test requirements, not extracts from a publisher. The wording varies
# from the demo documents and the cases cover each policy in the set.
DEMO_CASES = (
    ('access-and-training.md', 'All personnel receive awareness training annually.'),
    ('access-and-training.md', 'Multi-factor authentication protects privileged accounts.'),
    ('governance-and-risk.md', 'Risk treatment actions have an accountable owner and target date.'),
    ('governance-and-risk.md', 'Legal, regulatory and contractual obligations are recorded.'),
    ('incident-response.md', 'Incident response plans are exercised annually.'),
    ('incident-response.md', 'An evidence log records collection and transfer of custody.'),
    ('information-handling.md', 'Sensitive information is encrypted at rest and in transit.'),
    ('information-handling.md', 'Electronic storage media is sanitised before disposal.'),
    ('recovery.md', 'Backup restoration is tested quarterly.'),
    ('recovery.md', 'Critical services have recovery time and recovery point objectives.'),
    ('secure-development.md', 'Developers check input validation and error handling.'),
    ('secure-development.md', 'Development, test and production environments are separated.'),
    ('secure-systems.md', 'Maintain an inventory of hardware, software and online services.'),
    ('secure-systems.md', 'Review network access rules quarterly.'),
    ('supplier-security.md', 'Supplier dependencies are included in incident and recovery planning.'),
    ('supplier-security.md', 'Supplier access uses named accounts and multi-factor authentication.'),
)


class DemoAlignmentTests(unittest.TestCase):
    def test_demo_policies_find_expected_passages(self):
        rows = [requirement(str(i), text, 'synthetic') for i, (_, text) in enumerate(DEMO_CASES)]
        docs = [documents.extract(path) for path in sorted((ROOT/'examples/framework-alignment').glob('*.md'))]
        results = alignment.compare(rows, docs)
        for row, (filename, _) in zip(rows, DEMO_CASES):
            with self.subTest(policy=filename, requirement=row['authoritativeText']):
                result = results[row['id']]
                self.assertIn(result['status'], ('Mentioned', 'Related wording'))
                self.assertIn(filename, [m['documentName'] for m in result['matches']])

    def test_markdown_soft_wraps_preserve_matches_and_source_offsets(self):
        # Held-out topics and arbitrary widths keep this independent of the demo.
        samples = (
            'Visitors return temporary badges to reception before leaving the building.',
            'Cryptographic keys rotate automatically according to their approved lifetime.',
            'Wireless guest networks isolate client devices from each other.',
        )
        for text in samples:
            row = requirement('HELD-OUT', text)
            for width in (24, 39, 57):
                for newline in ('\n', '\r\n'):
                    wrapped = textwrap.fill(text, width=width).replace('\n', newline)
                    with self.subTest(text=text, width=width, newline=repr(newline)):
                        result = alignment.compare([row], [dict(document(wrapped), format='.md')])[row['id']]
                        self.assertEqual(result['status'], 'Mentioned')
                        match = result['matches'][0]
                        self.assertEqual(match['excerpt'], wrapped[match['start']:match['end']])
                        for span in match['matchedSpans']:
                            self.assertIn(match['excerpt'][span['start']:span['end']], match['matchedTerms'])

    def test_markdown_boundaries_do_not_assemble_unrelated_evidence(self):
        row = requirement('BOUNDARIES', 'Visitors return temporary badges to reception.')
        parts = (
            'Visitors arrive.\nReturn temporary badges.',
            'Visitors arrive\n\nReturn temporary badges',
            '- Visitors arrive\n- Return temporary badges',
            '1. Visitors arrive\n2. Return temporary badges',
            'Visitors arrive\n## Return temporary badges',
            'Visitors arrive  \nReturn temporary badges',
            'Visitors arrive\\\nReturn temporary badges',
            'Visitors arrive:\nReturn temporary badges',
            '| Visitors arrive |\n| Return temporary badges |',
        )
        for text in parts:
            with self.subTest(text=text):
                windows = [text[a:b] for a, b in alignment.windows(text, soft_wrap=True)]
                self.assertFalse(any('Visitors' in w and 'badges' in w for w in windows))
        # Plain-text and PDF line boundaries are ambiguous; keep them separate.
        for format in ('.txt', '.pdf'):
            result = alignment.compare([row], [dict(document('Visitors arrive\nReturn temporary badges'), format=format)])[row['id']]
            self.assertNotEqual(result['status'], 'Mentioned')

    def test_wrapped_negative_and_qualified_statements_stay_related(self):
        row = requirement('HELD-OUT', 'Visitors return temporary badges to reception.')
        for qualifier in ('do not', 'may', 'should'):
            text = f'Visitors {qualifier}\nreturn temporary badges to reception.'
            result = alignment.compare([row], [dict(document(text), format='.md')])[row['id']]
            self.assertEqual(result['status'], 'Related wording')
            self.assertTrue(result['matches'][0]['cautions'])

    def test_unpunctuated_lines_are_searched_without_joining_them(self):
        text = 'Visitors return temporary badges to reception\nWireless networks isolate guest devices'
        rows = [requirement('LINE', 'Visitors return temporary badges to reception.'),
                requirement('OTHER-LINE', 'Wireless networks isolate guest devices.')]
        for format in ('.txt', '.pdf'):
            results = alignment.compare(rows, [dict(document(text), format=format)])
            for result in results.values():
                self.assertEqual(result['status'], 'Mentioned')
                excerpt = result['matches'][0]['excerpt']
                self.assertFalse('Visitors' in excerpt and 'Wireless' in excerpt)

    def test_long_context_does_not_hide_a_child_requirement(self):
        row = requirement('CHILD', 'Visitors return temporary badges to reception.')
        row['context'] = ('The facilities director authorises inspections of perimeter fencing, '
                          'camera placement, lighting, fire doors and secure loading areas. ')
        result = alignment.compare([row], [document('Visitors return temporary badges to reception.')])[row['id']]
        self.assertEqual(result['status'], 'Related wording')
        self.assertIn('parent conditions', result['matches'][0]['cautions'][0])
        self.assertEqual(result['matches'][0]['score'], 1)
        self.assertNotEqual(alignment.compare([row], [document(row['context'])])[row['id']]['status'], 'Mentioned')

    def test_child_wording_ranks_above_parent_wording(self):
        row = requirement('CHILD', 'Visitors return temporary badges to reception.')
        row['context'] = 'Managers inspect perimeter fencing, camera placement, lighting and fire doors.'
        docs = [document(row['context']), dict(document(row['authoritativeText']), id='child', sha256='child')]
        result = alignment.compare([row], docs)[row['id']]
        self.assertEqual(result['matches'][0]['documentId'], 'child')

    def test_sparse_or_missing_qualifiers_cannot_make_clear_matches(self):
        cases = (
            ('Each system has a designated system owner.',
             'Business owners keep approvals in the designated records system.'),
            ('Application control is implemented on workstations.',
             'This covers workstations and applications.'),
            ('Service accounts are created as group managed service accounts.',
             'The service desk creates the account after approval.'),
            ('Electronic visitor badges expire automatically.',
             'Visitor badges expire at the end of the visit.'),
        )
        for query, text in cases:
            with self.subTest(query=query):
                row = requirement('SHORT', query)
                result = alignment.compare([row], [document(text)])[row['id']]
                self.assertNotEqual(result['status'], 'Mentioned')

    def test_unrelated_holdout_topics_remain_unmatched(self):
        docs = [documents.extract(path) for path in sorted((ROOT/'examples/framework-alignment').glob('*.md'))]
        texts = (
            'Radio frequency emanation shielding is independently certified.',
            'Biometric liveness detection rejects artificial fingerprints.',
            'Satellite navigation receivers resist spoofed timing signals.',
            'Quantum-resistant signature algorithms replace elliptic curve signatures.',
        )
        rows = [requirement(str(i), text) for i, text in enumerate(texts)]
        self.assertEqual({r['status'] for r in alignment.compare(rows, docs).values()}, {'Not mentioned'})

    def test_saved_alignment_keeps_its_original_method_and_results(self):
        run = dict(requirements=[dict(requirement('SAVED', 'Some text.'), alignment=dict(
            status='Not mentioned', matches=[], matchCount=0, searchComplete=True, method='policy-topics-1'))])
        before = deepcopy(run)
        self.assertEqual(alignment.for_run(run)['ism:SAVED']['method'], 'policy-topics-1')
        self.assertEqual(run, before)


if __name__ == '__main__':
    unittest.main()
