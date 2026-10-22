# Noesis integration planning pattern

Use this reference when a Noesis task asks whether to integrate another project,
agent framework, advisory workflow, dashboard, provider, gateway, or deployment
surface into the control plane.

## Evidence order

1. Confirm operator authorization and the requested mode: plan-only, read-only,
   fixture-only, implementation, live canary, or rollout.
2. Record each repository/source with branch/ref, commit SHA or retrieval date,
   and worktree cleanliness. Treat dirty local state as evidence that ownership
   and implementation baseline are not yet frozen.
3. Read implemented entrypoints and configuration before inferring purpose from
   the name: README/instructions, package manifests, app/CLI/MCP entrypoints,
   workflows, schedulers, state directories, tests, CI, deployment artifacts,
   and security docs.
4. Classify every finding as implemented, documented intention, proposed, or
   unknown. A README claim, installed dependency, directory name, or roadmap is
   not deployment evidence.
5. For external products, use official upstream docs for interfaces, auth,
   pricing, plan entitlements, rate limits, and self-hosting limits. Subscription
   access is not an API key and included credits are not extra cash.

## Architecture assignment rules

- Put runtime contracts, routing policy, task lifecycle, approval gates,
  provider policy, and memory-promotion rules in `noesis-agent-stack`.
- Put installation, host placement, service/scheduler lifecycle, state paths,
  backups, upgrades, rollbacks, and uninstall behavior in `noesis-ansible`.
- Put operator-facing UI in the existing dashboard/control-plane surface, but
  keep policy enforcement server-side in the runtime/adapter path. A dashboard
  outage must not disable budget or approval enforcement.
- Prefer thin adapters and fixture contracts before services. Introduce MCP,
  ACP, queues, databases, or new orchestration frameworks only after naming the
  unmet requirement and the source of truth they will not duplicate.
- Treat optional vendor tools as replaceable adapters with explicit data,
  credential, cost, and fallback boundaries.

## Advisory and reflective integrations

Use this pattern for councils, evaluators, reflection workers, and self-healing
agents:

1. Start with an on-demand fixture adapter and JSON schemas for request/result.
2. Minimize context by passing artifact references and data classification, not
   raw workspace dumps.
3. Preserve dissent, uncertainty, unsupported claims, source refs, partial
   failures, and usage metadata in the result.
4. Return to Hermes/noesis-orchestrator for disposition; route implementation or
   policy-impacting output through independent QA and human approval where
   required.
5. Block self-approval, recursive escalation, canonical memory promotion,
   publishing, merging, deployment, and budget changes unless a separate policy
   and approval manifest authorizes that exact action.

## Budget reconciliation pattern

- Reconcile the main allocation table first. If another note conflicts, treat it
  as an alternate/stale scenario until the operator picks one active policy.
- Separate planned allocation, fixed subscription cost, included credits, PAYG
  cap, platform/compute charges, reserved in-flight allowance, settled actual
  usage, unreconciled estimates, and remaining allowance.
- Do not double count subordinate workflow ceilings as new money; they consume a
  service allocation or shared pool.
- Reserve a per-run allowance before paid dispatch where supported. Retries,
  fallbacks, synthesis, retrieval, auxiliary calls, and partial failures draw
  from the same allowance or require a new approved reservation.
- Label limits honestly: `hard` only when the execution path enforces them;
  otherwise use `advisory`, `monitoring_only`, or `fail_closed_on_unknown`.
- Provider-native billing changes, credit purchases, subscription upgrades, and
  auto-refills are separate external actions requiring explicit approval.

## Initial acceptance bar

A minimal integration slice is ready for implementation only when it has:

- request/result schemas with positive and negative fixtures;
- a fixture-only adapter that performs no paid calls or external mutations;
- tests for authorization rejection, duplicate/idempotent delivery, timeout,
  cancellation/failure, budget exhaustion, and prohibited action rejection;
- a file-level ownership map across `noesis-agent-stack`, `noesis-ansible`, and
  any dashboard/control-plane repo;
- an independent QA owner and explicit human approval gate for live canaries.
