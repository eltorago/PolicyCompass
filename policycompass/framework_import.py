"""Parse publisher data in the bounded worker. Never import executable rules."""
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

from .contracts import PolicyError
from .documents import MAX_BYTES, checked_archive, local_file


def controls_for_comparison(existing, framework):
    """Count assessable rows once; omit headings and withdrawn requirements."""
    rows = []
    for c in existing.controls_for(framework):
        status = c.publisher_tags.get('status', [])
        status = [status] if isinstance(status, str) else status
        if (not c.text or c.attributes.get('structural') or c.attributes.get('ceased')
                or any(str(s).casefold() == 'withdrawn' for s in status)):
            continue
        if framework in ('aescsf', 'csf') and c.depth != 2:
            continue
        if framework == 'ism' and not re.fullmatch(r'ISM-\d+', c.identifier, re.I):
            continue
        rows.append(c)
    return rows


def control_rows(existing, framework):
    rows = []
    for c in controls_for_comparison(existing, framework):
        parent = existing.controls.get(c.parent_uid)
        context = parent.text if framework in ('aescsf', 'csf', 'nist-800-53') and parent else c.attributes.get('lead_in', '')
        if framework == 'asd-strategies':
            context = c.section_ref + '\nPublisher effectiveness rating: ' + c.attributes['relative_effectiveness']
        if framework == 'pspf' and c.applicability:
            context = 'Applicability: ' + str(c.applicability)
        row = dict(id=c.uid, frameworkId=framework, officialReference=c.identifier,
                   heading=c.title or c.section_ref or '', parentId=c.parent_uid,
                   authoritativeText=c.text, context=context,
                   sourceLocator=dict(reference=c.identifier))
        if framework == 'ism':
            row['ismMaturityLevels'] = c.publisher_tags.get('essential-eight-applicability', [])
            if isinstance(row['ismMaturityLevels'], str):
                row['ismMaturityLevels'] = [row['ismMaturityLevels']]
        if c.attributes.get('frameworkReferences'):
            row['frameworkReferences'] = deepcopy(c.attributes['frameworkReferences'])
        rows.append(row)
    return rows


def check_workbook(raw):
    with checked_archive(raw) as archive:
        if any('vbaproject' in n.lower() for n in archive.namelist()):
            raise PolicyError('Macro-enabled framework workbooks are not supported.')
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                xml = archive.read(name).upper()
                if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                    raise PolicyError('External entity declarations are not supported.')


