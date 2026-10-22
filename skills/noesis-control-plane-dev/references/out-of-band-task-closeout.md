# Closing out a task whose executor ran out-of-band

## When this applies

An executor (an agent launched as `hermes -p <profile> chat -q ...`) did the work
and wrote artifact files plus a `handoff.json` directly, without driving the
control-plane API. The ledger task is then left in `running`/`awaiting_review`
with `candidate_revision == null`; once the independent review runs past the
claim lease, the lease is also expired.

## Symptom

`Orchestrator.accept()` refuses with `PolicyViolation("candidate_required", ...)`
and/or `PolicyViolation("lease_expired", ...)`. `synthesize()` shows the task stuck
in `awaiting_review` with `complete: false` even though the work is done and
verified.

## Repair path — through the state machine, never bypass it

1. `block(task_id, reason=...)`        — `awaiting_review` → `blocked`
2. `enqueue(task_id)`                  — `blocked` → `queued`
3. `claim(task_id, claimed_by=assignee)` — `queued` → `claimed`, fresh lease (now + timeout_s)
4. `start(task_id)`                    — `claimed` → `running` (attempts increments)
5. `submit_candidate(task_id, candidate_revision=DIGEST, candidate_digest=DIGEST)` — `running` → `awaiting_review`
6. `submit_handoff(task_id, handoff)`  — re-attach evidence (idempotent; same-state no-op)
7. `record_review(..., stage="spec", verdict="PASS", reviewer=..., candidate_revision=DIGEST)`
8. `record_review(..., stage="quality", verdict="APPROVED", reviewer=..., candidate_revision=DIGEST, findings=[...])`
9. `accept(task_id, operator=...)`     — → `succeeded`

Allowed transitions (models.ALLOWED_TRANSITIONS): `awaiting_review` →
{succeeded, failed, blocked, cancelled}; `blocked` → {queued, cancelled, failed};
`queued` → {claimed, blocked, cancelled, failed}; `claimed` → {running, ...};
`running` → {awaiting_review, succeeded, ...}.

`DIGEST` must be a real content hash — recompute a manifest over the artifact
set (e.g. sha256 over the sorted per-file sha256s), never a placeholder string.

## Import the API correctly

`control_plane.py` does `from app import policy`, so `app` must be the top-level
package on `sys.path`:

```python
sys.path.insert(0, "<repo>/orchestration/orchestrator")
from app.control_plane import Orchestrator
```

Adding `<repo>` root and importing
`from orchestration.orchestrator.app.control_plane import Orchestrator` fails with
`ModuleNotFoundError: No module named 'app'`.

## Run with the project venv

Use `<repo>/.venv/bin/python`, not the Hermes runtime interpreter (which lacks the
repo's dependencies).

## Review-verdict tokens and constraints

- Verdicts are exact uppercase tokens: spec accepts only `PASS`/`REQUEST_CHANGES`/`BLOCKED`;
  quality accepts only `APPROVED`/`REQUEST_CHANGES`/`BLOCKED`.
- `reviewer` must differ from `assignee_profile`.
- Any attached finding with severity `critical`/`important` must carry `resolved: true`,
  or `accept()` blocks on `open_findings`.
