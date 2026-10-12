"""Supported framework choices and their publisher sources."""

NAMES = {
    'wa-csp': 'WA CSP',
    'ism': 'ASD ISM',
    'aescsf': 'AESCSF',
    'asd-strategies': 'ASD mitigation strategies',
    'csf': 'NIST CSF 2.0',
    'pspf': 'PSPF',
    'nist-800-53': 'NIST SP 800-53',
}

AUTOMATIC = tuple(key for key in NAMES if key != 'aescsf')

PAGES = {
    'wa-csp': 'https://www.wa.gov.au/government/publications/wa-government-cyber-security-policy',
    'ism': 'https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/ism/ism-oscal-releases',
    'asd-strategies': 'https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/mitigating-cyber-security-incidents/strategies-to-mitigate-cybersecurity-incidents',
    'csf': 'https://www.nist.gov/cyberframework',
    'pspf': 'https://www.protectivesecurity.gov.au/publications-library/pspf-release-2026-list-requirements',
    'nist-800-53': 'https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final',
    'aescsf': 'https://www.aemo.com.au/initiatives/major-programs/cyber-security/aescsf-framework-and-resources',
}

FILENAMES = {
    'wa-csp': 'wa-cyber-security-policy.pdf', 'ism': 'ISM_catalog.json',
    'asd-strategies': 'asd-strategies.html',
    'csf': 'nist-csf-2.0-cprt-all-olir.xlsx', 'pspf': 'pspf-list-of-requirements.pdf',
    'nist-800-53': 'NIST_SP-800-53_rev5_catalog.json', 'aescsf': 'aescsf-framework-core.xlsx',
}

DIRECT_DOWNLOADS = {
    'ism': 'https://raw.githubusercontent.com/AustralianCyberSecurityCentre/ism-oscal/main/ISM_catalog.json',
    'asd-strategies': PAGES['asd-strategies'],
    'csf': 'https://csrc.nist.gov/extensions/nudp/services/json/csf/download?olirids=all',
    'nist-800-53': 'https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json',
}

HOSTS = {
    'wa-csp': {'www.wa.gov.au', 'wa.gov.au'}, 'ism': {'raw.githubusercontent.com'},
    'asd-strategies': {'www.cyber.gov.au'}, 'csf': {'csrc.nist.gov'},
    'pspf': {'www.protectivesecurity.gov.au'}, 'nist-800-53': {'raw.githubusercontent.com'},
    'aescsf': {'www.aemo.com.au', 'aemo.com.au'},
}

REPOSITORY_PATHS = {
    'ism': '/AustralianCyberSecurityCentre/ism-oscal/',
    'nist-800-53': '/usnistgov/oscal-content/',
}
