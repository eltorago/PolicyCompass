"""Published audit metadata used by the framework registry."""
import json
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parents[1] / 'data/wa-audit-context.json').read_text(encoding='utf-8'))
REPORTS = DATA['reports']
for report in REPORTS:
    report['url'] = 'https://audit.wa.gov.au/reports-and-publications/reports/' + report['slug'] + '/'
