"""Synthetic security regressions; no executable fixture is ever launched."""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_policy_review import temporary
from test_policy_alignment import requirement
from policycompass import corpus, documents, rules, service, store
from policycompass.contracts import PolicyError, canonical, canonical_payload, fingerprint
from policycompass.desktop import Desktop

SENTENCE = 'All personnel must complete security awareness training annually. '


def baseline(count=1):
    rows = []
    for index in range(count):
        row = requirement('training-' + str(index), SENTENCE, 'wa-csp')
        row['obligations'] = [dict(atom, mandatory=True, ruleVersion='1.0',
            assessmentMethod='DocumentReview', reviewStatus='DraftNeedsHumanReview',
            provenance='Synthetic requirement with installed rules') for atom in corpus.training_rules()]
        rows.append(row)
    return dict(version='synthetic', requirements=rows, mappings=[], rulesHash='synthetic',
                frameworks=[dict(id='wa-csp', title='Synthetic training', edition='Synthetic')])


def analyse(paths, count=1, **options):
    with patch.object(corpus, 'load', return_value=baseline(count)):
        return service.analyse(paths, scope='Synthetic security regression', **options)


def open_original(state):
    ui = SimpleNamespace(state=state, doc_tree=SimpleNamespace(
        selection=lambda: (state['run']['documents'][0]['id'],)))
    ui.guarded = lambda action: Desktop.guarded(ui, action)
    Desktop.open_original(ui)


