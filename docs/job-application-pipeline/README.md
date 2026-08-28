# Human-in-the-Loop Job Application Pipeline

This is the canonical documentation/config bundle for the NoesisPraxis job-application pipeline.

Design constraints:
- Hermes/Noesis owns persistent profile memory, scheduling, ranking, queue management, and approval routing.
- Praxis workers are bounded executors for discovery, normalization, enrichment, and draft preparation.
- No autonomous submission.
- No disclosure of PII without explicit per-application approval.
- Prefer official company career pages and public ATS endpoints where available.
- Greenhouse job-board retrieval is allowed; Greenhouse candidate submission remains disabled until explicitly approved per application.

Artifact set:
- `identity.md`
- `policy.md`
- `guardrails.md`
- `evaluation.md`
- `runbook.md`
- `memory.md`
- `observability.md`
- `systemprompt.md`
- `config/candidate_profile.yaml`
- `config/workflow.yaml`
- `contracts/job_record.schema.json`
