# research-openclaw Architecture

> **Version:** 1.0  
> **Status:** Draft

---

## 1. Module Boundaries

The research-openclaw worker is organized into four internal modules:

| Module | File | Responsibility |
|---|---|---|
| **Fetcher** | `lib/fetcher.py` | HTTP fetching, GitHub API calls, RSS parsing, content hashing, retry logic. |
| **Claims** | `lib/claims.py` | Claim extraction from raw source text, normalization, deduplication, confidence scoring. |
| **Ledger** | `lib/ledger.py` | Append-only JSONL operations, atomic writes (temp + fsync + rename), schema validation on append. |
| **Schemas** | `lib/schemas.py` | JSON schema loading from `contracts/ledgers/`, validation helpers, error formatting. |

Scripts in `scripts/` are thin orchestrators that compose the library modules. No script contains business logic directly.

---

## 2. Data Flow

```
+-------------+     +----------+     +------------+     +----------+     +---------+
|   FETCHER   | --> |  CLAIMS  | --> |  SCHEMAS   | --> |  LEDGER  | --> |  VAULT  |
|             |     |          |     | (validate) |     | (append) |     |         |
+-------------+     +----------+     +------------+     +----------+     +---------+
      ^
      | collectors.yaml
      | (config-driven)
```

Per-run flow:

1. **Load state** → Read existing ledgers, last receipt, collector config.
2. **Fetch** → For each enabled collector, fetch sources, hash, skip duplicates.
3. **Extract** → For each new source, extract atomic claims via `claims.extract()`.
4. **Normalize** → Deduplicate claims against existing records via `claims.normalize()`.
5. **Promote** → Score claim clusters, promote to findings via `claims.promote()`.
6. **Validate** → `schemas.validate()` every record before ledger append.
7. **Write** → `ledger.append()` writes temp file, fsync, atomic rename.
8. **Signal** → Evaluate findings for signal events, write to `signals/`.
9. **Receipt** → Write run receipt to `state/runs/receipts.jsonl`.

---

## 3. Vault Directory Layout

```
workspace/research-vault/
  knowledge/
    sources.jsonl      # Source records
    claims.jsonl       # Atomic claims
    findings.jsonl     # Promoted findings
  output/
    dossiers/          # Topic dossiers (markdown)
    operator-briefs/   # Daily/midday briefs (markdown)
    handoff-candidates/# Build intents awaiting Hermes approval
  state/
    health/            # Health reports (JSON)
    runs/              # Run receipts (JSONL)
    queue/             # Pending job queue
    config/            # Runtime config snapshots
  signals/             # Signal events for subconscious
```

---

## 4. Ledger Interaction Patterns

### 4.1 Append-only JSONL

All ledgers are newline-delimited JSON. Records are never updated in-place. Superseded claims get a new `promotion_status` field on a subsequent line — the ledger reader must read all lines and take the last status for each ID.

### 4.2 Atomic Writes

```python
def append(path: Path, records: list[dict]) -> None:
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('a') as f:
        for record in records:
            f.write(json.dumps(record, separators=(',', ':')) + '\n')
        f.flush()
        os.fsync(f.fileno())
    temp.rename(path)
```

This ensures readers never see partially-written records.

### 4.3 Schema Validation on Append

Every record is validated against its schema before being written. If validation fails:
- The record is rejected.
- A validation error is logged.
- The run receipt notes `validation_failures`.
- The run continues with other records.

---

## 5. Error Handling and Recovery

### 5.1 Partial-run recovery

If the worker is interrupted:
- Any completed ledger appends are already atomic → safe.
- Any in-progress append is in a `.tmp` file → ignored by readers.
- On next run, the worker reads the last receipt to determine where to resume.
- Receipts include `last_completed_step` and `artifacts_written`.

### 5.2 Guardrail implementation

Guardrails are checked before every tool call and file write:

```python
def check_guardrail(capability: str, constraints: dict) -> None:
    if capability not in constraints['allowed_capabilities']:
        raise GuardrailBreach(f"Capability {capability} not allowed")
    # ... etc
```

A `GuardrailBreach` exception:
- Stops execution immediately.
- Writes a run receipt with `status: guardrail_breach`.
- Returns failed status to broker.

---

## 6. Script Responsibilities

| Script | Responsibility |
|---|---|
| `bootstrap.py` | Create vault directories, initialize empty ledgers, validate schemas exist, write initial health report. |
| `refresh.py` | Main evidence loop: fetch → extract → normalize → promote → write → signal → receipt. |
| `validate.py` | Check ledger integrity (valid JSONL, schema compliance, cross-reference consistency). |
| `daily_summary.py` | Aggregate findings from last 24h into an operator brief markdown file. |
| `midday_focus.py` | Re-query high-signal topics and produce a focused brief. |
| `backup.py` | Compress vault to a timestamped `.tar.gz` archive. |
| `restore.py` | Restore vault from a backup archive. |
| `recover.py` | Repair corrupted ledgers by replaying from receipts, or truncate after last valid record. |
