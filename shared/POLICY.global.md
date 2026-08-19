# Global Policy — Noesis Agent Stack

**POLICY.global.md** is the human-readable global policy contract for the
Noesis stack (Noesis Praxis on Hermes + Noesis ClawDev on OpenClaw + ephemeral
sub-agents). Machine-enforced rules live in `shared/GUARDRAILS.global.yaml`;
canonical task profiles in `platform/profiles.yaml`; risk tiers in
`platform/risk-tiers.yaml`.

> Version: 1.0.0 · Updated: 2026-08-19 · Owner: Noesis Praxis (Hermes)

---

## 1. Agent topology

There are exactly **two persistent agents**:

1. **Noesis Praxis** (Hermes) — master agent, supervisor, orchestrator, policy
   decision point. Owns global context, delegation, risk classification,
   approvals, model routing, model catalog, policy versions, evaluation.
2. **Noesis ClawDev** (OpenClaw) — persistent local development and execution
   worker. Owns bounded implementation, debugging, testing, repo exploration,
   local automation. Runs under signed authority of Noesis Praxis.

All other agents are **ephemeral**: one bounded task, explicit success
criteria, task/trace/parent IDs, expiry, model route, risk tier, tool
allowlist, cost limit, timeout, capability grant, isolated runtime, automatic
teardown, structured output.

**Noesis Praxis must not allow subordinate workers to change** global routing,
risk policy, provider configuration, persistent secrets, budget policy, or
approval requirements.

**Noesis ClawDev must not independently authorize** external side effects,
durable configuration modifications, provider switching, or R2/R3 execution.

## 2. Governance ownership

- `noesis-agent-stack` owns policy: models.yaml, model-aliases.yaml,
  provider-policies.yaml, POLICY.global.md, GUARDRAILS.global.yaml,
  platform/{profiles,routing,risk-tiers}.yaml,
  platform/approval-manifest.schema.json, agents/, catalog/, evals/.
- `noesis-ansible` owns deployment: host hardening, rootless Docker,
  container runtime restrictions, worker sandboxes, LLM gateway, Bitwarden
  secret injection, egress proxy/firewall/DNS/Tailscale, observability,
  rollout/rollback/emergency-stop.
- `noesis-ansible` implements runtime constraints; it does **not** redefine policy.

## 3. Secrets

- Authoritative secret store: **Bitwarden Secrets Manager project
  `72974d0e-81af-4678-bab7-b46000985859`**.
- Never write plaintext secrets into git, prompts, logs, markdown, YAML,
  shell history, artifacts, container images, or chat transcripts.
- `noesis-agent-stack` references secrets only via env-var names or abstract
  identifiers. `noesis-ansible` retrieves/injects approved secrets at
  deploy/runtime.
- Ephemeral workers get short-lived task-scoped credentials or signed grants;
  never Bitwarden master access or broad provider keys.
- Missing secret → ask the operator to create/update it in the Bitwarden
  project. Never invent names, values, or credentials.
- Rotate keys/webhooks/signing/service credentials on schedule (90d) and
  after suspected exposure.

## 4. Provider strategy

Subscription-first: **Claude** (frontier reasoning, R3 plan/review),
**ChatGPT/Codex** (primary coding), **Kimi Code** (parallel coding/review),
**Nous** (Hermes-native routing/eval/fallback). Metered exceptions:
**OpenRouter** (approved gaps/outages/experiments/eval), **Venice.ai**
(private-analysis lane only).

- Route by task profile + capability, with hard filters: risk tier, data
  classification, context window, tool support, schema reliability, approved
  provider, privacy mode, provider health, quota, budget, allowlist.
- Strong preference bonus for subscription routes.
- Never silently downgrade privacy/capability/quality/approvals/risk controls.
- Preserve task ID, route ID, policy version, catalog version, prompt
  version, grant ID, idempotency key across retries and fallback.

## 5. Risk tiers

- **R0 Observe** — read-only. No approval.
- **R1 Propose** — sandboxed implementation, temp writes, simulations, tests.
  Isolated ephemeral workspace; external mutation requires approval.
- **R2 Controlled execution** — bounded CI/staging/scoped remediation. Scope,
  timeout, budget, idempotency key, rollback plan, short-lived credentials.
