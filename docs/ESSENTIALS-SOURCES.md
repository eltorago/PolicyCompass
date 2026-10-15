# ASD Essentials source notes

PolicyCompass supports the ASD Essentials publications released on **15 October
2026**. The official [reading guide](https://www.cyber.gov.au/publication/essentials-reading-guide)
provides the starting sequence. The collection also includes the FAQ, glossary,
asset-scoping guides and enterprise IT evidence guide linked from the series.

## Public written sources

| Publication | PDF pages |
| --- | ---: |
| [Essentials reading guide](https://www.cyber.gov.au/publication/essentials-reading-guide) | 5 |
| [What is the Essentials?](https://www.cyber.gov.au/publication/what-is-the-essentials) | 6 |
| [The case for change](https://www.cyber.gov.au/publication/the-case-for-change) | 5 |
| [The Essentials for senior executives](https://www.cyber.gov.au/publication/the-essentials-for-senior-executives) | 13 |
| [Which chapter should I start with?](https://www.cyber.gov.au/publication/which-chapter-should-i-start-with) | 9 |
| [AI considerations within the Essentials](https://www.cyber.gov.au/publication/ai-considerations-within-the-essentials) | 12 |
| [Essentials for enterprise IT](https://www.cyber.gov.au/publication/essentials-for-enterprise-it) | 19 |
| [Essentials for cloud](https://www.cyber.gov.au/publication/essentials-for-cloud) | 24 |
| [Essentials for operational technology](https://www.cyber.gov.au/publication/essentials-for-ot) | 21 |
| [Transitioning from the Essential Eight](https://www.cyber.gov.au/publication/transitioning-from-the-essential-eight) | 25 |
| [Implementation planning guide](https://www.cyber.gov.au/publication/implementation-planning-guide) | 28 |
| [Assessment process guide](https://www.cyber.gov.au/publication/assessment-process-guide) | 27 |
| [Frequently asked questions](https://www.cyber.gov.au/publication/frequently-asked-questions) | 8 |
| [Essentials glossary](https://www.cyber.gov.au/publication/essentials-glossary) | 6 |
| [Asset scoping guide for enterprise IT](https://www.cyber.gov.au/publication/asset-scoping-guide-for-enterprise-it) | 10 |
| [Asset scoping guide for cloud](https://www.cyber.gov.au/publication/asset-scoping-guide-for-cloud) | 12 |
| [Assessment evidence guide for enterprise IT](https://www.cyber.gov.au/publication/assessment-evidence-guide-for-enterprise-it) | 64 |

The 17 PDFs total 294 pages. The enterprise IT page also provides the assessment
workbook. Its 13 worksheets contain 58 distinct actions repeated across their
applicable domains and 529 distinct indicators of good practice.

The automatic download includes these PDFs and the workbook, plus ASD's official
[ISM catalogue](https://github.com/AustralianCyberSecurityCentre/ism-oscal) for
principle definitions. It records addresses, editions and file fingerprints in a
local ZIP snapshot. Individual downloads and the saved ZIP are limited to 16 MiB;
the downloaded source collection is limited to 24 MiB before compression. The app
checks expected members and fingerprints when reading a snapshot. Publisher
documents are downloaded on demand and are not distributed with the application.

The PDFs attribute their material to the Commonwealth of Australia, 2026, under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), excluding the Coat of
Arms, entity logo, third-party content and material otherwise marked. No separate
licence statement was found in the workbook cells.

## Review coverage

The available written collection was read in three sequential passes, including
all 17 PDFs, the workbook's complete unique cell text and formula patterns, the
[ASD launch announcement](https://www.asd.gov.au/news/2026-10-15-asd-essentials-evolving-our-approach-cyber-security-resilience),
the [cyber.gov.au launch announcement](https://www.cyber.gov.au/news/asd-essentials-evolving-our-approach-to-cyber-security-resilience),
the [consultation announcement](https://www.cyber.gov.au/news/consultation-on-evolution-of-essential-eight)
and the [series landing page](https://www.cyber.gov.au/essentials). Repeated workbook
cells were compared and retained in the source record; formulas were inspected as
text and were not executed. Chapter HTML and PDF variants were compared, with
visual checks of selected diagrams and action tables.

The introductory video could not be read: its player returned HTTP 401 and no
accessible transcript was found. Historical consultation materials require the
ASD Partnership Portal. These unavailable resources are outside the review claim.

## Differences between publisher versions

PolicyCompass uses the chapter PDFs for action wording. This is an application
choice for a reproducible source, not a claim that ASD has declared all PDFs more
authoritative than its web pages. The evidence guide supplies its own action IDs,
indicator wording and potential evidence references. Source differences are kept
visible instead of silently combined.

- The cloud PDF expands several HTML actions, including AI approvals, supplier
  assurance, account management, privileged access, backups and incident response.
  It also uses **Privileged environments** where some HTML rows say **Privileged
  systems**. The outbound-content-inspection row leaves its responsibility markers
  blank; the app preserves that omission.
- Four enterprise IT actions differ between the chapter and the evidence
  guide/workbook: risk methodology approval, asset records, remediation of exposed
  credentials and the recording of administrative changes. The app retains the
  evidence-guide variant beside the chapter action.
- The workbook and evidence PDF differ in three substantive indicators for
  credential repositories (`IT.PRO-13.2`), including treatment of exceptions and
  partial MFA coverage. Seven other indicator differences are minor wording changes.
- The evidence PDF references NIST CSF `ID.RA-02` for `IT.PRO-16.2`; its HTML version
  says `DE.RA-02`. The PDF reference is retained with its source.
- The supplier-assurance principle (`GOV-11`) says **regularly verified** in the
  Essentials evidence guide and **regularly independently verified** in the ISM
  catalogue. The shared principle reference does not remove that wording difference.
- OT HTML and PDF action wording agrees, but some linked ATT&CK techniques differ.
  Technique links retain their source context and do not prove control effectiveness.

## Workbook calculations

Formula inspection identified differences from the assessment guide that matter
if the workbook is used for reporting:

- Its minimum-value calculation can let an unassessed action hide an already
  not-effective action when producing a principle rating. The guide says that one
  or more not-effective actions gives a not-effective principle rating, with
  insufficient assessment handled separately.
- Its domain percentage includes unassessed principles in the denominator and
  produces zero for a wholly unassessed domain. The guide's example reports such
  domains as **N/A** and requires that they remain distinct from ineffective domains.
- Its automatic Essential Eight status formulas check maturity flags without also
  checking whether the control belongs to the selected mitigation strategy. For
  example, a Patch applications ML3 selection can mark `ISM-0109` effective even
  though the workbook assigns that control to other strategies.

These findings come from reading formulas, not running Excel or validating a live
assessment. PolicyCompass does not import these calculations or derive ASD ratings
from policy wording. The [user guide](ESSENTIALS.md) explains what its comparison
results mean.
