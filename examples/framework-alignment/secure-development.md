# Secure development and service change policy

Fictional document for the PolicyCompass demonstration. Version 1.0.
Owner: Engineering Manager. Approver: Head of Technology. Review: every 12 months.

## Purpose and scope

This policy applies to software, scripts, integrations and significant service
changes developed internally or for the organisation by a supplier. Teams build
security into design, testing and maintenance so that a release can be supported
throughout its working life. The business sponsor names a service owner before
development begins.

## Design and planning

The project team records security and privacy requirements alongside business
requirements. A design review identifies sensitive data, trust boundaries,
external dependencies and plausible misuse of the service. Reviewers agree
controls and acceptance tests for the risks identified and keep the decisions
with the project records.

Architects prefer approved components and keep a record of third-party libraries
and their versions. The service owner identifies who will monitor vulnerabilities,
apply updates and support the service after release. A proposed design that cannot
meet the agreed requirements is referred to the Head of Technology before work
proceeds beyond a prototype.

## Development practices

Developers follow the approved secure coding standard and check input validation,
authorisation, error handling and protection of sensitive data. Source code is
stored in an access-controlled repository. Each change has a named author and
reviewer, and production changes receive review by someone other than the author.

Development, test and production environments are separated. Developers use
synthetic or suitably de-identified test data. Production information requires
the data owner's approval and equivalent access protections before use in a test.
Secrets are stored in the approved secrets service and must not be committed to
source code or included in diagnostic output.

## Testing and release

Automated checks scan source code and dependencies for known weaknesses during
the build. Teams test access restrictions, failure handling and security-sensitive
features before release. Internet-facing services and significant authentication
changes receive independent security testing proportionate to their risk.

The release owner records findings and confirms that critical defects are fixed
and retested before deployment. Any accepted unresolved issue needs a risk owner,
expiry date and interim safeguard. A release record identifies the version,
approvals, deployment steps, verification checks and rollback instructions.
Production deployment uses authorised accounts and records the outcome.

## Operation and retirement

Service owners keep technical documentation, support contacts and dependency
records current. They monitor vendor advisories and schedule updates under the
vulnerability policy. Users have a published channel for reporting suspected
security defects, and reports are triaged with the security team.

Emergency changes follow the incident process and receive a subsequent review.
Retiring a service includes revoking credentials, removing integrations and
disposing of information under the retention schedule. The Engineering Manager
reviews this policy annually and after a major release failure or security incident.
