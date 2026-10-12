# PolicyCompass

Find where your policies address a cybersecurity framework, and where the wording is missing.

PolicyCompass reads Word documents, text PDFs, Markdown, text files and ZIP archives.
For each framework requirement, it shows the relevant passages and their locations in
your documents. You can compare a whole policy set against several frameworks in one
run, then save the results or export a report.

Documents and comparisons stay on your computer. Framework downloads need internet
access; document matching runs locally without an AI service.

## What you can use it for

- **Review a policy set.** Bring together access, incident response, supplier, backup
  and other policies. Find requirements that none of the documents mention.
- **Prepare for an audit.** Give reviewers a report linking framework requirements
  to specific policy passages, then check the evidence and record what needs work.
- **Plan a framework transition.** Compare your existing policies with the 2026 WA
  Cyber Security Policy and use the unmatched requirements to organise the review.
- **Check a draft revision.** Run the revised documents through the same framework,
  keep the earlier comparison in History, and compare the exported reports.
- **Answer different reporting needs.** Assess the same documents against ISM,
  NIST CSF and other frameworks, then export a separate report for each audience.
- **Focus an Essential Eight review.** Select the ISM controls for ML1, ML2 or ML3
  and see which ones your documents discuss. The filter does not assign a maturity rating.

## Frameworks

| Framework | How to obtain it in the app |
|---|---|
| WA Government Cyber Security Policy, including the 2026 edition | Download from WA Government |
| ASD Information Security Manual (ISM) | Download from ASD; includes Essential Eight maturity filters |
| ASD Strategies to Mitigate Cyber Security Incidents | Download the published February 2017 strategies, including the Essential Eight |
| NIST Cybersecurity Framework 2.0 | Download the NIST workbook |
| Protective Security Policy Framework (PSPF) | Download the 2026 List of Requirements |
| NIST SP 800-53 Rev. 5 | Download the NIST control catalogue |
| Australian Energy Sector Cyber Security Framework (AESCSF) | Import the Core workbook downloaded from AEMO |

The app records the edition used in each comparison. Essential Eight is available
through ISM maturity filters and the ASD strategies, rather than as a duplicate
framework. Framework requirements are assessed independently; a match in one does
not automatically count as a match in another.

## Start a comparison

Use **Python 3.13 on Windows**, with Tkinter installed. From the repository folder:

```powershell
python -m pip install -r requirements.txt
python -m policycompass open
```

1. Open **Framework updates**, select the frameworks you need, and choose
   **Download updates**.
2. For AESCSF, choose **Open AEMO download page**, download the **Core workbook**,
   then choose **Import AESCSF workbook**. Select the downloaded file as it is;
   there is no need to rename it or put it in a particular folder.
3. Choose **New comparison**, describe the documents you are reviewing, and select
   your frameworks. If using ISM, choose all controls or an Essential Eight maturity level.
4. Add your files or ZIP archives, then choose **Compare and save**.

To try it out, use the fictional documents in [examples/framework-alignment](examples/framework-alignment/).
The [user guide](policycompass/README.md) covers results, saved files and reports.

## Reading the results

Each requirement is labelled **Mentioned**, **Related wording**, **Not mentioned**
or **Unable to check**. Open a result to read the framework text beside the matching
passages. Reports are available as HTML, CSV, Markdown or JSON.

Review the passages before drawing conclusions. Similar wording can have a different
meaning, and an implemented control may be documented elsewhere. The tool checks
document coverage; it cannot verify that controls operate effectively. Scanned PDFs
need text recognition before import.

Saved `.policycompass` files retain the documents' extracted text, framework wording
and comparison history. Updating a framework affects new comparisons; saved runs
keep the edition they used. See [configuration and saved files](docs/MIGRATION.md).

## Command line

Download frameworks and compare the example documents:

```powershell
python -m policycompass corpus update --framework wa-csp --framework csf
python -m policycompass compare examples/framework-alignment --framework wa-csp --also-assess csf --scope "Fictional example policies" --assessment example.policycompass --format json
python -m policycompass report example.policycompass --format html --output report.html
```

For ISM controls associated with Essential Eight ML2:

```powershell
python -m policycompass corpus update --framework ism
python -m policycompass compare policies.zip --framework ism --ism-maturity ML2 --scope "Essential Eight policy review" --assessment essential-eight.policycompass
```

See [commands and file limits](docs/COMMANDS.md) and [framework sources](docs/FRAMEWORKS.md).

## Development

This is a Windows pilot. To run the tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

The desktop and command line share the `policycompass/` application code.
`framework_core/` contains the framework models and loaders. Publisher files,
private policies and generated comparisons are excluded from Git.

For a change, include a test that demonstrates the behaviour, run the suite, and
update the relevant guide. See [testing](tests/README.md) and [Windows builds](docs/BUILD.md).
