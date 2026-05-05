# Development Plan

This development plan turns the platform specification into a build sequence for a Hermes-supervised, OpenClaw-backed multi-agent system. It assumes Hermes remains the conscious operator and final routing authority, while Research and Subconscious run as bounded OpenClaw worker profiles behind a broker control plane.[cite:126]

## Objectives

- Stand up a repo that cleanly separates supervisor logic, worker runtimes, contracts, and workspace state.[cite:126]
- Preserve the authority boundary between evidence collection, reflective signal generation, approval, implementation, and validation.[cite:126]
- Build the platform in a way that is observable, reversible, and safe to expand toward ops, treasury, and content agents later.[cite:126]

## Delivery principles

- Hermes is the only final routing and approval authority for cross-agent work.[cite:126]
- Research writes to the vault, Subconscious writes to the room, and downstream agents consume approved handoffs rather than mutating upstream evidence directly.[cite:126]
- The broker is the only service allowed to manage OpenClaw workers, their jobs, and their runtime lifecycle.[cite:126]
- Every major artifact should be typed, replayable, and auditable through schemas, ledgers, and run receipts.[cite:126]

## Phased roadmap

| Phase | Goal | Primary outputs |
|---|---|---|
| 0 | Repo scaffold and contracts | Base tree, top-level specs, shared policies, initial schemas |
| 1 | Broker control plane | Broker service skeleton, worker registry, job API, health endpoints |
| 2 | Hermes supervisor profile | `main-hermes` contract, routing rules, approval logic, workflow bindings |
| 3 | Research worker slice | `research-openclaw` profile, vault, refresh scripts, ledgers |
| 4 | Subconscious worker slice | `subconscious-openclaw` profile, room, walk and signal pipeline |
| 5 | Builder and QA lanes | `coder` and `qa` contracts, handoff schemas, validation workflow |
| 6 | Observability and hardening | Metrics, logs, traces, alerts, replay tooling, security controls |
| 7 | Expansion lanes | content, ops, treasury, richer schedules, operator UX |

## Phase 0: repo scaffold

Create the repository structure first so identity, policy, contracts, and workspace boundaries exist before any automation starts. The target tree should follow the platform layout already defined in the spec, including `agents/`, `platform/`, `contracts/`, `workspace/`, `orchestration/`, `infra/`, and `docs/`.[cite:126]

### Deliverables

- `README.md`
- `PLATFORMSPEC.md`
- `HEARTBEAT.platform.md`
- `WORKFLOWS.md`
- `EVALS.platform.yaml`
- `shared/` with global policy, guardrails, memory, models, and schemas
- `contracts/` with broker, handoff, and ledger schema placeholders
- `workspace/` with isolated write surfaces

### Exit criteria

- Repo tree matches the platform spec.[cite:126]
- Shared policy and schema directories exist and are versioned.[cite:126]
- Workspace boundaries are documented before code execution begins.[cite:126]

## Phase 1: broker control plane

Implement the broker before worker logic so Hermes never talks to OpenClaw runtimes through ad hoc shell calls. The broker should register workers, accept typed jobs, enforce timeouts and write scopes, return normalized job state, and emit structured events for observability and replay.[cite:126]

### Deliverables

- `orchestration/broker/README.md`
- `orchestration/broker/SPEC.md`
- `orchestration/broker/config.yaml`
- Broker app skeleton under `orchestration/broker/app/`
- Broker tests under `orchestration/broker/tests/`
- `contracts/broker-api/openapi.yaml`
- `contracts/broker-api/job.schema.json`
- `contracts/broker-api/events.schema.json`
- `contracts/broker-api/artifact.schema.json`

### Initial API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/jobs` | Submit a typed job to a worker |
| `GET` | `/v1/jobs/{job_id}` | Fetch job status |
| `POST` | `/v1/jobs/{job_id}/cancel` | Cancel a running job |
| `GET` | `/v1/jobs/{job_id}/events` | Stream or fetch events |
| `GET` | `/v1/jobs/{job_id}/artifacts` | List job artifacts |
| `GET` | `/v1/workers` | List workers and capabilities |
| `GET` | `/v1/health` | Control-plane health |

### Exit criteria

- Broker accepts and validates typed requests against schemas.[cite:126]
- Job IDs, correlation IDs, read scopes, and write scopes are enforced.[cite:126]
- Worker registry and health endpoints are operational.[cite:126]

## Phase 2: Hermes supervisor profile

