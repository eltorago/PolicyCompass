# Build and run the Windows application

You can run PolicyCompass from source with Python 3.13 and Tkinter. To make an
application folder that runs without a separate Python installation, use
PyInstaller through the supplied build command:

```powershell
python -m pip install -r requirements-dev.txt
python -m policycompass.build
```

Run both commands from the repository folder. The application is written to:

```text
data/local/offline-build/dist/policycompass/policycompass.exe
```

Double-click the executable to open the desktop. It also accepts the arguments
shown in the [command line guide](COMMANDS.md). Distribute the entire
`policycompass` application folder, including its supporting files.

## What the build contains

The build includes application code, rule files, framework source details,
trusted-key settings and required libraries. Publisher documents and saved
comparisons are excluded. Use **Framework updates** in the app to prepare the
frameworks you want to compare against.

The output includes file hashes, a list of dependencies and a release record
showing the Git revision and any uncommitted changes. These let a maintainer
identify what was built and check the files later.

## Before distribution

Run the [tests](../tests/README.md), open the built app, compare the
[demo policies](DEMO.md), then save, reopen and export a report. Repeat those
checks on a Windows machine with the same restrictions as the intended users.

This pilot is unsigned. Code signing and approval for managed workplace computers
remain release tasks. The supplied trusted-key list is empty. A maintainer must
configure an approved signing key before signed framework packages can be
installed. Normal publisher downloads use **Framework updates** and do not need
those packages.
