---
name: praxis-observability-health
description: Assess the health of the observability stack itself — target/exporter failures, scrape and ingestion problems, rule-evaluation failures, notification delivery failures, storage pressure, collector health, and monitoring blind spots. Use when asked whether monitoring itself is working correctly, not when investigating an application incident via its metrics.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-observability-health

Assess the monitoring stack itself — a meta-level check distinct from using
the stack to investigate something else (`praxis-metrics-investigate` is for
that). This skill does not assume Grafana, Prometheus, or any collector is
already deployed — if nothing is deployed, "nothing is deployed" is itself
the health finding; confirm via `praxis-observability-deploy`'s discovery
process rather than assuming either way.

## What to check, and what each failure mode actually means

- **Target and exporter failures**: scrape targets reporting `up == 0`, or
  missing from the target list entirely (a target that was never
  successfully discovered looks different from one that was discovered and
  then started failing — distinguish these). For each failing target, check
  the actual scrape error (connection refused, timeout, TLS failure, auth
  failure) rather than reporting just "target is down."
- **Scrape/ingestion problems**: scrape duration approaching or exceeding
  the scrape interval/timeout, dropped samples, out-of-order sample
  rejections, or remote-write queue backlog if remote-write is in use —
  these indicate the pipeline is struggling even when individual targets
  show `up == 1`.
- **Rule evaluation failures**: recording/alerting rules that are failing to
  evaluate (query errors, evaluation taking longer than the evaluation
  interval) — a silently-failing rule produces no alert and no error
  visible from the dashboard side, so check rule evaluation status
  explicitly rather than assuming "no alert fired" means "nothing's wrong."
- **Notification delivery failures**: Alertmanager/Grafana notifier error
  logs or delivery-failure metrics — an alert that fired but never reached
  its destination is functionally the same as an alert that never fired, so
  check delivery status as its own thing, not an assumed consequence of a
  rule firing.
- **Storage pressure and retention**: disk usage trend on the metrics/log
  storage backend relative to configured retention, compaction health (for
  Prometheus TSDB or Loki's storage), and whether retention is actually
  being enforced as configured (data silently outliving its stated
  retention, or being deleted earlier than expected, are both findings
  worth surfacing).
- **Collector health**: Alloy/agent-side health (config reload failures,
  pipeline component errors) separate from whether its *targets* are
  healthy — the collector itself can be unhealthy even while every target
  it's trying to scrape is fine.
- **Resource usage and cardinality**: CPU/memory of the monitoring
  components themselves, and overall series/cardinality trend (a slow
  cardinality creep is a leading indicator of future storage/query-cost
  problems, worth flagging before it becomes an incident).
- **Monitoring blind spots**: anything that should be monitored but isn't —
  a host/service with no corresponding target or exporter at all. This is
  the hardest category because it's an absence, not a signal; cross-check
  the inventory of things that *should* be monitored (per
  `praxis-observability-deploy`'s discovery) against what's actually being
  scraped, rather than only looking at what's already being collected.

## What this skill explicitly does NOT do

- It does not deploy or fix anything itself — findings here feed into
  `praxis-observability-deploy` (for a deployment/config gap) or
  `praxis-alert-management` (for a rule/notification-path gap), each under
  their own separate authorization for any actual change.
- It does not assume the stack exists — "not deployed" or "partially
  deployed" is a valid and expected finding, not an error in this skill.

## Source material

Prometheus's own self-monitoring guidance (its own `/metrics` endpoint and
TSDB status page), Alertmanager's notification-failure metrics, and Alloy's
component health/debugging documentation
(https://grafana.com/docs/alloy/latest/) are the authoritative sources for
what "healthy" actually looks like for each component.
