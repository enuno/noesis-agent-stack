# Gate-defect regression repair

Depth for repairing routing-gate defects in `orchestration/orchestrator` —
observe-mode authorization leakage, policy-resolved pair binding, epoch
freshness — and for converting their pinned regressions from stale xfails
to ordinary passing tests. Load when working in
tests/test_control_plane_routing_gate.py or `_assert_spawn_gates`.

## Stale xfails killed by newer gates

An `xfail(strict=False)` regression can be green for the wrong reason: when
a gate lands AFTER the regression was written (e.g. an epoch-required check
added in front of the enforcer branch), the test dies at the new gate
before ever reaching the defect's enforcement — and the lenient xfail
absorbs that death. The suite reports the defect open while the enforcement
is in fact unexercised, and the xfail never becomes XPASS because the test
never gets far enough to pass.

Procedure:
1. Reproduce the pre-repair failure and READ which branch raised. If the
   raised code belongs to a newer upstream gate rather than the defect's
   enforcement, the xfail is masking gate-order staleness, not an open
   defect.
2. Convert by carrying the identity the new gate demands — on a fresh
   `route_and_launch` task that is `expected_epoch=0`, because
   `_assert_spawn_gates` runs before `reserve_launch` and the task's
   `assignment_epoch` is still 0 at gate time.
3. Confirm the converted test passes by REACHING the enforcement branch
   (assert the refusal code the defect requires, e.g.
   `observe_mode_not_authorizing`, not merely that RoutingBlocked fired).

## Single-approved-lane policies: decision injection

When the repo policy admits exactly one approved lane (e.g. only the
policy lane is in `allowed_lanes`), a lane/model-mismatch ALLOW decision is
not constructible through the real enforcer — unapproved lanes deny before
resolution, so no real decision can both allow and resolve a different
pair. Inject the RoutingDecision through a stub enforcer mounted on the
REAL bounded `route_and_launch` path: the gate, the bounded launch path,
and the launcher contract under test stay real; only the decision source is
replaced. Never reimplement the gate inside the stub to make the scenario
constructible — that tests the stub, not the gate.

Also add positive controls through the same seam: an observe-mode ALLOW
must still refuse (G2), and a matching resolved pair must reach the
launcher with the lane-mapped provider id (assert the mapped value, e.g.
via `hermes_provider_for_lane`, not the raw lane name — the gate binds the
policy lane, the launcher consumes the provider id).

## Live-decision type validation at the gate

At a gate consuming a live decision object, validate field types
fail-closed: a PRESENT non-bool/non-str field raises a typed refusal
(e.g. `RoutingBlocked("inference_decision_invalid", ...)`), never
truthiness-coerces; only an ABSENT (None) field takes the documented
default. `bool("false")` is True, so coercing a live `allowed="false"`
authorizes. Apply the validation on the bounded non-dry-run branch only
and leave dispatchable/observe semantics elsewhere untouched — a hardening
that widens behavior outside the branch it protects is scope expansion,
not a fix. Cover both malformed shapes (`allowed="false"`,
`resolved_lane=True`) and confirm the absent-field default still holds.

## Worktree and repository verification around gate work

- Verify a path's tracked-ness with `git ls-files <path>` (empty means
  untracked) before concluding anything from `git check-ignore`:
  check-ignore echoes the queried path and exits 0 whenever any ignore
  pattern matches, so its echo is not evidence the path is in the index.
  A tracked-but-ignored file exists in every checkout; an
  untracked-and-ignored file exists only in the local tree — a worktree
  silently lacks it and a patch targeting it fails to apply.
- Gate-probe and repair-note docs under gitignored `workspace/` are
  local-only: no worktree contains them, so a reconciliation addendum
  cannot ride as a tracked-file edit on an isolated branch. Ship the
  addendum inside the review packet and apply it to the live doc at
  landing; do not count it among candidate bytes.
- A full-suite parity run may need a gitignored fixture (e.g.
  `workspace/subgoal5-sandbox/control-plane-ledger.jsonl`) copied from the
  operational checkout; two lease tests skip environmentally without it.
  Copy it in for the parity run, then remove it before freezing so the
  candidate carries zero untracked bytes, and disclose the reproduction
  source in the review packet (see the `noesis-in-fleet-review` skill's
  working-tree-candidate pitfall).