class SourceOpeningTests(unittest.TestCase):
    def test_correctly_hashed_programs_cannot_launch_from_saved_or_historical_run(self):
        with temporary() as directory:
            policy = directory/'policy.txt'
            policy.write_text(SENTENCE, encoding='utf-8')
            valid = analyse([policy])
            for suffix in ('.cmd', '.EXE', '.bat', '.lnk', '.url', '.hta', '.ps1'):
                for forged_archive in (False, True):
                    with self.subTest(suffix=suffix, archive=forged_archive):
                        companion = directory/('companion' + suffix)
                        companion.write_bytes(b'Harmless fixture; never executed.')
                        run = deepcopy(valid)
                        run.update(runId=str(uuid.uuid4()), requirements=[])
                        doc = run['documents'][0]
                        doc.update(path=str(companion), name='Policy.pdf', format='.pdf',
                                   sha256=hashlib.sha256(companion.read_bytes()).hexdigest(), passages=[])
                        if forged_archive:
                            doc.update(archiveMember='policy.pdf', archiveHash=doc['sha256'])
                        run['canonicalHash'] = fingerprint(canonical_payload(run))
                        saved = directory/(run['runId'] + '.wacc')
                        store.save(saved, run)
                        # Keep the crafted run as historical, exercising the same launch boundary.
                        store.save(saved, valid)
                        state = store.load(saved, run['runId'])
                        self.assertTrue(state['metadata']['historical'])
                        self.assertEqual(store.verify_sources(state)[0]['status'], 'Unchanged')
                        with patch('policycompass.desktop.os.startfile') as launch, patch('policycompass.desktop.messagebox.showerror') as error:
                            open_original(state)
                            launch.assert_not_called()
                            error.assert_called_once()

    def test_unsafe_windows_spellings_are_rejected_before_io(self):
        paths = ['payload.cmd:policy.txt', 'NUL.txt', 'COM1.pdf', 'policy.txt.',
                 'policy.txt ', 'bad\x00.txt', 'https://example.test/policy.pdf',
                 '\\\\server\\share\\policy.txt', '\\\\?\\C:\\policy.txt', '\\\\.\\NUL.txt']
        for path in paths:
            with self.subTest(path=path), patch.object(store, '_source_matches') as match:
                with self.assertRaises(PolicyError):
                    store.original_source(dict(path=path, format='.txt', sha256='unknown'))
                match.assert_not_called()

    def test_supported_originals_use_checked_absolute_path_and_hash(self):
        with temporary() as directory:
            for suffix in ('.TXT', '.md', '.pdf', '.docx'):
                source = directory/('Policy café' + suffix)
                source.write_bytes(b'Hash and path fixture; external viewer is mocked.')
                relative = os.path.relpath(source, ROOT)
                doc = dict(id='source', path=relative, format=suffix.lower(),
                           sha256=hashlib.sha256(source.read_bytes()).hexdigest())
                with self.subTest(suffix=suffix), patch('policycompass.desktop.os.startfile') as launch:
                    open_original(dict(run=dict(documents=[doc])))
                    launch.assert_called_once_with(str(source.absolute()))
                with patch('policycompass.desktop.os.startfile') as launch, patch('policycompass.desktop.messagebox.showerror') as error:
                    source.write_bytes(b'Changed source')
                    open_original(dict(run=dict(documents=[doc])))
                    launch.assert_not_called()
                    error.assert_called_once()

    def test_zip_original_opens_container_and_metadata_mismatch_is_rejected(self):
        with temporary() as directory:
            archive = directory/'policies.zip'
            with zipfile.ZipFile(archive, 'w') as output:
                output.writestr('nested/policy.TXT', SENTENCE)
            doc = documents.extract_worker(archive, member='nested/policy.TXT')
            with patch('policycompass.desktop.os.startfile') as launch:
                open_original(dict(run=dict(documents=[doc])))
                launch.assert_called_once_with(str(archive.absolute()))
            for changes in ({'format':'.exe'}, {'archiveMember':None}, {'archiveHash':''}):
                with self.subTest(changes=changes), self.assertRaises(PolicyError):
                    store.original_source(dict(doc, **changes))
            source = directory/'policy.txt'
            source.write_text(SENTENCE, encoding='utf-8')
            ordinary = documents.extract_worker(source)
            with self.assertRaises(PolicyError):
                store.original_source(dict(ordinary, format='.pdf'))
            source.unlink()
            with self.assertRaises(PolicyError):
                store.original_source(ordinary)
            self.assertEqual(store.verify_sources(dict(run=dict(documents=[ordinary])))[0]['status'], 'Unavailable')

    def test_failed_uppercase_sources_remain_openable_in_saved_history(self):
        with temporary() as directory:
            for suffix in ('.PDF', '.DOCX'):
                source = directory/('Unreadable' + suffix)
                source.write_bytes(b'Unparseable document fixture')
                with patch.object(documents, 'extract_worker', side_effect=PolicyError('Cannot extract')):
                    run = analyse([source])
                self.assertEqual(run['documents'][0]['format'], suffix)
                self.assertEqual(run['documents'][0]['status'], 'Failed')
                saved = directory/('history-' + suffix[1:] + '.wacc')
                store.save(saved, run)
                current = deepcopy(run)
                current['runId'] = str(uuid.uuid4())
                store.save(saved, current)
                for run_id in (None, run['runId']):
                    with self.subTest(suffix=suffix, run_id=run_id), patch('policycompass.desktop.os.startfile') as launch, patch('policycompass.desktop.messagebox.showerror') as error:
                        open_original(store.load(saved, run_id))
                        error.assert_not_called()
                        launch.assert_called_once_with(str(source.absolute()))


