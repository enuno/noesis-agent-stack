DOC: Hermes Supervisor Profile

AUDIENCE: Platform operators, systems engineers, and anyone responsible for running or debugging the Noesis agent stack.

---

# Hermes — Supervisor Profile (`main-hermes`)

> **Role:** Supervisor / Coordinator  
> **Agent ID:** `main-hermes`  
> **Stack position:** Apex. The only persistent reasoning layer in the Noesis stack.

Hermes is the strategic brain of the Noesis agent stack. It plans, delegates, monitors, interprets results, manages risk, and surfaces decisions to the human operator when required. All other workers — `research-openclaw` and `subconscious-openclaw` — are stateless and ephemeral. Hermes is the only agent that interacts with the human operator and the only agent authorized to issue broker jobs.

For Hermes's identity, values, and personality, see [SOUL.md](./SOUL.md).  
For the authoritative system prompt and operating loop, see [systemprompt.md](./systemprompt.md).

---

## QUICK START

1. **Ensure the broker is running.** Hermes submits all work through the broker control plane (`orchestration/broker/`). No ad-hoc worker calls.
2. **Verify MemPalace is reachable.** Hermes queries palace context before approving or delegating. See `agents/main-hermes/tools/palace_query.py`.
3. **Check `workspace/hermes/` exists.** This is Hermes's private working memory. If it is missing, create the tree shown below and ensure the process has read/write access.
4. **Start a planning cycle.** Hermes runs on a default 6-hour schedule and on-demand when the operator sends a message. The first cycle will assess vault health, check for signal events, and propose next actions.

---

## Stack Position

```
┌─────────────────────────────────────┐
│  Human Operator                     │
│  (founder, final authority)         │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Hermes (main-hermes)               │
│  - plans, approves, escalates       │
│  - issues broker jobs               │
│  - maintains sprint state           │
│  - owns decision log + cost ledger  │
└─────────────┬───────────────────────┘
              │ broker jobs (typed payloads)
┌─────────────▼──────────┬────────────┐
│ research-openclaw      │ subconscious-openclaw
│ - evidence collection  │ - pattern walks
│ - vault writes         │ - signal events
│ - build intents        │ - intent drafts
└────────────────────────┴────────────┘
```

Key boundary: Hermes **reads** the research vault and subconscious room; it **never writes** to them directly. Workers write their own artifacts. Hermes writes only to `workspace/hermes/`.

---

## Directory Layout

```
agents/main-hermes/
├── README.md           ← this file
├── SPEC.md             ← functional specification
├── POLICY.md           ← operational policy and authority matrix
├── RUNBOOK.md          ← operator procedures
├── SOUL.md             ← identity, values, personality
├── systemprompt.md     ← authoritative system prompt
├── GUARDRAILS.yaml     ← safety constraints (Phase 2 deliverable)
├── agent.yaml          ← agent contract and capabilities manifest
└── tools/
    └── palace_query.py ← MemPalace query interface
```

Hermes runtime working memory:

```
workspace/hermes/
├── plans/              ← current and historical planning documents
├── sprint-state.json   ← active sprint, sprint lock status, build intent ref
├── decision-log.jsonl  ← every significant decision with rationale and timestamp
├── cost-ledger.jsonl   ← running cost accounting across all jobs
└── signal-inbox/       ← unacknowledged signal events pending review
```

---

## Operating Cycle

Hermes runs a 7-step loop on a configurable schedule (default: every 6 hours) and on-demand:

1. **ASSESS** — Read latest run receipts and health reports. Check for signal events. Evaluate vault freshness. Check sprint state.
2. **PLAN** — Determine what needs to happen next (refresh, signal processing, build intent approval, release gate follow-up).
3. **AUTHORIZE** — For each planned action, decide whether it requires human approval. If yes, present a concise summary and wait.
4. **DISPATCH** — Issue broker jobs for approved actions. One job per worker type per cycle unless a critical signal warrants parallel dispatch.
5. **MONITOR** — Track job status via callback receipts. On timeout or failure: retry once, then escalate.
6. **INTERPRET** — Read findings and health reports. Update sprint state. Approve or reject build intents. Surface key findings to the operator.
7. **ESCALATE** — If health is `critical`, a build intent is blocked, costs are overrunning, or a finding is speculative with high signal value, notify the operator immediately.

See [systemprompt.md](./systemprompt.md) for full details on authorities, dispatch defaults, build intent lifecycle, and safety invariants.

---

## Sprint Model

A **sprint** is the period during which a specific build intent is active. Sprints are not time-boxed by calendar — they end when the build intent is either completed or abandoned.

- **During a sprint:** A sprint lock is active on the subconscious room. New `research-openclaw` jobs are not dispatched unless a `critical` or `high` severity signal demands it. `subconscious-openclaw` runs in `drift-from-research` mode. Hermes surfaces progress in every planning cycle summary.
- **Between sprints:** Normal research refresh cycle runs on schedule. `subconscious-openclaw` runs `digest` and `pattern-walk` modes. Hermes evaluates vault health and identifies candidate topics for the next build intent.

---

## Interfaces

| Interface | Purpose | Target |
|---|---|---|
| Broker job submission | Dispatch work to workers | `POST /v1/jobs` on broker |
| Artifact consumption | Read worker outputs | `workspace/research-vault/`, `workspace/subconscious-room/` |
| Palace query | Retrieve job history, KG context, diaries | `agents/main-hermes/tools/palace_query.py` |
| Human operator channel | Escalations, approvals, status summaries | Configured operator endpoint |

---

## PREREQUISITES

- Broker control plane is running and reachable (`orchestration/broker/`).
- MemPalace memory layer is initialized (`workspace/mempalace/`).
- `workspace/hermes/` directory exists with write permissions.
- Hermes has read access to `workspace/research-vault/` and `workspace/subconscious-room/`.
- Hermes does **not** have write access to worker write surfaces (enforced by broker scopes and filesystem permissions).

---

## VALIDATION

- [ ] `agents/main-hermes/systemprompt.md` is loaded into the supervisor runtime.
- [ ] `agents/main-hermes/GUARDRAILS.yaml` is present and parsed without error.
- [ ] `workspace/hermes/` contains `sprint-state.json`, `decision-log.jsonl`, and `cost-ledger.jsonl`.
- [ ] Broker `/v1/health` returns `200 OK`.
- [ ] MemPalace query tool returns expected taxonomy and KG stats.

---

## RELATED

- [SOUL.md](./SOUL.md) — Identity, core values, and personality
- [systemprompt.md](./systemprompt.md) — Authoritative system prompt and authorities
- [SPEC.md](./SPEC.md) — Functional specification
- [POLICY.md](./POLICY.md) — Authority matrix, cost controls, safety invariants
- [RUNBOOK.md](./RUNBOOK.md) — Step-by-step operator procedures
- `DEVELOPMENT_PLAN.md` — Phase 2 deliverables and exit criteria
- `WORKFLOWS.md` — Typed workflow definitions and state transitions
- `orchestration/broker/README.md` — Broker control plane
- `contracts/handoffs/broker-job.schema.json` — Job payload schema

---

## CHANGELOG

| Date | Change |
|---|---|
| Phase 2 | Initial supervisor profile documentation set. |