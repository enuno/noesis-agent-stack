# Profile Strategic Inference Assignment — Rationale

Date: 2026-10-04
Artifact: `platform/profile-inference-assignments.yaml` (version 2026-10-04.1)
Validator: `scripts/validate_profile_inference_assignments.py`
Eval fixtures: `evals/profile-inference-assignment.eval.yaml`

## 0. Scope statement (read first)

This plan is **observe-only design**. It does not change live dispatch, does not
activate or approve any provider lane, does not modify `~/.hermes`, and does not
weaken any prior policy status. Every record in the matrix carries one of three
statuses — `observe_only`, `blocked_missing_configuration`, or `proposed` — and
nothing in this document or the matrix may be read as `approved`, `active`,
`enforced`, or `production`. No provider API was invoked at any point; all
inputs are repository files and the already-extracted, non-secret reconciliation
evidence in `platform/runtime-reconciliation.yaml`.

## 1. Profile inventory and classification

The matrix covers the 22-profile union of the Noesis roster and the platform
agent registry:

- `profiles/noesis-roster.yaml` contributes **17** `noesis-*` IDs. (The roster
  header still says "16-agent fleet"; `noesis-orchestrator` was added
  subsequently and is counted here. The task brief's "16 roster + 6 platform"
  phrasing double-counts `noesis-orchestrator`, which appears in both
  registries; the union is 22 either way.)
- `platform/orchestrator.yaml` contributes 6 agent IDs, 5 of which are new to
  the union: `main-hermes`, `research-openclaw`, `subconscious-openclaw`,
  `coder`, `qa`.

Type classification (used by the lane permission rules):

| Type | Profiles |
|---|---|
| supervisor | noesis-core, main-hermes |
| orchestrator | noesis-orchestrator, noesis-steward, noesis-cartographer, noesis-architect |
| coder | noesis-forge, coder |
| ops | noesis-substrate |
| security | noesis-sentinel |
| qa | noesis-skeptic, qa |
| worker | noesis-scribe, noesis-grid, noesis-quill, noesis-herald |
| research | noesis-signal, noesis-tracer, noesis-ledger, noesis-advocate, research-openclaw |
| reflective | subconscious-openclaw |

## 2. Lane status facts the assignment preserves

From `platform/inference-routing.yaml` (policy_mode: proposed_not_live,
interim mode: reconciliation_freeze):

| Lane | Status | Consequence |
|---|---|---|
| KIMI_CODE | approved (pinned `kimi-k2.7-code`, max r2, data public/internal) | Only selectable lane. Permitted types: supervisor, orchestrator, worker, coder, qa, security, ops, reflective. **Research is not a permitted type.** |
| PERPLEXITY_API | proposed | Non-selectable. Strategic evidence lane for research; data public/internal_redacted; max r1; pinned_models empty (sonar/sonar-pro are observed aliases, not pins). |
| NOUS_PORTAL | proposed | Non-selectable until canonical pin/policy/evals. |
| CLAUDE_CODE_PRO | proposed | Non-selectable until approved. Bridge binding for cross-family code review does not exist yet. |
| XAI_GROK | blocked_missing_configuration | Non-selectable. |
| CHATGPT_PRO | blocked_missing_configuration | Non-selectable. |
| VENICE_PRO | blocked_missing_configuration | Non-selectable. Privacy lane unproven. |
| OPENROUTER_FALLBACK | disabled | Never primary, never fallback, r0-only, `primary_eligible: false`. |

## 3. Why transport availability does not equal route eligibility

A registered provider transport (an API base URL, an auth env var name, an
`enabled: true` flag in `shared/models.yaml`) is plumbing. Eligibility is a
policy property that requires, per the freeze invariants: a canonical provider
policy, a canonical model catalog entry, an immutable or explicitly pinned
model identifier, an approved lane definition, profile eligibility, data-class
policy, structured-output requirements where applicable, routing eval coverage,
security/secret-egress review, cost/latency budget, and explicit human approval.