Stand up `agents/main-hermes/` as the conscious operator and final routing authority. This profile owns approvals, rejections, plans, schedule changes, and delegations to builder, QA, content, ops, treasury, and the OpenClaw worker lanes.[cite:126]

### Deliverables

- `agents/main-hermes/README.md`
- `agents/main-hermes/SPEC.md`
- `agents/main-hermes/systemprompt.md`
- `agents/main-hermes/agent.yaml`
- `agents/main-hermes/POLICY.md`
- `agents/main-hermes/GUARDRAILS.yaml`
- `agents/main-hermes/RUNBOOK.md`
- `platform/orchestrator.yaml`
- `platform/routing.yaml`
- First-pass workflow definitions in `platform/workflows/`

### Core features

- Approval and escalation rules
- Delegation routing
- Workflow state transitions
- Handoff validation before execution
- Human-override hooks for destructive or high-risk actions

### Exit criteria

- Hermes can submit broker jobs with typed payloads.[cite:126]
- Hermes can consume worker artifacts without directly mutating worker state.[cite:126]
- Routing and approval rules reflect the contract boundaries in the spec.[cite:126]

## Phase 3: Research worker slice

Build `research-openclaw` as the evidence operator, not as a strategist or executor. Its responsibility is to collect, normalize, validate, and preserve findings, claims, sources, dossiers, briefs, and run receipts in the research vault.[cite:126]

### Deliverables

- `agents/research-openclaw/` contract files
- `agents/research-openclaw/config/` with collector and threshold configs
- `agents/research-openclaw/scripts/` including `bootstrap.py`, `refresh.py`, `validate.py`, `daily_summary.py`, `midday_focus.py`, `backup.py`, `restore.py`, `recover.py`
- `workspace/research-vault/` substructure
- Ledger schemas for findings, claims, sources, and run receipts

### First working loop

1. Hermes submits a `research-openclaw` refresh job through the broker.[cite:126]
2. Research reads bounded context and source plans.[cite:126]
3. Research writes new ledger entries and operator artifacts to the vault.[cite:126]
4. Broker returns normalized job status and artifact references to Hermes.[cite:126]

### Exit criteria

- Research writes only within `workspace/research-vault/`.[cite:126]
- Findings, claims, and sources are machine-readable and replayable.[cite:126]
- Run receipts support audit and failure recovery.[cite:126]

## Phase 4: Subconscious worker slice

Build `subconscious-openclaw` as the internal pattern-noticer with its own room, not as a production operator. It should consume research inbox snapshots and room memory, generate walks and signal events, maintain a signal board, and draft build intents without approving or executing them.[cite:126][cite:93]

### Deliverables

- `agents/subconscious-openclaw/` contract files
- `agents/subconscious-openclaw/config/` with jobs, thresholds, and delivery rules
- `agents/subconscious-openclaw/scripts/` including `walk.py`, `digest.py`, `signal_filter.py`, `board_rebuild.py`, `feedback_sync.py`
- `workspace/subconscious-room/` or the equivalent room structure from the spec
- `contracts/ledgers/signal-event.schema.json`

### First working loop

1. Hermes or a schedule triggers a walk mode through the broker.[cite:126][cite:93]
2. Subconscious reads research inbox snapshots, lessons, and prior walks.[cite:126][cite:93]
3. Subconscious writes walk notes, signal events, board state, and intent drafts into its room.[cite:126][cite:93]
4. Hermes reviews build signals but remains the only approval authority.[cite:126]

### Exit criteria

- Subconscious cannot code, self-approve, or alter its own thresholds to force promotion.[cite:126]
- Signal events and board states are persisted distinctly from approved jobs.[cite:126][cite:93]
- Research and Subconscious remain isolated by write surface.[cite:126]

## Phase 5: Builder and QA lanes

Once Hermes, broker, Research, and Subconscious are stable, add `coder` and `qa` as explicit downstream profiles. Coder should only build from approved plans and handoffs, while QA serves as the release gate with validation reports, contradiction checks, and release decisions.[cite:126]

### Deliverables

- `agents/coder/` contract set
- `agents/qa/` contract set
- `contracts/handoffs/build-intent.schema.json`
- `contracts/handoffs/build-plan.schema.json`
- `contracts/handoffs/verify-handoff.schema.json`
- `workspace/coder-jobs/`
- `workspace/qa-reports/`
- `platform/workflows/build-promotion.yaml`
- `platform/workflows/release-validation.yaml`

