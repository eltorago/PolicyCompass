# Build and run the Windows application

Use 64-bit Python 3.13 on Windows. The build bundles Python, the application,
browser interface and runtime libraries. Users do not need Python installed.

```powershell
python -m pip install -r requirements-dev.txt
python -m policycompass.build
```

Run both commands from the repository folder. The application is written to:

```text
data/local/browser-build/PolicyCompass/PolicyCompass.exe
```

Double-click it to open the local browser workspace. The `core/policycompass.exe`
program accepts the arguments in the [command line guide](COMMANDS.md), including
`open` for the original Tkinter desktop.

The `data/local/browser-build/release` folder contains a portable ZIP, checksums,
dependency list and release manifest. Users must extract the complete ZIP.

## Build the EXE installer

Install [Inno Setup](https://jrsoftware.org/isinfo.php), then run:

```powershell
python -m policycompass.build --installer --iscc "C:/Program Files (x86)/Inno Setup 6/ISCC.exe"
```

The installer is written beside the portable ZIP. It installs for the current user
and adds a Start menu shortcut. It does not request administrator privileges.
Code signing is not configured. The browser guide explains
[user data locations](BROWSER.md#where-files-are-kept), which survive uninstall.

The small windowed launcher starts the core without a console window. The core
keeps standard input and output available to its document worker. This avoids
breaking parser communication when using a windowed executable.

## What the build contains

The build includes application code, the browser interface, rule files, framework
source details, trusted-key settings, libraries and third-party licence notices.
Example policies, publisher documents, tests, local development files and saved
comparisons are excluded. Use **Framework updates** to prepare the frameworks you
want to compare against.

The output includes file hashes, a list of dependencies and a release record
showing the Git revision and any uncommitted changes. These let a maintainer
identify what was built and check the files later.

## Check the build

Run the [tests](../tests/README.md), then check the compiled core in a fresh local
workspace:

```powershell
python tools/smoke_release.py --exe data/local/browser-build/PolicyCompass/core/policycompass.exe
```

This check removes Python and application overrides from the child environment.
It imports a synthetic framework, reads TXT/DOCX/PDF/ZIP inputs, compares text,
reopens saved results, exports every format, reuses an existing instance and quits.
The test inputs are generated outside the release payload.

Open the packaged browser interface and test the main workflow. For automated
browser checks, start the core with `browser --no-browser` and use
`tools/test_browser.cjs` with Playwright and Edge. See [testing](../tests/README.md).

## Publish a release

The **Windows release** GitHub Actions workflow builds and checks the unsigned
installer and portable ZIP. Running it manually saves workflow artifacts. Pushing
a tag that matches `ENGINE_VERSION`, such as `v0.5.0-pilot`, also publishes a GitHub
prerelease using the matching file in `docs/releases/`.

The workflow pins and checks the Inno Setup compiler download. Release artifacts
include SHA-256 checksums, a dependency list and a manifest with the Git revision.
For a replacement release, use a new version and tag so existing downloads keep
their original meaning. Users can reinstall a previous version; saved comparisons
are stored separately from the installation.

This pilot is unsigned. The supplied trusted-key list is empty. A maintainer must
configure an approved signing key before signed framework packages can be
installed. Normal publisher downloads use **Framework updates** and do not need
those packages.