class EvidenceBudgetTests(unittest.TestCase):
    def test_normal_evidence_preserves_ids_spans_reviews_and_saved_contract(self):
        with temporary() as directory:
            source = directory/'policy.txt'
            source.write_text(SENTENCE + '\n\nSecurity awareness training is not required.', encoding='utf-8')
            run = analyse([source], approval='approved')
            row = run['requirements'][0]
            self.assertEqual(len(row['evidence']), 4)
            self.assertIn('Conflict', row['flags'])
            for entry in row['evidence']:
                self.assertEqual(entry['id'], fingerprint({k:v for k,v in entry.items() if k != 'id'}))
                self.assertTrue(all(entry['excerpt'][span['start']:span['end']] for span in entry['matchedSpans']))
            event = service.review_event(run, row['id'], 'Covered', 'Synthetic review', 'Tester',
                [a['id'] for a in row['obligations']], [e['id'] for e in row['evidence']])
            self.assertEqual(len(event['confirmedObligations']), 2)
            saved = directory/'comparison.wacc'
            store.save(saved, run)
            # New generation limits must not reject existing history or change digests.
            with patch.object(service, 'MAX_EVIDENCE_RECORDS', 1), patch.object(service, 'MAX_EVIDENCE_BYTES', 1):
                self.assertEqual(store.load(saved)['run'], run)

    def test_repetitive_policy_stops_at_byte_budget_before_final_hash(self):
        with temporary() as directory:
            source = directory/'repetitive.txt'
            source.write_text(SENTENCE * 60, encoding='utf-8')
            seen = []
            def entry_only(value):
                seen.append(value)
                return canonical(value)
            with patch.object(service, 'MAX_EVIDENCE_BYTES', 32_000), patch.object(service, 'canonical', side_effect=entry_only), patch.object(service, 'fingerprint') as final_hash:
                with self.assertRaisesRegex(PolicyError, 'evidence limit'):
                    analyse([source])
                final_hash.assert_not_called()
            self.assertLess(len(seen), 10)

    def test_count_budget_is_cumulative_across_requirements_documents_and_passages(self):
        with temporary() as directory:
            first, second = directory/'first.txt', directory/'second.txt'
            first.write_text(SENTENCE, encoding='utf-8')
            second.write_text('An additional policy.\n\n' + SENTENCE, encoding='utf-8')
            cases = [([first], 2), ([first, second], 1)]
            for paths, count in cases:
                with self.subTest(paths=paths, count=count), patch.object(service, 'MAX_EVIDENCE_RECORDS', 3):
                    with self.assertRaisesRegex(PolicyError, 'evidence limit'):
                        analyse(paths, count=count)
            first.write_text(SENTENCE + '\n\n' + SENTENCE, encoding='utf-8')
            with patch.object(service, 'MAX_EVIDENCE_RECORDS', 3):
                with self.assertRaisesRegex(PolicyError, 'evidence limit'):
                    analyse([first])

    def test_default_budget_rejects_amplification_without_replacing_saved_work(self):
        from policycompass.cli import parser, execute
        with temporary() as directory:
            source = directory/'policy.txt'
            source.write_text(SENTENCE, encoding='utf-8')
            saved = directory/'existing.wacc'
            store.save(saved, analyse([source]))
            previous = saved.read_bytes()
            # Would create 132 MB of repeated excerpts without the default budget.
            source.write_text(SENTENCE * 1000, encoding='utf-8')
            args = parser().parse_args(['compare', str(source), '--scope', 'Synthetic budget test', '--assessment', str(saved)])
            with patch.object(corpus, 'load', return_value=baseline()):
                with self.assertRaisesRegex(PolicyError, 'evidence limit'):
                    execute(args)
            self.assertEqual(saved.read_bytes(), previous)

    def test_budget_counts_json_escaping_and_utf8_bytes(self):
        with temporary() as directory:
            source = directory/'unicode.txt'
            source.write_text(SENTENCE + ' café \\path\t' + SENTENCE, encoding='utf-8')
            run = analyse([source])
            evidence = run['requirements'][0]['evidence']
            budget = sum(len(canonical(entry).encode('utf-8')) + 1 for entry in evidence)
            with patch.object(service, 'MAX_EVIDENCE_BYTES', budget):
                self.assertEqual(analyse([source])['requirements'][0]['evidence'], evidence)
            with patch.object(service, 'MAX_EVIDENCE_BYTES', budget-1):
                with self.assertRaisesRegex(PolicyError, 'evidence limit'):
                    analyse([source])

    def test_rule_iteration_is_lazy_and_cancellable_between_sentences(self):
        passage = dict(text=SENTENCE * 30, locator={})
        rule = corpus.training_rules()[0]['rule']
        cancel = threading.Event()
        with patch.object(rules, 'check', wraps=rules.check) as check:
            iterator = rules.iter_evaluate(rule, passage, cancel)
            next(iterator)
            calls = check.call_count
            self.assertGreater(calls, 0)
            cancel.set()
            with self.assertRaises(KeyboardInterrupt):
                next(iterator)
            self.assertEqual(check.call_count, calls)
        self.assertEqual(rules.evaluate(rule, passage), list(rules.iter_evaluate(rule, passage)))


if __name__ == '__main__':
    unittest.main()
