# Tests

Install `requirements-dev.txt`, then run:

```powershell
python -m unittest discover -s tests -v
```

The alignment and update suites use fictional inputs and local fixtures. They
cover matching, ZIP limits and unsafe paths, batch imports, unreadable documents,
report selection, source updates and recovery. The standalone suite checks that
the renamed CLI and extraction worker run without WACC and that migrated asset
paths, cache settings and saved comparisons work.

Some inherited integration tests need locally prepared publisher sources and
skip when those are absent. To run all inherited cases, prepare the reviewed
WA extract at `data/corpus/wa-csp.json`, plus the ISM catalogue, AESCSF workbook,
CSF workbook and ISM Essential Eight profiles under `sources/files/`. These are
ignored local inputs, never test fixtures committed to Git. The WA pilot rules
are pinned to their original reviewed extract; newer editions require separate
rule review. Framework imports do not require those legacy rules to run alignment.

Desktop tests require Tkinter and a graphical session. CI runs the portable
synthetic cases on Windows and Linux; Linux uses Xvfb for the desktop widget test.
