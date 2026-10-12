# How matching works

PolicyCompass searches the supplied documents for wording related to each selected
framework requirement. It runs on your computer. It uses word matching, spelling
rules and a small list of abbreviations; it does not train a model on your files or
send them to an AI service.

## What the labels mean

**Mentioned** means that a passage shares enough specific wording to be a clear
lead for a reviewer. It does not mean the requirement is satisfied. Check who must
act, what they must do, when they must do it and any conditions in the framework.

**Related wording** means there is a possible overlap that needs closer reading.
This includes named references, short or qualified statements, and matches to a
requirement whose wider conditions are missing from the passage.

**Not mentioned** means no passage passed the matching checks. It can indicate a
policy gap, but different wording can also cause this result. **Unable to check**
means the document set could not be searched completely.

## What the search keeps together

The search works within sentences. It reads soft line breaks in Markdown prose
as part of the same sentence, while preserving the original text and locations.
Blank lines, sentence endings, lists, headings, table rows and explicit Markdown
hard breaks remain boundaries. It does not combine separate statements to build
a match.

Plain text and PDF line breaks can represent either layout or separate statements.
The current matcher keeps those boundaries. If a PDF appears to miss obvious
wording, inspect its extracted text in **Documents** and try a clean Word or
Markdown copy. Scanned pages need text recognition first.

## Why context matters

A short requirement can have a long parent description, deadline or applicability
note. The search checks the requirement wording separately so that this context
does not hide a useful passage. If only that wording passes the checks, the result
stays **Related wording** and carries a reminder to review the wider conditions.
Passages are ranked by overlap with the requirement itself.

Two isolated content words are too little for a **Mentioned** result. Short
requirements also need all their content words for that label. Negative and
qualified passages remain **Related wording**, even when many words overlap.
The matcher does not determine whether a prohibition is the right control.

## What still needs a person

Broad policies often cover only part of a detailed technical control. A long
requirement may discuss protocols, timeframes or multiple actions that the policy
does not name. Synonyms, cross-references and responsibilities spread over several
sentences can be missed. Numeric deadlines and legal applicability need checking
against the source; a shared topic is not enough.

Up to five passages are shown per requirement, with the total number found. A
framework mapping does not carry a match into another framework. Saved runs keep
their original results and matching version; compare the documents again to use a
newer version.

For reproducible checks, see [testing](../tests/README.md). For a practical review,
use the [demo walkthrough](DEMO.md).
