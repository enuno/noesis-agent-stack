# research-openclaw

> **Agent ID:** `research-openclaw`  
> **Role:** Evidence collection and knowledge extraction worker  
> **Type:** Stateless OpenClaw worker, broker-governed  
> **Write surface:** `workspace/research-vault/` only

---

## Overview

research-openclaw is the evidence operator of the Noesis Agent Stack. It fetches sources, extracts atomic claims, normalizes and deduplicates them, promotes validated claims to findings, and writes all artifacts to the research vault. It does not strategize, approve, or execute builds.

It runs in four modes, dispatched by Hermes through the broker:

| Mode | Purpose |
|---|---|
| `bootstrap` | Cold-start: fetch all configured collectors, extract claims, write initial source and claim records. No findings yet. |
| `refresh` | Scheduled: fetch updated collectors, extract new claims, promote high-confidence claims to findings, write health report. |
| `targeted-query` | Directed: fetch specific URLs or answer a precise question, write targeted findings. |
| `build-intent-research` | Deep-dive: authorized build intent creation. Produces a complete build intent document if evidence is sufficient. |

---

## Quickstart

### Bootstrap the vault

```bash
cd ~/projects/noesis-agent-stack
python agents/research-openclaw/scripts/bootstrap.py \
  --vault-dir workspace/research-vault \
  --config-dir agents/research-openclaw/config
```

This creates the ledger files, directory structure, and validates schemas.

### Run a refresh

```bash
python agents/research-openclaw/scripts/refresh.py \
  --mode refresh \
  --config-dir agents/research-openclaw/config \
  --vault-dir workspace/research-vault
```

### Validate ledger integrity

```bash
python agents/research-openclaw/scripts/validate.py \
  --vault-dir workspace/research-vault
```

---

## Broker Integration

research-openclaw is never invoked directly by Hermes. All interaction goes through the broker:

1. Hermes submits a typed job to `POST /v1/jobs` with payload shaped per `contracts/broker-api/job.schema.json`.
2. The broker spawns an ephemeral research-openclaw worker with the job's `constraints` (write paths, capabilities, budgets).
3. The worker executes its protocol, writes artifacts, and exits.
4. The broker writes a job receipt to the palace and returns normalized status to Hermes.

The job payload must include:
- `objective`: string describing what to research
- `mode`: one of `bootstrap`, `refresh`, `targeted-query`, `build-intent-research`
- `constraints.allowed_capabilities`: list of permitted tool calls
- `constraints.write_paths`: list of allowed write directories
- `constraints.max_cost_usd`, `max_llm_calls`, `max_tool_calls`: budget limits

---

## Directory Layout

```
agents/research-openclaw/
  README.md          # This file
  SPEC.md            # Detailed execution specification
  SOUL.md            # Identity, guardrails, quality standards
  agent.yaml         # Agent identity and broker registration
  ARCHITECTURE.md    # Script architecture and data flow
  config/
    collectors.yaml  # Source collector registry
    thresholds.yaml  # Promotion and signal thresholds
    jobs.yaml        # Job type definitions and defaults
    capabilities.yaml # Allowed tools per mode
  scripts/
    bootstrap.py     # Vault initialization
    refresh.py       # Main evidence collection
    validate.py      # Ledger integrity checks
    daily_summary.py # Aggregate brief generation
    midday_focus.py  # Focused re-query
    backup.py        # Vault backup
    restore.py       # Vault restore
    recover.py       # Ledger repair
    lib/
      schemas.py     # Schema loading and validation
      ledger.py      # Append-only JSONL ledger
      fetcher.py     # Source fetching
      claims.py      # Claim extraction and normalization
```

---

## Integration with Other Agents

| Direction | Agent | Interaction |
|---|---|---|
| **Triggered by** | Hermes (via broker) | Submits typed research jobs |
| **Reads from** | Subconscious | Walk notes may inform targeted-query objectives |
| **Writes to** | Palace | Run receipts and job events via broker hook |
| **Downstream** | Subconscious | Reads findings.jsonl for drift walks |
| **Downstream** | Hermes | Reviews findings and build intents for approval |
| **Downstream** | Coder | Receives approved build intents only |

---

## Guardrails Summary

- Never write outside `workspace.write_paths`.
- Never call tools not in `allowed_capabilities`.
- Never write a finding without a grounding source.
- Never write a build intent unless `allow_write_build_intent: true`.
- Never emit signals unless `emit_signal` is in capabilities.
- Stop immediately if budget limits are reached.
