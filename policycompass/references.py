"""Resolve source references without transferring policy results between frameworks."""
from copy import deepcopy


def resolve(rows, frameworks):
    targets = {r['id']: r for r in rows}
    editions = {f['id']: f for f in frameworks}
    mappings = []
    for row in rows:
        for reference in row.get('frameworkReferences', []):
            target_framework = editions.get(reference['frameworkId'])
            target = targets.get(reference['targetId'])
            if target_framework is None:
                reference['status'] = 'Framework not selected'
                continue
            reference['resolvedTargetEdition'] = target_framework['edition']
            reference['targetSourceHash'] = target_framework.get('sourceHash') or target_framework.get('extractHash', '')
            if target is None:
                reference['status'] = 'Reference absent from selected edition'
                continue
            expected = reference.get('expectedTargetHash')
            if expected and expected != reference['targetSourceHash']:
                reference['status'] = 'Target source differs from reviewed version'
            elif reference['targetEdition'] != target_framework['edition']:
                reference['status'] = 'Target edition differs or is not specified'
            else:
                reference['status'] = 'Edition matches'
            # Publisher assertions remain assertions, including where editions differ.
            # Interpretations are held back when their pinned target changes.
            if reference['kind'] != 'Publisher' and reference['status'] != 'Edition matches':
                continue
            mappings.append(dict(source=row['id'], target=target['id'], relationship=reference['relationship'],
                relation='MappedOnly', provenance=reference['kind'] + ': ' + reference['basis'],
                reviewStatus=reference['status'], sourceReference=deepcopy(reference)))
    return mappings
