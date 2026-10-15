# Essentials integration checks

Checked on 15 October 2026 against the source editions listed below. These checks
cover import fidelity, framework relationships and application behaviour. They
do not measure operational effectiveness or certify compliance.

## Source and import run

All 4,049 checks passed. The audit imported the three chapters into an empty cache
through the bounded document worker and compared the output with an independent
reading of the PDF tables.

- All 19 source files were retained: 17 PDFs, the assessment workbook and the ISM
  catalogue. A fresh internet download matched the reviewed collection exactly.
- All 197 actions, 41 shared principles, domain ticks, phase assignments,
  responsibility markers and source locations matched. The separate principles
  choice retained all 49 ISM principles.
- All 893 potential-evidence references were preserved, including 179 external
  SP 800-171r3 references. Assessment indicators and workbook scores did not become
  additional requirements.
- Incomplete, corrupt and interrupted updates left the installed collection intact.

## Cross-framework run

All 60 checks passed. The combined corpus contained 3,337 requirements across
eleven choices and 2,543 relationship occurrences:

| Relationship | Count |
| --- | ---: |
| Chapter action to shared principle | 197 |
| Enterprise IT potential evidence to ISM, CSF and AESCSF | 714 |
| CSF informative references to SP 800-53 | 736 |
| AESCSF references to ISM | 802 |
| PolicyCompass topic suggestions to WA CSP, PSPF and ASD strategies | 94 |

The 714 potential-evidence references represent 713 distinct action/target pairs;
one reference appears in two publisher groups. Missing or unsupported targets
remain visible. The audit checked changed editions and source fingerprints, and
confirmed that suggested links are withheld when their reviewed source changes.

The existing 3,091 requirement results were identical with and without the new
frameworks selected, using both the eight demo policies and an independent test
document. Removing relationships left every matching result unchanged. The
combined corpus and saved runs passed their strict JSON contracts.

Positive matching checks retrieved all 197 action texts: 173 were **Mentioned**
and 24 were **Related wording**. The result was the same through document
extraction and direct passage input. Nine independently worded checks produced
eight **Mentioned** results and one **Related wording** result. The demo policies
produced fewer overlaps because they use different wording and cover only part
of the chapter scope. Matching thresholds, dictionaries and example policies
were not changed to increase these counts.

Of the 24 exact texts labelled **Related wording**, 23 triggered the existing
qualification or negative-word caution. One action spans two sentences; neither
sentence alone met the threshold for **Mentioned**. These are matching limits,
not missing source text.

Evidence spread across sentences can also be missed. For example, the demo's
backup-testing statement and its separate recovery-target statement each fall
just below the retrieval threshold for `IT.PRO-10.3`. The matcher does not combine
them. **Not mentioned** therefore means no sufficiently overlapping passage was
retrieved; it does not establish that the policy set lacks the requirement.

After the scope-label fix, 37 focused checks passed for ML1, ML2 and ML3. References
to excluded ISM controls were labelled correctly, all relationship endpoints
remained in scope, and saved results continued to pass their contracts.

## Application run

All 159 regression tests and both browser workflows passed. The Essentials browser
workflow used all eleven framework choices and the eight fictional policies. It
checked domain and phase filters, blank cloud responsibility, source links,
narrow-screen layout and HTML, CSV, Markdown and JSON exports. The HTML report
was also opened in a browser.

Reopening an earlier run and importing a downloaded comparison reproduced the
original report exactly, including framework text, references and matches. An
unrelated catering document left all 197 Essentials actions **Not mentioned**.
No browser errors were recorded. [Screenshots](ESSENTIALS.md) show the source
context and unknown cloud responsibility in the tested app.

Testing also corrected PSPF text crossing PDF row boundaries and stale reference
labels after an ISM maturity filter excluded a target. Source wording differences
and ATT&CK links are visible in the browser and readable reports. Prepared local
principles and downloaded principles now retain identical editions, source
fingerprints and topic links when their source bytes match.

## Editions used

| Source | Edition |
| --- | --- |
| ASD Essentials | 15 October 2026 |
| ISM and ASD principles | 2026.09.4 |
| WA Government Cyber Security Policy | 2026 |
| NIST CSF | 2.0 |
| NIST SP 800-53 | 5.2.0 |
| PSPF List of Requirements | July 2026 |
| ASD mitigation strategies | February 2017 |
| AESCSF | Core v2 workbook |

The AESCSF workbook labels its edition using its sheet title; ASD's reference
guide calls it v2. That difference is shown for review. AESCSF references that do
not specify an ISM edition keep that caveat.

See [testing instructions](../tests/README.md) to repeat the automated and browser
checks. Publisher files, generated comparisons and detailed local audit outputs
stay outside Git. The [source notes](ESSENTIALS-SOURCES.md) record reading coverage
and unavailable material.