Concrete illustrations from the sources:

- **Kimi** is the only lane whose policy status is `approved` — and even there,
  approval is design-only; observed runtime remains evidence, not policy
  (eval fixture IR-002). The lane note warns that if `kimi-k2.7-code` turns out
  to be an alias rather than an immutable identifier, the lane must be
  reclassified `blocked_missing_configuration`.
- **Perplexity** has a live transport and keys, but zero pinned models; its
  aliases `sonar`/`sonar-pro` are explicitly recorded as observed, not
  canonical (IR-003, IR-009 in the routing eval file).
- **Anthropic/Claude** identifiers are inconsistent across the repo
  (claude-sonnet-4-5 vs claude-sonnet-5 vs claude-opus-4-5), and the lane
  `CLAUDE_CODE_PRO` is `proposed` (not approved).
- **OpenRouter** appears as a declared primary in several `profiles/live/*`
  configs; every one of those declarations is represented as `blocked` in the
  reconciliation matrix because the catalog and policy keep OpenRouter
  disabled (IR-008).
- **Nous** keys are reported dead in roster comments, but the operator
  indicates (2026-10-04) the portal should be available; key validity is
  unverified and the lane remains proposed.

Therefore: no profile received a lane assignment "because a key exists." The
only primary assignments made are to KIMI_CODE, the single approved lane, and
only where the lane's own `permitted_profile_types`/`permitted_task_classes`
cover the profile.

## 4. Per-profile strategy summary

| Profile | Type | Authority | Ceiling | Status | Primary lane / model_ref | Critic | Key blocker / requirement |
|---|---|---|---|---|---|---|---|
| noesis-core | supervisor | approval_gated | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Cross-family critic lane (CLAUDE_CODE_PRO/CHATGPT_PRO) not selectable |
| noesis-orchestrator | orchestrator | planning | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Resolve KIMI-vs-CLAUDE_CODE_PRO reconciliation drift |
| noesis-steward | orchestrator | planning | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | No approved cheap_router lane (NOUS_PORTAL proposed) |
| noesis-cartographer | orchestrator | planning | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Repo OpenRouter declaration must stay blocked |
| noesis-architect | orchestrator | planning | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Cross-family design critic unavailable |
| main-hermes | supervisor | approval_gated | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Runtime route unobserved; observe then reconcile before binding |
| noesis-forge | coder | bounded_execution | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Independent-family reviewer (Claude bridge) not bound |
| coder | coder | bounded_execution | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Repo-declared zai-org-glm-4.7 has no canonical lane |
| noesis-substrate | ops | bounded_execution | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | r3-class ops need manifest + human approval + independent review |
| noesis-sentinel | security | validation | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | not required | Reviewer currently shares kimi family with implementers |
| noesis-skeptic | qa | validation | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | not required | Distinct-ecosystem mandate unmet with one approved family |
| qa | qa | validation | r2 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Same-family acceptance review blocked until second family approved |
| noesis-scribe | worker | bounded_execution | r1 | observe_only | KIMI_CODE / kimi-k2.7-code | not required | NOUS_PORTAL repo route proposed, not approved |
| noesis-grid | worker | bounded_execution | r1 | observe_only | KIMI_CODE / kimi-k2.7-code | not required | NOUS_PORTAL repo route proposed, not approved |
| noesis-quill | worker | bounded_execution | r1 | observe_only | KIMI_CODE / kimi-k2.7-code | not required | claude-sonnet-5 writing route has no approved lane |
| noesis-herald | worker | bounded_execution | r1 | observe_only | KIMI_CODE / kimi-k2.7-code | required, null (gap) | Cross-check critic unavailable; external send always human-gated |
| noesis-signal | research | advisory | r1 | proposed | null / null | required, null | PERPLEXITY_API proposed; no pinned canonical model |
| noesis-tracer | research | advisory | r1 | proposed | null / null | required, null | PERPLEXITY_API proposed; skeptic independence unresolved |
| noesis-ledger | research | advisory | r1 | proposed | null / null | required, null | PERPLEXITY_API proposed; VENICE_PRO blocked for wallet topics |
| noesis-advocate | research | advisory | r1 | proposed | null / null | required, null | No approved lane may take confidential_redacted case material |
| research-openclaw | research | advisory | r1 | proposed | null / null | required, null | Catalog profiles (extraction_fast/synthesis_mid) lack approved lanes |
| subconscious-openclaw | reflective | advisory | r0 | observe_only | KIMI_CODE / kimi-k2.7-code (interim) | not required | Strategic local lane (local_drift) has no approved lane definition |

