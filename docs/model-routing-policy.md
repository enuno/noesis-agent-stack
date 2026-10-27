# Model routing policy

Status: source and policy only. Not activated.

Owner: Noesis. The managed declaration lives at `platform/model-routing-policy.yaml`. The loader and admission rules live in `orchestration/orchestrator/app/model_policy.py`. Neither file is an installed Hermes profile, a credential store, or a live route table.

## Managed source is not live configuration

`platform/model-routing-policy.yaml` is repository source. It does not mutate `~/.hermes`, any installed profile, any plugin, or any provider credential. Loading it does not select a live model, open a socket, or grant activation authority.

Installed profile configuration is a separate artifact. It is changed only by a later operation that has its own exact approval, fresh route evidence, managed materialization, and a rollback plan. Publishing this source, or merging it after independent review, is not that operation.

This change does not activate any route. Applying the policy to live profiles remains a separate, separately approved operation.

## The three routes

The file declares exactly three lanes. A fourth lane was not added to make the list look complete. No privacy, capability, or review-independence field was weakened to force a lane to fit.

`noesis_implement_primary` records the measured MiniMax implementation lane (`minimax-oauth` / `MiniMax-M3`, family `minimax`). A later bounded dispatch returned HTTP 429 Token Plan usage limit reached. The lane is `disabled`, readiness state `quota_exhausted`, quota `known_exhausted`, and it has no fallback. It stays in managed source so a future separately approved requalification can update the declaration. It is not selectable. Leaving it disabled is not a silent re-enable, and a later edit that flips it back to `approved` without that requalification would be a different change.

`noesis_review_primary` is the default route. It is the measured reachable xAI lane (`xai-oauth` / `grok-4.7`, family `xai`), status `approved`, quota `unknown`, readiness state `reachable`, no fallback. It serves `implementation`, `review`, and `adversarial_review` because it is the only approved reachable lane, not because using the same provider family for implementation and review creates an independent review. Reachability is not remaining quota.

`noesis_cheap_fallback` records a proposed Nous free-tier classification lane (`nous` / `upstage/solar-mini4:free`, family `nous`). Status is `proposed`, readiness state `unverified`, quota `unknown`, no fallback. Proposed routes are never selected. The name describes the class of lane. It is not an enabled fallback, and the shipped policy enables no fallback at all.

## Quota and reachability

Quota is `unknown` where no quota API exists. `unknown` is an explicit state, not a guess that credits remain. MiniMax is `known_exhausted` because a measured limit response said so, not because a quota API returned a balance.

A successful readiness probe proves reachability only. It never proves remaining credits. Caller-supplied readiness evidence is an input to admission. This module does not probe providers and does not read the Hermes home to invent that evidence.

## Selection order

Selection is fail-closed. The code applies gates in this order:

1. Policy: the workload class must be served by a declared route, and the route status must be `approved`. `risk_tier_max` is a ceiling, the highest risk tier allowed on that route. A request whose rank is less than or equal to the maximum is eligible. A request above the maximum is refused. A caller must not inflate an `r0` or `r1` request to `r2` to match a lane. When several routes are otherwise eligible, the lowest sufficient maximum is chosen. The default route is used only when it is in that least-privileged set. Disabled and proposed routes are refused.
2. Data-handling: the requested data classification must be one of the route's permitted data classes. A fallback candidate that changes that set is not used.
3. Tool-use and capability compatibility: if the caller requires tools, the route must declare them. A fallback candidate that changes required tool capability is not used.
4. Supported authentication method and model availability: `credential_scope` is a category label validated at load, never a credential value. `oauth-device-code`, `api-key-env`, `free-tier-anonymous`, and `subscription-oauth` are categories. A token-shaped segment is rejected in every hyphen-separated segment, not only when the whole scope is one segment. A secret-prefix form is rejected in every segment, including when it is not at the start of the scope, even if the value otherwise matches category grammar. Availability is the caller-supplied set of routes that are reachable right now. This module does not probe.
5. Verified quota or explicit unknown state: `known_exhausted` refuses the route. `unknown` does not prove credits and does not by itself authorize a call. `known_available` still requires fresh evidence.
6. Task-specific correctness evidence: admission requires fresh readiness evidence for the same task epoch, naming the selected route, provider, and model exactly, with `reachable` true and no failure category. Missing, wrong-epoch, or mismatched evidence refuses the attempt. A timestamp newer than `now` is refused as future, not as stale. Evidence older than the route TTL is stale.
7. Subscription value, latency, effective cost, and context requirements: this module does not score them. They cannot override a refusal and they cannot authorize a route the gates rejected.
8. Provider and model diversity for independent review: acceptance review uses one role rule. The implementer route must be distinct and serve `implementation`. The reviewer route must serve `review`. Both must be approved and selectable. Provider families must differ. `adversarial_review` alone is not acceptance review. A quota-exhausted or otherwise unselectable route does not qualify.

