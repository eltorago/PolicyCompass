# PolicyCompass

Compare cybersecurity policy documents with WA CSP, ASD ISM and AESCSF. Import
multiple Word documents, text PDFs, Markdown/text files or ZIP archives, then
inspect matching passages and requirements that are not mentioned. Each framework
is compared independently. Matching runs locally without an AI service.

## Run

Use Python 3.13 on Windows, including Tkinter. From this repository:

```powershell
python -m pip install -r requirements.txt
python -m policycompass open
```

Open **Framework updates** to download the frameworks you want, or import their
publisher files. Publisher documents and extracts are local inputs, excluded from
this repository. The [user guide](policycompass/README.md) covers the full workflow.

## Command line

```powershell
python -m policycompass corpus update --framework ism
python -m policycompass compare examples/framework-alignment --framework ism --scope "Fictional example policies" --assessment example.wacc --format json
python -m policycompass report example.wacc --format html --output report.html
```

Comparisons and exports retain supporting passages and source locations. Results
are **Mentioned**, **Related wording**, **Not mentioned** or **Unable to check**;
these describe document alignment, not certification of compliance.

Existing WACC `.wacc` files remain readable, with their original framework
snapshots and history. See [migration notes](docs/MIGRATION.md).

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

See [testing](tests/README.md) and [Windows builds](docs/BUILD.md).
The desktop and CLI share `policycompass/`; `framework_core/` contains the
framework models, vocabulary and loaders extracted from WACC. The original WACC
control workspace and operational reporting are maintained separately.
