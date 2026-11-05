---
name: noesis-council
description: Use when the operator requests a governed multi-perspective deliberation on a consequential Noesis decision. Runs the bounded advisory council protocol (duo mode) as a child of an existing task contract; verdicts are evidence, never execution authorization.
user-invocable: true
argument-hint: "[decision question and alternatives, bound to an existing parent task contract]"
homepage: https://github.com/enuno/noesis-agent-stack
compatibility: Requires the noesis-agent-stack task-contract plane (orchestrator); offline duo slice only — no live inference dispatch without a separately authorized adapter.
metadata:
  hermes.plugins.version: 1
  primary_domain: orchestration
  estimated_tokens: 2200
---

# Noesis Council (Duo Slice)

## Purpose

Run a bounded, blind-first, multi-perspective deliberation as a child of an
existing Noesis task contract, and return an advisory verdict artifact. The
council never approves its own task, never mutates the orchestrator ledger,
never releases execution authority, and never spends beyond its recorded
budget.

Duo mode is the minimal protocol that still exercises every authority
boundary (two seats + an excluded chairman, two blind rounds, weighted
tally). Full panels (triad/full) are later phases.

## Protocol snapshot (current duo slice)

1. **Bind.** The session is created as a child contract of an existing
   parent task (`parent_task_id` is required). Modes are protocol names,
   not risk tiers.
2. **Freeze routes.** Every seat resolves its inference route through
   `platform/inference-routing.yaml`. The operator-approved allowlist is
   enforced **before any seat work is reserved**; an unapproved route
   fails closed (`RouteDenied`). The default route is never silently
   substituted.
3. **Reserve budget.** The session's token reservation (per-seat
   `max_output_tokens` × rounds) is checked against the cost ceiling
   **before any seat work**; over-ceiling sessions never start
   (`BudgetExhausted`). Usage is observed tokens only — currency values
   are never recorded.
4. **Round 1 — blind.** Each seat receives a sealed envelope built by
   construction: decision framing + evidence refs only. No peer seat IDs,
   no profile names, no peer positions. Leaks are caught structurally
   (schema `not` clause plus engine leak checks), not by prompt promises.
5. **Anonymized release.** Positions are re-keyed by `seat_id` only and
   shown to every seat in the final round.
6. **Final round + tally.** Confidence-weighted 2/3 threshold. Split
   verdicts are preserved (dissent + minority report) and escalated; the
   round budget is never exceeded — no extra round is run to force
   consensus.
7. **Verdict assembly.** An artifact shaped by
   `contracts/orchestration/council-verdict.schema.json` is attached to
   the parent task as advisory evidence.

## Authority boundaries

- The verdict has **no** approval, acceptance, lifecycle, execution, or
  spend fields. A task cannot succeed on a council verdict alone.
- The chairman is excluded from the panel; `chairman_failed_fallback` and
  provider fallbacks must stay `false`/empty — fail closed.
- Panel membership is sealed at session start; blocked seats are reported
  and the panel goes partial (quorum floor for duo: two-of-two). Seats
  are never silently substituted.
- `synthesis_notes` must state deviations (duo slice: no domain
  multiplier applied).

## How to run (offline slice)

The engine is `orchestration/orchestrator/app/council.py`
(`run_duo_session`). It is stdlib-only and takes a validated
council-session document plus a `SeatRunner`. **Only scripted offline
runners are authorized in this phase.** A governed dispatch adapter
(Phase E) must be separately authorized; it must reuse existing
delegation budget/lease/identity protection, never a parallel system.

## Evidence ledger

Record per session: parent task id, session id, mode, seat routes and
their allowlist check, budget reservation vs ceiling, round count,
tally outcome (carried/split), dissent presence, stop condition, and
observed token usage. Source integrity cites the pinned upstream council
revision recorded in the session's `council_revision` block.
