# Build the Windows application

The source checkout runs with Python 3.13 and Tkinter. An optional PyInstaller
build creates a self-contained Windows folder:

```powershell
python -m pip install -r requirements-dev.txt
python -m policycompass.build
```

The application is `data/local/offline-build/dist/policycompass/policycompass.exe`.
Launch it without arguments for the desktop, or pass the same CLI arguments used
with `python -m policycompass`. Distribute the entire application folder.

The build includes application rule assets, trust-key configuration, source
metadata and required libraries. Publisher documents and private comparisons
are not bundled. Prepare frameworks using the app's Framework updates screen.

The output also includes file hashes, dependency inventory and a release manifest
recording the repository revision and working-tree changes. This remains an
unsigned pilot; signing and managed-endpoint deployment acceptance are separate
release work. The shipped trust-key list is empty, so signed corpus installation
requires an explicitly approved key configured by the application maintainer.
