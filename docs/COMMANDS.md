# Command line

Use `python -m policycompass --help` for all commands and add `--help` after a
command for its options. Downloads happen only when explicitly requested.

```powershell
python -m policycompass frameworks --format json
python -m policycompass corpus update --framework wa-csp --framework ism --framework csf --framework pspf --framework nist-800-53 --framework asd-strategies
python -m policycompass corpus update --framework aescsf --import-file C:/Frameworks/aescsf-framework-core.xlsx
python -m policycompass compare policies.zip policy.docx --framework wa-csp --also-assess ism --scope "Current departmental policies" --assessment comparison.policycompass --format json
python -m policycompass requirements comparison.policycompass --status "Not mentioned" --format json
python -m policycompass evidence comparison.policycompass --format json
python -m policycompass gaps comparison.policycompass --format json
python -m policycompass validate comparison.policycompass --format json
python -m policycompass report comparison.policycompass --framework ism --format html --output report.html
python -m policycompass open comparison.policycompass
```

Use `--ism-maturity ML1`, `ML2` or `ML3` on `compare` to select ISM controls
with ASD's Essential Eight applicability tag. Include `--framework ism` or
`--also-assess ism`. Omit the option to include the full ISM. An older cached
ISM without these tags must be downloaded again before the filter can be used.
The selected profile is recorded with the saved framework edition.

`corpus update` with no framework argument downloads all automatically supported
frameworks. AESCSF uses an explicit Core workbook import, as shown above.

Reports support HTML, CSV, Markdown and JSON. Repeat `--framework` on `report` to
select several frameworks; omit it to include every assessed framework. Use
`--summary-only` to omit excerpts and `--force` to replace an existing output.

Input limits are 250 documents, 16 MiB per input, 32 MiB expanded ZIP contents
and eight million extracted characters per comparison. Scanned PDFs need OCR
before import. Nested ZIPs and unsupported files are listed as skipped. Unsafe
archives are rejected and duplicate documents are counted once.

Rule-based analysis also limits generated evidence to 10,000 records and 16 MiB
of serialized evidence per comparison. If either limit is reached, the analysis
stops without saving partial results; split the inputs into smaller comparisons.
Existing saved assessments remain readable. Opening an original document from a
saved assessment requires a supported local file type and an unchanged hash.

The CLI returns code 0 on success and 7 when results contain limitations, such as
unreadable documents or failed framework updates. Other failures return nonzero
codes and an error message. JSON output includes status, warnings and errors.

Legacy `analyse`, `review`, `finalise`, `snapshot` and signed `corpus` commands
remain available for existing saved assessments and automation. New document
alignment workflows should use `compare`; it reports wording matches without
requiring reviewer approval or claiming control effectiveness.
