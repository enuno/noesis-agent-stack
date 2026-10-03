# Runtime Inference-Routing Enforcer

Design + deployment reference for the fail-closed inference-routing gate that
enforces `platform/inference-routing.yaml` at task-dispatch time.

## Architecture

The enforcer (`orchestration/orchestrator/app/inference_routing.py`) is a
pre-dispatch gate inside the orchestrator control plane. It executes in
`Orchestrator.dispatchable()` **after** the existing task-state/approval checks
and **before** any provider/model selection or provider adapter invocation.

```
task queued
   |
   v
Orchestrator.dispatchable()
   |-- circuit breaker
   |-- task.state == queued
   |-- policy.check_dispatchable (existing)
   |-- InferenceRoutingEnforcer.evaluate(RoutingContext)
   |      load policy YAML (read-only, local files only)
   |      resolve profile reconciliation entry
   |      resolve candidate lane/model
   |      check freeze, data class, lane status, model pin,
   |            risk ceiling, review evidence, approval gates
   |      emit typed RoutingDecision
   |-- if decision.allowed == False -> DispatchDecision(False, reason)
   v
provider/model selection (only if allowed)
```

The enforcer never calls a provider, never reads `~/.hermes`, never mutates
routes, and never logs prompts, task bodies, credentials, or model outputs.
The only side effect is a structured JSONL decision record.

## Typed decisions and reason codes

Decisions: `allow`, `deny`, `observe_allow`,`, `observe_deny`.

| reason_code | meaning |
|---|---|
| `allowed` | route satisfied every gate |
| `policy_unavailable` | no validated policy loaded at startup |
| `policy_reload_failed` | reload rejected; enforce modes fail closed |
| `profile_missing_from_reconciliation` | profile absent from runtime reconciliation |
| `reconciliation_blocked` | profile blocked in reconciliation matrix |
| `reconciliation_freeze` | freeze permits only observed existing behavior |
| `data_classification_denied` | data class not routable pre-provider |
| `openrouter_selected` | OpenRouter requested; always denied |
| `unknown_lane` | requested/derived lane not in policy |
| `lane_not_selectable` | lane proposed/disabled/blocked |
| `model_missing` | no model resolvable for lane |
| `model_not_allowed` | model not pinned/aliased on the lane |
| `risk_tier_exceeds_lane_max` | task risk exceeds lane ceiling |
| `independent_review_required` | r2/r3 without cross-provider review evidence |
| `independent_review_same_provider_family` | review family equals route family |
| `r3_approval_required` | r3 without human approval manifest |
| `r3_rollback_required` | r3 without rollback metadata |
| `not_allowlisted` | tuple not in enforce_allowlist set |
| `route_unresolvable` | no eligible lane/model derived |

## Modes (environment-selected only)

| mode | behavior |
|---|---|
| `off` | disabled; startup-only, requires `INFERENCE_ROUTING_EMERGENCY_DISABLE=true` |
| `observe` | record decision; never block dispatch (default) |
| `shadow_deny` | record would-deny; never block dispatch |
| `enforce_allowlist` | deny unless profile:lane:model tuple allowlisted |
| `enforce` | deny every policy violation |

## Routing decision log

JSONL, one record per evaluation:

```json
{"timestamp": "...", "task_hash": "sha256...", "profile_id": "...",
 "task_class": "...", "risk_tier": "r0", "data_classification": "...",
 "resolved_lane": "...", "resolved_model": "...", "decision": "observe_deny",
 "reason_code": "...", "policy_version": "...", "policy_sha256": "...",
 "mode": "observe", "latency_ms": 0.0}
```

Only non-sensitive metadata is recorded. Task bodies, prompts, credentials,
tokens, and model outputs are never written.

## Deployment configuration

See `config/runtime-inference-routing.example.env` for the full variable set.
Defaults: mode `observe`, fail-closed `true`, 60 s reload interval.

### File mounting

All policy inputs are mounted read-only:

- `platform/inference-routing.yaml`
- `platform/runtime-reconciliation.yaml`
- `platform/risk-tiers.yaml`
- `shared/models.yaml`
- `shared/model-aliases.yaml`
- `shared/provider-policies.yaml`

### Service account

Run the orchestrator as a non-root, dedicated user. The only writable paths
are the task ledger and the routing-decision log directory
(`/var/lib/noesis/` by convention).

### Atomic policy update procedure

1. Write the new policy to a temp file on the same filesystem.
2. `fsync` the temp file.
3. `os.rename()` temp over the target (atomic on same filesystem).
4. The enforcer's reload loop picks it up within `RELOAD_SECONDS`.
5. A failed reload retains the last known-good policy in observe/shadow
   modes; enforce modes deny new dispatches until a valid policy loads.

### Pre-deploy validation

```bash
python scripts/validate_inference_routing.py --strict
python -m pytest orchestration/orchestrator/tests -q
```

Both must pass before any mode other than `observe` is enabled.

### Health checks

- `policy_loaded` — last reload succeeded.
- `policy_sha256` — matches the deployed policy fingerprint.
- `mode` — matches configured mode.
- decision-log writable and rotating.

### Rollout sequence

1. `observe` — deploy, record decisions, compare against baseline dispatch.
2. `shadow_deny` — record would-deny; confirm no legitimate route is blocked.
3. `enforce_allowlist` — allow an explicit r0/r1 profile:lane:model tuple only.
4. `enforce` — full policy enforcement.

### Rollback

Set `INFERENCE_ROUTING_MODE=observe` and restart the orchestrator process.
The baseline route is never altered by the enforcer, so rolling back to
observe always restores pre-enforcement dispatch semantics.

### Alert thresholds

| signal | threshold |
|---|---|
| policy load failures | >= 1 in any reload window |
| denial spike | denials > 20 % of evaluations over 5 min in observe/shadow |
| OpenRouter attempts | any `openrouter_selected` record |
| unexpected provider substitution | resolved lane differs from policy baseline without explicit approval |
| enforce-mode blocks | any block after allowlist phase begins |

## Explicit non-goals

- no `~/.hermes` modification or reads
- no provider/model lane activation
- no external model/provider call during authorization
- no silent provider fallback
- no credential creation, storage, or logging
