# Try the demo policies

The [framework-alignment folder](../examples/framework-alignment/) contains eight
original, fictional policies. They are intended for demonstrations, not adoption
as an organisation's approved policies. Names, roles, review periods and response
targets belong to the fictional scenario.

## What is in the set

| Policy | Topics to look for |
|---|---|
| [Access and staff security](../examples/framework-alignment/access-and-training.md) | Account approval, remote access, MFA, staff training and departures |
| [Governance and risk](../examples/framework-alignment/governance-and-risk.md) | Accountability, risk treatment, exceptions and assurance |
| [Information handling](../examples/framework-alignment/information-handling.md) | Classification, sharing, retention and disposal |
| [Secure systems](../examples/framework-alignment/secure-systems.md) | Asset records, configuration, patching and logging |
| [Secure development](../examples/framework-alignment/secure-development.md) | Design review, coding, testing and release approval |
| [Supplier security](../examples/framework-alignment/supplier-security.md) | Purchasing checks, contract terms, access and exit plans |
| [Incident response](../examples/framework-alignment/incident-response.md) | Reporting, triage, evidence, communication and exercises |
| [Continuity and recovery](../examples/framework-alignment/recovery.md) | Service priorities, backups, restoration and exercises |

Each policy includes its purpose, scope, owner, approval role and review process.
The folder contains only policy files, so selecting it on the command line will
not add this guide to the comparison.

## Run the demonstration

1. Open PolicyCompass and use **Framework updates** to download WA CSP and NIST CSF.
2. Choose **New comparison**. Enter `Policy set demonstration` as the name and
   `Eight fictional business policies` as the scope.
3. Select WA CSP and NIST CSF. Add ISM or another installed framework if useful.
4. Choose **Add files or ZIP archives** and select all eight Markdown files in
   `examples/framework-alignment`.
5. Choose **Compare and save**. Save the file in `data/local/demo-check` or another
   local working folder.

The same comparison from PowerShell:

```powershell
New-Item -ItemType Directory -Force data/local/demo-check | Out-Null
python -m policycompass corpus update --framework wa-csp --framework csf
python -m policycompass compare examples/framework-alignment --name "Policy set demonstration" --framework wa-csp --also-assess csf --scope "Eight fictional business policies" --assessment data/local/demo-check/demo.policycompass --format json --output data/local/demo-check/results.json
python -m policycompass report data/local/demo-check/demo.policycompass --format html --output data/local/demo-check/report.html
python -m policycompass open data/local/demo-check/demo.policycompass
```

Choose fresh output names for another run, or use `--force` where supported to
replace exported files. Reusing the assessment path adds to its saved history.

## Review a few results

Start with **Overview**, then open **Requirements** and search for a reference or
phrase. Read the requirement, its context and the actual passage before deciding
what the policy covers.

| Framework | Reference or search | Useful passage |
|---|---|---|
| WA CSP 2026 | `3.2a` | Induction and annual awareness training |
| WA CSP 2026 | `3.1.8b` | Recovery time and recovery point objectives |
| WA CSP 2026 | `5.4` | Annual incident response exercises |
| NIST CSF 2.0 | `ID.AM-1` | Hardware inventory |
| NIST CSF 2.0 | `GV.SC-8` | Suppliers in incident and recovery planning |
| ISM | `ISM-1784` | Annual incident response exercise |
| NIST SP 800-53 | `IA-2(1)` | MFA for privileged accounts |
| AESCSF | `ACCESS-2f` | Account requests approved by the owner |

The downloaded files can display lowercase references, unpadded numbers or a dot
in place of parentheses. Search a distinctive phrase if an identifier differs.
Most overlaps need review and are labelled **Related wording**. A high number of
**Not mentioned** results is expected: these business policies leave out many
specialised technical controls and government-specific obligations.

## Check a change

Copy one policy to a separate working folder and remove its annual training clause.
Compare the changed policy set in a new run, using the same framework editions.
Inspect `3.2a` and its passages: other training wording may still produce a related
match. Use **History** to reopen the original run and compare the text, not just
the totals.

Export an HTML report and open a requirement to show its source location. A report
can also be restricted to one framework. See the [user guide](../policycompass/README.md)
and [command line guide](COMMANDS.md).
