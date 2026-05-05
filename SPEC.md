# Concrete Repo and Spec Layout

This repository should be structured as a multi-agent platform repo, with shared personas, policies, models, and orchestration at the top level, and each agent or worker living in its own bounded directory with explicit contracts and operational files.[cite:3][cite:2] The Research design calls for a dedicated research profile with a structured vault and mode-based runtime, while the Subconscious design calls for a separate room-based profile with its own state, schedules, and guardrails rather than being folded into Main or Coder.[cite:92][cite:93]

## Top-level tree

```text
.
├── README.md
├── PLATFORMSPEC.md
├── HEARTBEAT.platform.md
├── WORKFLOWS.md
├── EVALS.platform.yaml
├── personas/
│   ├── SOUL.core.md
│   ├── SOUL.main-operator.md
│   ├── SOUL.evidence-operator.md
│   ├── SOUL.subconscious-houseguest.md
│   ├── SOUL.builder.md
│   ├── SOUL.auditor.md
│   └── SOUL.publisher.md
├── shared/
│   ├── tools.yaml
│   ├── models.yaml
│   ├── POLICY.global.md
│   ├── GUARDRAILS.global.yaml
│   ├── MEMORY.global.md
│   ├── memory/
│   │   ├── domain-knowledge.md
│   │   ├── api-conventions.md
│   │   ├── orchestration-patterns.md
│   │   └── incidents.md
│   └── schemas/
│       ├── evidence/
│       ├── handoffs/
│       ├── broker/
│       └── agent-cards/
├── agents/
│   ├── main-hermes/
│   ├── coder/
│   ├── qa/
│   ├── content/
│   ├── ops/
│   ├── treasury/
│   ├── research-openclaw/
│   └── subconscious-openclaw/
├── platform/
│   ├── orchestrator.yaml
│   ├── routing.yaml
│   ├── workflows/
│   │   ├── research-refresh.yaml
│   │   ├── subconscious-walk.yaml
│   │   ├── build-promotion.yaml
│   │   └── release-validation.yaml
│   └── registry/
│       ├── agents.yaml
│       └── capabilities.yaml
├── contracts/
│   ├── broker-api/
│   │   ├── openapi.yaml
│   │   ├── events.schema.json
│   │   ├── job.schema.json
│   │   └── artifact.schema.json
│   ├── handoffs/
│   │   ├── build-intent.schema.json
│   │   ├── build-plan.schema.json
│   │   ├── verify-handoff.schema.json
│   │   ├── content-handoff.schema.json
│   │   ├── ops-handoff.schema.json
│   │   └── treasury-handoff.schema.json
│   └── ledgers/
│       ├── findings.schema.json
│       ├── claims.schema.json
│       ├── sources.schema.json
│       ├── run-receipt.schema.json
│       └── signal-event.schema.json
├── workspace/
│   ├── shared-handoffs/
│   ├── main-state/
│   ├── research-vault/
│   ├── subconscious-room/
│   ├── coder-jobs/
│   └── qa-reports/
├── orchestration/
│   ├── broker/
│   │   ├── README.md
│   │   ├── SPEC.md
│   │   ├── config.yaml
│   │   ├── app/
│   │   ├── policies/
│   │   └── tests/
│   ├── schedules/
│   ├── health/
│   └── observability/
├── infra/
│   ├── docker/
│   ├── systemd/
│   ├── tailscale/
│   └── ansible/
├── docs/
│   ├── architecture/
│   ├── operations/
│   ├── decisions/
│   └── security/
└── .github/
    └── workflows/
```

This layout follows the platform and per-agent file conventions from the standards docs, while adding dedicated contract and workspace areas to reflect the evidence vault and Subconscious room patterns in your attached designs.[cite:3][cite:2][cite:92][cite:93]

## Per-agent layout

Each agent directory should keep a consistent internal structure so that identity, behavior, policy, memory, evaluations, and operations remain readable and auditable.[cite:3][cite:2] That consistency matters more in this project because Hermes-managed agents and OpenClaw workers need to interoperate without blurring authority boundaries.[cite:92][cite:93]

```text
agents/<agent-name>/
├── README.md
├── SPEC.md
├── systemprompt.md
├── MEMORY.md
├── agent.yaml
├── POLICY.md
├── GUARDRAILS.yaml
├── EVALS.yaml
├── RUNBOOK.md
├── HEARTBEAT.md
├── METRICS.md
├── memory/
├── evals/
├── logs/
├── state/
└── palace/
```

### Hermes-managed agents

