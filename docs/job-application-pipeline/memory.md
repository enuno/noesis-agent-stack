# Memory

## Stable profile facts

- The target positioning is a technical leader for AI-agent, distributed infrastructure, and blockchain/DePIN systems.
- The user wants a human-in-the-loop job-application pipeline.
- The user does not want the system to submit applications autonomously.
- The user does not want the system to disclose PII without explicit per-application approval.
- The user prefers official company career pages and public ATS endpoints when available.
- Greenhouse job-board retrieval is allowed; Greenhouse submission remains approval-gated.

## Persistent workflow facts

- Hermes owns scheduling, persistent profile memory, ranking, dedupe, queue management, and approvals.
- Praxis workers are bounded executors and do not own authority.
- Application prep is draft-only until the operator approves a specific action.
- Every application should retain a canonical job record, source URL, requisition ID when available, and description hash.

## Versioning notes

- This pipeline is intended to be versioned as configuration and prompt artifacts, not as a hidden autonomous script.
- Any future change to submission authority should be treated as a policy change and reviewed explicitly.