### Exit criteria

- Raw research output and raw subconscious signal cannot directly trigger builds.[cite:126]
- Coder only receives approved handoffs from Hermes.[cite:126]
- QA can block release progression based on evidence and validation status.[cite:126]

## Phase 6: observability and hardening

Add platform-wide telemetry and operational controls after the first end-to-end slice is working. This phase should make the system inspectable, measurable, and safe under failure conditions rather than merely functional.[cite:126]

### Deliverables

- `orchestration/observability/` assets for logs, metrics, dashboards, and traces
- `orchestration/health/` probes and health summaries
- replay tooling for broker events and receipts
- alert rules for stuck jobs, stale workers, failed validations, and broken schedules
- security docs under `docs/security/`
- operational runbooks under `docs/operations/`

### Controls to add

- Structured event logging
- OpenTelemetry or equivalent tracing across Hermes, broker, and workers
- Prometheus metrics for job counts, durations, failures, retries, and queue depth
- Circuit breakers and manual stop controls
- Secret scoping and credential isolation
- Artifact indexing and retention policy

### Exit criteria

- Every job has an event trail and artifact index.[cite:126]
- Failed runs can be replayed or diagnosed from receipts and logs.[cite:126]
- Operators can stop, retry, quarantine, or downgrade workflows safely.

## Phase 7: expansion lanes

After the core loop is stable, expand into content, ops, and treasury profiles using the same contract-first pattern. These lanes should consume typed handoffs, maintain isolated write surfaces, and inherit the same approval, QA, and observability controls used by the initial platform slice.[cite:126]

### Deliverables

- `agents/content/`
- `agents/ops/`
- `agents/treasury/`
- handoff schemas for content, ops, and treasury
- schedule definitions for recurring workflows
- docs and ADRs for each new lane

## Recommended build order

1. Scaffold repo and shared schemas.
2. Implement broker contracts and service skeleton.
3. Stand up Hermes profile and routing.
4. Deliver the Research vertical slice.
5. Deliver the Subconscious vertical slice.
6. Add Coder and QA gating.
7. Add observability, hardening, and additional lanes.

This ordering keeps authority, evidence, and worker lifecycle constraints in place before more autonomous behavior is introduced.[cite:126]

## Milestones

| Milestone | Description | Success signal |
|---|---|---|
| M1 | Repo and contracts scaffolded | Tree, schemas, and workspace boundaries committed |
| M2 | Broker operational | Hermes can submit and inspect typed jobs |
| M3 | Hermes routing live | Supervisor can approve and delegate through workflows |
| M4 | Research vertical slice complete | Refresh run produces vault artifacts and receipts |
| M5 | Subconscious vertical slice complete | Walk run produces board state and intent drafts |
| M6 | Build gate complete | Approved plan reaches Coder and QA through typed handoffs |
| M7 | Ops-ready platform | Metrics, logs, alerts, and runbooks in place |

## Risks and controls

| Risk | Impact | Control |
|---|---|---|
| Worker authority creep | Research or Subconscious starts acting like a decision-maker | Enforce write scopes, approval gates, and explicit forbidden actions.[cite:126] |
| Prompt-level orchestration drift | Hermes bypasses broker with ad hoc runtime calls | Make broker the sole worker control plane.[cite:126] |
| Weak evidence promotion | Claims reach implementation without enough validation | Typed ledgers, QA gates, and Main approval only.[cite:126] |
| State contamination | Agents overwrite one another’s memory or artifacts | Isolated workspaces and handoff-only downstream flow.[cite:126] |
| Poor replayability | Failures cannot be debugged or audited | Run receipts, structured events, and artifact indexing.[cite:126] |

## First sprint recommendation

The first sprint should target a narrow but real end-to-end path: Hermes submits a `research-openclaw` refresh job through the broker, the worker writes findings and run receipts to the research vault, Hermes receives the resulting artifacts, and the system exposes job status through the broker API.[cite:126] This path validates the control plane, workspace isolation, schema discipline, and supervisor-to-worker pattern before more complex reflective or build workflows are added.[cite:126]

## Definition of done

The platform should be considered ready for broader development once the broker is the only worker control plane, Hermes can supervise typed jobs, Research and Subconscious have isolated write surfaces, approved handoffs are required for build execution, and observability is good enough to replay failures and inspect agent behavior.[cite:126][cite:93]
