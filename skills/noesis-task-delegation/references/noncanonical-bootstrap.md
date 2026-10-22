# Noncanonical implementation and review bootstrap

Use this recipe only when canonical Noesis implementation and review routes are unavailable and the operator explicitly authorizes external bootstrap sessions. It preserves progress without converting degraded execution into canonical qualification.

## Decision sequence

1. Prove the canonical implementer and required reviewer routes are unavailable or unqualified at the actual child boundary. A roster entry or installed profile is not executable readiness.
2. Check whether an independently authorized non-supervisor executor already exists. The orchestrator never inherits terminal or code authority.
3. If none exists, prepare two contracts rather than a recursive dispatch:
   - a write-capable development executor in isolated worktrees;
   - a separate read-only reviewer launched only after the candidate is frozen.
4. Prefer different harness/provider ecosystems for implementation and review. Independence is actual runtime separation, not two prompts in one session.
5. Do not launch either contract from a supervisor that lacks authority. Return the exact contract paths and classify execution as `not started`.

## Development contract

Bind all of these before launch:

- actual harness and version preflight;
- explicit model/provider when selectable, no silent fallback;
- resumable session id in structured output;
- isolated worktree paths and base revisions;
- closed write set across every repository;
- explicit turn, time, tool, network and monetary limits supported by the harness;
- fail-closed behavior for missing binary, auth, permission, limit or clean-worktree prerequisites;
- tests-first boundary work and complete command/exit chronology;
- no commit, push, merge, install, activation, secret access or production mutation unless separately approved;
- `not_self_approved: true` and a deterministic candidate manifest.

A write receipt proves only that the contract artifact exists. It does not prove the harness is installed, authenticated, launchable or running.

## Candidate freeze

Freeze tracked diffs and untracked files together. Record, per repository:

- base revision;
- `git status --short`;
- binary diff from the base;
- sorted path and SHA-256 manifest for every untracked candidate file.

Compute one combined digest over the repository manifests. A tracked-diff hash alone is incomplete when new files exist. Any affected byte change invalidates every prior review.

## Reviewer contract

The reviewer contract must:

- name the exact combined candidate digest and base revisions;
- run in a separate fresh harness/session with read-only candidate access;
- independently recompute the digest before substantive review;
- reproduce focused offline tests without installing dependencies or contacting external services;
- emit `BLOCKED_DIGEST_MISMATCH` on pin failure and `INSUFFICIENT_EVIDENCE` when required checks cannot run safely;
- map findings to requirement, file/line and correction;
- record actual harness/version/model/session provenance;
- state that bootstrap PASS is not canonical Sentinel/Skeptic qualification.

## Status reporting

Report these independently; never collapse them into “done”:

- specified;
- implemented;
- offline tested;
- bootstrap independently reviewed;
- formally qualified;
- installed;
- live authenticated;
- canonically dispatched.

Before execution, only `specified` may be yes. After an external reviewer PASS, `bootstrap independently reviewed` may be yes while `formally qualified` remains no. Offline tests never imply installation, authentication or dispatch.

## Common failure rules

- Do not call intended Noesis ownership actual delivery; ownership labels are design metadata until a runtime identity is observed.
- Do not silently substitute a second harness after preflight failure; classify the contract `dispatch_not_delivered` and return the exact prerequisite.
- Do not let the implementer review its own candidate; self-review can supplement but never satisfy independent review.
- Do not let external bootstrap review waive profile-specific policy; preserve the mandatory qualification gate explicitly.
- Do not infer executor readiness from contract-file creation, skill availability or a command printed in chat; require observed binary/auth/session evidence from the authorized launcher.
