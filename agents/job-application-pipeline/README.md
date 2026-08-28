# Job Application Pipeline

Placeholder locator for the human-in-the-loop job application pipeline.

Canonical artifacts live under `docs/job-application-pipeline/`.

Purpose:
- Discover relevant roles from official company career pages and public ATS endpoints.
- Normalize, deduplicate, score, and stage reviewable job records.
- Prepare application packets and outreach drafts without autonomous submission.
- Keep all external writes, uploads, and disclosures gated by explicit per-application approval.

Operating stance:
- Hermes owns scheduling, memory, ranking, dedupe, approvals, and escalation.
- Praxis workers are stateless collectors and preparers.
- No autonomous application submission.
- No PII disclosure or external write without explicit approval for that exact application.