Use this layout directly for `main-hermes`, `coder`, `qa`, `content`, `ops`, and `treasury` because those agents are execution and decision profiles whose primary role is orchestration, building, validation, or downstream action.[cite:92][cite:93] Their `agent.yaml` files should reference shared personas and models rather than embedding one-off identity rules in prompts.[cite:3][cite:2]

### OpenClaw workers

For `research-openclaw` and `subconscious-openclaw`, keep the same outer contract files, but also add worker-specific runtime directories because those agents need dedicated workspaces, schedules, and mode entrypoints.[cite:92][cite:93]

```text
agents/research-openclaw/
├── README.md
├── SPEC.md
├── SOUL.md
├── systemprompt.md
├── agent.yaml
├── POLICY.md
├── GUARDRAILS.yaml
├── EVALS.yaml
├── RUNBOOK.md
├── HEARTBEAT.md
├── METRICS.md
├── config/
│   ├── config.yaml
│   ├── collector-config.json
│   ├── source-registry.json
│   ├── source-weights.json
│   └── thresholds.json
├── skills/
│   └── research-agent-loop/
├── scripts/
│   ├── bootstrap.py
│   ├── refresh.py
│   ├── validate.py
│   ├── daily_summary.py
│   ├── midday_focus.py
│   ├── backup.py
│   ├── restore.py
│   └── recover.py
├── workspace/
│   └── research-vault/
├── state/
└── palace/
```

```text
agents/subconscious-openclaw/
├── README.md
├── SPEC.md
├── SOUL.md
├── systemprompt.md
├── agent.yaml
├── POLICY.md
├── GUARDRAILS.yaml
├── EVALS.yaml
├── RUNBOOK.md
├── HEARTBEAT.md
├── METRICS.md
├── config/
│   ├── config.yaml
│   ├── jobs.json
│   ├── thresholds.json
│   └── delivery.yaml
├── scripts/
│   ├── walk.py
│   ├── digest.py
│   ├── signal_filter.py
│   ├── board_rebuild.py
│   └── feedback_sync.py
├── room/
│   ├── walks/
│   ├── projects/
│   ├── notes/
│   ├── feedback/
│   ├── inbox-from-research/
│   ├── signal-log/
│   ├── signal-state/
│   ├── fascinations.md
│   └── lessons.md
└── state/
```

The Research worker needs a vault that preserves findings, claims, sources, dossiers, queues, health, and run receipts, while the Subconscious worker needs a room that preserves walks, signals, project states, retrospectives, and inbox snapshots from Research.[cite:92][cite:93]

## Workspace contracts

The most important implementation rule is to isolate write surfaces. Research writes to the vault, Subconscious writes to the room, Hermes Main writes approvals and decisions, and downstream agents consume approved handoffs rather than mutating upstream evidence directly.[cite:92][cite:93]

```text
workspace/
├── research-vault/
│   ├── context/
│   ├── config/
│   ├── dossiers/
│   ├── knowledge/
│   │   ├── findings.jsonl
│   │   ├── claims.jsonl
│   │   └── sources.jsonl
│   ├── raw/
│   ├── queue/
│   ├── notes/
│   ├── wiki/
│   ├── health/
│   ├── ops/
│   ├── decisions/
│   ├── runs/
│   └── indexes/
├── subconscious-room/
│   ├── walks/
│   ├── projects/
│   ├── notes/
│   ├── feedback/
│   ├── inbox-from-research/
│   ├── signal-log/
│   ├── signal-state/
│   ├── fascinations.md
│   └── lessons.md
├── shared-handoffs/
│   ├── build/
│   ├── verify/
│   ├── content/
│   ├── ops/
│   └── treasury/
├── memory-palace/
│   ├── wings/
│   ├── kg/
│   └── diary/
├── coder-jobs/
├── qa-reports/
└── main-state/
```

This prevents the common failure mode where a reflective or research agent becomes accidentally authoritative just because it can write into every other lane.[cite:92][cite:93]

## Agent contracts

Each agent should declare five contract layers: identity, scope, capabilities, write surfaces, and escalation rules.[cite:3][cite:2] In this project, those layers should be explicit because the design depends on keeping evidence, noticing, decision, and execution separate.[cite:92][cite:93]

### 1. Main Hermes contract

**Identity:** conscious operator and final routing authority.[cite:92][cite:93]

**Allowed inputs:**
- operator requests
- research briefs and dossiers
- subconscious signal boards and intent drafts
- downstream execution results and QA reports[cite:92][cite:93]

**Allowed outputs:**
- approvals and rejections
- plans
- delegations to coder, QA, content, ops, treasury
- routing updates and schedule changes[cite:92][cite:93]

