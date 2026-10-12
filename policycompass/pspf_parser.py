"""Read the numbered requirements table, excluding recommended approaches."""
import re

from .contracts import PolicyError


def parse(path):
    import pdfplumber

    title = None
    columns = None
    rows = []
    guidance = False
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) > 100:
            raise PolicyError('PSPF file exceeds the supported page limit.')
        for number, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                for cells in table:
                    cells = [' '.join((cell or '').split()) for cell in cells]
                    first = cells[0] if cells else ''
                    if re.fullmatch(r'PSPF Release \d{4}.*List of Requirements', first):
                        title = first
                        continue
                    if first == 'PSPF Recommended Approach':
                        guidance = True
                    if guidance:
                        continue
                    if first == 'Req Number':
                        columns = cells
                        continue
                    if not first.isdigit():
                        if any(cells) and columns:
                            raise PolicyError('Unrecognised row in the PSPF requirements table.')
                        continue
                    if not title or not columns or len(cells) != len(columns):
                        raise PolicyError('PSPF table headings or columns have changed.')
                    record = dict(zip(columns, cells))
                    text_column = next((c for c in columns if re.fullmatch(r'Release \d+ Requirement', c)), None)
                    if not text_column or not {'Domain', 'Section'} <= record.keys():
                        raise PolicyError('PSPF requirement columns are missing.')
                    decision = next((record[c] for c in columns if c.startswith('Decision')), '')
                    if re.search(r'\b(retire[ds]?|ceased)\b', decision, re.I):
                        continue
                    text = record[text_column]
                    if not text:
                        raise PolicyError('A numbered PSPF requirement has no text.')
                    applicability = next((record[c] for c in columns if c.startswith('Applicability')), '')
                    section = record['Section']
                    context = 'Applicability: ' + applicability if applicability else ''
                    start = record.get('Start Date', '')
                    if start:
                        context += ('\n' if context else '') + 'Start date: ' + start
                    # The mandatory-reporting column describes the reporting question,
                    # not the force of the underlying requirement.
                    rows.append(dict(id='pspf:req ' + first, frameworkId='pspf', officialReference='Req ' + first,
                                     heading=record['Domain'] + ' > ' + section, parentId=None,
                                     authoritativeText=text, context=context,
                                     sourceLocator=dict(reference='Req ' + first, section=section, page=number)))
    if not title or not rows:
        raise PolicyError('The file does not contain a PSPF List of Requirements table.')
    return dict(id='pspf', title='Protective Security Policy Framework', edition=title), rows
