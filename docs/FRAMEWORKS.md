# Framework sources

The app downloads publisher files when you choose **Download updates**. It keeps
a local copy and records the file hash, download address, edition and parser
version. A failed download or parse leaves the current version in place.

| Choice | Source and format | Compared rows |
|---|---|---|
| WA CSP | [WA Government policy page](https://www.wa.gov.au/government/publications/wa-government-cyber-security-policy), PDF | Numbered requirements, including nested controls in the 2026 policy |
| ASD ISM | [ASD OSCAL releases](https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/ism/ism-oscal-releases), JSON from ASD's GitHub mirror | ISM security controls |
| ASD mitigation strategies | [ASD strategies](https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/mitigating-cyber-security-incidents/strategies-to-mitigate-cybersecurity-incidents), HTML | The 37 strategies in the February 2017 publication |
| NIST CSF | [NIST CSF](https://www.nist.gov/cyberframework), CPRT Excel export | Active CSF 2.0 subcategories; function and category headings provide context |
| PSPF | [2026 List of Requirements](https://www.protectivesecurity.gov.au/publications-library/pspf-release-2026-list-requirements), PDF | Active numbered requirements; recommended approaches and retired entries are excluded |
| NIST SP 800-53 | [NIST catalogue](https://github.com/usnistgov/oscal-content/tree/main/nist.gov/SP800-53/rev5), OSCAL JSON | Active controls and enhancements; withdrawn controls are excluded |
| AESCSF | [AEMO Core workbook](https://www.aemo.com.au/initiatives/major-programs/cyber-security/aescsf-framework-and-resources), local Excel import | Practices, with their objective context |

## WA policy editions

The download selects the newest non-draft policy PDF identified on the official
page. The parser supports the 2024 and 2026 editions and reads the edition from the
PDF itself. It rejects an unknown layout rather than silently labelling it as a
supported policy. The 2026 importer preserves nested references such as `3.1.1a`
and includes parent conditions, including the Protect implementation deadline.
Footnotes, running page headings and the separate guidance section are excluded
from the requirement text.

The earlier training rules are tied to their reviewed 2024 source hash. They do
not carry over to the 2026 text. The wording comparison works for both editions.
Saved comparisons retain their own framework snapshots after an update.

## Essential Eight

Essential Eight is part of the ISM and the ASD mitigation strategies. It is not a
separate framework choice in PolicyCompass.

Choose **All ISM controls**, **ML1**, **ML2** or **ML3** when creating a comparison.
The filter uses ASD's `essential-eight-applicability` properties in the downloaded
ISM catalogue. It preserves the original ISM identifiers and does not count the
controls twice. The selected level is saved with the framework and appears in
reports. An old cache without these tags needs a fresh ISM download.

The mitigation-strategies view retains ASD's published effectiveness ratings.
The eight strategies rated **Essential** can be found in their source context.
The February 2017 strategies are shown with that edition; the app does not rewrite
the historical publication with newer ISM wording.

## AESCSF import

1. Open **Framework updates → Open AEMO download page**.
2. Download the **AESCSF Framework Core** workbook, rather than a toolkit.
3. Choose **Import AESCSF workbook** and select the downloaded `.xlsx` file.

The app reads the workbook's edition and practice identifiers, validates its
structure and copies it into the framework cache. No filename changes are needed.
Importing a newer workbook retains the previous version and existing comparisons.
If the workbook is invalid, the import leaves the active version unchanged.

Equivalent command:

```powershell
python -m policycompass corpus update --framework aescsf --import-file "C:/Downloads/AESCSF Core.xlsx"
```

AESCSF is excluded from the default automatic update batch because AEMO can block
automated downloads. Its dedicated import path is available in the same screen.

## Interpreting coverage

PSPF applicability and start dates remain visible as context; the app does not
choose which obligations legally apply to an entity. Its reporting-question
mandatory flag is not treated as a separate control requirement. NIST control
parameters remain labelled where the organisation must supply a value.

Publisher files and extracted text stay in the local cache and are not bundled
with the application. Framework matching reports document coverage. Reviewers
still need to assess applicability, meaning and evidence of implementation.
