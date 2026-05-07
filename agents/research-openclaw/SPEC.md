# research-openclaw — Specification

> **Version:** 1.0  
> **Status:** Draft  
> **Last updated:** 2026-05-06

---

## 1. Execution Flow

Every run follows the same 9-step protocol, regardless of mode. Steps may be no-ops depending on mode.

```
1. READ VAULT STATE
   - Load existing sources, claims, findings relevant to job topic.
   - Read most recent run receipt to determine freshness window.

2. FETCH SOURCES
   - For each collector authorized by allowed_capabilities:
     - Fetch up to max_entries.
     - Compute content_hash (SHA-256 of normalized body).
     - Skip if hash exists in sources.jsonl.
     - Write new source record.

3. EXTRACT CLAIMS
   - For each new source, extract atomic claims.
   - Each claim = single assertable proposition + verbatim excerpt.
   - Assign claim_type, confidence, topic.
   - Write to claims.jsonl with promotion_status: pending.

4. NORMALIZE AND DEDUPLICATE
   - Compare new claims against existing claims for same topic.
   - Mark duplicates as superseded.
   - Mark normalized: true on processed claims.

5. PROMOTE TO FINDINGS
   - For each cluster of normalized, non-superseded claims with confidence >= medium:
     - Require at least one source with trust_level: trusted or provisional.
     - Write finding record to findings.jsonl.
     - Update promoted claims with promoted_to_finding_id and status: promoted.
   - Speculative claims are stored but not promoted unless mode is build-intent-research.

6. EVALUATE SIGNAL
   - For each new finding, check if it warrants a signal event:
     - Breaking change to spec or dependency.
     - Critical security or CVE finding.
     - Direct contradiction of existing high-confidence finding.
   - If yes and emit_signal is in capabilities: write signal_event.

7. WRITE BUILD INTENT (mode == build-intent-research only)
   - Require allow_write_build_intent: true in constraints.
   - Require findings support a clear, well-evidenced objective.
   - Validate against contracts/handoffs/build-intent.schema.json before writing.
   - Write to workspace/research-vault/output/handoff-candidates/.

8. WRITE HEALTH REPORT
   - Assess vault integrity, source freshness, collector health.
   - Write to workspace/research-vault/state/health/.

9. WRITE RUN RECEIPT
   - Record metrics, artifact IDs, tool call log.
   - Write to workspace/research-vault/state/runs/receipts.jsonl.
   - Trigger broker callback.
```

---

## 2. Mode Behaviors

| Step | bootstrap | refresh | targeted-query | build-intent-research |
|---|---|---|---|---|
| Fetch sources | All enabled collectors | Collectors updated since last run | URLs/questions from objective | Deep-dive on objective topic |
| Extract claims | Yes | Yes | Yes | Yes |
| Normalize | Yes | Yes | Yes | Yes |
| Promote to findings | No | Yes | Yes | Yes |
| Evaluate signal | No | Yes | Yes | Yes |
| Write build intent | No | No | No | Yes (if authorized) |
| Health report | Yes | Yes | Yes | Yes |
| Run receipt | Yes | Yes | Yes | Yes |

---

## 3. Ledger Formats

All ledgers are append-only newline-delimited JSON (JSONL) files.

### 3.1 sources.jsonl

Path: `workspace/research-vault/knowledge/sources.jsonl`

Each line is a source record per `contracts/ledgers/sources.schema.json`.

Key fields:
- `source_id`: UUIDv4
- `collector_key`: matches collectors.yaml
- `content_hash`: SHA-256 of normalized content
- `trust_level`: trusted | provisional | low_trust | social_signal
- `fetched_at`: ISO 8601 timestamp

### 3.2 claims.jsonl

Path: `workspace/research-vault/knowledge/claims.jsonl`

Each line is a claim record per `contracts/ledgers/claims.schema.json`.

