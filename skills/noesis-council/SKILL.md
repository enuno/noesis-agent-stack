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

## Contract, test, and repair rules

These rules come from the phase-by-phase review rounds; apply them to any
future council contract, engine, or fixture change.

- **Pin the intended negative-validation mechanism, not just the failure.**
  A negative fixture that asserts only "some validation error occurred"
  can be passing for an incidental reason. Assert the failing validator
  keyword (`e.validator == "not"` vs `"additionalProperties"`), add a
  control case that fails for the distinguishable neighboring reason, and
  prove the targeted guard is load-bearing by removing it from a deep copy
  of the schema and showing the fixture then validates. If the removal
  proves the guard was dead text (another keyword was catching the fixture
  first), make the intended mechanism real — reshape the fixture so only
the targeted guard can catch it, or extend the guard's coverage — and say
so in the repair record. Never write the assertion the reviewer assumed;
write the one that is true.
- **Partial results are a first-class shape, not a relaxed completed shape.**
  When a completed artifact's schema enforces minima (positions, tally
  rows, kill criteria), define an explicit partial-result variant keyed on
  a discriminator field (for council: `session_metadata.stop_condition`
  non-null) with an `allOf` if/then so the completed constraints apply
  unchanged when the discriminator says completed. Never fabricate entries
  to satisfy minimum-item constraints, and never report a zero count for
  work that ran — document what each counter means (for council:
  `rounds_run` = rounds that completed with full panel quorum) and make the
  engine report it honestly per failure path.
- **Exact-count CI assertions move only with evidence, never to floors.**
  When a repo's combined-suite job asserts an exact pytest count, adding
  tests legitimately breaks it. Update the count in the same diff, with a
  dated note naming the added tests and the measured local result. Do not
  convert exact counts to `>=` to go green, and do not touch pinned
  historical focused-count jobs — those measure fixed SHAs and must keep
  their frozen numbers.
- **Keep repair diffs minimal; never whole-file-rewrite for a targeted
  change.** Re-serializing a JSON file (e.g. `json.dump` with indent)
  reformats every line and turns a five-hunk schema edit into a hundreds-of
  lines diff that reviewers cannot audit. If a programmatic edit inflates
  the diff, `git checkout` the file and redo the change with targeted text
  patches.
- **Call an import guard what it is.** A static AST scan for banned
  mutator modules is a tripwire, not comprehensive authority isolation.
  Harden it within its class — check every dotted path segment, names
  brought in by `from x import store`, and relative imports (`from .
  import store`, which has no module string to inspect) — and add
  parametrized snippet tests for the catch and no-false-positive sides.
  Label it "tripwire" in the test name and docstring so nobody reads it as
  a complete boundary proof.

## Independent review of a council slice

Council slices are reviewed through the operator-mediated packet flow
documented in the `noesis-in-fleet-review` skill (see its
review-packet-identity reference): the operator hand-carries the frozen
packet; reviewer inference is never launched from the orchestrator. A REQUEST_CHANGES round produces a
successor candidate (uncommitted base + diff + frozen changed-file
identities) reviewed by BOTH reviewers independently — no verdict
transfers between candidates.

## Evidence ledger

Record per session: parent task id, session id, mode, seat routes and
their allowlist check, budget reservation vs ceiling, round count,
tally outcome (carried/split), dissent presence, stop condition, and
observed token usage. Source integrity cites the pinned upstream council
revision recorded in the session's `council_revision` block.
