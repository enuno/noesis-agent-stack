# Blocked-dispatch reconciliation preparation

Read-only procedure for a dispatch refused by the reconciliation block
(`inference_denied → reconciliation_blocked`) or for a specialist profile
whose registry entry is `blocked` in `platform/runtime-reconciliation.yaml`.
Use when the operator asks for reconciliation preparation, or when a retry
is gated by declared-vs-observed route drift under the interim
reconciliation freeze. Nothing here dispatches, spawns, infers, or changes
runtime policy.

## Reconciliation state vocabulary

`platform/runtime-reconciliation.yaml` profiles entries carry a
`resolution.state` field whose value drives the enforcer and the
validator. Pick the right one before editing the YAML; the validator
will reject the wrong value for an unknown model id (see R006 below).

| State | Dispatch? | Validator (R006) for unknown model id | Use it when |
|---|---|---|---|
| `blocked` | denied | accepted | drift is unrecoverable without operator action (e.g. `OPENROUTER_FALLBACK` declared while OpenRouter is `status: disabled`) — the recipe says "stop, present operator with two or three legitimate moves" |
| `needs_evidence` | permitted | accepted | the lane itself is approved and the model id is policy-permitted but the model id is not yet in `shared/model-aliases.yaml`'s `capability_aliases` (or another canonical pin list) — gate promotion is a separate catalog work item, recorded in `required_gates` |
| `allowed` | permitted | **rejected** for unknown model id | the model id is in a known set — the profile is fully policy-anchored. If you can't list the model in `known_aliases` or a pin list, use `needs_evidence` instead; do not edit the validator to allow `allowed` for unknown ids |
| `runtime_not_observed` | permitted | n/a (no `repo_declared` to check) | the active Hermes profile metadata is unavailable; the registry has `observed_runtime.source: repo_only` — needs the operator to install the profile before further work |
| `missing_repo_declaration` | n/a (not a denier) | skip | the profile has no `profiles/live/<profile>/config.yaml` yet — flagged for the integrator, not the dispatch gate |

The "needs_evidence vs blocked" distinction is the operator's principal
choice when the lane is approved but the model id is not yet in the
catalog. "needs_evidence" is the right state for a freshly reconciled
route (KIMI_CODE / kimi-k2.7-code is policy-permitted; the catalog
entry is the next follow-up). "blocked" is the right state when the
declared route is itself rejected by policy (OpenRouter while
OpenRouter is disabled).

The R006 rule in `scripts/validate_inference_routing.py` (line ~206)
asserts: if `repo_declared.model_alias_or_id` is not in `known_aliases`
(set of `capability_aliases` keys ∪ model names from `shared/models.yaml`),
then `resolution.state` must be `blocked` or `needs_evidence`, or
`alignment` must be `missing_repo_declaration`. The rule fails with
`R006 | platform/runtime-reconciliation.yaml | profiles[N].repo_declared.model_alias_or_id | Unknown model/alias must be blocked, needs_evidence, or explicitly non-verifiable.`
This is why `state: allowed` fails for a freshly reconciled profile:
the model id is not yet a known alias; the rule enforces that the
profile's resolution state explicitly acknowledges the gap. Add the
model id to `shared/model-aliases.yaml` capability aliases (or to a
pinned-models list) to flip the entry from `needs_evidence` to
`allowed` later.

## Procedure

1. **Evidence table (read-only).** Record every fact with a file path
   citation: repo-declared route (`profiles/live/<profile>/config.yaml`
   model block), installed route (`~/.hermes/profiles/<profile>/config.yaml`),
   registry entry (`platform/runtime-reconciliation.yaml`: observed_runtime,
   repo_declared, alignment, resolution.state, required_gates), freeze
   constraints (`platform/inference-routing.yaml` interim_operating_mode),
   lane definitions (approved_lanes: status, provider_family,
   pinned_models, model_aliases, max_risk_tier), class lanes
   (profile_routing_classes), and the staged dispatch payload. Resolve
   exact identifiers from the artifacts: the gate pair is
   `<lane-name>/<pinned-model>`; the spawn pair is
   `<model_aliases[0]>/<pinned-model>`. Never infer aliases or substitute
   models. Label each claim as evidenced vs still-unverified (observation
   provenance, per-launch credential availability inside the isolated
   spawn env, missing canonical catalog entries).

2. **Gate status table.** For every `required_gates` entry record the
   documented acceptance criterion, the required authority (human-
   designated independent review, operator QA/policy decision, a
   config-diff-satisfiable contradiction fix, or the current human
   review), the supporting evidence, and the status. Never mark a gate
   satisfied solely because a configuration edit would remove the block;
   human gates remain human decisions until their evidence exists.

