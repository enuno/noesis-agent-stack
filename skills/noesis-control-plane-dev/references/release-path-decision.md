# Release-path decision assessment (read-only)

Use when the operator authorizes a bounded, read-only assessment to
choose between releasing a custom-built backend and adopting a native
platform capability — "smallest supported path to working governed X
without creating competing production systems." Planning only: no
installation, enablement, upgrade, launch, or dispatch during the
assessment.

## Evidence rules

- Verify capability from INSTALLED source and observed operation only —
  never from README/catalog claims alone. For Hermes: the install at
  `~/.hermes/hermes-agent` (check `git rev-parse HEAD` and `git status`
  for fork/hardening divergence), `plugin-catalog/*.yaml` entries vs
  the actual installed plugin directory and the profile's enabled list
  in `config.yaml`, and the tool implementation files.
- Separate the four state layers for each path: repository bytes,
  installed bytes, enabled/configured state, and observed runtime
  behavior. A catalog entry or config listing proves intent, not
  operation.
- Treat operational history as evidence: which path has actually
delivered governed work, and which has never completed a live run.

## Decision standard (all criteria, no tiebreakers by sunk cost or officialness)

Score each path on: smallest remaining VERIFIED engineering scope;
security and operational reliability; ongoing maintenance burden;
supported upstream interfaces; ability to enforce approval/reviewer
boundaries; reversible deployment. Two explicit anti-biases: do not
recommend the custom path merely because work was consumed on it; do
not recommend the native path merely because it is official. The
deciding question is which path's remaining gaps are configuration and
procedure versus new engineering that itself needs qualification.

## Packet shape (one consolidated artifact)

1. Qualification/asset state accepted and frozen (hashes preserved).
2. Responsibility/requirement table: one row per governance requirement,
   each cell stating what is verified in code or operation, not what is
   claimed.
3. Verified gaps and unknowns per path — including the systemic ones:
   does installing path A create a second dispatch system alongside the
   working one (competing-systems risk), and can any profile holding a
   broad tool bypass both paths (true for most launcher/library designs
   — neither is OS-enforcing; mitigation is role toolsets, not code).
4. Recommended path with concise rationale tied to the standard.
5. Exact resolution for any provenance/installation-assurance blocker
   (see `noesis-in-fleet-review` → `references/provenance-attribution.md`).
6. Smallest next envelope — and keep THREE readiness levels separate:
   planning readiness (authorized by the assessment output),
   installation readiness (requires explicit operator authorization),
   and live verification (a bounded pilot IS the live verification for
   the selected path).
7. Rollback/retirement for the nonselected backend: nothing installed
   means no rollback; preserve the nonselected artifact frozen as a
   reference asset with its evidence; revival starts from its recorded
   blockers, not from scratch.

## Governance-mapping notes for native-path adoption

When the native path wins, the governance features the custom backend
implemented in code (pre-spawn contract gates, routing-pair
enforcement, reviewer-boundary checks, spend ceilings) do NOT vanish —
they revert to procedural enforcement (toolset restriction, deny-by-
default child approvals, operator-mediated route amendments, ledger
maintained by the supervisor). State explicitly which controls become
config, which become procedure, and which are genuinely lost, so the
operator can see the enforcement delta rather than discovering it in
operation.
