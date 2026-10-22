# Repair-contract mechanism-inspection rules

Topical depth for launch-boundary / review-gate remediation (extends
`bootstrap-handoffs.md`). Always-on rules live in the parent SKILL.md
(`noesis-control-plane-dev`); this file holds the decision table and citation
pattern you reference when writing the contract clauses for F1–F5.

## What to inspect before claiming enforcement

For each mechanism claim, cite the installed source path and confirm the path
is called at the real adapter/child boundary (not synthetic transport):

- Authorization before spawn: `authorize_inference_request` (or supported
  equivalent) must be invoked inside the adapter's `.launch()` before `_run`
  starts the child process. A synthetic test that passes through the adapter is
  not proof unless the adapter entry itself calls the authorization path.
- Profile identity: either (a) profile-scoped launch that preserves the full
  selected profile (with only fallback-policy override), with second
  in-process child-side readback; or (b) complete isolated clone with atomic
  unique-per-attempt HERMES_HOME. Attesting the installed profile then
  launching a different minimal identity is a bypass — reject it.
- Credential-attempt bound: disable same-provider pool rotation (supported
  mechanism cited from `cron/scheduler.py` or `run_agent.py`) or enforce a
  durable counter/block-state verified with an offline multi-credential
  double. `fallback_providers: []` file content is NOT proof of effective
  runtime state.
- Verification consistency (`verification_pending`): must derive from
  `verified_digest is not None`, not hard-coded `True`; replay must recover
  both artifact-present and artifact-absent outcomes.
- Contract/baseline (`F1`): non-optional fields on reservation/store; validated
  before spawn; replay uses persisted values, not optional caller assertions.

## BLOCKER format (when mechanism missing)

When the installed Hermes mechanism does not expose the required boundary
within authorized Noesis integration code:

```
BLOCKER: <finding> — mechanism <name> missing at <installed-source-path>.
Installed source citation: <file>:<line-range> (quoted or summarized, not fabricated).
Required: separately scoped core/integration proposal addressing <exact gap>.
Not permitted: monkey-patch, silent core edit, unsupported mechanism, profile-attestation-bypass.
```

The BLOCKER is an output artifact, not a silent workaround. The repair does
not proceed past the mechanism check until the separate proposal is accepted.

## Concrete enforcement seam (verified in installed source)

When implementing the runtime-enforcement extension itself (a separate dev
checkout), target the true per-attempt boundary, not the parent launch call:

- Choke point: `agent/turn_api_call.py::perform_api_call` is the single
  per-physical-attempt function every primary, retried, fallback-activated, and
  credential-rotated request re-enters (via `conversation_loop._run_api_retry_loop`).
  Run admission there, BEFORE the transport is invoked; a denial then re-enters
  the same gate on each subsequent physical attempt, so there is nothing to
  rotate/fall back "to". Report usage after the call on both success and error
  (`turn_api_error.py`).
- Auth must validate the EFFECTIVE outbound request, not the caller-supplied
  args handed to `.launch()`. A transport/child that rewrites `--provider` after
  the launch call can bypass an authorization keyed to the original caller args.
- Same-provider credential-pool rotation is INDEPENDENT of the fallback chain,
  even for pinned routes: `cron/scheduler.py` states pinned jobs still apply
  "same-provider credential-pool rotation ... not the chain";
  `run_agent.py::_pool_may_recover_from_rate_limit` returns True once
  `len(pool.entries()) > 1`. An empty `fallback_providers: []` therefore does
  NOT bound the number of credential requests.
- Durable attempt budget must be keyed to the ATTEMPT lineage and survive
  process restart; a new `task_id` or a fresh process must not reset an
  exhausted attempt (issuing another launch is exactly the escape hatch).
  A module-level in-process dict is limited parent-side protection at best —
  label it as such and keep real execution blocked until the durable child-side
  control exists. An autouse test fixture that resets the budget for isolation
  is test isolation, not production enforcement; keep an explicit
  restart/cross-instance test that shows the remaining limitation.
- A governed extension is opt-in (default None = unchanged standalone behavior);
  fail closed on a malformed governed argument rather than silently running
  ungoverned.
