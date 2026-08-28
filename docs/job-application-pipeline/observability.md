# Observability

## Required logs

Record every run with:
- run ID,
- timestamp,
- source set,
- query terms,
- job counts,
- dedupe counts,
- score distribution,
- decision counts,
- approval status,
- file outputs,
- any blocked action.

## Audit trail fields

At minimum, keep these audit fields in the review queue or logs:
- job_id
- discovered_at
- company
- title
- source
- job_url
- application_url
- ats
- requisition_id
- fit_score
- decision
- status
- next_action
- next_action_due

## Metrics

Track:
- discovery volume,
- dedupe rate,
- source freshness,
- comp-verification rate,
- pursue/watch/reject ratio,
- approval turnaround time,
- application-to-interview conversion,
- interview-to-offer conversion,
- duplicate submission attempts blocked,
- PII disclosure attempts blocked.

## Health checks

A healthy pipeline should confirm:
- source fetches succeeded,
- canonicalization produced one record per unique role,
- salary policy was applied,
- approval gates are active,
- no submit path is enabled by default,
- audit files were written successfully.

## Failure signals

Escalate when:
- a source changes structure,
- a job board starts rate-limiting,
- a duplicate record appears repeatedly,
- a submit endpoint becomes reachable without approval,
- logs show PII leakage,
- a worker tries to bypass the approval gate.
