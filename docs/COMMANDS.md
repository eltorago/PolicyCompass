# Command line guide

Run commands from the repository folder after installing
`requirements.txt`. Use `python -m policycompass --help` to list commands, or add
`--help` after a command to see its options.

In a compiled release, replace `python -m policycompass` with
`core/policycompass.exe`. Start the local browser workspace with
`python -m policycompass browser`. The original desktop uses
`python -m policycompass open`.

## Download or import frameworks

List installed editions:

```powershell
python -m policycompass frameworks --format json
```

Download only the frameworks you need:

```powershell
python -m policycompass corpus update --framework wa-csp --framework ism --framework csf
```

With no `--framework` argument, `corpus update` downloads all automatic framework
choices, including the three ASD Essentials chapters and ASD cyber security
principles. It needs internet access. Later comparisons use the local copies.
AESCSF needs the Core workbook downloaded from AEMO:

```powershell
python -m policycompass corpus update --framework aescsf --import-file "C:/Downloads/AESCSF Core.xlsx"
```

See [framework sources](FRAMEWORKS.md) for the available editions and formats.
The [Essentials guide](ESSENTIALS.md) has examples using `essentials-it`,
`essentials-cloud`, `essentials-ot` and `asd-principles`.

## Compare documents

```powershell
python -m policycompass compare policies.zip policy.docx --framework wa-csp --also-assess ism --scope "Current business policies" --assessment comparison.policycompass --format json
```

Use files, folders or ZIP archives as inputs. Repeat `--also-assess` to add
frameworks. Add `--recurse` to include subfolders outside ZIP archives. The
`--scope` description is required so a reader knows what the comparison covers.
Use `--assessment` to save the results for reopening and reports.

For an Essential Eight review, include ISM and choose `--ism-maturity ML1`, `ML2`
or `ML3`. Omit this option for the full ISM. The filter selects controls tagged
by ASD for that level; it does not assign a maturity rating. Download ISM again
if an older local copy does not contain the tags.

The [demo walkthrough](DEMO.md) has commands using the supplied fictional policies.

## Inspect and export results

```powershell
python -m policycompass requirements comparison.policycompass --status "Not mentioned" --format json
python -m policycompass evidence comparison.policycompass --format json
python -m policycompass gaps comparison.policycompass --format json
python -m policycompass validate comparison.policycompass --format json
python -m policycompass report comparison.policycompass --framework ism --format html --output report.html
python -m policycompass open comparison.policycompass
```

`gaps` includes both **Not mentioned** and **Unable to check**. Keep the distinction:
an unreadable document cannot establish that wording is absent. `validate` checks
the saved file and reports whether the original documents have changed.

Reports support HTML, CSV, Markdown and JSON. Repeat `--framework` on `report` to
select several frameworks, or omit it to include all frameworks in the saved run.
Use `--summary-only` to leave out matching policy passages. Framework wording still
appears in the report. Use `--force` to replace an existing output file.

## File limits

| Limit | Maximum |
|---|---:|
| Documents in one comparison, including ZIP members | 250 |
| Each input file | 16 MiB |
| Uncompressed ZIP contents | 32 MiB |
| Extracted text in one comparison | 8 million characters |
| Sentence windows searched | 50,000 |

A MiB is 1,048,576 bytes. Scanned PDFs need text recognition before import. Nested
ZIPs and unsupported files are listed as skipped. Unsafe archives are rejected;
duplicate documents are counted once. Split large inputs into smaller, clearly
named comparisons when a limit is reached.

Older rule-based analysis also stops at 10,000 evidence records or 16 MiB of
stored evidence. It does not save a partial run after reaching either limit.
Opening an original document from a saved comparison requires a supported local
file type and a matching file hash.

## Exit codes and older commands

The command line returns `0` on success and `7` when it finishes with limitations,
such as unreadable documents or a failed framework update. Other failures return
a nonzero code and an error message. JSON output includes status, warnings and
errors for scripts to check.

`analyse`, `review`, `finalise`, `snapshot` and signed `corpus` package commands
remain available for older assessments and scripts. Use `compare` for new wording
comparisons. See [saved files and configuration](MIGRATION.md) and
[how matching works](MATCHING.md).
