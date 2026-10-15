"""Read the reviewed ASD Essentials source collection inside the bounded worker.

Chapter actions are assessable rows. Principles, guidance, assessment indicators
and workbook calculations remain supporting material. No spreadsheet is executed.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import io
import json
import re
import unicodedata
from xml.etree import ElementTree as ET

from framework_core.model import normalise_identifier
from .contracts import PolicyError
from .documents import MAX_BYTES, MAX_TEXT, checked_archive
from .essentials_sources import CHAPTERS, EDITION, PDF_LICENCE, PUBLICATIONS

CAPABILITIES = ('Governance and culture', 'Visibility and response')
DOMAINS = ('Boundary services', 'Identity services', 'Critical processes and services',
           'Privileged environments', 'Business systems', 'User devices')
EXPECTED = {
    'chapter-it': (58, 28, (9, 12, 37)),
    'chapter-cloud': (78, 30, (17, 14, 47)),
    'chapter-ot': (61, 34, (10, 11, 40)),
}
TITLES = {'essentials-it': 'ASD Essentials for enterprise IT',
          'essentials-cloud': 'ASD Essentials for cloud', 'essentials-ot': 'ASD Essentials for OT'}
CHAPTER_LABELS = {'chapter-it': 'Enterprise IT', 'chapter-cloud': 'Cloud', 'chapter-ot': 'Operational technology'}
IT_ACTIONS = '''IT.GOV-01.1 IT.GOV-08.1 IT.GOV-04.1 IT.GOV-04.2 IT.GOV-03.1
IT.GOV-11.1 IT.GOV-11.2 IT.GOV-14.1 IT.PRO-14.2 IT.IDE-01.1 IT.IDE-04.1
IT.PRO-13.3 IT.DET-01.3 IT.DET-02.2 IT.DET-03.1 IT.DET-03.2 IT.DET-05.1
IT.RES-05.1 IT.RES-03.1 IT.RES-04.1 IT.RES-04.2 IT.IDE-01.2 IT.PRO-01.1
IT.PRO-01.2 IT.PRO-16.1 IT.PRO-16.2 IT.PRO-13.1 IT.PRO-13.2 IT.PRO-13.4
IT.PRO-13.5 IT.PRO-13.6 IT.PRO-12.1 IT.PRO-12.2 IT.PRO-12.3 IT.PRO-05.1
IT.PRO-05.2 IT.PRO-05.3 IT.PRO-04.1 IT.PRO-04.2 IT.PRO-04.3 IT.PRO-06.1
IT.PRO-06.2 IT.PRO-06.3 IT.PRO-07.1 IT.PRO-07.2 IT.PRO-10.1 IT.PRO-10.2
IT.PRO-10.3 IT.PRO-18.1 IT.PRO-18.2 IT.PRO-09.1 IT.PRO-09.2 IT.PRO-09.3
IT.PRO-14.1 IT.DET-01.1 IT.DET-01.2 IT.DET-04.1 IT.DET-02.1'''.split()
REFERENCE_GROUPS = {
    'ISM (excl. E8)': ('ism', '2026.09.4', r'ISM-\d{4}'),
    'E8': ('ism', '2026.09.4', r'ISM-\d{4}'),
    'CSF': ('csf', '2.0', r'[A-Z]{2}\.[A-Z]{2}-\d{2}'),
    '800-171r3': ('nist-800-171', '3', r'\d{2}\.\d{2}\.\d{2}'),
    'AESCSF': ('aescsf', '2', r'[A-Z-]+-\d+[a-z]'),
}
NOTICES = [
    'PolicyCompass uses the chapter PDFs for action wording and applicability. ASD HTML pages contain wording and link differences; PDF precedence is a PolicyCompass choice.',
    'The three chapters contain 197 actions using 41 shared ISM principles. Guidance and assessment indicators are supporting material, not additional requirements.',
    'Priority phases describe implementation order. Policy text matches do not establish effectiveness, maturity or completion of a phase.',
    'Enterprise IT potential-evidence references come from ASD’s assessment evidence guide. They do not establish equivalence or transfer policy results between frameworks.',
    'Cloud and OT action locators beginning PC. are assigned by PolicyCompass; ASD publishes principle identifiers for those matrices.',
    'The cloud PDF leaves PaaS and SaaS responsibility blank for the outbound-flow inspection action. PolicyCompass keeps both values unknown.',
    'The enterprise assessment workbook is supporting material. Its formulas and ratings are not executed or copied into policy comparison results.',
    'The enterprise evidence guide and chapter use different wording for four actions. Both versions are retained; the chapter supplies comparison text.',
    'The ISM GOV-11 principle includes independent supplier verification; the enterprise evidence guide omits the word independently. Both descriptions are retained.',
]


def _require(condition, message):
    if not condition:
        raise PolicyError('Essentials source could not be read: ' + message + ' The previous collection has been kept.', 5)


def _text(value):
    value = (value or '').replace('-\n', '-')
    return re.sub(r'\s+', ' ', value).strip()


def _key(value):
    return re.sub(r'\W+', '', unicodedata.normalize('NFKC', value).casefold())


def _principle(value):
    match = re.fullmatch(r'([A-Z]{3}-\d{2})\s*[-–—]?\s*(.+)', _text(value))
    _require(match is not None, 'unrecognised principle heading')
    return match.groups()


def _open_pdf(raw):
    import pdfplumber
    _require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES and raw.startswith(b'%PDF-'), 'invalid PDF')
    pdf = pdfplumber.open(io.BytesIO(raw))
    if not 1 <= len(pdf.pages) <= 100:
        pdf.close()
        _require(False, 'unsupported PDF page count')
    return pdf


def _resource_text(raw, title):
    texts = []
    count = 0
    with _open_pdf(raw) as pdf:
        for page in pdf.pages:
            value = page.extract_text() or ''
            count += len(value)
            _require(count <= MAX_TEXT, 'PDF text exceeds the supported limit')
            texts.append(value)
            page.close()  # pdfplumber otherwise retains every page's character objects.
    words = set(re.findall(r'[a-z0-9]+', title.casefold()))
    cover = set(re.findall(r'[a-z0-9]+', texts[0].casefold()))
    _require(words <= cover, 'publication cover does not match its title')
    return texts


def _techniques(page, bbox):
    links = {}
    for item in page.hyperlinks:
        uri = item.get('uri') or ''
        x, y = (item['x0'] + item['x1']) / 2, (item['top'] + item['bottom']) / 2
        if not (bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]):
            continue
        _require(re.fullmatch(r'https://attack\.mitre\.org/(?:versions/v\d+/)?techniques/T\d+(?:/\d+)?/', uri) is not None,
                 'unexpected technique link')
        label = page.crop((item['x0']-.3, item['top']-.3, item['x1']+.3, item['bottom']+.3)).extract_text() or ''
        links.setdefault(uri, []).append(label)
    _require(len(links) <= 30, 'too many technique links in an action')
    return [dict(label=_text(' '.join(parts)), url=uri) for uri, parts in links.items()]


def _matrix_row(header, values, current, section, source, techniques):
    _require(len(header) == len(values), 'matrix row width changed')
    if values[0]:
        current = _principle(values[0])
    _require(current is not None, 'action has no principle')
    headings = [_text(h).casefold() for h in header]
    action_i = headings.index('cloud actions' if 'cloud actions' in headings else 'action')
    action = _text(values[action_i])
    _require(bool(action) and len(action) <= 10000, 'empty or overlong action')
    domains = [section]
    responsibility = None
    if 'mitre att&ck' in headings:
        start = headings.index('mitre att&ck') + 1
        domains = []
        for i in range(start, len(header)):
            _require(values[i] in ('', '✔', '✓'), 'unknown domain marker')
            if values[i]:
                domains.append(_text(header[i]))
        _require(bool(domains), 'technical action has no applicable domain')
    if 'paas shared responsibility' in headings:
        responsibility = {}
        for name in ('paas', 'saas'):
            marker = values[headings.index(name + ' shared responsibility')]
            _require(marker in ('C', 'P', 'S', ''), 'unknown shared responsibility marker')
            responsibility[name] = marker or None
    return dict(principle=current[0], title=current[1], text=action, domains=domains,
                responsibility=responsibility, techniques=techniques, section=section, source=source), current


def _matrix(raw, role):
    rows, section, current = [], None, None
    allowed = DOMAINS if role != 'chapter-ot' else DOMAINS[:-1]
    with _open_pdf(raw) as pdf:
        for page in pdf.pages:
            detected = page.find_tables()
            candidates = [t for t in detected if t.extract()[0][0] == 'Principle'
                          and any(h in ('Action', 'Cloud actions') for h in t.extract()[0])]
            for ti, initial in enumerate(candidates):
                header = initial.extract()[0]
                top = initial.bbox[1]
                before = page.crop((0, 0, page.width, top)).extract_text() or ''
                previous_section = section
                if 'MITRE ATT&CK' in header:
                    section = 'Technical domains'
                    start = header.index('MITRE ATT&CK')+1
                    _require(set(_text(v) for v in header[start:]) == set(allowed), 'technical domains changed')
                else:
                    headings = re.findall(r'(?m)^(Governance and culture|Visibility and response)\s*$', before)
                    if headings:
                        section = headings[-1]
                _require(section in (*CAPABILITIES, 'Technical domains'), 'unrecognised matrix section')
                if previous_section != section:
                    current = None
                expected_header = (['Principle', 'PaaS Shared Responsibility', 'SaaS Shared Responsibility', 'Action']
                                   if role == 'chapter-cloud' else ['Principle', 'Action'])
                if section != 'Technical domains':
                    _require([_key(v) for v in header] == [_key(v) for v in expected_header], 'capability columns changed')
                else:
                    expected_prefix = (['Principle', 'Cloud actions', 'PaaS shared responsibility', 'SaaS shared responsibility', 'MITRE ATT&CK']
                                       if role == 'chapter-cloud' else ['Principle', 'Action', 'MITRE ATT&CK'])
                    _require([_key(v) for v in header[:len(expected_prefix)]] == [_key(v) for v in expected_prefix], 'technical columns changed')
                xs = sorted({v for cell in initial.rows[0].cells for v in (cell[0], cell[2])})
                next_top = candidates[ti+1].bbox[1] if ti+1 < len(candidates) else page.height-35
                bottoms = [e['top'] for e in page.edges if e.get('orientation') == 'h'
                           and e['width'] > (xs[-1]-xs[0])*.8 and top < e['top'] < next_top]
                bottom = max([initial.bbox[3], *bottoms,
                              *(t.bbox[3] for t in detected if t.bbox[1] >= top and t.bbox[3] < next_top)])
                # Striped OT rows have no vertical borders. Extend the header's
                # column boundaries through those rows instead of dropping them.
                crop = page.crop((xs[0]-.2, top-.2, xs[-1]+.2, bottom+.2))
                tables = crop.find_tables({'vertical_strategy': 'explicit', 'explicit_vertical_lines': xs,
                                           'horizontal_strategy': 'lines'})
                _require(len(tables) == 1, 'ambiguous matrix geometry')
                table = tables[0]
                for ri, values in enumerate(table.extract()[1:], 1):
                    source = dict(page=page.page_number, table=ti+1, row=ri,
                                  boundingBox=','.join(f'{v:.2f}' for v in table.rows[ri].bbox))
                    row, current = _matrix_row(header, values, current, section, source,
                                               _techniques(page, table.rows[ri].bbox))
                    rows.append(row)
                    _require(len(rows) <= 250, 'unexpected action count')
            page.close()
    count, principles, sections = EXPECTED[role]
    actual = Counter(r['section'] for r in rows)
    _require(len(rows) == count and len({r['principle'] for r in rows}) == principles
             and tuple(actual[s] for s in (*CAPABILITIES, 'Technical domains')) == sections, 'matrix coverage changed')
    _require(len({(r['principle'], _key(r['text']), tuple(r['domains'])) for r in rows}) == len(rows), 'duplicate actions')
    return rows


def _evidence(raw, pages):
    plain = '\n'.join(pages)
    plain = re.sub(r'(?m)^\d*\s*Assessment evidence guide for enterprise IT\s*\d*\s*$', '', plain)
    definitions = {}
    for match in re.finditer(r'(?m)^([A-Z]{3}-\d{2})\s*[-–]\s*(.*?)\nPrinciple:\s*(.*?)\nIT\.', plain, re.S):
        _require(match[1] not in definitions, 'duplicate evidence principle')
        definitions[match[1]] = _text(match[3])
    actions = {}
    for match in re.finditer(r'(IT\.[A-Z]{3}-\d{2}\.\d+)\s+Action:\s*(.*?)\s*Domains:\s*(.*?)\s*Indicators of Good Practice', plain, re.S):
        _require(match[1] not in actions, 'duplicate evidence action')
        actions[match[1]] = dict(text=_text(match[2]), references={}, referencePages={}, indicators=False)
    _require(set(actions) == set(IT_ACTIONS) and len(definitions) == 28, 'evidence action coverage changed')
    current = None
    with _open_pdf(raw) as pdf:
        for page in pdf.pages:
            events = [(line['top'], 'action', line) for line in page.extract_text_lines()
                      if re.fullmatch(r'IT\.[A-Z]{3}-\d{2}\.\d+', line['text'])]
            for table in page.find_tables():
                if table.extract()[0] in (['Framework', 'References'], ['Not effective', 'Partially effective', 'Fully effective']):
                    events.append((table.bbox[1], 'table', table))
            for top, kind, obj in sorted(events, key=lambda e: e[0]):
                if kind == 'action':
                    _require(obj['text'] in actions, 'unrecognised evidence action')
                    current = actions[obj['text']]
                    _require('page' not in current, 'repeated evidence action heading')
                    current['page'] = page.page_number
                else:
                    _require(current is not None, 'evidence table has no action')
                    values = obj.extract()
                    if values[0] == ['Framework', 'References']:
                        for group, refs in values[1:]:
                            group, refs = _text(group), _text(refs)
                            _require(group in REFERENCE_GROUPS and group not in current['references'], 'unknown or repeated evidence group')
                            current['references'][group] = refs
                            current['referencePages'][group] = page.page_number
                    else:
                        _require(len(values) == 2 and all(values[1]) and not current['indicators'], 'assessment indicator table changed')
                        current['indicators'] = True
            page.close()
    _require(all(set(a['references']) == set(REFERENCE_GROUPS) and a['indicators'] and 'page' in a for a in actions.values()),
             'incomplete assessment evidence')
    return actions, definitions


def _join_action(action_id, chapter, evidence):
    """Only the four reviewed publisher wording variants may cross this boundary."""
    substitutions = {
        'IT.GOV-03.1': ('an approved risk management', 'a risk management'),
        'IT.PRO-13.3': ('Identify and remediate unsecured', 'Identify unsecured'),
        'IT.IDE-01.2': ('records of infrastructure, operating systems, applications, identities, credentials and data assets',
                       'records of assets including infrastructure, operating systems, applications, identities, credentials and data'),
        'IT.PRO-05.3': ('details of the associated user', 'details of the user'),
    }
    if _key(chapter) == _key(evidence):
        return
    alias = substitutions.get(action_id)
    _require(alias is not None and _key(chapter) == _key(evidence.replace(*alias)), 'enterprise action and evidence no longer agree')


def _walk(value, pointer=''):
    if isinstance(value, dict):
        yield value, pointer
        for key, child in value.items():
            yield from _walk(child, pointer + '/' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, pointer + '/' + str(index))


def _principles(raw, source):
    value = json.loads(raw)
    metadata = value.get('catalog', {}).get('metadata', {})
    _require('information security manual' in metadata.get('title', '').casefold()
             and metadata.get('version') == '2026.09.4', 'ISM principle source edition changed')
    result = {}
    for item, pointer in _walk(value):
        if item.get('class') != 'ISM-principle':
            continue
        labels = [p['value'] for p in item.get('props', []) if p.get('name') == 'label']
        statements = [p['prose'] for p in item.get('parts', []) if p.get('name') == 'statement']
        _require(len(labels) == len(statements) == 1, 'ambiguous ISM principle definition')
        label = labels[0]
        _require(re.fullmatch(r'[A-Z]{3}-\d{2}', label) is not None and label not in result
                 and item['id'] == 'ism-principle-' + label.lower(), 'invalid ISM principle label')
        result[label] = dict(id=label, title=item['title'], text=statements[0], sourceUri=source['uri'],
                             sourceHash=source['sha256'], sourceEdition=metadata['version'],
                             oscalId=item['id'], jsonPointer=pointer)
    _require(len(result) == 49, 'ISM principle count changed')
    return result


def _workbook(raw):
    from .framework_import import check_workbook
    check_workbook(raw)
    names, formulas = [], 0
    with checked_archive(raw) as archive:
        root = ET.fromstring(archive.read('xl/workbook.xml'))
        names = [item.attrib['name'] for item in root.iter() if item.tag.endswith('}sheet')]
        for name in archive.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                root = ET.fromstring(archive.read(name))
                formulas += sum(item.tag.endswith('}f') for item in root.iter())
    _require(len(names) == 13 and len(set(names)) == 13 and set((*CAPABILITIES, *DOMAINS)) <= set(names),
             'assessment workbook worksheets changed')
    return dict(sheetNames=names, sheetCount=len(names), formulaCount=formulas)


def _phases(role, domains):
    values = {name: [1, 2, 3] for name in CAPABILITIES}
    if role == 'chapter-ot':
        values.update({name: [phase] for phase, group in enumerate(((DOMAINS[0], DOMAINS[2]),
                       (DOMAINS[3], DOMAINS[1]), (DOMAINS[4],)), 1) for name in group})
    else:
        values.update({name: [i//2+1] for i, name in enumerate(DOMAINS)})
    return {name: values[name] for name in domains}


def _references(evidence, source):
    result = []
    for group, text in evidence['references'].items():
        target, edition, pattern = REFERENCE_GROUPS[group]
        if text in ('N/A', 'See E8 references'):
            continue
        for reference in text.split(','):
            reference = re.sub(r'-\s+(?=\d)', '-', reference.strip())
            _require(re.fullmatch(pattern, reference) is not None, 'unrecognised published reference')
            basis = 'ASD enterprise IT assessment evidence guide: potential evidence sources (' + group + ')'
            if group == 'E8':
                basis += '; Essential Eight model, 2 October 2024; ISM 2026.09.4 reference identifiers'
            result.append(dict(frameworkId=target, reference=reference,
                targetId=target + ':' + normalise_identifier(reference), targetEdition=edition,
                sourceUri=source['uri'], sourceHash=source['sha256'], sourceEdition=source['edition'],
                sourcePage=evidence['referencePages'][group], sourceGroup=group, kind='Publisher',
                basis=basis,
                relationship='PotentialEvidenceFor'))
    return result


def parse(files, manifest, framework):
    """Return metadata, chapter requirements and references from a verified bundle."""
    _require(framework in CHAPTERS and manifest.get('edition') == EDITION, 'unsupported chapter or edition')
    resources = deepcopy(manifest['resources'])
    by_role = {r['role']: r for r in resources if r['role'] != 'guidance'}
    expected = {slug + '.pdf' for slug, _, _ in PUBLICATIONS} | {'ISM_catalog.json', 'enterprise-assessment-workbook.xlsx'}
    _require(set(files) == expected and len(resources) == 19, 'incomplete source collection')
    texts = {}
    for resource in resources:
        body = files[resource['filename']]
        _require(len(body) <= MAX_BYTES and hashlib.sha256(body).hexdigest() == resource['sha256'], 'source fingerprint differs')
        if resource['filename'].endswith('.pdf'):
            pages = _resource_text(body, resource['title'])
            texts[resource['role'] if resource['role'] != 'guidance' else resource['id']] = pages
            resource.update(pages=len(pages), licence=PDF_LICENCE,
                            principleReferences=sorted(set(re.findall(r'\b[A-Z]{3}-\d{2}\b', '\n'.join(pages)))))
        elif resource['role'] == 'workbook':
            resource.update(_workbook(body))
    principles = _principles(files[by_role['ism-principles']['filename']], by_role['ism-principles'])
    by_role['ism-principles'].update(edition='2026.09.4', principleReferences=sorted(principles))
    chapters = {role: _matrix(files[source['filename']], role) for role, source in by_role.items() if role.startswith('chapter-')}
    used = {r['principle'] for chapter in chapters.values() for r in chapter}
    _require(len(used) == 41 and used <= principles.keys(), 'chapter principle coverage changed')
    for chapter in chapters.values():
        _require(all(_key(row['title']) == _key(principles[row['principle']]['title']) for row in chapter), 'chapter and ISM principle labels differ')
    evidence_source = by_role['evidence-it']
    evidence, evidence_definitions = _evidence(files[evidence_source['filename']], texts['evidence-it'])
    _require(set(evidence_definitions) == {row['principle'] for row in chapters['chapter-it']}, 'evidence principle coverage changed')
    for action_id, row in zip(IT_ACTIONS, chapters['chapter-it']):
        _require(action_id.split('.')[1] == row['principle'], 'enterprise action order changed')
        _join_action(action_id, row['text'], evidence[action_id]['text'])
        row['officialId'] = action_id
    for label, text in evidence_definitions.items():
        _require(label in principles, 'unknown evidence principle')
        if _key(text) != _key(principles[label]['text']):
            _require(label == 'GOV-11' and _key(text) == _key(principles[label]['text'].replace('regularly independently verified', 'regularly verified')),
                     'evidence and ISM principle descriptions changed')
            principles[label]['evidenceText'] = text
    role = CHAPTERS[framework]
    chapter_source = by_role[role]
    rows = []
    for action in chapters[role]:
        principle = principles[action['principle']]
        identifier = action.get('officialId') or 'PC.' + role.removeprefix('chapter-').upper() + '.' + action['principle'] + '.' + hashlib.sha256(action['text'].encode()).hexdigest()[:12]
        details = dict(chapter=CHAPTER_LABELS[role], principleReference=action['principle'],
                       principleText=principle['text'], domains=action['domains'], phases=_phases(role, action['domains']),
                       referenceKind='Publisher action ID' if 'officialId' in action else 'PolicyCompass locator',
                       techniques=action['techniques'])
        if action['responsibility'] is not None:
            details['sharedResponsibility'] = action['responsibility']
        references = [dict(frameworkId='asd-principles', reference=principle['id'],
            targetId='asd-principles:' + normalise_identifier(principle['id']), targetEdition=principle['sourceEdition'],
            sourceUri=chapter_source['uri'], sourceHash=chapter_source['sha256'], sourceEdition=chapter_source['edition'],
            sourcePage=action['source']['page'], kind='Publisher', basis='ASD chapter matrix principle label',
            relationship='HasPrinciple', expectedTargetHash=principle['sourceHash'])]
        if 'officialId' in action:
            evidence_action = evidence[action['officialId']]
            details['evidenceActionText'] = evidence_action['text']
            if 'evidenceText' in principle:
                details['evidencePrincipleText'] = principle['evidenceText']
            references.extend(_references(evidence_action, evidence_source))
        rows.append(dict(id=framework + ':' + normalise_identifier(identifier), frameworkId=framework,
            officialReference=identifier, heading=principle['title'], parentId=principle['id'], authoritativeText=action['text'],
            context='', sourceLocator=dict(reference=identifier, section=action['section'], kind='PDF table',
                uri=chapter_source['uri'], sourceHash=chapter_source['sha256'], sourceFile=chapter_source['filename'],
                **action['source']),
            essentials=details, frameworkReferences=references))
    metadata = dict(id=framework, title=TITLES[framework], edition=EDITION, resources=resources,
                    notices=NOTICES[:], principles=[principles[pid] for pid in sorted({r['principle'] for r in chapters[role]})])
    return metadata, rows, []
