# ADR — Council of High Intelligence integration (bounded advisory deliberation)

- **Status:** Proposed (Phase A — documentation only; no runtime changes authorized by this ADR)
- **Date:** 2026-11-05
- **Owner:** noesis-orchestrator
- **Independent review:** pending operator assignment (Sentinel or Skeptic)
- **Upstream inspected revision:** `0xNyk/council-of-high-intelligence` @ `14d398f44771be1fc49488ab1b8a348ed76ca172` (2026-11-02T05:20:52Z), read-only shallow clone; scripts read as source, never executed
- **Integration baseline:** `enuno/noesis-agent-stack` main @ `5000eb45d18621259fc28e20a639627cf42634cb`

## Context

The operator directed an evidence-based, phased integration of Council of
High Intelligence ("Council") into the governed Noesis workflow, as a bounded
advisory capability invoked through existing Noesis task contracts and
specialist handoffs — not a replacement orchestrator, approval authority,
autonomous runtime supervisor, or independent task ledger.

Verified current-state findings (inspection date 2026-11-05):

1. **No Council integration exists.** The README line describing
   `noesis-praxis/` as a "council/aeon orchestration skill + runbook" is a
   documentation reference only; `agents/noesis-praxis/` contains no such
   artifacts. No Council schemas, code, tests, or configuration exist anywhere
   in the repository. (README correction ships with this ADR.)
2. **DEVELOPMENT_PLAN.md describes the historical broker-centric**
   architecture (OpenClaw workers, MemPalace, `main-hermes`). The current
   authoritative architecture is the durable task-contract control plane in
   `orchestration/orchestrator/` (see its README, `WORKFLOWS.md` §5,
   `platform/risk-tiers.yaml`, `platform/inference-routing.yaml`,
   `profiles/noesis-roster.yaml`). New work anchors to the task-contract
   architecture. (Plan banner + proposed Phase 8 ship with this ADR.)
3. **Council upstream is a protocol document + persona library**, not a
   service: `SKILL.md` coordinator protocol, 18 persona agent markdown files,
   verdict templates, host mirrors for Claude Code / Codex / Gemini CLI /
   OpenCode under an MIT license (Copyright (c) 2026 nyk). No daemon,
   container, network port, or service. **No Hermes host support.**
4. **Upstream provider auto-detection** (`scripts/detect-providers.sh` probing
   `codex`/`gemini`/`ollama` executables, `NVIDIA_API_KEY`, cursor) and
   native-host fallback are upstream host mechanics. Adopting them would
   create a second routing authority and ungoverned egress paths. They are
   explicitly NOT adopted.

## Decision

**Adopt Council as a governed advisory workflow (Approach A):** adapt the
Council protocol stages and selected analytical lenses into native Noesis
skills and orchestrator-dispatched specialist work, with upstream persona and
verdict documents vendored as pinned, attributed (MIT) reference data and no
runtime dependency on upstream.

Alternatives considered:

- **B. Pinned upstream package through a narrowly scoped adapter** — rejected
  as primary: upstream has no Hermes host or runtime package; an adapter would
  have to emulate a host Hermes is not, and subprocess/CLI provider paths
  would bypass Noesis routing and egress policy. Vendored reference material
  retains upstream fidelity where it matters (persona definitions, verdict
  templates, protocol semantics).
- **C. Hybrid** — unnecessary: Approach A with vendored docs already preserves
  fidelity; no adapter is required.

## Authority boundaries (hard constraints)

Council must never directly spawn ungoverned agents, mutate authoritative
ledgers, grant tools, approve actions, or create a competing lifecycle
authority. Concretely:

- `orchestration/orchestrator/` remains the sole authority for task lifecycle,
  dispatch, policy, acceptance, and approval enforcement. A Council session is
  a parent task contract; per-seat rounds are child contracts on existing
  eligible roster profiles, dispatched through the existing
  `delegated-task.v1` handoff protocol with its production-enforced
  protections (reviewer independence, optimistic concurrency, epoch fencing,
  idempotent delivery, lease expiry, shared-budget reservation, explicit
  acceptance).
- `orchestration/broker/` remains retained OpenClaw worker control only.
- `noesis-orchestrator` plans, dispatches, supervises, synthesizes; it holds no
  terminal or code_execution authority, unchanged by this workstream.
