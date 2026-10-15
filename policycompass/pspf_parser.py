"""Read the numbered requirements table, excluding recommended approaches."""
import re

from .contracts import PolicyError


def _tables(page, columns):
    """Keep text crossing a row border with the row where the line starts."""
    if not hasattr(page, 'find_tables'):
        return page.extract_tables()
    from pdfplumber.utils import extract_text

    result = []
    for table in page.find_tables():
        values = table.extract()
        for cells, geometry in zip(values, table.rows):
            first = (cells[0] or '').strip() if cells else ''
            if first == 'Req Number':
                columns = [' '.join((cell or '').split()) for cell in cells]
            if not first.isdigit() or not columns:
                continue
            index = next((i for i, name in enumerate(columns)
                          if re.fullmatch(r'Release \d+ Requirement', name)), None)
            if index is None or index >= len(geometry.cells) or geometry.cells[index] is None:
                continue
            left, top, right, bottom = geometry.cells[index]
            # Table.extract assigns a character by its vertical midpoint. In the
            # July 2026 PDF a final line of retired Req 92 crosses the border and
            # is consequently attached to Req 93. Its top edge retains its row.
            chars = [c for c in page.chars if left <= (c['x0'] + c['x1']) / 2 < right
                     and top <= c['top'] < bottom]
            cells[index] = extract_text(chars) if chars else ''
        result.append(values)
    return result


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
            for table in _tables(page, columns):
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
