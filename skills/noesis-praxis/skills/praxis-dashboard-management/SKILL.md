---
name: praxis-dashboard-management
description: Read, create, review, and manage versioned Grafana dashboards with export/baseline discipline and schema-aware validation. Use when working with a specific Grafana dashboard's JSON/definition, reviewing a dashboard change, or planning a new dashboard. Does not publish a live dashboard.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-dashboard-management

Read, create, review, and manage versioned dashboards. This skill does not
publish a live dashboard as part of this installation task or as a default
side effect of being loaded — any actual publish/update against a running
Grafana instance needs its own explicit authorization at the time it's
requested.

## Required before working with any dashboard

1. **Grafana version and schema compatibility**: confirm the target Grafana
   version. **Do not assume classic dashboard JSON and newer dashboard
   schema formats are interchangeable** — Grafana has evolved its dashboard
   model (panel/row structure, variable syntax, newer schema versions) and a
   dashboard authored against one version's assumptions can fail to import
   or render correctly against a meaningfully different version. Confirm
   compatibility rather than assuming.
2. **Data-source identity and stable references**: dashboards should
   reference data sources by a stable identifier (UID), not by a
   human-readable name that can collide or change — confirm which reference
   style the target Grafana version/setup expects and actually uses.

## Required workflow

1. **Export/baseline before any update**: before changing an existing
   dashboard, export its current definition as the rollback baseline —
   never edit "in place" against the only copy.
2. **Correctness checks on the dashboard definition**: units (don't mix
   seconds/ms, bytes/bits across panels showing the same underlying data),
   labels and legends (clear and non-ambiguous), template variables (confirm
   they resolve to real label values on the actual data source, not
   assumed/sample ones), transformations (confirm they do what they claim —
   e.g. a rename/merge transform applied to the wrong field silently
   produces a misleading panel), and time-range/relative-time behavior
   (confirm a dashboard's default range and any per-panel override is
   intentional).
3. **Query validation**: validate that every panel's query is syntactically
   valid against the actual data source in use (PromQL via
   `praxis-metrics-investigate`'s correctness guidance, LogQL similarly) —
   do not assume a query that looked right at authoring time still matches
   current label/metric names.
4. **Dashboard verification**: after any change, verify the dashboard
   actually renders as intended against real data in the target
   environment before considering the change complete — a JSON file that
   parses is not the same as a dashboard that displays correctly.

## No credentials or sensitive data in committed artifacts

- Dashboard JSON committed to any repository must never embed a credential,
  API key, or a hardcoded sensitive value — data-source auth belongs in the
  data source's own configuration, referenced by UID, never inlined into a
  dashboard definition.

## What this skill explicitly does NOT do

- It does not publish/apply a dashboard against a live Grafana instance as
  part of this installation task.
- It does not assume Grafana is deployed at all — confirm via
  `praxis-observability-deploy`'s discovery if that hasn't already been
  established.

## Source material

Grafana's dashboard JSON model and schema-version documentation
(https://grafana.com/docs/grafana/latest/dashboards/) is the authoritative
reference — consult it for the specific schema version actually in use
rather than assuming compatibility across versions.