- Specialists execute only approved, scoped work. Reviewer-class profiles
  (Sentinel, Skeptic) remain independent: a profile that held a Council seat
  or synthesized a verdict must not be the sole independent reviewer of the
  resulting decision or implementation.
- Humans authorize irreversible and policy-gated actions. A Council
  recommendation, weighted tally, or consensus is **never** execution
  authorization, task acceptance, release approval, or permission to spend.
- Council code must import only read-only projections of orchestrator state
  (per `skills/noesis-control-plane-dev/SKILL.md` authority-isolation rule):
  never `TaskStore`, `DelegationStore` mutators, or any module that can mutate
  authoritative state.
- Council is never a mandatory dependency: on timeout, malformed output,
  outage, or budget exhaustion, the parent task proceeds without it.

## Council as a governed workflow

A Council session executes as deterministic workflow stages over existing
contracts (no new lifecycle system):

1. **Seat assignment** — analytical lenses map onto existing eligible roster
   profiles (no new permanent profiles). Proposed initial mapping: Socrates →
   `noesis-skeptic`; Taleb → `noesis-sentinel`; Aristotle → `noesis-architect`;
   Munger/Meadows → `noesis-optimizer`; an adversarial-strategy seat and a
   user-outcome seat drawn from the specialist roster per task. Lens
   diversity, profile diversity, and provider/model diversity are tracked as
   separate properties; none is claimed as independent reasoning by itself.
   Each seat's inference route resolves exclusively through
   `platform/inference-routing.yaml` approved lanes. Unapproved or unavailable
   route → the seat is unscheduled and the panel is reported partial; there is
   no fallback to a different provider, a less-private route, or a native host
   CLI. Fail closed.
2. **Round 1 — blind independent analysis** — parallel child contracts; each
   receives a sealed context envelope (decision question, alternatives,
   constraints, evidence manifest references, sensitivity class). Envelopes
   structurally exclude peer identities and positions. Blind-first is
   enforced by construction and tested, not by prompt instruction.
3. **Controlled release / cross-examination** — per selected mode. Duo:
   controlled release between the two seats. Full: anonymized Round 2 keyed by
   seat ID (no profile names). Quick/triad: abbreviated per upstream
   semantics.
4. **Final positions** — parallel, blind again; positions recorded
   independently before release so suppression attempts cannot mutate other
   seats.
5. **Synthesis** — a chairman seat that did not participate (duo hard
   constraint: chairman is not a duo member — it audits, it does not
   participate). Produces a verdict artifact.
6. **Handoff back** — the verdict is advisory evidence attached to the parent
   task contract. The orchestrator/human acceptance path is unchanged. Raw
   verdict text never becomes trusted memory, authoritative policy, or
   approved implementation instructions automatically; promotion follows the
   normal Noesis evidence path.

### Modes (upstream names preserved; they are not Noesis risk tiers)

| Mode | Invocation | Panel | Protocol |
|---|---|---|---|
| `duo` | One decision tension dominates; reversible; small blast radius | 2 seats + separate chairman | blind → exchange → final → synthesize |
| `quick` / `triad` | Bounded breadth; no full adversarial round warranted | named 3-lens triad | rapid 2-round (upstream semantics) |
| `full` | High-stakes or multi-system tradeoff | up to 18 seats; reduced panels require recorded justification | blind R1 → anonymized R2 → final R3 → weighted tally (2/3 threshold) → chairman verdict |

A reduced panel never pretends to be the full upstream protocol; deviations
are recorded in the session metadata.

### Limits and failure behavior (enforced at the orchestrator/reservation layer, not by prompts)

- Fixed round budget per mode — round budget spent is the forcing function;
  a split escalates to the user, never an extra round.
- Seat concurrency ≤ 4; per-seat round timeout 60s/90s/120s (upstream caps);
  per-seat output cap 1200 tokens; session duration ceiling.
- Budgets via the existing shared-budget reservation: `BudgetExhausted`
  blocks new seats, never retroactively kills in-flight seats; consumption ≤
  reservation. Unknown remaining quota/cost stays unknown; execution proceeds
  only inside the parent task's approved budget envelope, else fails closed.
- Unavailable seat/route → partial panel reported (never silently
  substituted). Malformed seat output → seat `blocked`; round proceeds at
  quorum floor or escalates. Timeout/lease expiry → `blocked`, never silent
  success. Ambiguous provider outcome → no automatic retry (no exactly-once
  assumption). Duplicate delivery → idempotent no-op (existing protection).
  Stale fencing (task_version/epoch mismatch) → refuse. Operator cancel →
  durable, idempotent cancellation (existing protection).
