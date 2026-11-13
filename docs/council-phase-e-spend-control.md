# Council Phase E spend-control design (T10)

Status: DESIGN + OFFLINE TOKEN ENFORCEMENT ONLY. No monetary enforcement
exists in this repository after this document. No live spending is
authorized by anything here.

## Layers kept distinct

1. Per-request output-token cap (`max_output_tokens`). Enforced by the
   launcher before inference; a transport that cannot enforce it refuses
   with `output_cap_unsupported` (PR #33). Implemented.
2. Total request/turn/token budget (session ceiling).
   `limits.cost_ceiling.estimated_tokens` is the admission estimate;
   `CouncilSeatDispatch(enforce_budget=True)` now refuses a round before
   inference when observed output tokens plus this round's requested cap
   would exceed the ceiling (prepared under this mission, production path
   only). Implemented, offline-tested.
3. Estimated cost. A projection from token counts. Not a control; never
   presented as one.
4. Hard monetary ceiling. NOT IMPLEMENTED. Nothing in this repository can
   stop currency spend.
5. Provider/account-level spending control. Outside this repository
   (provider console/API). No evidence gathered; no settings applied.

Layers 1–2 are token accounting. Calling them monetary enforcement is a
false claim and is prohibited in every artifact and report.

## Implemented offline enforcement (this mission)

- Enforcement point: `CouncilSeatDispatch.run_round`, pre-call, only when
  `enforce_budget=True`; the production factory sets it non-optionally.
- Reservation/accounting semantics: reservation = session admission
  (`reserve_session_budget` in app/council, unchanged); consumption =
  sum of recorded `output_tokens` per completed launcher call; projection =
  consumed + requested `max_output_tokens`; refusal when projection exceeds
  the ceiling. Observed overage beyond the per-request cap is recorded
  honestly by the usage mapping and surfaces on the next round's gate.
- Concurrency: the council engine drives seats sequentially in the offline
  contract; the gate state lives in the dispatch instance, so a single
  session is consistent. Concurrent sessions share no budget state — a
  known limit, not a silent guarantee (see evidence limits).
- Unknown usage: a launcher result without `output_tokens` is refused as
  malformed; zeros are never invented.
- Ambiguous outcomes: attempt fencing settles timeout/refusal/exception as
  `uncertain` (PR #33); uncertain attempts are not re-fenceable and not
  retried. Recorded consumption for completed rounds is reported exactly
  once on every exit path.
- Enforcement unavailable: admission refuses a missing/non-positive ceiling
  estimate; a transport that cannot enforce the per-request cap refuses
  pre-spawn.
- Exhaustion/stop: `BudgetExhausted` before inference; session
  `stop_conditions` include `budget_exhausted`; `abort()` stops all further
  launcher calls.

## Evidence limits

- A bool or missing `budget.max_output_tokens` with `enforce_budget=True`
  currently fails untyped (`int(True) == 1`; a missing key raises
  KeyError), and admission accepts a bool `estimated_tokens`. The offline
  contract always passes a positive int; typed refusal of malformed budget
  fields is activation-time hardening, not yet implemented.
- Concurrent sessions share no budget state; per-session accounting is
  exact only within one dispatch instance.

## Monetary ceiling — what is missing and why

A hard currency stop needs a rate (price per token for the approved
provider/model pair) and an enforcement point that holds currency before
the provider call. This repository has neither: `currency_value` is null in
the council fixtures, and no pricing source is pinned. An attempt lock,
token estimate, or post-hoc usage report is not a prevention mechanism.

## Decision request (exact, unresolved)

The operator must choose ONE before any provider canary:

D1. Provider/account hard cap: name the provider account-level spend
    control to enable (e.g. monthly budget cap in the provider console),
    who sets it, and the evidence receipt that will prove it. Requires
    provider-account access — a separate, explicit authorization; no
    credential retrieval is authorized now.

D2. Manual stop accepted in writing: the operator accepts that this
    repository cannot stop spend, that the canary's 1 USD ceiling is a
    target not a mechanism, and that manual abort plus post-hoc invoice
    reconciliation (per the canary proposal) is the control. This is the
    operator's risk acceptance and cannot be made by a reviewer or delegate.

D3. No canary until a mechanism exists: defer Phase E provider execution
    until D1 is satisfied by evidence.

No default is chosen here. The canary contract names this decision as a
prerequisite and is not executable without it.

## Decision package (prepared 2026-11-12; still requires the operator)

Scope note: nothing in this package changes provider/account settings,
retrieves credentials, or spends. It is a decision aid. Labels D1/D2/D3
are the authoritative decision names from the section above.

### D1 — provider/account hard cap

- Exact question: which provider-account-level spend control will be
  enabled for the canary account, who enables it, and what evidence
  receipt proves it before the canary runs?
- Supported options: (a) provider console hard budget cap; (b) provider
  API usage-alerts plus a hard cap where the provider supports one;
  (c) a prepaid/burner account funded with exactly the canary allowance.
- Recommendation: (c) prepaid/burner account, or (a) hard cap if the
  approved provider supports a cap that cannot self-raise. Rationale: it
  is the only option where the ceiling is a mechanism, not a target; a
  prepaid balance cannot be exceeded regardless of reporting delays.
- Enforcement mechanism: provider-side, outside this repository (layer
  5). Nothing in the agent-stack enforces it.
- Cost/usage uncertainty: provider usage reporting can lag minutes to
  hours; token-to-currency conversion needs a pinned rate.
- Consequence of missing enforcement: spend can exceed the intended
  allowance with no in-repo stop; the token gate (layer 2) does not
  prevent this.
- Human authorization required: yes — provider-account access and
  setting changes are a separate, explicit operator authorization; no
  credential retrieval is authorized now.

### D2 — manual stop accepted in writing

- Exact question: does the operator accept, in writing, that the canary's
  1 USD ceiling is a target rather than a mechanism, with manual abort
  plus post-hoc invoice reconciliation as the only controls?
- Supported options: accept / decline.
- Recommendation: decline as a sole control; acceptable only as a
  written supplement to D1. Rationale: reviewers and delegates cannot
  accept risk on the operator's behalf, and a single ambiguous execution
  under a "target" ceiling can exceed it before a human reacts.
- Enforcement mechanism: none (human supervision only).
- Cost/usage uncertainty: highest of the three options; real-time
  visibility depends on provider dashboards.
- Consequence of missing enforcement: identical to D1-without-mechanism.
- Human authorization required: yes — this is by definition the
  operator's explicit risk acceptance, recorded verbatim.

### D3 — no canary until a mechanism exists

- Exact question: defer Phase E provider execution until D1 is satisfied
  by evidence?
- Supported options: defer / do not defer.
- Recommendation: defer, if D1 evidence cannot be produced before the
  canary window. This is the default-safe posture and changes nothing
  already built.
- Enforcement mechanism: n/a (a scheduling decision).
- Cost/usage uncertainty: none; no spend occurs.
- Consequence of missing enforcement: none; Phase E provider evidence
  remains outstanding.
- Human authorization required: yes — the operator chooses the schedule.

### Distinctions this package enforces in every artifact

Per-request/turn/token limits and the cumulative token budget are token
accounting (layers 1-2). Estimated currency cost is a projection (layer
3). Hard monetary prevention is layer 4 and does not exist in this
repository. Provider/account spending limits are layer 5 and live outside
this repository. Delayed or unknown usage reporting affects all currency
claims. No artifact may describe layers 1-3 as a hard currency ceiling.