## 5. Why each profile has its primary/critic strategy

**Supervisors and control plane (noesis-core, main-hermes).** Selection
weights: long-context synthesis, planning quality, structured decision records,
independent critique. KIMI_CODE is the only approved lane covering the
supervisor type; it is assigned observe_only as an evaluable baseline. The
critic is mandatory but cannot be same-family for r2+ material, so the critic
lane is null and the gap is recorded rather than waived. main-hermes
additionally has an unobserved runtime: its assignment is explicitly not an
adoption of the repo-declared claude route.

**Orchestrators (noesis-orchestrator, steward, cartographer, architect).**
Planning profiles: structured artifacts, deterministic dispatch judgment.
noesis-orchestrator's dispatch gating is deterministic policy code, not model
judgment; the model does synthesis and risk-classification support. All four
carry drifted repo declarations (OpenRouter or CLAUDE_CODE_PRO); the matrix
assigns the observed aligned KIMI route observe_only and keeps the drift
blocked pending human review.

**Coders (noesis-forge, coder).** Weights: repository-aware transformation,
test construction, patch quality, bounded bridge, independent review. KIMI_CODE
is the approved implementation lane and both profiles are aligned with it at
runtime. The mandatory r2+ cross-family critic is unselectable, so activation
requires the Claude Code bridge binding first. The platform `coder`'s
repo-declared `zai-org-glm-4.7` maps to no canonical lane and is recorded as
drift, not adopted.

**Ops (noesis-substrate).** Conservative: planning plus bounded non-production
execution only. r3-class effects (firewall/DNS/production) require a canonical
action manifest, independent review, and human approval; automatic fallback is
disabled.

**Security/QA reviewers (sentinel, skeptic, qa).** Adversarial reasoning and
independence dominate. The uncomfortable fact: with one approved family, the
reviewer shares the implementer's provider family. The matrix refuses to
launder this into compliance — reviewer lanes are observe_only with the
independence gap recorded, and qa carries an explicit
`independent_provider_review` gate requirement that cannot be satisfied until a
second family activates. qa is tool-first by design: deterministic
test/schema/policy tools before any model judgment, and the model is never the
sole acceptance authority (qa cannot waive gates on confidence alone).

**Structured workers (scribe, grid, quill, herald).** Deterministic schema
compliance, bounded transformation, quarantine on invalid output. All observe_only
on KIMI_CODE. herald carries a mandatory critic for high-stakes external drafts
and permanently lacks external-send authority.

**Research (signal, tracer, ledger, advocate, research-openclaw).** Evidence
capture, source provenance, current-information capability, conflict reporting.
No approved lane covers the research type — KIMI_CODE explicitly excludes it —
so no primary is assigned. The strategic conceptual primary is PERPLEXITY_API
(proposed): public/internal_redacted data, r1 ceiling, provenance artifacts
mandatory. Every record is `proposed` with `stage: blocked`, null lane/model,
and the Perplexity activation requirements copied forward. research-openclaw's
canonical catalog bindings (extraction_fast, synthesis_mid) are recorded under
evidence; they are catalog profiles without approved lanes. advocate adds a
hard boundary: no approved lane may receive confidential_redacted case
material, so such material stays off every external route in this plan.