**Forbidden actions:**
- direct promotion of weak claims without evidence review
- bypassing QA on gated workflows
- allowing Subconscious or Research to self-approve execution[cite:92][cite:93]

### 2. Research OpenClaw contract

**Identity:** evidence operator, not strategist, publisher, or executor.[cite:92]

**Allowed inputs:**
- bounded source plan
- prior vault state
- shared global memory
- operator interest profile[cite:92]

**Allowed outputs:**
- raw captures
- findings ledger
- claims ledger
- sources ledger
- dossiers
- operator brief
- handoff candidates
- health and validation artifacts[cite:92]

**Forbidden actions:**
- public publishing
- purchases or commitments
- touching secrets or wallets
- creating build tickets from weak or unresolved claims[cite:92]

### 3. Subconscious OpenClaw contract

**Identity:** houseguest / internal pattern-noticer with a room, not a production operator.[cite:93]

**Allowed inputs:**
- research inbox snapshots
- room memory
- lessons and retrospectives
- prior walks and board state[cite:93]

**Allowed outputs:**
- walk notes
- signal events
- signal board state
- build intents
- intent elaborations
- retrospectives and feedback artifacts[cite:93]

**Forbidden actions:**
- coding
- changing its own thresholds to force promotion
- touching secrets or auth surfaces
- directly approving or executing builds
- producing public content as if it were Main or Content[cite:93]

### 4. Coder contract

**Identity:** builder of approved work only.[cite:92][cite:93]

**Inputs:** approved plans, build handoffs, verified context.[cite:92]

**Outputs:** code, services, scripts, migration notes, implementation receipts.[cite:92]

**Forbidden actions:** self-starting from raw research or subconscious signals without Main approval.[cite:92][cite:93]

### 5. QA contract

**Identity:** auditor and release gate.[cite:92][cite:93]

**Inputs:** build artifacts, validation rules, evidence trails, release criteria.[cite:92]

**Outputs:** test results, audit reports, release gates, contradiction flags.[cite:92]

**Forbidden actions:** waiving evidence or release checks based only on agent confidence.[cite:92]

## Broker pattern

The broker should be the only service that Hermes uses to interact with OpenClaw workers. This keeps supervisor logic, worker lifecycle, and job execution separate, which is especially important because your system mixes long-lived Hermes profiles with specialized OpenClaw loops.[cite:92][cite:93]

### Broker responsibilities

- Register available workers and their capabilities.
- Accept typed jobs from Hermes.
- Route jobs to `research-openclaw` or `subconscious-openclaw`.
- Enforce timeouts, write-scope rules, and approval requirements.
- Return normalized status, logs, and artifact references.
- Emit events for observability and replay.[cite:92][cite:3]

### Broker service card

```yaml
name: hermes-openclaw-broker
role: control-plane
listen:
  host: 127.0.0.1
  port: 8787
workers:
  - research-openclaw
  - subconscious-openclaw
policies:
  require_job_id: true
  structured_events: true
  approval_gate_for_destructive: true
  artifact_indexing: true
```

## Broker API schema

