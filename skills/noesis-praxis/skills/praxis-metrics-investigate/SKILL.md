---
name: praxis-metrics-investigate
description: Read Prometheus/Grafana metrics, inspect scrape targets, and investigate incidents with bounded, evidence-backed PromQL queries. Use when investigating an incident via metrics, checking whether a target is being scraped, or asking what a specific metric/label means. Read-only.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-metrics-investigate

Read metrics, inspect scrape targets, and investigate incidents. Read-only
against an already-deployed stack — this skill does not assume one exists;
see `praxis-observability-deploy` if no stack is actually present yet.

## Required before answering any metrics question

1. **Correct data source**: confirm which Prometheus/Grafana instance is
   actually being queried (environment, cluster, region if more than one
   exists) — never assume "the" Prometheus when several could be in scope.
2. **Bounded time range**: every query needs an explicit time range; an
   unbounded "show me everything" query against a high-cardinality series
   is both slow and likely to produce a response too large to be useful —
   scope the range to the actual investigation window.

## Evidence-backed discovery, not guessed metric/label names

- Confirm a metric name and its labels actually exist (via the data
  source's own metadata/labels API or a minimal query) before building a
  larger query around an assumed name — metric names and label sets vary by
  exporter version and configuration; don't guess.
- When reporting a finding, tie it to its exact query, timestamp/range, and
  target/instance — "X was elevated" without the query and window that
  produced it isn't a verifiable finding.

## Query-cost and cardinality awareness

- High-cardinality label combinations (especially unbounded ones like raw
  user IDs or full URLs used as label values) can make a query expensive or
  can indicate a cardinality problem worth flagging on its own — notice and
  report this rather than only answering the original question.
- Prefer aggregated/rate-based queries over raw high-resolution pulls when
  the investigation doesn't need per-sample detail.

## Missing data vs. healthy zero — these are different findings

- A target that stopped being scraped (gap in `up`, or the series simply
  absent) is a different problem than a target reporting a real zero value
  (e.g. zero error rate is good; a missing error-rate series because the
  target isn't being scraped is not the same as zero errors) — always check
  which one you're looking at before concluding "nothing's wrong."

## Counter/rate/unit correctness

- Counters only increase (until a reset); always wrap a counter in
  `rate()`/`increase()` over an appropriate window rather than reading raw
  counter values as if they were a rate.
- Confirm the actual unit of a metric (seconds vs. milliseconds, bytes vs.
  bits) from its metadata/help text rather than assuming from the name
  alone — naming conventions aren't always followed consistently across
  exporters.

## What this skill explicitly does NOT do

- It does not assume Prometheus/Grafana/any collector is already deployed —
  confirm the stack exists and is reachable before investigating; if it
  isn't, that's itself the finding (see `praxis-observability-health`).
- It does not modify any rule, dashboard, or alert as part of answering a
  metrics question — see `praxis-alert-management` and
  `praxis-dashboard-management` for those, under their own authorization.

## Source material

Prometheus querying documentation
(https://prometheus.io/docs/prometheus/latest/querying/basics/) is the
authoritative reference for PromQL semantics (counters, rate, aggregation) —
consult it directly for exact function behavior.
