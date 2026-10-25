---
name: praxis-alert-management
description: Review and manage approved Prometheus/Grafana alert rules and notification configuration, distinguishing rule authority and management path. Use when reviewing, proposing, or investigating an alert rule, notification policy, silence, or inhibition. Changes that reduce coverage or affect notification routing need explicit separate approval.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-alert-management

Review and manage approved alert definitions and notification configuration.

## Distinguish these systems explicitly — never conflate them

- **Prometheus rule files** (`.rules.yml` loaded directly by a Prometheus
  server) — the base mechanism, no higher-level resource wrapping it.
- **Prometheus Operator `PrometheusRule` custom resources** — Kubernetes-
  native, reconciled into Prometheus config by the Operator; only relevant
  if the Operator is actually in use (confirm before assuming it is).
- **Grafana-managed alert rules** (Grafana's own unified alerting, evaluated
  by Grafana itself, separate from Prometheus's own rule evaluation) — a
  genuinely different system from the two above even though it can query
  the same Prometheus data source.
- **Alertmanager routing vs. Grafana notification policy** — Alertmanager's
  routing tree (receivers, routes, inhibition rules, silences) governs
  Prometheus-originated alerts; Grafana's own notification policies govern
  Grafana-managed alert rules. These are two separate routing systems even
  in a stack that uses both Prometheus and Grafana alerting — do not assume
  a change to one affects the other.

## Required before reviewing or changing any alert

1. **Ownership and authoritative management path**: which of the four
   systems above actually owns this specific alert, and through what
   management path is it maintained (a file in a repo reconciled by
   automation, a Kubernetes CR, Grafana UI/API state) — identify this
   before proposing any change, since the "right" way to change an alert
   differs by system.
2. **Rule quality attributes**: severity, `for`/duration (avoid both
   alerts that fire too eagerly on a blip and ones delayed so long they're
   useless), labels (used for routing — confirm they match what the
   routing tree actually expects), annotations (clear enough for whoever
   receives the page to act), and a runbook reference where one exists.
3. **Missing-data and error behavior**: does the rule correctly distinguish
   "no data" from "healthy zero" (same distinction as in
   `praxis-metrics-investigate`) — an alert rule that can't fire when its
   underlying metric goes missing (rather than going to zero) has a
   dangerous blind spot worth calling out explicitly.
4. **Rule testing with supported tools**: validate rule syntax/logic with
   the tooling the active system actually supports (e.g. `promtool test
   rules` for Prometheus-native rules) before treating a rule as ready —
   don't just eyeball the YAML.

## Separately authorized, every time

- **Notification-path verification** (actually confirming a test
  notification reaches its destination) is itself an action with side
  effects (it will page/notify someone or something) and needs its own
  explicit authorization at the time it's requested — this skill documents
  the review process, it does not trigger test notifications on its own.
- **Silences, inhibitions, contact-point changes, and anything that reduces
  monitoring coverage** (disabling a rule, widening a `for` duration,
  loosening a threshold, adding/expanding an inhibition) need explicit,
  specific approval for that exact change — never bundled into a larger
  "cleanup" without being called out individually, since each one reduces
  what the team will be told about.

## Avoid accidental duplication

- Before adding a new alert, check whether equivalent coverage already
  exists in another of the four systems above for the same condition —
  duplicate alerts for the same underlying problem create duplicate pages
  and alert fatigue; consolidate or explicitly justify keeping both.

## What this skill explicitly does NOT do

- It does not create, modify, silence, or inhibit any live alert as part of
  this installation task.
- It does not assume Alertmanager, the Prometheus Operator, or Grafana
  unified alerting is in use — confirm which systems are actually present
  before applying system-specific guidance.

## Source material

Prometheus alerting rules (https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/),
Alertmanager configuration (https://prometheus.io/docs/alerting/latest/configuration/),
Prometheus Operator `PrometheusRule` docs
(https://prometheus-operator.dev/), and Grafana unified alerting
(https://grafana.com/docs/grafana/latest/alerting/) are the authoritative
references for whichever system is actually in play.