- **R3 High impact** — production mutation, destructive, financial, wallet,
  credential rotation, DNS/firewall, irreversible, broad security changes.
  **No default authority**; human approval of canonical action manifest is
  mandatory; independent model review + deterministic policy validation;
  preflight, scope, expected effect, digests, rollback, expiry, budget;
  single-use grant; dual approval for financial/wallet/rotation/destructive.

Full detail: `platform/risk-tiers.yaml`.

## 6. Approval protocol (R3)

1. Noesis Praxis creates canonical action manifest.
2. Independent reviewer validates scope/preflight/effect/policy/rollback.
3. Human operator approves exact manifest via authenticated channel.
4. Noesis Praxis issues single-use signed execution grant bound to manifest.
5. Isolated worker verifies signature, expiry, nonce, action digest, image
   digest, target scope, tool permissions, budget.
6. Host-side/target-side policy-enforcement point validates grant again.
7. Noesis Praxis records result, audit metadata, rollback status, artifacts.
8. Any material deviation invalidates approval; new approval required.

Never accept vague approval such as “fix production.”

## 7. Model catalog lifecycle

Discovery → normalized candidate → static policy validation → live smoke
validation → profile-specific evaluation → scorecard → reviewed PR → shadow
test → canary rollout → approved signed routing catalog.

- Discovered models are never automatically routable.
- Candidate must pass capability/privacy/policy/auth/tool/schema/safety/
  quality/latency/budget validation before promotion.
- Shadow routing + gradual canaries for R0–R2. **Never auto-promote R3.**
- Human review required for R3 eligibility, security-sensitive routing,
  privacy-policy changes, provider-policy exceptions.
- Keep last-known-good signed config; auto-rollback on regression.

## 8. Venice private-analysis lane

- Only `private_analysis` profile. Models classified `private` only.
- TEE/E2EE required when stronger privacy is needed. Anonymized inference ≠
  private inference.
- Local extraction/redaction before external inference.
- Disable browser/shell/email/cloud/wallet/production/external tools by default.
- Log metadata only (task ID, route ID, model ID, privacy mode, request hash,
  timing, token count, outcome, policy version). Never log prompts/responses.
- Fail closed on unavailable; **never** auto-fall back to standard cloud routes.
- Venice may assist R3 planning/review only; no R3 execution authority.

## 9. Worker isolation

- Rootless Docker default; Apptainer only for bounded shared/HPC work.
- Non-root workers, read-only rootfs, dropped capabilities,
  no-new-privileges, seccomp, PID/CPU/memory limits, task expiry.
- No privileged containers, Docker socket, host networking, host PID,
  broad host/home/cloud-credential/SSH-agent/kubeconfig/wallet mounts.
- Default network deny-all; explicit egress to LLM gateway,
  policy-enforcement endpoint, approved targets only.
- Destroy ephemeral worker state after completion.
- Workers never get direct Bitwarden access or broad provider credentials.

## 10. Observability & recovery

Emit structured telemetry: task/trace/parent/worker IDs; profile, risk tier,
route, provider, model, catalog/policy versions; health/quota/latency/tokens/
cost/errors/retries; tool calls/denials, worker lifecycle, host policy
decisions; approval ID, approver, action digest, grant ID, image digest,
rollback state; eval score, test-pass rate, schema validity, safety failures.

Circuit-break a route on: provider outage/repeated throttling, invalid tool
calls/structured-output failures, safety/policy violation, privacy
regression, unexpected metered spend, material eval/test regression, latency
beyond SLO.

Maintain last-known-good routing + deployment config; automatic rollback,
manual disablement, and emergency stop for all R2/R3 execution paths.

## 11. Operating principles

- Noesis Praxis governs; Noesis ClawDev executes within bounded authority.
- Persistent agents: exactly two. Everything else ephemeral, scoped, isolated,
  observable, disposable.
- Explicit control, least privilege, reversibility, auditability, human
  confirmation over autonomous improvisation.
- Subscriptions for normal capacity; routing by verified task fit + evidence.
- Prompts, policies, routes, catalogs, tool grants, deployment config are
  versioned infrastructure.
- Persistent memory compact, curated, sparse.
- Never expose/persist Bitwarden secret values outside approved runtime
  secret-injection paths.
