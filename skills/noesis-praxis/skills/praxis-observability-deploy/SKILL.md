---
name: praxis-observability-deploy
description: Plan and maintain approved Grafana/Prometheus/Loki/Alloy observability deployments through discovery of existing state and reconciliation via noesis-ansible. Use when planning, reviewing, or changing how an observability stack is deployed. Does not deploy or invent playbooks/charts/roles itself.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-observability-deploy

Plan and maintain approved observability deployments. This skill is a
**discovery and reconciliation-planning** skill — the actual deployment
implementation (Ansible roles/playbooks, Helm charts, whatever mechanism
this environment actually uses) lives in noesis-ansible, not here, and this
skill does not invent one.

## Required discovery before any deployment plan is proposed

- **Existing deployment method and ownership**: how is the current stack
  (if any) actually deployed and managed today — a specific noesis-ansible
  role/playbook, a Helm release, a hand-run docker-compose, something else?
  Identify the real mechanism before proposing a change to it; do not
  assume a mechanism that isn't actually there.
- **Versions**: the actual running version of each component (Grafana,
  Prometheus, Loki, Alloy, any exporters) — version skew matters for API/
  schema compatibility (see `praxis-dashboard-management`).
- **Persistence, retention, capacity**: where each component's data lives,
  what retention policy is configured, and whether current capacity/
  resource limits are known to be adequate or already under pressure.
- **Private access and identity**: how access is actually gated today
  (reverse proxy auth, Grafana's own auth, network-level restriction via
  Tailscale/firewall) — do not assume a stack is "internal-only" without
  confirming how that's actually enforced.
- **Secrets references**: where credentials (datasource passwords, API
  tokens, Alertmanager webhook secrets) are actually sourced from — confirm
  they're referenced (e.g. via Bitwarden/`.env`/a secrets-manager
  integration) rather than hardcoded, and never print their values while
  investigating this.
- **Backup and recovery**: whether dashboards/config/rules/data have any
  backup coverage, and whether recovery from that backup has ever actually
  been tested — an unverified backup is a gap to report, not a safety net
  to rely on.
- **Relevant exporters and collection paths**: what's actually being
  scraped/collected today (node_exporter, cAdvisor, application-specific
  exporters, Alloy pipelines) and from where.

## Boundary with noesis-ansible

Any *implementation* of an approved deployment change (a new/changed
playbook, role, inventory entry, Helm values, or supported variable) belongs
in the noesis-ansible repository — this skill does not invent, draft, or
assume the existence of a specific chart, playbook, role, or variable name.
If a deployment change is approved, the next step is working in
noesis-ansible directly, with this skill's discovery output as the input to
that work — not writing deployment code here.

## What this skill explicitly does NOT do

- It does not deploy, upgrade, restart, or reconfigure Grafana, Prometheus,
  Loki, Alloy, any exporter, or any security tool as part of this skill or
  this installation task.
- It does not create live dashboards, alerts, contact points, silences, or
  monitoring jobs.

## Source material

Official docs for whichever components are actually in scope: Grafana
(https://grafana.com/docs/grafana/latest/), Prometheus
(https://prometheus.io/docs/), Loki (https://grafana.com/docs/loki/latest/),
Alloy (https://grafana.com/docs/alloy/latest/) — and this environment's own
noesis-ansible repository for the actual deployment mechanism in use.