def parse(framework, path):
    path = local_file(path)
    if path.stat().st_size > MAX_BYTES:
        raise PolicyError('Framework file exceeds the 16 MiB limit.')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if framework == 'wa-csp':
        from .wa_parser import parse as parse_wa
        value = parse_wa(path)
        metadata = dict(id=framework, title=value['title'], edition=value['title'])
        rows = [dict(id='wa-csp:' + r['identifier'], frameworkId=framework, officialReference=r['identifier'],
                     heading=r['section_title'], parentId=r['section_number'], authoritativeText=r['text'],
                     context=r.get('lead_in',''), sourceLocator=dict(reference=r['identifier'],section=r['section_number']))
                for r in value['records']]
        mappings = []
    elif framework == 'pspf':
        from .pspf_parser import parse as parse_pspf
        metadata, rows = parse_pspf(path)
        mappings = []
    elif framework.startswith('essentials-'):
        from .essentials_sources import unpack
        from .essentials_parser import parse as parse_essentials
        files, manifest = unpack(raw)
        metadata, rows, mappings = parse_essentials(files, manifest, framework)
    elif framework == 'asd-principles':
        from framework_core.model import Corpus
        from framework_core.registry import FRAMEWORKS_BY_KEY
        from framework_core.loaders import oscal, principles
        existing = Corpus()
        ism = deepcopy(FRAMEWORKS_BY_KEY['ism'])
        fw = deepcopy(FRAMEWORKS_BY_KEY['asd-principles'])
        existing.add_framework(ism)
        existing.add_framework(fw)
        value = json.loads(raw)
        if 'information security manual' not in value.get('catalog', {}).get('metadata', {}).get('title', '').casefold():
            raise PolicyError('The download is not the ISM principles catalogue.')
        oscal.load_into(existing, ism, str(path), applicability_prop='applicability')
        principles.partition(existing, fw)
        metadata = dict(id=framework, title=fw.name, edition=ism.revision or '')
        rows, mappings = control_rows(existing, framework), []
    elif framework in ('ism', 'aescsf', 'csf', 'nist-800-53', 'asd-strategies'):
        from framework_core.model import Corpus
        from framework_core.registry import FRAMEWORKS_BY_KEY
        from framework_core.loaders import oscal, aescsf, csf, extended
        from framework_core.io.xlsx import Workbook
        from framework_core.model import normalise_identifier
        existing = Corpus()
        fw = deepcopy(FRAMEWORKS_BY_KEY[framework])
        fw.revision = None
        existing.add_framework(fw)
        mappings = []
        if framework in ('ism', 'nist-800-53'):
            value = json.loads(raw)
            title = value.get('catalog', {}).get('metadata', {}).get('title', '')
            expected = 'information security manual' if framework == 'ism' else 'nist sp 800-53'
            if expected not in title.casefold():
                raise PolicyError('The download is not the selected framework catalogue.')
            ids = [c['id'] for c, *_ in oscal.walk_controls(value['catalog'])]
            if len(ids) != len(set(ids)):
                raise PolicyError('The catalogue has duplicate control identifiers.')
            counts = oscal.load_into(existing, fw, str(path), applicability_prop='applicability')
            if counts['controls'] != len(existing.controls_for(framework)):
                raise PolicyError('Catalogue labels resolve to duplicate control identifiers.')
        elif framework == 'asd-strategies':
            if 'Strategies to mitigate cyber security incidents (February 2017)' not in raw.decode('utf-8'):
                raise PolicyError('ASD strategies edition changed; this importer requires the February 2017 table.')
            extended.strategies(existing, fw, str(path))
            fw.revision = 'February 2017'
        elif framework == 'csf':
            check_workbook(raw)
            counts = csf.load_into(existing, fw, str(path))
            if fw.revision != '2.0':
                raise PolicyError('The workbook must identify NIST Cybersecurity Framework 2.0.')
            if counts['subcategories'] != len(controls_for_comparison(existing, framework)):
                raise PolicyError('The workbook has duplicate or empty CSF subcategories.')
            # Preserve references even when the target is not selected.
            for values in list(Workbook(str(path)).rows('CSF 2.0'))[2:]:
                values = list(values) + [''] * 5
                match = csf._SUB_ID.match(values[2].strip())
                if not match or csf._WITHDRAWN.match(match.group(2)):
                    continue
                control = existing.controls.get('csf:' + normalise_identifier(match.group(1)))
                if control is None:
                    continue
                refs = control.attributes.setdefault('frameworkReferences', [])
                for label, target in csf.parse_references(values[4]):
                    if label == 'SP 800-53 Rev 5.2.0':
                        refs.append(dict(frameworkId='nist-800-53', reference=target,
                            targetId='nist-800-53:' + normalise_identifier(target), targetEdition='5.2.0',
                            sourceUri='https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all',
                            sourceHash=digest, sourceEdition='2.0', kind='Publisher',
                            basis='NIST CPRT informative reference: ' + label,
                            relationship='InformativeReference'))
        else:
            check_workbook(raw)
            aescsf.load_into(existing, fw, str(path))
            book = Workbook(str(path))
            headings, body = book.table()
            indexes = {name:i for i,name in enumerate(headings)}
            for values in body:
                practice = values[indexes['Practice ID']].strip()
                control = existing.controls.get('aescsf:' + normalise_identifier(practice))
                for ism, _ in aescsf.parse_australian_references(values[indexes['Australian References']]):
                    if control:
                        control.attributes.setdefault('frameworkReferences', []).append(dict(frameworkId='ism', reference=ism,
                            targetId='ism:' + normalise_identifier(ism), targetEdition='',
                            sourceUri=fw.source_url or '', sourceHash=digest, sourceEdition=fw.revision or '',
                            kind='Publisher', basis='AEMO Australian References column; target edition not specified',
                            relationship='RelatedTo'))
        metadata = dict(id=framework,title=fw.name,edition=fw.revision or '')
        rows = control_rows(existing, framework)
    else:
        raise PolicyError('Unsupported framework import.')
    if not metadata['edition'] or not 1 <= len(rows) <= 20000 or len({r['id'] for r in rows}) != len(rows):
        raise PolicyError('Framework has no edition, invalid counts or duplicate requirements.')
    if sum(len(r['authoritativeText']) + len(r['context']) for r in rows) > 8_000_000:
        raise PolicyError('Framework text exceeds supported limits.')
    metadata.update(sourceHash=digest, sourceFile=path.name)
    metadata.setdefault('licence', 'Publisher source imported locally; redistribution permission is not granted by this import.')
    if framework == 'asd-principles':
        from .principle_links import enrich
        enrich(rows, metadata)
    return dict(framework=metadata, requirements=rows, mappings=mappings)
