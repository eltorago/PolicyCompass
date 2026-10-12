# Framework sources

The app downloads publisher files when you choose **Download updates**. It keeps
a local copy and records the edition, download address and a hash that identifies
the downloaded file. It also records which reader processed the file. If a download
fails or the app cannot read the new file, it keeps the current version.

| Choice | Source and format | What the app compares |
|---|---|---|
| WA CSP | [WA Government policy page](https://www.wa.gov.au/government/publications/wa-government-cyber-security-policy), PDF | Numbered requirements, including nested controls in the 2026 policy |
| ASD ISM | [ASD OSCAL releases](https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/ism/ism-oscal-releases), JSON from ASD's GitHub mirror | ISM security controls |
| ASD mitigation strategies | [ASD strategies](https://www.cyber.gov.au/business-government/asds-cyber-security-frameworks/mitigating-cyber-security-incidents/strategies-to-mitigate-cybersecurity-incidents), HTML | The 37 strategies in the February 2017 publication |
| NIST CSF | [NIST CSF](https://www.nist.gov/cyberframework), CPRT Excel export | Active CSF 2.0 subcategories; function and category headings provide context |
| PSPF | [2026 List of Requirements](https://www.protectivesecurity.gov.au/publications-library/pspf-release-2026-list-requirements), PDF | Active numbered requirements; recommended approaches and retired entries are excluded |
| NIST SP 800-53 | [NIST catalogue](https://github.com/usnistgov/oscal-content/tree/main/nist.gov/SP800-53/rev5), OSCAL JSON | Active controls and enhancements; withdrawn controls are excluded |
| AESCSF | [AEMO Core workbook](https://www.aemo.com.au/initiatives/major-programs/cyber-security/aescsf-framework-and-resources), local Excel import | Practices, with their objective context |

## WA policy editions

The app downloads the newest published policy PDF listed on the official page.
It supports the 2024 and 2026 editions and reads the edition from the PDF itself.
An unfamiliar layout is rejected so the app does not give it the wrong edition
or read it incorrectly. For 2026, references such as `3.1.1a` stay intact. Parent
conditions, including the Protect implementation deadline, appear as context.
Footnotes, repeated page headings and the separate guidance section are excluded
from the requirement text.

The older automated training checks only run against the exact reviewed 2024
source. Wording comparisons work for both editions. Saved comparisons keep the
framework text they used after an update.

## Essential Eight

Essential Eight is part of the ISM and the ASD mitigation strategies. It is not a
separate framework choice in PolicyCompass.

Choose **All ISM controls**, **ML1**, **ML2** or **ML3** when creating a comparison.
The filter uses the maturity tags supplied by ASD in its ISM catalogue. Original
ISM identifiers are kept and controls are counted once. The selected level is
saved with the framework and appears in reports. Download ISM again if an older
copy does not include the tags.

The mitigation-strategies view keeps ASD's published effectiveness ratings.
The eight strategies rated **Essential** can be found in their source context.
The February 2017 strategies are shown with that edition; the app does not rewrite
the historical publication with newer ISM wording.

## AESCSF import

1. Open **Framework updates → Open AEMO download page**.
2. Download the **AESCSF Framework Core** workbook, rather than a toolkit.
3. Choose **Import AESCSF workbook** and select the downloaded `.xlsx` file.

The app checks the workbook, reads its edition and practice identifiers, then
copies it into the local framework folder. No filename changes are needed.
Importing a newer workbook retains the previous version and existing comparisons.
If the workbook is invalid, the import leaves the active version unchanged.

Equivalent command:

```powershell
python -m policycompass corpus update --framework aescsf --import-file "C:/Downloads/AESCSF Core.xlsx"
```

AESCSF is excluded from the default automatic update batch because AEMO can block
automated downloads. Its dedicated import path is available in the same screen.

## Interpreting coverage

PSPF applicability and start dates appear with the requirement. A reviewer still
needs to decide which obligations apply. A mandatory reporting question does not
become an extra control in the comparison. NIST placeholders stay visible where
the organisation must choose a value, such as a review interval.

Publisher files and extracted text stay in the local cache and are not bundled
with the application. Matches show shared wording. Reviewers need to check meaning,
scope and evidence that controls work. The [matching guide](MATCHING.md) explains
the result labels and common reasons for missed matches.
