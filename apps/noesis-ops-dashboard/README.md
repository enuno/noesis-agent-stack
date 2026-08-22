# Noesis Ops Dashboard

Self-contained operations dashboard for the Noesis agent fleet — part of the
noesis-agent-stack repo. A single static HTML page (no build step, no
runtime dependencies beyond Google Fonts) that shows the agent roster,
activity stream, kanban board, approval queue, and live tool-call log in one
view.

This is a port of `~/personal-dashboard-template.html` (a Data-Component
`.dc.html` page) into a dependency-free vanilla JS page. The visual design,
data model, and interactions are preserved; the dc runtime (`support.js` +
`_ds/` bundle) is no longer required.

## What it shows

- **Agent roster rail** — fleet agents (hermes supervisor, aletheia legal
  research, argus infra/observe, lucidus build/deploy, mnemosyne memory)
  with status dots, role labels, sparklines, and current task; filter the
  stream to a single agent or show all.
- **Activity stream** — task cards with agent, project, status pill
  (RUNNING / AWAITING APPROVAL / ERROR / DONE / QUEUED), progress bars,
  MCP/ACP/A2A tool chips, and elapsed time. New task envelopes arrive
  periodically with a skeleton loading state.
- **Kanban board** — QUEUED / RUNNING / AWAITING APPROVAL / CLOSED columns.
- **Approval queue** — modal listing human-in-the-loop actions awaiting
  operator approval (outbound comms, destructive ops, above-limit
  transactions, prod publishes), with APPROVE / DENY and an approval banner
  in the header.
- **Detail pane** — selected task context plus a live streaming stdout /
  tool-call log (MCP, ACP, A2A, warnings, acks).
- **Command palette** (⌘K) — jump to an agent, switch view, change theme
  (Hermes gold / Poseidon / Mono), open approvals.
- **Fleet header** — online/idle/error/held chips, uptime, clock.

## Run

No build step. Serve the directory with any static file server:

```bash
cd apps/noesis-ops-dashboard
python3 -m http.server 8080
# open http://localhost:8080
```

Or open `index.html` directly in a browser (all assets are inline).

## Deploy

The page is a static artifact; the intended deployment pattern matches the
rest of the Noesis stack:

- **Local (Ansible):** serve via a static role in `noesis-ansible` (e.g.
  nginx or Caddy on the Tailscale interface) so the dashboard is reachable
  from the tailnet only.
- **Fly.io:** a two-line static deploy or a tiny nginx/caddy image; see
  `platform/` for the agent-stack deployment conventions.

## Wiring real data

The dashboard is intentionally self-contained with representative sample
data in the `AGENTS`, `TASKS`, `APPROVALS`, `LOGPOOL`, and `ARRIVALS`
constants at the top of the inline script. To make it live:

1. Replace those constants with a fetch from a JSON endpoint (e.g.
   `const res = await fetch('/api/ops'); const { agents, tasks, approvals,
   logs } = await res.json();`).
2. Keep the same field shapes: `state` is one of
   `running|approval|error|done|idle|queued`; chips are `[kind, name]`
   pairs where kind is `MCP`, `ACP`, or `A2A`.
3. The 1s ticker advances `running` task progress and elapsed time; the log
   pool cycles for a live feel. Replace `pushLog()` with a WebSocket or
   polling source for real telemetry.

Candidate live sources in the stack: the Hermes gateway API (`:8642`),
AgentMail inbox threads (outreach tracker), cron job status, and the
`platform/agent-registry.yaml` roster.

## Layout

```
apps/noesis-ops-dashboard/
├── index.html   # single self-contained page (CSS + JS inline)
└── README.md
```

## Related

- `apps/careerops-dashboard/` — Next.js control plane for the job-application
  pipeline (the other dashboard in the stack).
- `~/wiki/ywca-missoula/concepts/attorney-representation-outreach-tracker.md`
  — outreach tracking table that can feed an ops card.
- `platform/agent-registry.yaml` — canonical agent roster.
