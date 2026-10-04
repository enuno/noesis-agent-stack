# KIMI Canonicalization Plan

Date: 2026-10-04
Artifact: `shared/models.kimi-proposed.yaml` (version 2026-10-04.1, `observed_not_verified`)
Validator: `scripts/validate_kimi_canonical_mapping.py`
Eval fixtures: `evals/kimi-canonical-mapping.eval.yaml`

## 0. Scope statement

Local design package only. Nothing here is committed to the catalog, loaded by
dispatch, or promoted to a pin. No KIMI (or any other provider) API was called;
no `~/.hermes` file was modified; key material was never read or printed. The
only `~/.hermes` access was reading non-secret provider/model metadata lines
(base URLs, provider names) already referenced by repository evidence.

## 1. Evidence classification

**Classification: UNRESOLVED — live-observed reference, immutability unverified.**

`kimi-k2.7-code` is:
- NOT a verified immutable upstream model identifier (cannot be confirmed
  offline; no API call permitted in this task);
- NOT declared in `shared/model-aliases.yaml` (that file holds capability
  aliases only — vendor model IDs are explicitly out of scope there);
- NOT a profile-local string either — it is the fleet-observed runtime model
  across 18 profiles, recorded in `platform/runtime-reconciliation.yaml` with
  evidence source "active profile metadata";
- therefore recorded as `pin_status: observed_not_verified`,
  `canonical_model_id: null`.

Why not simply trust the lane pin? The lane definition itself carries the
caveat: "If kimi-k2.7-code becomes an alias rather than an immutable model
identifier, promotion must reclassify this as blocked_missing_configuration."
The string is accepted by the live endpoint (this very session runs on it),
but provider acceptance of a string does not prove the string is a stable
model ID versus a rolling alias.

## 2. Provider transport

The serving endpoint is `https://api.kimi.com/coding/v1` (subscription class,
auth env `KIMI_API_KEY` per `shared/models.yaml`). The transport identifier is
**dual-named** in the repo:

| Context | Identifier |
|---|---|
| shared/models.yaml provider block | `kimi` |
| KIMI_CODE lane `model_aliases` | `kimi-coding` |
| roster `apply_model.provider` | `kimi-coding` |
| active profile config providers map | `kimi-coding` |

One canonical transport identifier must be chosen (recommendation: keep
`kimi-coding` for the coding-plan endpoint and alias `kimi` to it, or vice
versa — decided at activation time, not here).

## 3. Exact profile references

18 of 22 profiles observed on `kimi-k2.7-code` (`platform/runtime-reconciliation.yaml`):

noesis-core (aligned), noesis-orchestrator (drift — declared claude-sonnet-5),
noesis-steward (aligned), noesis-cartographer (drift), noesis-forge (aligned),
noesis-sentinel (drift), noesis-scribe (drift — declared deepseek-v4-flash),
noesis-signal (drift), noesis-substrate (aligned), noesis-tracer (drift),
noesis-ledger (drift), noesis-grid (drift), noesis-quill (drift),
noesis-advocate (drift), noesis-herald (drift), noesis-architect (drift),
noesis-skeptic (drift), coder (missing repo declaration).

Not observed at runtime: main-hermes, research-openclaw, subconscious-openclaw,
qa (`runtime_not_observed: 4`).

Roster `apply_model` blocks additionally name `kimi-k2.7-code @ kimi-coding`
for core/steward/forge/scribe/substrate/grid (and reference `kimi` more
broadly for fast lanes).

## 4. Task classes and data classes

Lane `permitted_task_classes` (KIMI_CODE): supervisor_control_plane,
structured_worker, implementation_planning, code_critique, qa_analysis,
ops_planning, reflective_advisory.

The proposed candidate narrows initial eligibility to structured_worker,
technical_decomposition, code_review — the lowest-risk classes — and caps the
candidate at **r1 / advisory** until verification, even though the lane itself
allows r2. Lifting the candidate to r2 requires its own explicit step.

Data: provider policy `classification_allowed: [public, internal]`,
`private_analysis: false`; prohibited: confidential, restricted, secret.
The candidate preserves this exactly. Terminology note: the assignment matrix
and research lanes use `internal_redacted`; the kimi policy says `internal`.
Harmonize the vocabulary at catalog time.

## 5. Cost / latency / reliability evidence

Repo-local evidence only:
- `shared/provider-policies.yaml`: kimi class subscription, spend model
  fixed_subscription, burst guardrail $5.00/job, health dimensions
  [latency, quota, cooldown, outage].
- No repo telemetry, benchmark, or latency measurement files for this model
  exist. Per-session experience (this design doc's own runtime) is anecdotal
  and is not policy evidence.

A cost-rate/latency budget with measured baselines is a required activation
item, not a present fact.

## 6. Gaps blocking promotion

1. **Immutable-ID verification** — must confirm via provider documentation or
   a minimal sanctioned API read whether `kimi-k2.7-code` is an immutable
   model ID or an alias.
2. **Canonical catalog entry** — `shared/models.yaml` has no such model; the
   only kimi catalog model is `kimi-k2-thinking`.
3. **Dual transport naming** — `kimi` vs `kimi-coding` (see §2).
4. **Risk-tier posture** — candidate capped at r1; lane currently permits r2
   with an unverified pin (this tension is itself a finding).
5. **Structured-output contract** — none defined for this model.
6. **Evals** — no offline or shadow evals exist against the exact model
   reference; `evals/runtime-inference-routing-enforcer.eval.yaml` uses it as
   a fixture baseline only.
7. **Reconciliation drift** — 13 of the 18 observed profiles are drifted or
   missing declarations; drift must be resolved, not adopted.
8. **Terminology harmonization** — internal vs internal_redacted.
9. **Independent security review and explicit human approval** — outstanding
   by definition in this design-only package.

## 7. Future activation test (exact)

When all activation_requirements are satisfied:

1. Merge the canonical catalog entry + lane pin update as a design PR with the
   full validation gate (both strict validators, all pytest suites, scoped
   secret scan).
2. Set the runtime enforcer to `shadow_deny` (record would-deny, never block)
   with the new pin in the allowlist for exactly one profile-lane-model
   tuple: `noesis-grid : KIMI_CODE : <verified canonical id>` (r1
   structured_worker, public/internal data only).
3. Run the shadow window; require: 100% decision-log completeness (policy
   version + SHA-256 on every decision), zero confidential/restricted/secret
   data-class observations, zero r2+ dispatches on the candidate, fallback
   frequency zero, and green runs of `evals/kimi-canonical-mapping.eval.yaml`
   plus the offline structured-output eval suite.
4. Independent security review signs off; explicit human approval promotes
   the lane pin from `observed_not_verified` to approved canonical.

Auto-promotion is forbidden (`shared/GUARDRAILS.global.yaml`).

## 8. Explicit statement

This package does not change live dispatch, does not pin the model, does not
activate the lane beyond its existing design-only status, does not modify
`~/.hermes`, and does not invoke any provider. It is the preparation artifact
for the first enablement PR, to be published only after separate explicit
confirmation.