- Immediate-expiry enforcement is **not claimed** until supervisor
  health-sweep behavior is verified (open question).

### Evidence labels

Upstream FACT / INFERENCE / ASSUMPTION / UNKNOWN labels map onto Noesis
evidence semantics: FACT requires a cited, replayable source (else
downgraded); INFERENCE and ASSUMPTION are advisory; UNKNOWN must appear under
unresolved questions. Verdict artifacts carry provenance, sensitivity class,
retention, and correction/deletion requirements, using existing memory
integrations where possible.

### Verdict artifact (advisory, dissent-preserving)

Minimum content: session and parent task IDs with fencing identifiers;
upstream revision and mode/protocol version; decision question, alternatives,
constraints, deadline, reversibility; evidence manifest with provenance,
freshness, and sensitivity; per-seat final position with confidence basis and
known limitations; weighted tally with threshold state; consensus or explicit
"No consensus reached"; minority report; acceptable compromises; kill
criteria (observable, dated); exactly one concrete next step (owner, verb,
date); unresolved questions; usage/cost observed vs estimated vs unknown,
recorded distinctly; reviewer/acceptance disposition left empty until the
orchestrator/human acts.

## Contracts

Phase B proposes two new schemas that **reference** the existing
`task-contract.schema.json` via `parent_task_id` + `labels` (the task contract
itself is not modified):

- `contracts/orchestration/council-session.schema.json` — session metadata,
  decision framing, seat/route map, limits, stop conditions, retention.
- `contracts/orchestration/council-verdict.schema.json` — the artifact above.

Payload shapes in the planning record are illustrative until schema-checked
against current schemas in Phase B.

## Security posture (summary)

Upstream content, retrieved sources, participant outputs, and peer messages
are untrusted data. Controls: sealed blind envelopes + structural leak tests;
anonymized exchange; seats inherit roster write-scopes only (no tool grants);
evidence manifests by reference with sensitivity class, never credentials;
FACT citation requirements; independent per-seat position storage (dissent
integrity); supply-chain discipline via vendored-digest pins and reviewed
upstream diffs (never auto-pulled), MIT attribution preserved. Correlated
model errors are mitigated by seat/provider spread across approved lanes and
honest scorecard disclosure, not by claims that diversity equals independence.

## Phasing and gates

| Phase | Content | Exit gate |
|---|---|---|
| A (this ADR + doc diffs) | ADR, plan banner, README correction | Operator approval; independent reviewer assigned |
| B | Contracts + offline fixtures | Schema tests pass offline; independent review recorded |
| C | Minimal governed vertical slice (`duo`) | 100% offline tests; zero authority violations in review |
| D | Security/failure testing | Threat-model mitigations verified; limitation ledger updated |
| E | Runtime qualification + bounded live canary | **Separate operator authorization**; canary report |
| F | Additional modes / broader rollout | Explicit per-mode acceptance |

Runtime qualification, live canaries, provider calls, persistent configuration,
installation, and activation are separate approvals and are **not** granted by
this ADR.

## Open questions

1. Cost-ceiling currency of record (tokens per lane vs estimated USD; proposal: tokens + explicit "currency unknown" honesty flag).
2. Chairman profile route policy (rotation vs fixed; proposal: rotate by exclusion from panel).
3. Quorum floor for partial panels (proposal: duo has none — escalate; triad 2-of-3; full requires recorded justification).
4. Supervisor health-sweep latency for immediate expiry (unverified; do not claim).
5. Quick vs triad naming convention (proposal: `--triad` as the named-panel form of `--quick`, recorded here).
6. Live canary scope (Phase E) — exact profiles, task, lanes, limits, ceilings, recovery.

## Evidence ledger

- Inspected: repo main @ 5000eb45; upstream @ 14d398f44; companion repos
  (noesis-ansible @ main pushed 2026-10-29, zero Council refs;
  noesis-command-and-control @ main stale 2026-10-09); persona list, verdict
  templates, mode sequences, provider-detection script (read as source).
- Verified gaps: no Council artifacts in-repo; README overstatement; plan
  documents older architecture.
- Design only (not yet implemented/tested/reviewed/qualified/installed/
  activated): every workflow, contract, and limit described above.