3. **Smallest justified diffs.** (a) Repo live profile: fix the declared
   primary route to the policy-permitted lane, preserving fallback-only
   restrictions and leaving global policy, lane definitions, the freeze,
   and gate lists untouched. (b) Registry entry: re-align repo_declared,
   alignment, and resolution only after gate disposition. (c) Staged
   payload: change only the pair, keeping every stored-contract field
   byte-identical. Rollback: reverse-patch the versioned files; scratch
   payloads keep both versions side by side. State the effect of each
   diff on approval validity, payload identity, idempotency, and
   ledger-resume semantics.

4. **Retry contract, verified without dispatching.** Read the control
   plane, do not live-probe:
   - `propose` is idempotent by key: an existing key returns the stored
     contract unchanged, so changing any stored-contract field silently
     replays old content and requires a new key plus a new proposal.
   - The approved pair lives in the launch reservation, not the stored
     proposal, so a pair-only change preserves the idempotency key and
     epoch-resume semantics.
   - `expected_epoch` must equal the persisted `assignment_epoch`;
     `reserve_launch` increments the epoch; after a failed attempt with
     `max_attempts` exhausted, recovery requires the ledger's sole
     epoch-increment path (`grant_new_attempt`).
   - Duplicate prevention: idempotent propose, reservation replay
     (reservation_exists_no_respawn), epoch equality,
     identity-re-derivation mismatch raising instead of overwriting, and
     fail-closed quarantine.
   - Statically trace the enforcer path (lane resolution order
     observed→declared→class, lane status, pinned-model membership,
     freeze checks, risk-tier and data-class rules) and report the
     predicted decision as a trace, never as a probe result.
   - Attempt-budget hazard: a pair that passes the gate but is
     unlaunchable at the spawn boundary consumes the attempt. Verify the
     launcher bridge before re-firing (see the SKILL.md vocabulary
     discipline).

5. **Trace authorization mode separately from policy.** Read the installed
   caller that constructs `EnforcerConfig`, the final spawn gate, and the
   runtime host configuration. Record: the supported mode names, default,
   exact selector (environment/config/CLI), effective mode, scope, reload
   boundary, and the decision token that authorizes execution. For an
   observe result, preserve both layers:
   - authorization result (`observe_allow`/`observe_deny` is non-authorizing);
   - underlying `reason_code` and policy finding (`reconciliation_blocked`,
     non-selectable lane, risk mismatch, and so on).
   Predict what enforcement would return. If it is `deny`, resolve the policy
   finding instead of proposing a mode switch. Prefer an inline setting on a
   one-shot canonical CLI process when that is the narrowest supported scope;
   call it process-scoped, not task-local, and list every dispatch the process
   can handle. Do not restart a long-lived host merely to simulate task scope.

6. **Validate canary bounds against the actual launch command.** Trace every
   requested bound to its enforcing mechanism at the child boundary: one task,
   attempt budget, wall-clock deadline, fallback denial, turn cap, request/token
   reservation, and cost ceiling. Inspect the command builder and isolated child
   config; runtime support for a flag is irrelevant if the canonical launcher
   does not forward it. Treat these as distinct controls:
   - process timeout bounds elapsed time only;
   - `max_turns` bounds agent iterations only when passed or loaded by the child;
   - observed request/token/cost fields are accounting, not pre-spend authority;
   - a USD cap requires a pre-request reservation or provider-side hard limit.
   If any mandatory bound is unsupported, do not emit a runnable payload. Mark
   the canary HOLD and request either a separately reviewed interface repair or
   an explicit requirement amendment. Never substitute prompt language for an
   enforced limit.

7. **Disposition superseded undelivered tasks through the state machine.**
   Rehydrate the task and verify its folded state before choosing a transition.
   When no worker launched and an explicitly permitted supervisor fallback
   completed the objective, cancel the original proposal with a reason naming
   `undelivered`, the fallback provenance, and the superseding artifact. Use the
   authoritative `Orchestrator.cancel(...)` path (or its supported CLI/tool when
   present), append the normal terminal event, and read it back. Do not mark the
   specialist task succeeded, rewrite JSONL, reuse its key, or create a duplicate
   active attempt. If no lifecycle CLI exists, provide the smallest operator-run
   call to the public lifecycle API rather than inventing a command.

8. **Stop for review.** Deliver the evidence summary, gate table, proposed
   configuration action, exact retry pair, lifecycle disposition, enforced-limit
   matrix, and approval implications. A later go-ahead binds only to the reviewed
   artifacts and never bypasses an unresolved gate. A dry-run, reservation, or
   manifest from an isolated historical attempt is not current delivery or
   installed-profile identity evidence; require fresh attestation immediately
   before spawn.
