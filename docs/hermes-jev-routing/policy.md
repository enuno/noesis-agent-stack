# hermes-jev-routing — policy

Governing artifacts: `platform/hermes-jev-routing.yaml` (machine-readable)
and this file (the reasoning behind it).

## Egress review

**This is the part that decides whether a profile may run the plugin at all.**

On every routed turn, `hermes-jev-routing` sends the following to
`https://api.typesafe.ai/v1/systemone`:

| Payload | Content |
|---|---|
| `current_user_message` | the full text of the turn being routed |
| `conversation_excerpt` | the last N turns of history, capped at 4000 characters |
| `estimated_context_size` | an integer token estimate — no content |
| `spend_snapshot` | provider, model, and dollar figures — no content |

The first two are **prompt text, verbatim**. The plugin performs no
redaction, and the upstream service is not contracted to redact on receipt.
Under `shared/provider-policies.yaml`, every provider's
`classification_allowed` list is a ceiling on what may leave the host; for a
surface that receives raw turns, the ceiling is `internal`.

Three consequences:

1. **`shadow` mode still egresses.** The mode controls what happens to the
   *model*. It does not control what leaves the *host*. A profile in
   `shadow` is still sending every turn to TypeSafe. Anyone reading
   "shadow" as "no-op" will be wrong about the data path.
2. **Confidential material is excluded.** `misjustice-advocacy` handles
   civil-rights and legal material. It is listed in
   `platform/hermes-jev-routing.yaml` → `profile_eligibility.ineligible` and
   in `catalog/typesafe-models.yaml` → `eligibility.excluded_profiles`. No
   configuration is written to it, and `scripts/apply-jev-routing.sh` refuses
   it by name as a second guard.
3. **Reviewer-only profiles are excluded.** `noesis-sentinel` and
   `noesis-skeptic` carry no execution authority and no conversation
   traffic; routing them would add egress with no benefit.

The `prompt_text_egress: true` flag in `providers.typesafe` is the
machine-readable form of this finding. Any future provider that receives
prompt text needs the same flag and the same ceiling.

## Activation preconditions

`platform/inference-routing.yaml` → `required_before_route_activation` lists
ten preconditions. Their status is tracked in
`platform/hermes-jev-routing.yaml` → `required_before_route_activation`.

Two are not fully satisfied, and both are stated rather than glossed:

**`routing_eval_coverage: partial`.** The upstream paper measures the
harness-level *mechanism* (L0–L3 verification designs) on Terminal-Bench 2.1
and SWE-bench Verified. It does **not** measure this stack's task
distribution, its profile mix, or its tier ladder. There is no stack-local
routing eval yet. Building one is the natural next artifact; the
`docs/hermes-jev-routing/` set is where it would live.

**`explicit_human_approval: pending`.** The deployment is in `shadow` mode,
which does not rewrite models, so it does not require the `auto` gate. The
`auto` gate is untouched and still open.

## Why `auto` is gated

`auto` is the only mode that changes the model on the wire. It introduces
three new failure surfaces that `shadow` does not have:

1. **Cache thrash.** The plugin's cache-aware hold mitigates this — a
   1-tier move whose demand sits inside the current tier's band (±0.5 plus
   `deadband`) is held to keep the warm cache, and a move of
   `bypassTierDelta` (2) tiers or more pays for its own miss. But the
   mitigation is a band heuristic, and on this host, where sessions already
   average 39.3M input tokens, a mid-session model swap is expensive even
   when the plugin decides it is worth it.
2. **Capability surprise.** A tier assignment the operator did not expect
   changes what the agent can do. In `shadow` the tier is *reported*, so a
   bad ladder is visible before it is load-bearing.
3. **Egress on every turn, in a mode that also rewrites models.** The two
   combine: the operator loses the ability to reason about "is this turn
   worth sending?" independently of "is this turn worth a model change?".

The sequencing that follows from this: run `shadow` long enough to observe
the tier distribution and the ledger, confirm the ladder matches the real
task mix, and only then ask for `auto`.

## Risk-tier and lane interaction

The plugin routes *inside* a session, after the task has been dispatched. It
does not participate in the orchestrator's dispatch gate, so it must not be
allowed to become a route-selection path:

- `platform/routing.yaml` and `platform/inference-routing.yaml` remain the
  authority for which provider/model a task gets. Jev-routing operates
  within a lane it has already been given.
- The `separation_of_duties` profiles (`code_parallel` requires a different
  route than `code_primary`; `r3_reviewer` a different route than
  `r3_planner`) are enforced by the orchestrator. Jev-routing must not
  collapse them: because the plugin can only rewrite the model on the
  already-bound provider, it cannot move a reviewer onto a different
  provider — which is a safety property here, not a limitation.
- `r2_independent_provider_review_required` and
  `r3_human_approval_required` are unaffected: a model rewrite mid-task
  does not satisfy an independent-review requirement.

## Known gaps

- **`jev-latest` is a moving alias.** The catalog entry records the alias,
  not a resolved build. A reproducible deployment needs the resolved model
  id pinned in the plugin's `jevModel` setting and the catalog entry
  updated to match.
- **The catalog edition reads no quota window.** `quota.minQuota` floors are
  therefore not enforced; `quota.onUnknown: use` admits the model. The
  Codex rate-limit floors in the config are correct in shape but inert in
  this edition.
- **The provider catalogue is not consulted.** A configured row that the
  provider no longer serves stays eligible and fails at request time. The
  row set in `docs/hermes-jev-routing/config/` was verified against live
  `/v1/models` catalogues on 2026-10-28 and must be re-verified before any
  `auto` activation.
- **Per-profile configs are required.** There is no single config that
  routes on more than one provider. Adding a fourth provider to the fleet
  means adding a fourth config file, not adding rows to an existing one.
