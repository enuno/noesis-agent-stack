# Inference Lanes Design

Status: proposed_not_live
Version: 2026-10-03.1
Routing seed: `f6116a9c11971a82a7082590f5501980df4d239eb0c0823c69e69045c5f786d2`

This document is a design artifact only. It does not activate providers, mutate active Hermes profiles, change credentials, restart services, call model APIs, or authorize execution.

## 1. Control-plane problem

The Noesis Hermes + OpenClaw stack currently has drift between repository declarations and observed active runtime state. The repository contains multiple sources of routing intent: `profiles/noesis-roster.yaml`, `profiles/model-profiles.yaml`, `shared/models.yaml`, `platform/profiles.yaml`, `platform/orchestrator.yaml`, and `profiles/live/*/config.yaml`. The observed active fleet metadata is predominantly configured around `KIMI_CODE` / `kimi-coding` / `kimi-k2.7-code`, while repository live profile files still declare OpenRouter primaries, Nous primaries, or custom routes.

The problem is not merely naming drift. Routing affects data boundaries, risk-tier handling, fallback safety, reviewer independence, cost controls, structured-output guarantees, and human approval gates. A provider lane must therefore be a policy object, not a brand preference or a runtime accident.

## 2. Source-of-truth and precedence hierarchy

The proposed precedence hierarchy is:

```text
Global guardrails
  > provider policy
  > model catalog and alias policy
  > inference lane policy
  > profile routing declaration
  > observed runtime state
```

Observed runtime state is evidence for reconciliation and incident analysis. It is not authorization and must not silently promote a provider, model alias, route, tool scope, or execution mode into policy.

Canonical layers:

1. Global guardrails: `shared/GUARDRAILS.global.yaml` and risk-tier policy define non-negotiable safety boundaries.
2. Provider policy: `shared/provider-policies.yaml` defines provider eligibility, data policy, hard filters, and disabled/exception paths.
3. Model catalog and alias policy: `shared/models.yaml` and `shared/model-aliases.yaml` define model profiles and capability aliases.
4. Inference lane policy: `platform/inference-routing.yaml` maps strategic lanes to allowed profile types, task classes, data classes, risk ceilings, fallback behavior, and required checks.
5. Profile routing declaration: repository profile declarations express which routing class/lane a profile should use after approval.
6. Observed runtime state: safe non-secret runtime metadata is read-only evidence for reconciliation, not a source of authority.

## 3. Proposed reconciliation_freeze interim operating mode

`platform/inference-routing.yaml` defines `interim_operating_mode.mode: reconciliation_freeze`. This proposed design state prevents further provider and model drift while preserving observed runtime as evidence.

Under the freeze:

- Existing KIMI_CODE behavior is documented as an observed runtime baseline for existing non-privileged work only.
- Observed KIMI_CODE routing is not automatic policy and cannot justify new profile assignments, new aliases, live configuration changes, or runtime adoption as architecture.
- New provider activation, new model activation, OpenRouter primary routing, automatic execution fallback, r2/r3 route promotion, unapproved profile reconciliation, secret/restricted external egress, and live runtime mutation are prohibited.
- Route activation requires a provider policy entry, model catalog entry, immutable or explicitly pinned model identifier, lane definition, profile eligibility, data policy, structured-output requirements where applicable, eval coverage, security review, cost/latency budget, and explicit human approval.

## 4. Provider lane matrix

| Lane | Status | Canonical pinned model in this proposed policy | Max risk | Max execution mode | Rationale / missing configuration |
|---|---|---|---|---|---|
| KIMI_CODE | approved | yes: kimi-k2.7-code | r2 | bounded_execution | Currently observed active fleet baseline from safe active-profile metadata. Approval here is design-only; runtime remains unchanged. If kimi-k2.7-code becomes an alias rather than an immutable model identifier, promotion must reclassify this as blocked_missing_configuration. |
| PERPLEXITY_API | proposed | no: observed aliases only (sonar, sonar-pro) | r1 | advisory | Proposed evidence-only lane. Local aliases sonar and sonar-pro are observed aliases, not canonical pins. Activation requires verified API auth, terms, data handling, canonical model identifiers, provenance artifacts, evals, budgets, and explicit human approval. |
| NOUS_PORTAL | blocked_missing_configuration | no: none | r1 | advisory | shared/models.yaml contains placeholder Nous aliases and roster comments report dead Nous key; no active fleet-wide canonical pinned model is verified. |
| CLAUDE_CODE_PRO | blocked_missing_configuration | no: none | r2 | bounded_execution | Repo contains inconsistent Anthropic/Claude identifiers and live profiles route some Claude traffic through OpenRouter; approved lane label and authentication route are not canonically pinned. |
| CHATGPT_PRO | blocked_missing_configuration | no: none | r2 | bounded_execution | Repo and active configs disagree between gpt-4.1, gpt-5, and openai-codex gpt-5.4-mini; no canonical CHATGPT_PRO lane binding is defined. |
| VENICE_PRO | blocked_missing_configuration | no: none | r1 | advisory | Provider appears in config, but no pinned model, privacy-mode proof, or eval record is present. Cannot receive secrets or restricted data. |
| OPENROUTER_FALLBACK | disabled | no: none | r0 | draft_only | Disabled while shared/models.yaml and provider policy treat OpenRouter as disabled/exception-only. It cannot be primary, cannot be automatic execution fallback, and cannot be selected for r1-r3 while reconciliation_freeze is proposed. |

