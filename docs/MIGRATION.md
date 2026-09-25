# Transfer from WACC

PolicyCompass was extracted from the local WACC policy application on
25 September 2026. The source checkout was based on WACC commit
`429502846a256b53ee5a0eb04f9331c78a0175ce` plus its uncommitted separation into
`framework_alignment/` and `framework_core/`.

The application is now `policycompass/`. It includes the desktop, CLI, document
and ZIP import, deterministic alignment, saved comparisons and history, reports,
framework imports and updates, and signed corpus package verification. Framework
models, source metadata, vocabulary and loaders are retained in `framework_core/`
so PolicyCompass can run from its own checkout without installing WACC.

The transfer completes the unfinished split's launch command, worker imports,
asset paths, WA parser location, requirement-file includes and executable build.
The interface and reports use PolicyCompass branding. The comparison algorithm
is carried across; framework relationships do not transfer matches automatically.

## Existing work

Open existing `.wacc` files directly. The SQLite format, schema version, legacy
obligation identifiers and corpus signatures are preserved. Historical runs keep
their original engine version, evidence and framework snapshots. Original policy
documents are needed only to reopen their source or make a new comparison.

The new default framework cache is `%LOCALAPPDATA%/PolicyCompass/frameworks`;
signed corpus packages use `%LOCALAPPDATA%/PolicyCompass/corpus`.
Explicit configuration accepts:

| Setting | Purpose | Legacy alias |
|---|---|---|
| `POLICYCOMPASS_LIBRARY` | Prepared library containing `sources/files` and `data/corpus` | `WACC_LIBRARY` |
| `POLICYCOMPASS_FRAMEWORK_CACHE` | Downloaded/imported framework cache | `WACC_FRAMEWORK_CACHE` |

The PolicyCompass setting takes precedence. To reuse an existing WACC cache,
point the new setting at that cache, or import the publisher files through
Framework updates. Existing installations are not modified automatically.

## Repository boundary

No WACC source files were removed or edited during this transfer. WACC's control
workspace, web server, Sentinel and implementation-report workflows are not part
of PolicyCompass. The WACC pull request and its branch remain separate.

Publisher documents, extracted publisher corpora, personal assessments, local
dependencies and generated builds are excluded from Git. `sources/permissions.json`
and `sources/acquisition.json` preserve the original source provenance records;
they are not a new permission review or a licence for the application.

The framework component is vendored at the source revision above. Until it is
published as a shared package, loader fixes must be deliberately synchronised
between the two projects.