**Reflective (subconscious-openclaw).** Low cost, curated snapshots, concise
structured signals, low autonomy, no external research. The strategic end-state
is a local/self-hosted lane (catalog profile `local_drift`), which does not
exist in `approved_lanes`. Interim: observe_only KIMI_CODE for the
reflective_advisory class with curated internal inputs only. Write capability
is room-scoped; build intents pass the signal_filter gate; no terminal, no
code execution, no broker submission, no external research without supervisor
request.

## 6. Gaps blocking strategic assignment (consolidated)

1. **Cross-family independence.** r2+ review rules require an independent
   provider family; only kimi is approved. Blocks: all critic slots, sentinel/
   skeptic distinct-ecosystem mandates, qa same-family acceptance, forge/coder
   independent review. Unblocks via: CLAUDE_CODE_PRO bridge binding, CHATGPT_PRO
   activation, or a local lane for advisory review.
2. **Perplexity evidence lane.** Pinned model IDs unverified (sonar/sonar-pro
   are aliases); terms, retention, budgets, provenance policy, and evals
   outstanding. Blocks: all five research profiles.
3. **Claude Code bridge.** Canonical lane binding + bridge constraints +
   independent review + QA gates missing. Blocks: cross-family code review and
   the repo-declared claude routes (orchestrator, quill, advocate, etc.).
4. **Nous portal.** Lane proposed; roster comment reports key dead but operator
   indicates it should be available (2026-10-04); key validity, canonical model
   pin, and evals unverified.
   Blocks: cheap_router economics for steward triage and the scribe/grid repo
   declarations.
5. **xAI (XAI_GROK).** Proposed lane only; no canonical pin, budget, or evals.
   Non-selectable.
6. **ChatGPT/Venice policy bindings.** Both blocked_missing_configuration.
   Venice additionally needs privacy-mode proof (TEE/E2EE, metadata-only
   logging) before it can touch confidential_redacted material.
7. **Local/self-hosted lane.** Catalog profiles exist (local_drift,
   extraction_fast via `local`/`ollama`/`self_hosted` providers) but no lane is
   defined in inference-routing. Blocks: the reflective strategic primary and
   cheap extraction.
8. **Runtime observation.** main-hermes, research-openclaw, subconscious,
   qa runtimes were not observed by the reconciliation pass; their assignments
   are design baselines, not reconciled truth.

## 7. Exact data / risk / tool boundaries

Data classes: every profile's `allowed_data_classes` is a subset of its lane's
`permitted_data_classes` (validator rule PIA015), and no route anywhere admits
`confidential`, `restricted`, or `secret` data (PIA014). Research profiles are
bounded to `public` + `internal_redacted` (redaction gate before dispatch);
`confidential_redacted` handling requires an activated lane whose policy
explicitly permits it (none today).

Risk ceilings: workers r1, supervisors/orchestrators r2 (planning authority
only), reviewers r2 (validation authority), research r1, reflective r0. No
profile is granted r3 execution authority in this plan; r3 effects route
through approval manifests, privileged executors, and human approval per
`platform/risk-tiers.yaml`.

