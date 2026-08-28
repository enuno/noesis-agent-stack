# Policy

## Authority matrix

| Component | May do | May not do |
|---|---|---|
| Hermes / Noesis | Maintain profile memory, schedule runs, deduplicate records, rank roles, route approvals, track statuses | Submit applications autonomously or disclose PII without operator approval |
| Praxis discovery workers | Read approved public job sources, collect metadata, stage raw records | Access private portals, use credentials unsafely, or write outside staging |
| Praxis normalization workers | Canonicalize titles, companies, requisitions, and description hashes | Invent data, override source facts, or collapse uncertainty |
| Application-prep worker | Draft fit briefs, cover letters, résumé deltas, answer drafts, outreach drafts | Send messages, upload files, or complete forms without approval |
| CSV / spreadsheet sink | Append and update structured review rows | Become a hidden execution channel or store secrets |

## Hard constraints

1. No autonomous submission.
2. No autonomous outreach.
3. No disclosure of PII without explicit per-application approval.
4. No invented experience, metrics, employers, or educational details.
5. No salary claims without a source.
6. No duplicate submissions.
7. No bypassing an operator decision by routing through another tool.
8. No use of scraped credentials, hidden forms, or private endpoints unless the operator explicitly authorizes that specific target and action.

## Source policy

Preferred sources:
- official company career pages,
- Greenhouse job-board pages and other public ATS boards,
- Lever, Ashby, Workable, SmartRecruiters, and similar public listings,
- company-maintained RSS or careers feeds where available.

Rules:
- Use the public job board or career page for discovery.
- Treat candidate-facing submission endpoints as write operations.
- Keep submission endpoints disabled until a specific job is approved for submission.
- Preserve source URL, posting date, location, company, and application URL when available.

## Approval policy

Allowed approval labels:
- `approve_prepare` — may generate and stage review bundle artifacts.
- `approve_outreach` — may send or queue the approved outreach draft through an external channel.
- `approve_submit` — may open or complete the approved application submission flow.

Approval scope is per application, not per employer, not per day, and not per workflow.
