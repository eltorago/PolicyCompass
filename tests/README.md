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

The local browser tests exercise the actual HTTP server, including its session,
host and origin checks, bounded uploads, cancellation, instance reuse, framework
import, saved history and report downloads:

```powershell
python -m unittest discover -s tests -p test_local_web.py -v
```

## Browser and packaged checks

Use a fresh local workspace when testing the browser. Set `POLICYCOMPASS_HOME`,
`POLICYCOMPASS_FRAMEWORK_CACHE` and `POLICYCOMPASS_LIBRARY` to separate test folders,
then start `python -m policycompass browser --no-browser`. The first two folders are
created by the app; leave the library folder empty. The workspace's `instance.json`
contains a temporary session credential, so do not publish it.

With Node.js, Playwright 1.62.1 and Edge available, run:

```powershell
node tools/test_browser.cjs path/to/workspace/instance.json data/local/browser-screenshots
```

This tests framework setup, file selection, comparison, evidence, text escaping,
reports, history, saved-file imports, settings, reload and quitting. It also checks
a narrow layout and captures screenshots containing only generated test inputs.
The script needs a fresh framework cache on each run and quits the application
when it finishes successfully.

To create and close an isolated workspace automatically, use
`python tools/run_browser_check.py`. Add `--exe` with the path to the packaged
`core/policycompass.exe` to exercise the release. Playwright must be installed in
a location Node.js can resolve, such as a test-only directory on `NODE_PATH`.

For compiled releases, run `tools/smoke_release.py` as described in
[Windows builds](../docs/BUILD.md#check-the-build). It exercises document workers
without relying on the developer's Python environment or publisher files.

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
