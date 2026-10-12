# Business continuity, backup and recovery policy

Fictional document for the PolicyCompass demonstration. Version 1.0.
Owner: Operations Manager. Approver: Chief Executive. Review: every 12 months.

## Purpose and scope

This policy sets out how the organisation keeps essential services running during
a disruption and restores them safely. It covers business teams, technology
services, premises and suppliers supporting critical activities. The incident
response policy governs investigation and containment of a cyber incident.

## Understand service dependencies

Service owners complete a business impact analysis each year and before a major
service change. The analysis identifies critical activities, dependencies,
minimum staffing, essential records and the consequences of an extended outage.
Owners agree the order in which services will be restored with the executive team.

Each critical service has an approved recovery time objective and recovery point
objective. The recovery time objective sets the target for restoring service;
the recovery point objective sets the acceptable period of lost data. The
technology team checks that backup schedules and supplier commitments can meet
these targets and escalates gaps to the Operations Manager.

## Keep usable backups

The technology team backs up critical business data, software and configuration
settings daily. Service owners specify retention periods in the backup schedule
to support recovery and records obligations. Backup jobs send failure alerts to
the service desk, which records the cause and confirms a successful replacement.

Backups are encrypted and stored separately from production systems. At least
one recovery copy is isolated from routine production administration. Backup
administrators use separate credentials and restrict access to authorised staff.
Changes to retention settings and deletion of recovery copies require approval
from the service owner and are recorded in the change register.

## Prepare to operate during an outage

Business continuity plans identify essential activities, manual workarounds,
alternative communication channels and the people authorised to activate them.
The Operations Manager keeps an offline copy of emergency contacts and service
dependencies. Team leaders check contact details quarterly and brief their deputies
on the decisions they may need to make during an extended disruption.

The incident commander and Operations Manager agree when to activate recovery.
Safety and containment take priority where returning a system to service could
spread a compromise. Communications staff give affected teams practical advice
on available services, workarounds and the next update time.

## Restore and test

Backup restoration is tested quarterly using an isolated recovery environment.
Tests include business records and system configuration, with the service owner
checking completeness and accuracy before signing off the result. The recovery
team records actual restoration times and compares them with approved targets.

The organisation exercises its business continuity and disaster recovery plans
annually, including a scenario involving an unavailable supplier. A restored
service returns to normal operation only after security checks and business
validation. The service owner confirms the recovered data is usable and reconciles
transactions recorded during manual operation.

## Follow up and review

The Operations Manager assigns an owner and due date to every exercise or recovery
action. Unresolved failures are reported to the executive team each month.
Temporary departures from backup or recovery requirements need written approval,
an alternative recovery arrangement and an expiry date. Plans are updated after
an exercise, major outage or significant service change and reviewed annually.
