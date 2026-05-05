# MemPalace Workspace

This directory is the on-disk bridge between the broker control plane and the
MemPalace semantic memory layer. It follows the wing/hall/room taxonomy defined
in `contracts/mempalace/taxonomy.yaml`.

## Structure

```
mempalace/
├── broker/           # Broker-generated receipts and events
│   ├── jobs/         # Job completion receipts (JSON)
│   ├── events/       # Event stream snapshots
│   ├── cancelled-jobs/
│   ├── worker-registry/
│   ├── worker-health/
│   └── diary/
├── hermes/           # Supervisor routing and decision records
│   ├── decisions/    # Routing choices, delegation records
│   ├── state/        # Workflow state and preferences
│   └── diary/
├── research-vault/   # Research worker output
│   ├── knowledge/    # findings, claims, sources
│   ├── output/       # dossiers, briefs, handoff candidates
│   ├── state/        # queue, config, health, runs
│   └── diary/
├── subconscious-room/# Subconscious worker output
│   ├── walks/        # walk notes, drift, tangents
│   ├── signals/      # signal events, board, intent drafts
│   ├── state/        # projects, feedback, inbox, lessons
│   └── diary/
├── coder-jobs/       # Builder output
│   ├── builds/       # active builds, artifacts, migrations
│   ├── context/      # implementation decisions, tech constraints
│   └── diary/
└── qa-reports/       # QA output
    ├── audits/       # test results, audit reports, release gates
    ├── evidence/     # claim verification, contradiction flags
    └── diary/
```

## Receipts

Broker job receipts are written as `{job_id}.receipt.json` files under
`broker/jobs/`. Each receipt contains:

- `job_id`, `worker`, `status`, `correlation_id`
- `started_at`, `finished_at`, `exit_code`
- `artifact_count`, `warnings`, `summary`
- `receipt_version` (always "1.0")

Hermes (or a sync agent) reads these receipts and forwards them to the
live MemPalace via `mcp_mempalace_add_drawer`.

## Initialization

Run `python workspace/mempalace/init_palace.py` to create missing directories
and validate structure against `contracts/mempalace/taxonomy.yaml`.
