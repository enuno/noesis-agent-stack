# Guardrails

## Privacy

- Redact PII from logs, traces, and exports wherever practical.
- Store contact data in an encrypted private store if needed for the workflow.
- Keep raw applicant details out of summary digests unless the operator asked for them.
- Never send the user's PII to an employer, recruiter, or ATS before explicit approval for that application.

## Drafting constraints

- Do not fabricate experience, titles, projects, clients, employers, or outcomes.
- Do not imply direct ownership of a skill or project if the evidence only supports familiarity.
- If a requirement is not directly supported, mark it as missing or inferential in the fit brief.
- Keep cover letters one page and grounded in verifiable evidence.

## Compensation constraints

- Reject roles that explicitly fall below the base-salary floor.
- Put salary-unlisted leadership roles into `needs-comp-verification` instead of rejecting them outright.
- Never claim compensation bands unless a source provides them.

## Submission constraints

- The application worker may open the form and guide completion.
- Final submission requires explicit approval for the exact application.
- Automated submission is only allowed for deterministic ATS flows that are authorized and immediately reviewable before final submit.
- If the flow is ambiguous, brittle, or login-protected, stop at draft and request human review.

## Source-handling constraints

- Use source hashes, requisition IDs, and canonical company/title fields for dedupe.
- Preserve multiple sightings as supporting evidence while maintaining one canonical record.
- Flag broken or ambiguous company pages instead of silently substituting a different source.

## Failure handling

- If a worker cannot verify a field, leave it blank or mark it unknown.
- If a source is blocked or rate-limited, record the failure and move on.
- If the job posting disappears, preserve the last-known canonical record and mark source freshness accordingly.
