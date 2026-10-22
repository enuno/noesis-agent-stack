# NetClaw reference review — prometheus-monitoring

**Status: reference-only, outside active skill discovery. Execution blocked
(no installed MCP tool), even though the content itself needed almost no
adaptation.**

Source: `automateyournetwork/netclaw`, commit `45a333ed18b75643c2d1589eb884be7b303817c1`,
path `workspace/skills/prometheus-monitoring/SKILL.md`. License: Apache-2.0.
Upstream disposition from review: A (minimal glue to strip; tool surface is
read-only by the server's own design). Noesis disposition: preserved as
reviewed reference material only — **not** copied into
`skills/noesis-praxis/skills/`, because the backing tool
(`pab1it0/prometheus-mcp-server`, a real independently-published PyPI
package) is not installed as an MCP server in this profile, and this
installation task does not `pip install` anything or stand up a new MCP
server. `praxis-metrics-investigate` (this skill tree's own Noesis skill)
covers the same operational need by citing Prometheus's own query
documentation directly, with no invented tool interface.

## Missing interface

`prometheus-mcp-server` (installed via `pip3 install prometheus-mcp-server`,
not performed here) exposes exactly 6 read-only tools: `execute_query`,
`execute_range_query`, `list_metrics`, `get_metric_metadata`, `get_targets`,
`health_check`. **None of these exist in this Hermes profile.** If this
integration is ever wanted for real, it is a genuinely good candidate (small,
documented, read-only-only tool surface, real upstream package) — but
standing it up is a separate, explicitly authorized infrastructure task, not
something this review performs.

## Preserved reusable workflow (harness-agnostic PromQL operational knowledge)

Health-check reachability first → discover available metric names before
assuming one exists → check a metric's type/unit from its own metadata
before querying it (counter vs. gauge vs. histogram changes how it must be
queried) → instant query for current value, range query for trend → cross-
check scrape-target health (`up`/down) before concluding a metric's absence
means something healthy. This sequencing matches
`praxis-metrics-investigate`'s own guidance and is restated there in
harness-agnostic form.

## Stripped glue (not carried over)

- GAIT audit-mandate language.
- NetClaw-specific cross-skill references (`pyats-health-check`,
  `te-network-monitoring`, `servicenow-change-workflow`, etc.) — none of
  those skills exist in this profile.

## Security review

No write-capable tool exists in this server's documented surface at all —
genuinely read-only by design, not merely by policy. The one explicitly
flagged risk in the source doc itself —
`PROMETHEUS_URL_SSL_VERIFY=false` — is correctly scoped and labeled
"(development only)" in the original material, which is good practice
already present upstream, not something this review needed to add.
