# Testing PolicyCompass

Use Python 3.13 on Windows with Tkinter. Install the development requirements and
run the suite from the repository folder:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## What the tests cover

The tests check document and ZIP imports, matching, file limits, saved history,
report exports, framework downloads and recovery after failed updates. They also
check that the command line and document-reading worker run from a standalone
checkout. Most cases use small fictional inputs and need no network access.

Desktop tests need a graphical Windows session. CI runs the fictional cases on
Windows. The document worker uses Windows Job Objects to limit memory and refuses
to parse documents on other platforms.

## Demo policy checks

Run the demo matching regressions on their own:

```powershell
python -m unittest discover -s tests -p test_demo_alignment.py -v
```

These checks search all eight supplied policies for 16 independently worded
requirements. They also use topics absent from the demo set and sentences wrapped
at different widths. Regressions check exact source offsets, list and paragraph
boundaries, negative statements, long parent context, misleading short matches
and saved results from the earlier matching version.

Keep test requirements separate from the example policies. Do not change a policy
or lower a threshold just to increase a match count. Diagnose whether a miss comes
from extraction, sentence boundaries, wording, framework context or an actual
policy gap. Check unrelated and qualified passages whenever retrieval changes.

For a publisher check, follow the [demo walkthrough](../docs/DEMO.md) with the
framework editions installed locally. Inspect the actual passages against the
source requirements, save and reopen the comparison, and export each report format.
Record the editions used. A count of matching requirements is not an accuracy or
compliance score.

## Tests that need publisher files

Some older integration tests skip when their local publisher inputs are absent.
To run them, prepare the reviewed WA extract at `data/corpus/wa-csp.json`, plus the
ISM catalogue, AESCSF Core workbook, CSF workbook and ISM Essential Eight profiles
under `sources/files/`.

These files stay outside Git. The old WA training checks depend on the exact
reviewed extract. A newer edition needs its own review before those rules can be
used; normal wording comparisons do not depend on them. See
[framework sources](../docs/FRAMEWORKS.md) and [configuration](../docs/MIGRATION.md).

## Check instructions and presentation

After editing a guide, check local links and run any changed commands. For desktop
changes, open a saved fictional comparison and inspect the affected screens. Check
an exported HTML report in a browser where one is available. Screenshots should
show only fictional documents and relevant framework text, with readable labels
and no private paths or unrelated windows.
