# HEARTBEAT — Platform Save Cadence and Trigger Protocol

> Platform-level save discipline derived from the agent HEARTBEAT pattern. Every save is typed, trigger-bound, and auditable so the system can recover or replay from any point without reconstructing state from chat logs or ad hoc notes.

## Purpose

Define when the platform MUST persist state, what MUST be included in each save, and which component owns the trigger. This applies across broker jobs, MemPalace receipts, workspace artifacts, agent diaries, and workflow transitions.

## Save types

### 1. Checkpoint save (`TYPE: checkpoint`)

| Field | Value |
|---|---|
| **Trigger** | Every 15 exchanges (turns) between any two platform actors, or every 15 broker job state transitions, whichever comes first |
| **Owner** | Broker event hook writes receipt; MemPalace hook writes drawer; Hermes writes diary entry if Main is involved |
| **Scope** | Job state, artifact references, correlation IDs, room/vault deltas since last checkpoint |
| **Format** | `checkpoint-<timestamp>-<exchange_count>.json` in job events stream; drawer in `broker/jobs/<job_id>/checkpoints/` |
| **Retention** | Last 20 checkpoints per active job; compacted to a single baseline after job completion |
| **Recovery use** | Resume a job from the most recent checkpoint if the worker fails or times out |

**Contents required**
- `exchange_count`: monotonic turn counter for the session or job
- `job_id` and `correlation_id`
- `read_scopes` and `write_scopes` active at this point
- `artifact_checksums` for all files written since last checkpoint
- `agent_state_hash`: opaque hash of any in-memory worker state that cannot be reconstructed from artifacts alone
- `timestamp_utc` and `ttl` if the checkpoint is time-bounded

### 2. Pre-compact save (`TYPE: pre_compact`)

| Field | Value |
|---|---|
| **Trigger** | Before any compaction, merge, archive, or deduplication operation that would mutate or delete prior state |
| **Owner** | The component performing compaction (broker, MemPalace janitor, or agent cleanup script) |
| **Scope** | Full snapshot of the region about to be compacted, plus the compaction plan |
| **Format** | `precompact-<timestamp>-<region>.tar` or equivalent archive; receipt drawer in `broker/jobs/<job_id>/compactions/` |
| **Retention** | Until the next successful checkpoint after compaction, or 7 days, whichever is longer |
| **Recovery use** | Roll back a bad compaction; audit what was removed or merged |

**Contents required**
- `region`: wing/room path, job ID range, or workspace directory being compacted
- `compaction_plan`: what will be merged, deleted, deduplicated, or re-indexed
- `snapshot_manifest`: checksums of every item before compaction
- `operator_approval`: null if automated; `approved_by` if human override required by policy

### 3. End-of-session save (`TYPE: eos`)

| Field | Value |
|---|---|
| **Trigger** | Session or job reaches terminal state (`completed`, `failed`, `cancelled`, `rejected`); OR Hermes Main explicitly closes a routing window |
| **Owner** | Broker writes final receipt; worker writes final artifacts; MemPalace writes terminal drawer; Hermes writes closing diary entry |
| **Scope** | Complete artifact set, final job state, all checkpoints merged, handoff eligibility verdict |
| **Format** | `eos-<timestamp>-<job_id>.json` in job events; terminal drawer in `broker/jobs/<job_id>/terminal/` |
| **Retention** | Indefinite for terminal receipts; artifact retention follows workspace policy |
| **Recovery use** | Replay a complete session; validate handoff integrity; prove what was produced and when |

**Contents required**
- `terminal_state`: one of `completed`, `failed`, `cancelled`, `rejected`
- `handoff_verdict`: `eligible`, `ineligible`, or `pending_approval` with reason
- `artifact_inventory`: list of every artifact with checksum, path, and schema version
- `checkpoints_merged`: reference to the compacted checkpoint baseline
- `next_actions`: suggested follow-up jobs, scheduled walks, or operator briefs
- `session_duration_ms`, `exchange_count_total`, `error_count`

## Platform-wide save matrix

| Actor | Checkpoint | Pre-compact | End-of-session |
|---|---|---|---|
| Broker | Job state receipt | Archive before job log compaction | Terminal receipt and artifact index |
| MemPalace | Drawer in `broker/jobs/<job_id>/checkpoints/` | Archive manifest in `compactions/` | Terminal drawer in `terminal/` |
| Research (OpenClaw) | Vault delta snapshot before next exchange batch | Archive before vault deduplication | Final ledger, dossier, run receipt |
| Subconscious (OpenClaw) | Room state snapshot before next walk segment | Archive before signal board rebuild | Final board state, intent drafts, walk receipt |
| Hermes Main | Diary entry every 15 routing turns | Diary snapshot before schedule compaction | Closing diary entry, handoff approval record |
| Coder / QA | Job artifact checkpoint | Archive before test result rollup | Final build artifact, validation report |

## Trigger protocol

1. **Counting exchanges**: An exchange is a request/response pair between two platform actors (e.g., Hermes → broker, broker → worker, worker → MemPalace). Multi-turn streaming inside a single OpenClaw profile counts as one exchange if it shares a correlation ID and produces a single terminal artifact.

2. **Counter scope**: Each `correlation_id` carries its own exchange counter. If a job spawns sub-jobs, the parent counter pauses while children run; children report their own checkpoints.

3. **Save ordering**: Checkpoint MUST complete before the 16th exchange begins. If the save fails, the current exchange MUST NOT proceed until the save succeeds or the job is cancelled.

4. **Pre-compact gate**: Compaction MUST NOT start until the pre-compact save is durably persisted. Durable means the archive checksum is written and a receipt exists in MemPalace or the broker event log.

5. **EOS gate**: No downstream handoff may be marked `eligible` until the EOS save is complete and its checksum is recorded in the broker terminal receipt.

## Failure handling

| Scenario | Action |
|---|---|
| Checkpoint write fails | Pause exchange stream; retry 3 times with backoff; escalate to Hermes Main after final failure |
| Pre-compact write fails | Abort compaction; preserve existing state; alert operator |
| EOS write fails | Job remains in `stabilizing` state; no handoff permitted; retry until success or manual cancellation |
| Checkpoint counter desync | Rebuild counter from broker event log; if ambiguous, treat as requiring immediate checkpoint |

## Integration with MemPalace

- Every save type writes a receipt drawer to the palace under the broker wing.
- Hermes Main queries palace for the most recent checkpoint or EOS receipt before approving any handoff.
- Diary entries reference checkpoint IDs so human operators can correlate agent narrative with platform state.

## Version

- `heartbeat_schema_version`: `1.0.0`
- Effective immediately for all broker-managed jobs and agent sessions.
