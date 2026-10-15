"""Attach version-pinned topic links to ISM principles, without scoring them."""
import json
from pathlib import Path


KIND = 'PolicyCompass interpretation — needs human review'
SOURCE_CHANGED = ('Topic links are unavailable because this ISM principles source differs '
                  'from the version reviewed by PolicyCompass. The links need review before reuse.')
REVIEW_NOTICE = ('Topic links are PolicyCompass interpretations that need human review. '
                 'They do not establish equivalence or implementation effectiveness.')


def enrich(rows, metadata):
    """Update principle rows and metadata in place; return rows for caller convenience.

    Chapter actions do not inherit principle-level links: an action can cover only
    part of its principle, and its applicability must be assessed independently.
    """
    if metadata.get('id') != 'asd-principles':
        return rows
    asset = json.loads((Path(__file__).parent / 'assets' / 'essentials-topic-links.json').read_text(encoding='utf-8'))
    source = asset['source']
    # A reused packet must not retain links from our previously reviewed source.
    for row in rows:
        if 'frameworkReferences' in row:
            row['frameworkReferences'] = [r for r in row['frameworkReferences']
                if not (r.get('kind') == KIND and r.get('relationship') == 'TopicOverlap'
                        and r.get('sourceHash') == source['sourceHash'])]
    notices = metadata.setdefault('notices', [])
    notices[:] = [n for n in notices if n not in (SOURCE_CHANGED, REVIEW_NOTICE)]
    if metadata.get('sourceHash') != source['sourceHash'] or metadata.get('edition') != source['edition']:
        notices.append(SOURCE_CHANGED)
        return rows

    by_id = {row['id']: row for row in rows if row.get('frameworkId') == 'asd-principles'}
    attached = False
    for link in asset['links']:
        row = by_id.get(link['principleId'])
        if row is None:
            continue
        framework = link['targetId'].split(':', 1)[0]
        target = asset['targets'][framework]
        row.setdefault('frameworkReferences', []).append(dict(
            frameworkId=framework, reference=link['reference'], targetId=link['targetId'],
            targetEdition=target['edition'], sourceUri=source['sourceUri'],
            sourceHash=source['sourceHash'], sourceEdition=source['edition'], kind=KIND,
            basis=link['rationale'] + ' ' + link['limitation'], relationship='TopicOverlap',
            expectedTargetHash=target['sourceHash']))
        attached = True
    if attached:
        notices.append(REVIEW_NOTICE)
    return rows
