# Asset, vulnerability and secure configuration policy

Fictional document for the PolicyCompass demonstration. Version 1.0.
Owner: Head of Technology. Approver: Chief Executive. Review: every 12 months.

## Purpose and scope

This policy sets requirements for keeping business technology known, supported
and securely configured. It covers servers, workstations, network devices,
applications and cloud services. Operational equipment must have a named owner
and an agreed maintenance approach that considers safety and service availability.

## Asset records

The technology team maintains an inventory of hardware, software and online
services. Each record includes an owner, business purpose, location, support
status and information classification. New assets are registered before use.
Automated discovery results are reconciled with the inventory each month, and
unknown devices are investigated before they receive access to business networks.

Service owners identify critical assets and their dependencies. Retired assets
are removed from service, their access is revoked and their storage is sanitised
before disposal. Owners plan replacement of unsupported software before vendor
support ends and record any temporary risk acceptance.

## Configuration and change

The technology team maintains approved secure configuration baselines for each
supported platform. Asset owners apply the approved secure configuration before
deploying a device or service and check it after installation.
Baselines remove unused services and default accounts, limit
administrative access and enable security logging. Application control restricts
software execution to approved applications. Office macros are blocked unless
there is an approved business need and a controlled source.

Changes to production settings require an authorised change record describing
the purpose, risk, testing, implementation steps and rollback plan. Emergency
changes are recorded when made and reviewed on the next business day. Platform
owners check configuration drift monthly and investigate unauthorised changes.

## Find and address vulnerabilities

The security team scans internet-facing systems weekly and internal systems
monthly for known vulnerabilities. Asset owners review findings for exposure,
exploit activity and business impact. The team subscribes to vendor security
advisories and checks whether newly reported vulnerabilities affect the inventory.

Actively exploited vulnerabilities in internet-facing systems receive immediate
attention, with remediation or isolation targeted within 48 hours. Other critical
findings have a seven-day target and remaining findings receive a risk-based due
date. Owners test patches, record installation results and rescan affected assets
to verify that the vulnerability has been resolved.

Where patching would interrupt a critical or safety-related service, the owner
records alternative safeguards and an agreed maintenance date. The Head of
Technology approves time-limited exceptions and reviews overdue critical findings
with the executive sponsor each week.

## Network protection and monitoring

Business, guest and administrative networks are separated. Network access rules
allow only approved connections and are reviewed every quarter. Endpoint
protection is enabled on supported devices and sends alerts to the security team.
Security logs record authentication, administrative actions and configuration
changes with synchronised timestamps. Analysts investigate significant alerts
under the incident response policy.

## Review and evidence

Platform owners retain inventory changes, scan results, patch records and
configuration reviews. The Head of Technology reviews this policy annually and
after a major platform change or incident involving an unaddressed vulnerability.
