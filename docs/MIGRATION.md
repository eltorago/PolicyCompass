# Configuration and saved files

PolicyCompass includes the desktop, CLI, document and ZIP import, local matching,
saved comparisons and history, reports, framework updates and signed corpus
package verification. Shared framework models and loaders live in `framework_core/`.

## Saved comparisons

New comparisons and snapshots use `.policycompass`. Existing SQLite comparisons
remain readable regardless of their filename extension: select **All files** in
Open, then **Save a copy** with the new extension. Historical runs retain their
original engine version, evidence, identifiers and framework snapshots. New runs
use PolicyCompass obligation identifiers. Original policy documents are needed
only to reopen a source or make a new comparison.

Signed corpus packages use `.policycompasspack`. Reinstall previously downloaded
packages with `python -m policycompass corpus install <package-path>` to store them
under the current extension. Verification checks package contents and signatures,
not the input filename extension.

## Local configuration

The default framework cache is `%LOCALAPPDATA%/PolicyCompass/frameworks`;
signed corpus packages use `%LOCALAPPDATA%/PolicyCompass/corpus`.

| Setting | Purpose |
|---|---|
| `POLICYCOMPASS_LIBRARY` | Prepared library containing `sources/files` and `data/corpus` |
| `POLICYCOMPASS_FRAMEWORK_CACHE` | Downloaded/imported framework cache |
| `POLICYCOMPASS_SOURCES` | Prepared publisher-file cache for direct `framework_core` use |

Use these names in existing shell and launch configurations. To reuse a prepared
library or framework cache, set the appropriate path or import the publisher
files through Framework updates. The application passes an explicit library path
to its framework loaders; the standalone source setting applies to direct loader
use. Existing installations are not modified automatically.

## Source data

Publisher documents, extracted corpora, personal comparisons, local dependencies
and generated builds are excluded from Git. `sources/permissions.json` and
`sources/acquisition.json` retain source provenance and permission conditions;
they are not a new permission review or a licence for the application.