`select_route` is not dispatch. A positive selection still requires caller-supplied availability and fresh same-epoch evidence. Disabled MiniMax and proposed Nous are refused. xAI can be selected for an eligible implementation, review, or adversarial-review workload only when those caller inputs pass. Eligible means the requested risk tier is at or below the route maximum and the data class is permitted. Lower-risk work stays on the approved ceiling. It is not refused for being below that ceiling.

## Route selection is not acceptance-review independence

Selecting xAI for implementation does not create an independent acceptance review. Implementation acceptance requires a reviewer provider family different from the implementer family, and it requires the role and selectability rule above. The current approved set has no qualifying independent pair: the only approved route is xAI, and pairing xAI implementation with xAI review fails the family check. Profile or session separation does not create provider-family diversity. The shipped file records that blocked state. Loading it succeeds because an honest blocked state is valid configuration. `check_review_independence` and the shipped pair flag use the same rule. The check is in code, not only in this document.

## Closed-loop admission

The module models dispatch gates. It does not launch work.

Readiness evidence is admitted only when it is fresh for the route TTL, belongs to the same task epoch, names the selected route, provider, and model exactly, is reachable, and has no failure category. A timestamp newer than `now` is future, not stale. Evidence older than the TTL is stale.

Actual result provenance must report the same route, provider, and model that were selected. A different reported route, provider, or model is rejected.

Fallback planning uses declared `fallback_routes` only. Names are deduplicated, and unique candidates count toward a maximum of three. If `workload_class` is supplied, it must be a member of the origin route's workload classes before any candidate is considered, and the candidate must serve that same origin workload. An implementation origin cannot authorize a classification route by passing `classification`. A candidate is not planned when it does not serve the origin workload, when its maximum cannot cover the origin maximum or the caller risk, or when that route was already attempted. Boolean, non-integer, and negative attempt counts are rejected in planning and in retry authorization. Planning still refuses an undeclared route, a proposed or disabled route, stale or wrong-epoch evidence, a data-policy change, a tool-capability change, partial output, a possible side effect, and an unknown failure. The shipped three-lane policy declares no fallbacks. Tests may build synthetic policies with explicit fallbacks; those routes are not written into the shipped file.

Retry and fallback are refused after partial output, and whenever side effects may already have occurred. A second attempt on a route that was already attempted is a duplicate retry and is refused. That prevents duplicate side-effectful work.

Known failure categories are an explicit set: `missing_auth`, `quota_exhausted`, `rate_limited`, `model_unavailable`, `wrong_backend`, `unsupported_effort`, `unsupported_tier`, `malformed_route`, `data_policy_mismatch`, `tool_capability_mismatch`, `partial_output`, and `route_mismatch`. Categorizing a known failure is not authorization to fall back. Exception text is not parsed. An unknown failure, including a raw provider error string, refuses fallback.

Load rejects contradictory route state while still accepting the three shipped lanes. Approved requires readiness state `reachable` and quota `unknown` or `known_available`. Disabled and proposed must not be readiness state `reachable`. `known_exhausted` must not be paired with `reachable`. `known_available` must not be paired with `quota_exhausted`, `missing_auth`, or `disabled`. MiniMax stays disabled and known exhausted. Nous stays proposed. Neither is silently re-enabled.

## Synchronous reconciliation is not background delivery

`reconcile_synchronous_result` accepts only `execution_mode="synchronous"`, and it requires the caller task epoch and the current time. Background, deferred, and detached execution are unsupported and not activated. `BACKGROUND_EXECUTION_SUPPORTED` is false. A synchronous result is accepted as success only when provenance matches the selected route, provider, and model; the result task epoch equals the caller epoch; the evidence timestamp is not in the future and is within the route TTL; the route is still selectable; `reachable` is true; failure category is absent; `partial_output` is False; and `side_effects_may_have_occurred` is False. None, integer zero, and every other non-boolean are not success. A future timestamp is reported as future. A timestamp outside the TTL is reported as stale. A disabled route cannot be accepted as success. A matching provenance with a failure, partial output, or possible side effects is reconciled as a failure and is not accepted.

## Publication is not activation

This change is source and policy only. It does not install a profile, switch a runtime, call a provider, or grant anyone authority to do those things. A document, a green test run, or a later merge does not activate the policy.

## Requalification is not a silent re-enable

`noesis_implement_primary` remains declarative and disabled. A future requalification would be a separate approved edit to managed source, with fresh evidence, not an automatic retry and not a fallback hidden inside this file. Until that happens, the lane stays unselectable.

## What operational application still requires

Operational application requires all of the following, each still outstanding:

- a separate exact approval for the live change
- fresh route evidence for the attempt, including an explicit quota state rather than a reused stale probe
- managed materialization and a rollback plan
- a provider-diverse reviewer route before independently accepted implementation can complete

Until that reviewer route exists, implementation can be selected onto the approved reachable lane only as a bounded development dispatch. It cannot be independently accepted.
