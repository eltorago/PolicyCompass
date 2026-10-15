# PolicyCompass

Find passages in your policies that relate to a cybersecurity framework, and requirements that need a closer look.

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
  Cyber Security Policy or ASD Essentials and use the unmatched requirements to
  organise the review.
- **Check a draft revision.** Run the revised documents through the same framework,
  keep the earlier comparison in History, and compare the exported reports.
- **Answer different reporting needs.** Assess the same documents against ISM,
  NIST CSF and other frameworks, then export a separate report for each audience.
- **Focus an Essential Eight review.** Select the ISM controls for ML1, ML2 or ML3
  and see which ones your documents discuss. The filter does not assign a maturity rating.
- **Review different technology environments.** Compare policies with the
  enterprise IT, cloud or operational technology chapters of ASD Essentials, then
  use their domains and priority phases to organise the findings.

## Frameworks

| Framework | How to obtain it in the app |
|---|---|
| WA Government Cyber Security Policy, including the 2026 edition | Download from WA Government |
| ASD Information Security Manual (ISM) | Download from ASD; includes Essential Eight maturity filters |
| ASD Cyber Security Principles | Download the 49 principles from the ISM catalogue |
| ASD Essentials: enterprise IT, cloud and operational technology | Download the complete ASD publication collection; select chapters separately |
| ASD Strategies to Mitigate Cyber Security Incidents | Download the published February 2017 strategies, including the Essential Eight |
| NIST Cybersecurity Framework 2.0 | Download the NIST workbook |
| Protective Security Policy Framework (PSPF) | Download the 2026 List of Requirements |
| NIST SP 800-53 Rev. 5 | Download the NIST control catalogue |
| Australian Energy Sector Cyber Security Framework (AESCSF) | Import the Core workbook downloaded from AEMO |

The app records the edition used in each comparison. Essential Eight is available
through ISM maturity filters and the ASD strategies, rather than as a duplicate
framework. Framework requirements are assessed independently; a match in one does
not automatically count as a match in another.

The [Essentials guide](docs/ESSENTIALS.md) explains chapter selection, the 197
published actions and links to other frameworks. The app shows potential evidence
sources and suggested topic links separately. Those links help a reviewer find
related material; they do not establish that two requirements are equivalent.

## Start a comparison

Download the unsigned **Windows installer** from
[Releases](https://github.com/eltorago/PolicyCompass/releases). Choose the file
ending in `windows-x64-setup.exe`, install it, then open the **PolicyCompass**
shortcut. The application opens in your default browser. Python and its libraries
are included; there are no terminal commands to run.

The portable ZIP is also available. Extract the entire folder and open
`PolicyCompass.exe`. Keep its supporting files beside the launcher.

1. Open **Framework updates**, select the frameworks you need, and choose
   **Download updates**.
2. For AESCSF, choose **Open AEMO download page**, download the **Core workbook**,
   then choose **Import AESCSF workbook**. Select the downloaded file as it is;
   there is no need to rename it or put it in a particular folder.
3. Choose **New comparison**, describe the documents you are reviewing, and select
   your frameworks. If using ISM, choose all controls or an Essential Eight maturity
   level. For Essentials, choose any combination of enterprise IT, cloud and OT.
4. Add your files or ZIP archives, then choose **Compare and save**.

Comparisons are saved automatically in the local workspace. Use **Saved
comparisons** to reopen them, **Download comparison** to keep a separate copy, or
**Reports** to export results. Use **Quit PolicyCompass** to close the local
application. See the [browser guide](docs/BROWSER.md) for storage and troubleshooting.

The repository also has a [demo walkthrough](docs/DEMO.md). It uses eight fictional
policies covering governance, access, training, information handling, suppliers,
secure systems, development and recovery. Each has an owner, responsibilities,
working requirements and a review process. These example policies are excluded
from the executable release.

The [browser guide](docs/BROWSER.md) covers results, saved files and reports.
The [desktop guide](policycompass/README.md) covers the original Tkinter interface.

## Reading the results

Each requirement is labelled **Mentioned**, **Related wording**, **Not mentioned**
or **Unable to check**. Open a result to read the framework text beside the matching
passages. Reports are available as HTML, CSV, Markdown or JSON.

Review the passages before drawing conclusions. Similar wording can have a different
meaning, and a requirement with no match may be covered in different words or another
document. PolicyCompass checks wording; it cannot verify that controls work in
practice. Scanned PDFs need text recognition before import. See
[how matching works](docs/MATCHING.md) for the main limits.

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

For an Essentials review across enterprise IT and cloud:

```powershell
python -m policycompass corpus update --framework essentials-it --framework essentials-cloud --framework asd-principles
python -m policycompass compare policies.zip --framework essentials-it --also-assess essentials-cloud --also-assess asd-principles --scope "Enterprise IT and cloud policies" --assessment essentials.policycompass
```

See [commands and file limits](docs/COMMANDS.md) and [framework sources](docs/FRAMEWORKS.md).

## Development

This is a Windows pilot. To run the tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

To run the browser application from source:

```powershell
python -m policycompass browser
```

The original Tkinter desktop remains available with `python -m policycompass open`.
The browser, desktop and command line share the `policycompass/` application code.
`framework_core/` contains the framework models and loaders. Publisher files,
private policies and generated comparisons are excluded from Git.

When changing application behaviour, add a regression check, run the relevant tests
and update the guide. Documentation-only changes need a check of the instructions
and links. See [testing](tests/README.md) and [Windows builds](docs/BUILD.md).
