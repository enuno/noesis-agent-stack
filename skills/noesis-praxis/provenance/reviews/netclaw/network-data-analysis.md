# NetClaw reference review — network-data-analysis

**Status: reference-only, outside active skill discovery. Execution blocked.**

Source: `automateyournetwork/netclaw`, commit `45a333ed18b75643c2d1589eb884be7b303817c1`,
path `workspace/skills/network-data-analysis/SKILL.md`. License: Apache-2.0.
Upstream disposition from review: B. Noesis disposition: preserved as
reviewed reference material only — **not** copied into
`skills/noesis-praxis/skills/`.

## Missing interface

The upstream skill invokes `analysis-mcp`, a NetClaw-authored DuckDB-backed
SQL-over-log-exports server. Tools: `analysis_status`, `analysis_datasets`,
`analysis_query`. **Not available in this Hermes profile** — no `analysis-mcp`
server, and this installation task does not install `duckdb` or stand up a
new MCP server. Do not invent these tool names.

## Preserved design pattern (worth keeping as a model, independent of DuckDB specifically)

The access-control design described is a genuinely sound pattern for
"expose read-only SQL over log exports without creating a filesystem/network
backdoor": rather than hand-rolled path-pattern blocking, the implementation
(per the upstream doc, not independently re-verified against the actual
`sandbox.py` source by this review) relies on DuckDB's own
`enable_external_access=false` + `lock_configuration=true` lockdown API, set
once at process start and irreversible for the life of the process — this
closes file reads, network access, extension loading (`INSTALL`/`LOAD`), and
external attachment (`ATTACH`) at the engine level rather than trying to
pattern-match dangerous queries. Any future similar tool (SQL or otherwise
exposed to a model) should prefer an engine-level capability lockdown over
hand-rolled input filtering when the engine actually offers one.

Operational lessons worth preserving regardless of backend:
- Check what's actually loaded (table/column names, row counts) before
  writing a query against assumed schema — guessing column names wastes a
  round trip and risks a wrong-but-plausible-looking query.
- A result marked "truncated" is a page, never the total — run an explicit
  count for the real number.
- "Zero datasets/rows" means no data was exported/loaded, not "nothing
  happened on the network" — the distinction matters for not under-reporting
  an incident as quiet when it's actually a tooling gap.
- Any analysis inherits every caveat of its source — e.g. a Zeek run with
  checksum validation on (see `nsm-session-pivot`'s reference doc) may be
  missing entire protocol logs, and SQL over an incomplete log is confidently
  wrong; always know the posture of the data being queried.

## Stripped glue (not carried over)

- `analysis-mcp` tool names, DuckDB-specific implementation detail (not
  independently re-verified here).
- `~/.openclaw/analysis` path convention.
- GAIT audit-trail references.

## Security review

Read-only by design per the upstream doc's own claim; write statements are
refused and (per the described lockdown mechanism) independently impossible
after startup. This review did not re-verify `sandbox.py` byte-for-byte —
that residual trust gap is noted explicitly, consistent with not treating a
vendor's/author's own safety claim as proof by itself.