Key fields:
- `claim_id`: UUIDv4
- `source_id`: foreign key to sources.jsonl
- `claim_text`: single assertable proposition
- `claim_type`: fact | observation | trend | warning | recommendation | speculation
- `confidence`: high | medium | low | speculative
- `promotion_status`: pending | promoted | rejected | superseded
- `promoted_to_finding_id`: UUID or null

### 3.3 findings.jsonl

Path: `workspace/research-vault/knowledge/findings.jsonl`

Each line is a finding record per `contracts/ledgers/findings.schema.json`.

Key fields:
- `finding_id`: UUIDv4
- `title`: 5-200 chars
- `summary`: standalone-readable, 20-2000 chars
- `confidence`: high | medium | low | speculative
- `signal_value`: high | medium | low | noise
- `evidence[]`: source_id + relevance + excerpt
- `freshness`: oldest_source_date, within_threshold

### 3.4 receipts.jsonl

Path: `workspace/research-vault/state/runs/receipts.jsonl`

Each line is a run receipt per `contracts/ledgers/run-receipt.schema.json`.

Key fields:
- `run_id`: UUIDv4
- `job_id`: broker job ID
- `mode`: execution mode
- `status`: completed | partial | failed | guardrail_breach
- `artifacts_written[]`: list of artifact paths
- `metrics`: source_count, claim_count, finding_count, signal_count, build_intent_count
- `guardrail_breaches[]`: empty if none

---

## 4. Error Handling

### 4.1 Partial-run recovery

If the worker is interrupted or hits a budget limit:
1. Write any pending ledger entries using atomic temp-file + rename.
2. Write a partial run receipt with `status: partial`.
3. Include `interrupted_at_step` and `reason`.
4. Return partial status to broker.

### 4.2 Guardrail breach protocol

If a guardrail is violated:
1. Log the breach with `breach_type`, `breach_detail`, `step`.
2. Immediately stop further tool calls and writes.
3. Write a run receipt with `status: guardrail_breach`.
4. Return failed status to broker.

### 4.3 Collector failure

If a collector fetch fails:
1. Retry up to `global.retry_attempts` with `global.retry_backoff_s` exponential backoff.
2. If still failing, skip the collector and record failure in health report.
3. Do not fail the entire run for one collector failure.

---

## 5. Broker Job Payload Schema

The worker expects a job payload shaped as follows:

```json
{
  "objective": "string",
  "mode": "bootstrap | refresh | targeted-query | build-intent-research",
  "context": {
    "topic": "string",
    "since": "ISO-8601 timestamp (for refresh mode)",
    "urls": ["string"],
    "questions": ["string"]
  },
  "constraints": {
    "allowed_capabilities": ["rss_fetch", "fetch_url", "github_read", "search_web", "llm_call", "emit_signal"],
    "write_paths": ["workspace/research-vault/"],
    "max_cost_usd": 0.50,
    "max_llm_calls": 20,
    "max_tool_calls": 50,
    "allow_write_build_intent": false,
    "freshness_threshold_h": 168
  },
  "callback": {
    "url": "string",
    "method": "POST"
  }
}
```

---

## 6. Vault Directory Layout

```
workspace/research-vault/
  knowledge/
    sources.jsonl
    claims.jsonl
    findings.jsonl
  output/
    dossiers/           # Topic dossiers (markdown)
    operator-briefs/    # Daily/midday briefs (markdown)
    handoff-candidates/ # Build intents awaiting approval
  state/
    health/             # Health reports (JSON)
    runs/               # Run receipts (JSONL)
    queue/              # Pending job queue
    config/             # Runtime config snapshots
  signals/              # Signal events emitted to subconscious
```

---

## 7. Quality Standards

- Finding summaries must be readable without source access.
- Claims must be single propositions (split on "and").
- `confidence: high` requires two independent trusted/provisional sources.
- `confidence: speculative` must be clearly labeled.
- Freshness matters: flag findings with stale sources.