A compact REST or MCP-exposed API is enough. The key requirement is typed payloads and immutable job IDs rather than prompt strings passed around ad hoc.[cite:92][cite:3]

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/jobs` | Submit a job to a worker |
| `GET` | `/v1/jobs/{job_id}` | Fetch current job status |
| `POST` | `/v1/jobs/{job_id}/cancel` | Cancel a running job |
| `GET` | `/v1/jobs/{job_id}/events` | Stream or fetch job events |
| `GET` | `/v1/jobs/{job_id}/artifacts` | List produced artifacts |
| `GET` | `/v1/workers` | List workers and capabilities |
| `GET` | `/v1/health` | Control-plane health |

### Submit job request

```json
{
  "job_id": "uuid",
  "worker": "research-openclaw",
  "mode": "refresh",
  "requested_by": "main-hermes",
  "correlation_id": "uuid",
  "priority": "normal",
  "timeout_s": 1800,
  "write_scope": [
    "workspace/research-vault"
  ],
  "read_scope": [
    "shared/",
    "workspace/research-vault/context",
    "workspace/research-vault/config"
  ],
  "input_artifacts": [
    "workspace/research-vault/context/interest-profile.json"
  ],
  "approval": {
    "required": false,
    "approved_by": null
  },
  "parameters": {
    "source_plan": "default",
    "max_sources": 5,
    "rebuild_operator_brief": true
  }
}
```

### Job status response

```json
{
  "job_id": "uuid",
  "worker": "research-openclaw",
  "mode": "refresh",
  "status": "completed",
  "started_at": "2026-05-05T12:00:00Z",
  "finished_at": "2026-05-05T12:11:42Z",
  "exit_code": 0,
  "health": "ok",
  "artifact_count": 6,
  "warnings": [
    "collector:rss:vendor-x marked stale"
  ],
  "summary": {
    "findings_written": 14,
    "claims_written": 5,
    "handoffs_created": 2
  }
}
```

### Worker card schema

```json
{
  "name": "subconscious-openclaw",
  "runtime": "openclaw",
  "modes": ["drift-from-research", "continue-project", "pure-tangent", "tend-the-room", "digest"],
  "read_scopes": [
    "workspace/subconscious-room",
    "workspace/research-vault/notes",
    "workspace/research-vault/queue"
  ],
  "write_scopes": [
    "workspace/subconscious-room"
  ],
  "emits": [
    "signal-events",
    "signal-board",
    "intent-drafts"
  ],
  "approval_required_for": [
    "build-promotion"
  ]
}
```

## Ledger schemas

The Research design requires at least three machine-readable ledgers: findings, claims, and sources, plus run receipts for replay and audit.[cite:92] The Subconscious design adds signal events and board state as distinct artifacts so thoughts are not conflated with approved tasks.[cite:93]

### `findings.schema.json`

```json
{
  "type": "object",
  "required": ["finding_id", "run_id", "source_ids", "timestamp", "topic_tags", "summary"],
  "properties": {
    "finding_id": {"type": "string"},
    "run_id": {"type": "string"},
    "source_ids": {"type": "array", "items": {"type": "string"}},
    "timestamp": {"type": "string", "format": "date-time"},
    "topic_tags": {"type": "array", "items": {"type": "string"}},
    "summary": {"type": "string"},
    "novelty": {"type": "number"},
    "relevance": {"type": "number"}
  }
}
```

### `claims.schema.json`

```json
{
  "type": "object",
  "required": ["claim_id", "derived_from", "status", "confidence", "statement"],
  "properties": {
    "claim_id": {"type": "string"},
    "derived_from": {"type": "array", "items": {"type": "string"}},
    "status": {"enum": ["candidate", "needs-verification", "verified", "rejected", "contradicted"]},
    "confidence": {"type": "number"},
    "statement": {"type": "string"},
    "contradiction_links": {"type": "array", "items": {"type": "string"}},
    "promotion_blocked": {"type": "boolean"}
  }
}
```

### `sources.schema.json`

```json
{
  "type": "object",
  "required": ["source_id", "url", "retrieved_at", "trust_tier", "freshness_status"],
  "properties": {
    "source_id": {"type": "string"},
    "url": {"type": "string"},
    "retrieved_at": {"type": "string", "format": "date-time"},
    "trust_tier": {"type": "string"},
    "freshness_status": {"enum": ["fresh", "aging", "stale", "degraded"]},
    "collector": {"type": "string"},
    "weight": {"type": "number"}
  }
}
```

### `signal-event.schema.json`

```json
{
  "type": "object",
  "required": ["signal_id", "walk_id", "project_slug", "signal_type", "score_delta"],
  "properties": {
    "signal_id": {"type": "string"},
    "walk_id": {"type": "string"},
    "project_slug": {"type": "string"},
    "signal_type": {"enum": ["commit", "friction", "excitement", "reuse", "mention", "return", "cooling"]},
    "score_delta": {"type": "number"},
    "evidence_refs": {"type": "array", "items": {"type": "string"}},
    "created_at": {"type": "string", "format": "date-time"}
  }
}
```

## Handoff schemas

The system should move downstream by handoff objects, not free-form summaries, because the source documents repeatedly emphasize routing cues, build intents, and approval gates.[cite:92][cite:93]

### Build intent

```json
{
  "intent_id": "uuid",
  "origin": "subconscious-openclaw",
  "project_slug": "import-lock-watcher",
  "intent_summary": "Watcher that flags imports outside trusted agent framework boundaries.",
  "why_alive": "Repeated return signal across multiple walks and reuse pressure from prior build notes.",
  "non_goals": ["Full dependency management", "Auto-remediation"],
  "constraints": ["Read-only analysis first", "No production enforcement without QA"],
  "status": "pendingintent"
}
```

### Build plan

```json
{
  "plan_id": "uuid",
  "derived_from_intent": "uuid",
  "approved_by": "main-hermes",
  "implementation_owner": "coder",
  "risk_level": "medium",
  "tasks": [
    "scaffold parser",
    "implement allowlist rules",
    "write tests",
    "prepare rollout note"
  ],
  "qa_required": true,
  "status": "pendingbuild"
}
```

### Verify handoff

```json
{
  "handoff_id": "uuid",
  "origin": "research-openclaw",
  "target": "qa",
  "claim_ids": ["claim-17", "claim-18"],
  "reason": "High-value infrastructure claim blocked by conflicting source trails.",
  "required_checks": ["source reconciliation", "freshness check", "contradiction review"],
  "status": "pending"
}
```

## Platform routing

The platform routing file should express the system as a graph with Main Hermes as supervisor, Research and Subconscious as specialized workers, and Coder/QA/Content/Ops/Treasury as downstream execution lanes.[cite:92][cite:93][cite:3]

```yaml
nodes:
  - main-hermes
  - research-openclaw
  - subconscious-openclaw
  - coder
  - qa
  - content
  - ops
  - treasury
