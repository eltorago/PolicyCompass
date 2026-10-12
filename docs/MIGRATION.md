# Saved files and configuration

A `.policycompass` file contains extracted policy text, framework wording,
comparison results and history. You can reopen it without downloading the
frameworks again. Keep these files and exported reports in a folder suitable for
the information they contain; saved comparisons are not encrypted by the app.

## Reopen an older comparison

Older SQLite assessment files remain readable even if they have a different
extension. In **Open**, choose **All files**, select the assessment, then use
**Save a copy** to save it with the `.policycompass` extension.

Past runs keep the wording, results, identifiers and engine version used at the
time. A new framework download or matching change affects new runs. To search
revised policies, choose **Compare new documents** and select the original files.
The app keeps earlier runs in **History**.

Some older files retained only selected passages. Make a new comparison from the
original documents to search their full text. Originals are also needed when you
choose to open a source document from the app.

## Choose where frameworks are stored

The default locations are:

| Files | Windows folder |
|---|---|
| Downloaded and imported frameworks | `%LOCALAPPDATA%/PolicyCompass/frameworks` |
| Installed signed framework packages | `%LOCALAPPDATA%/PolicyCompass/corpus` |

Developers can set these environment variables before starting the app:

| Setting | What it points to |
|---|---|
| `POLICYCOMPASS_FRAMEWORK_CACHE` | Folder for downloaded and imported frameworks |
| `POLICYCOMPASS_LIBRARY` | Prepared library containing `sources/files` and `data/corpus` |
| `POLICYCOMPASS_SOURCES` | Publisher-file folder used when calling `framework_core` directly |

For an isolated local demo cache in PowerShell:

```powershell
$env:POLICYCOMPASS_FRAMEWORK_CACHE = Join-Path (Get-Location) "data/local/demo-frameworks"
python -m policycompass corpus update --framework wa-csp --framework csf
```

This setting applies to that shell and the app processes it starts. The app uses
an explicit library path for its own loaders; `POLICYCOMPASS_SOURCES` is for direct
loader use. Existing installations are not moved automatically.

## Signed framework packages

Signed packages use `.policycompasspack`. Reinstall an older package with:

```powershell
python -m policycompass corpus install "C:/Frameworks/package.policycompasspack"
```

The installer checks contents and signatures, regardless of the original filename,
and stores the package with the current extension. It requires a trusted signing
key configured by the maintainer. See [build and distribution](BUILD.md).

## Files kept out of Git

Publisher downloads, extracted framework text, private policies, saved comparisons,
local dependencies and builds are excluded from Git. The records in
`sources/permissions.json` and `sources/acquisition.json` describe where source
files came from and the recorded permission conditions. They do not grant new
permission to redistribute a source or provide a licence for the application.

The desktop and command line share `policycompass/`. Framework models and file
readers live in `framework_core/`.
