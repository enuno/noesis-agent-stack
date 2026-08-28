# Runbook

## Daily discovery

Run discovery twice daily.
Target:
- employer career pages,
- Greenhouse public job boards,
- Lever, Ashby, and similar ATS endpoints,
- selected job aggregators,
- company watchlists,
- GitHub or VC-backed company lists when useful.

Search variants should include:
- VP AI Infrastructure
- Head of Agentic Systems
- Director LLM Platform
- VP Blockchain Infrastructure
- Head of DePIN
- Director Distributed Systems
- VP Infrastructure
- VP Engineering
- CTO
- COO

For each result, capture:
- source URL,
- company,
- title,
- location,
- posting date when available,
- ATS/application link when available.

## Normalize and deduplicate

Canonicalize:
- company,
- normalized title,
- source URL,
- requisition ID,
- description hash.

Treat as the same role when:
- company + requisition ID match, or
- title/location + description similarity match strongly enough to indicate the same opening.

Preserve multiple sightings but keep one canonical record.

## Filter and score

Reject roles below the compensation floor when compensation is explicit.
Keep salary-unlisted leadership roles in a `needs-comp-verification` lane.
Score with the evaluation rubric and record the sub-scores.

## Export review queue

Write a daily CSV named `jobs_YYYY-MM-DD.csv`.
Include the review columns from the schema.
Set `decision` to one of:
- `pursue`
- `watch`
- `reject`
- `needs_research`

Send a short digest:
- top 10 new roles,
- top 3 high-conviction targets,
- roles closing soon.

## Application preparation

For each `pursue` row, generate:
- fit brief,
- tailored one-page cover letter,
- résumé-delta checklist,
- application-form answer drafts,
- networking/outreach draft.

Hermes must check drafts for:
- unsupported claims,
- stale facts,
- incorrect company references,
- salary mismatch,
- duplicated submissions.

## Approval and submission

Before any external write, request one of:
- `approve_prepare`
- `approve_outreach`
- `approve_submit`

The default behavior is to open the application page and guide the operator through it.
Only deterministic, authorized ATS flows may be auto-filled, and only if the final submit step is still gated by explicit approval.

## Follow-up operations

Track:
- application status,
- submitted date,
- recruiter contacts,
- interview stages,
- follow-up due date,
- notes.

Create reminders 5–7 business days after submission and after each interview.

## Failure handling

If a source blocks, rate-limits, or changes structure, record the failure and continue with other sources.
If the application flow requires login, stop and ask the operator instead of guessing credentials.