edges:
  - from: main-hermes
    to: research-openclaw
    when: needs_external_evidence
  - from: research-openclaw
    to: main-hermes
    when: operator_brief_ready
  - from: research-openclaw
    to: subconscious-openclaw
    when: snapshot_ready
  - from: subconscious-openclaw
    to: main-hermes
    when: signal_board_updated
  - from: main-hermes
    to: coder
    when: plan_approved
  - from: coder
    to: qa
    when: build_complete
  - from: qa
    to: main-hermes
    when: gate_result_ready
```

## Memory Layer (MemPalace)

MemPalace is the platform's persistent semantic memory system, providing cross-session continuity and high-recall retrieval across all agent operations. It stores verbatim conversation history, structured knowledge, and temporal facts locally — zero cloud dependency.

### Palace structure

| Level | Description | Example |
|-------|-------------|---------|
| **Wings** | People or projects | `wing_platform`, `wing_research`, `wing_hermes` |
| **Rooms** | Specific topics within a wing | `auth-migration`, `redis-decision`, `broker-policy` |
| **Drawers** | Individual memory chunks | Verbatim text, findings, session transcripts |
| **Tunnels** | Cross-wing connections via shared room names | Same room bridging `wing_research` and `wing_main` |
| **Knowledge Graph** | Entity-relationship facts with time validity | `ProjectX` → `uses` → `PostgreSQL` |

### Agent interactions

| Agent | Interaction | Purpose |
|-------|-------------|---------|
| `main-hermes` | Queries on wake-up and before decisions | Retrieve prior decisions, operator preferences, project state |
| `research-openclaw` | Saves findings and dossiers | File evidence into wing/room taxonomy; link sources to KG |
| `subconscious-openclaw` | Saves signals and walk notes | Record pattern observations, fascinations, lessons |
| `coder` | Reads context | Pull relevant implementation decisions and constraints |
| `qa` | Reads context | Retrieve prior audit results, claim verification history |

### Write-back rules

- **Checkpoint saves:** Triggered at 15-minute intervals during long sessions to preserve incremental progress.
- **Pre-compact saves:** Emergency save before compaction or resource-constrained operations.
- **End-of-session saves:** Every agent calls a palace diary write on session end, recording what happened, what was learned, and what matters.
- **Knowledge graph updates:** When facts change, old triples are invalidated and new ones are added with timestamps.

### Broker integration

Jobs submitted through the broker may reference palace artifacts by drawer ID. The `artifact.schema.json` supports `palace_drawer_id` as a first-class artifact type, enabling workers to pass memory references instead of duplicating large verbatim content.

```json
{
  "artifact_type": "palace_drawer_ref",
  "palace_drawer_id": "drawer-uuid",
  "wing": "platform",
  "room": "routing-decisions",
  "retrieval_hint": "semantic search: 'broker timeout policy'"
}
```

## First files to write

The most valuable next files are:

1. `PLATFORMSPEC.md` as the source-of-truth architecture document for responsibilities, workflows, and boundaries.[cite:3][cite:2]
2. `platform/orchestrator.yaml` and `platform/routing.yaml` to codify the graph and workflows.[cite:3]
3. `agents/main-hermes/SPEC.md`, `agents/research-openclaw/SPEC.md`, and `agents/subconscious-openclaw/SPEC.md` because those three contracts define the spine of the entire system.[cite:92][cite:93]
4. `contracts/ledgers/*.schema.json` and `contracts/handoffs/*.schema.json` so artifacts become enforceable rather than aspirational.[cite:92][cite:93]
5. `orchestration/broker/openapi.yaml` so Hermes-to-OpenClaw control is typed and auditable.[cite:92]

## Recommended naming rule

Use Hermes profile names for decision and execution agents, and reserve OpenClaw worker names for the long-loop cognition workers. That keeps logs, routing, and approval paths legible, and it matches the system’s intended separation between conscious operation, evidence gathering, and subconscious noticing.[cite:92][cite:93]