Tools: supervisors/orchestrators/research/reviewers/reflective profiles deny
`terminal` and `code_execution`. Treasury tools and external publish are denied
everywhere. Broker submission is exclusive to main-hermes (and the
orchestrator's contract ledger is a workspace write, not a broker call).
Reflective profiles additionally deny web_search/rss_fetch and any external
execution (PIA008). noesis-orchestrator's denial of terminal/code_execution is
preserved verbatim from the roster.

## 8. Evaluation design

Three layers:

1. **Assignment validator** (`scripts/validate_profile_inference_assignments.py
   --strict`): 15 machine-checked rules (PIA001–PIA015) covering inventory
   completeness, strategic-field presence, canonical model pins, lane
   selectability, type/task/data/risk permission, critic independence, coder/QA
   separation, research provenance, reflective tool boundaries, privileged
   fallback/approval rules, OpenRouter prohibition, fallback constraint
   preservation, gap-recording discipline, and secret hygiene.
2. **Eval fixtures** (`evals/profile-inference-assignment.eval.yaml`): 15
   scenario fixtures (PIA-001..PIA-015) mapped one-to-one to validator rules,
   mirroring the structure of `evals/inference-routing.eval.yaml`. The
   validator also asserts fixture completeness (names + required fields).
3. **Upstream suites already referenced in `validation.required_evals`:**
   `evals/inference-routing.eval.yaml` (IR-*), `EVALS.platform.yaml`
   (HERMES-*, ISOLATE-*, HANDOFF-*, ORCH-*, PALACE-*), and the orchestrator
   pytest suite for control-plane behavior.

## 9. Rollout order (all stages gated on explicit human approval)

1. **Observe** (current): matrix + validator land; no dispatch change. The
   enforcer rollout ladder from the fail-closed skill applies to any future
   runtime enforcement: observe → shadow_deny → enforce_allowlist → enforce.
2. **Canonical KIMI mapping** (highest priority, lowest risk): verify
   `kimi-k2.7-code` is an immutable model identifier (not an alias); publish
   the canonical KIMI mapping with parameter blocks and eval coverage.
3. **Perplexity evidence lane** activation for one research profile shadow
   rollout (recommendation in §12).
4. **Claude Code bridge binding** for cross-family code review (unblocks
   forge/coder r2+ review and the qa acceptance gate).
5. **Nous model pin/policy** (cheap_router economics), **xAI pin/policy**
   (dissent lane), **ChatGPT/Venice policy bindings** (review/ideation/privacy).
   OpenRouter remains disabled throughout.

## 10. Providers intentionally not selected

- **OpenRouter**: disabled fleet-wide; declared repo primaries remain blocked.
  Never primary, never automatic fallback.
- **Perplexity** for non-research profiles: task-scope enforcement (evidence
  lane only, never executor).
- **Venice** for all current assignments: privacy posture unverified; no
  pinned model; cannot receive secrets or restricted data. (The roster's
  venice mentions for tracer/ledger/advocate are recorded as intentions, not
  routes.)
- **Nous**: roster comment reports key dead, operator asserts availability
  (2026-10-04); key validity unverified; lane proposed, not approved.
- **ChatGPT/xAI/Venice**: blocked pending canonical pins, provider policy,
  evals, and bridge/bindings.

## 11. Graduation path: blocked → proposed → shadow → approved

1. **blocked_missing_configuration → proposed**: supply the lane's published
   `activation_requirements` (canonical catalog entry, provider policy
   approval, eval coverage, security review, budget/latency definition).
2. **proposed → shadow_candidate**: explicit human approval; lane added to the
   routing policy with status `proposed`; assignments flip from null lane to
   the lane with `stage: shadow_candidate`; shadow traffic is recorded,
   never blocking.
3. **shadow_candidate → approved**: shadow evals green (structured output,
   provenance, secret-denial, outage/substitution), cost/latency within budget,
   routing matrix review, independent provider review, QA/policy gate, and
   explicit human approval. Auto-promotion is forbidden
   (`shared/GUARDRAILS.global.yaml` catalog rules).

## 12. Lowest-risk shadow rollout recommendation

**`noesis-signal` primary on `PERPLEXITY_API`** is the single lowest-risk
future shadow pair: advisory-only authority, r1 ceiling, public/internal_redacted
data only, provenance-artifact gate already designed, and no execution
authority of any kind. It exercises the full evidence-lane activation path
(canonical pins, terms verification, provenance policy, budgets, evals) with
the smallest possible blast radius.

Runner-up: `subconscious-openclaw` on a new local/self-hosted lane
(`local_drift` catalog profile) — r0, offline, curated inputs, zero external
egress — blocked only on lane definition, not on provider terms.

## 13. Compact summary table

See §4 (22 rows, one per profile).
