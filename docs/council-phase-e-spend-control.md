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
