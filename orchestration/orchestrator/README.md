# noesis-orchestrator — control plane

Durable task-contract control plane for cross-profile work in the Noesis fleet.

The orchestrator is a **planner, dispatcher, supervisor, and synthesizer**. It
holds no `terminal` and no `code_execution` toolset, by roster construction, and
it never performs production, financial, wallet, credential, or destructive
operations. Those are classified `r3`, held at a human approval gate, and
assigned to a narrowly privileged executor profile.

## Layout

| Path | Purpose |
|---|---|
| `app/models.py` | `TaskContract` and the state machine (`ALLOWED_TRANSITIONS`) |
| `app/registry.py` | Roster-backed profile registry (`profiles/noesis-roster.yaml` + `agents/*/agent.yaml`) |
| `app/policy.py` | Deterministic refusals: assignment, risk, approval, dependency, evidence, staleness |
| `app/store.py` | Append-only JSONL ledger, replayed on start |
| `app/control_plane.py` | `Orchestrator` and `CircuitBreaker` — the only component that mutates state |
| `tests/` | 59 tests covering policy, lifecycle, schema conformance, and worked examples |

## Contracts

- Schema: `contracts/orchestration/task-contract.schema.json`
- Ledger: `workspace/orchestrator/tasks.jsonl` (append-only; one `{event, recorded_at, task}` record per line)
- Risk tiers: `platform/risk-tiers.yaml`
- R3 approval binding: `platform/approval-manifest.schema.json`

## Task lifecycle

```
proposed -> approved -> queued -> claimed -> running
         -> awaiting_review | blocked | failed | succeeded | cancelled
```

Full transition table, approval gates, operator procedures, recovery, and
emergency stop are documented in `WORKFLOWS.md` §5.

## Run the tests

```bash
cd orchestration/orchestrator
python -m pytest -q
```

No network, no credentials, and no repository writes: every test uses a
`tmp_path` ledger.

## Invariants the tests enforce

1. An assignee absent from the roster is rejected.
2. Reviewer-only and supervisor profiles (including the orchestrator itself) are never assigned executing work.
3. A capability the assignee does not declare is rejected.
4. Irreversible operations require `r3`, a human approval gate, and an executor that actually holds terminal authority.
5. Unresolved dependencies block dispatch.
6. Structured handoff evidence is required before `succeeded`.
7. Lease-expired work cannot succeed silently.
8. Idempotent re-delivery never duplicates work, including across a restart.
9. The circuit breaker halts dispatch; escalation requires a human.
10. Every persisted contract validates against the published schema, and no secret-like material reaches the ledger.