## 5. Perplexity API as proposed citation/evidence lane

`PERPLEXITY_API` remains `status: proposed`. It is evidence-only, advisory, and limited to `public` and `internal_redacted` data. It is not an execution authority, generic fallback, deployment engine, or approval source.

The aliases `sonar` and `sonar-pro` are recorded only as observed aliases, not canonical pinned models. `pinned_models` remains empty until the repository contains verified canonical API model identifiers, documented authentication posture, data-handling/retention policy, budgets/rate limits, structured-output contract, outage/substitution evals, redaction/secret-denial evals, and explicit human approval.

Perplexity outputs must preserve source capture, claim-to-source mapping, retrieval timestamp, and uncertainty/conflict reporting. Material research still requires Hermes synthesis against internal artifacts and independent critique where risk or uncertainty warrants it.

## 6. Why OpenRouter remains disabled

`shared/models.yaml` marks OpenRouter disabled, and provider policy treats it as a controlled exception path. Some `profiles/live/*/config.yaml` declarations nevertheless use OpenRouter as primary. That contradiction is intentionally retained as `blocked` in the reconciliation matrix; it is not normalized by enabling OpenRouter.

`OPENROUTER_FALLBACK` therefore remains disabled with `primary_eligible: false`, `automatic_execution_fallback: false`, `fallback_eligible: false`, and `max_risk_tier: r0`. It cannot be primary, cannot be automatic fallback, and cannot be selected for r1-r3 while the reconciliation freeze is unresolved.

OpenRouter could be reconsidered only after resolving the shared-catalog contradiction, approving provider policy, allowlisting and pinning models, defining data policy and budgets, adding structured-output contracts, logging substitutions, adding circuit breakers and outage/degraded-mode evals, completing security review, and receiving explicit human approval.

## 7. Promotion procedure for a new provider/model

1. Add provider/model metadata to the global catalog without secrets.
2. Define or update provider policy and data boundary.
3. Define the inference lane and profile eligibility.
4. Pin the exact model version or immutable provider identifier; do not rely on mutable aliases.
5. Add structured-output and schema requirements where applicable.
6. Add redaction, secret-denial, provider-outage, fallback, cost, latency, and prompt-injection evals.
7. Review cost, latency, reliability, fallback frequency, QA rejection rate, and human correction rate.
8. Approve staged rollout with human review for r2/r3-affecting lanes.
9. Reconcile runtime state only after design and CI validation pass.

## 8. Rollback procedure

1. Disable the route centrally in `platform/inference-routing.yaml` or the catalog.
2. Halt fallback promotion and mark the route unavailable.
3. Retain artifacts, routing events, provider failure events, and eval logs.
4. Revert per-profile references to the last-known-good class/lane.
5. Verify degraded safe mode: `draft_only`, `read_only`, or `blocked_degraded` with no data-classification, tool-scope, approval, or risk-tier downgrade.

## 9. Explicit non-goals and deferred phases

- No live fleet changes.
- No active profile mutation.
- No automatic provider activation.
- No secrets or credentials in Git.
- No transfer of approval authority to models.
- No merge, deployment, reload, restart, external API call, or service configuration change.
- No shadow-mode inference run in this task. Shadow-mode comparison of one low-risk profile is a later phase after this design, validator, and CI gate are reviewed.

## 10. Policy contradictions retained for review

- OpenRouter is disabled/exception-only in shared policy but appears as a primary provider in several `profiles/live/*/config.yaml` files.
- The roster, repo live configs, platform model profiles, and active runtime metadata use different model/provider identifiers for the same conceptual profiles.
- Perplexity exists in observed noesis-orchestrator metadata but not in the shared repository model catalog/provider policy.
- Nous appears as a desired/placeholder lane while the assessment records no verified active fleet-wide lane.
- ChatGPT/Codex and Claude lane labels are not canonically bound to exact programmatic model identifiers across the repo.
