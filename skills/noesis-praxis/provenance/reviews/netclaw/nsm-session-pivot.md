# NetClaw reference review — nsm-session-pivot

**Status: reference-only, outside active skill discovery. Execution blocked.**

Source: `automateyournetwork/netclaw`, commit `45a333ed18b75643c2d1589eb884be7b303817c1`,
path `workspace/skills/nsm-session-pivot/SKILL.md`. License: Apache-2.0.
Upstream disposition from review: B. Noesis disposition: preserved as
reviewed reference material only — **not** copied into
`skills/noesis-praxis/skills/`.

## Missing interface

Same `nsm-mcp` backend as `nsm-ids-triage` (see that reference doc), this
time wrapping a Zeek 8.2.1 container. Tools: `nsm_status`, `nsm_analyze`,
`nsm_sessions`, `nsm_protocol_log`. **Not available in this Hermes profile.**
Do not invent these tool names.

## Preserved forensic insight (the genuinely valuable, non-obvious lesson)

**A missing protocol log does not mean the traffic didn't happen.** Zeek
discards packets with invalid TCP checksums by default. The upstream
measurement: on a reference capture, with checksum validation on, Zeek
produced **no `http.log` at all** (the HTTP request became invisible) and
even `conn.log` was wrong (3 rows instead of the correct 2), because
discarded packets fragment the flow — with the only signal being a stderr
warning. This matters generally: captures taken from a NIC with checksum
offloading routinely have "invalid" checksums that are actually fine on the
wire (the NIC computes/validates them in hardware, so what's captured before
that point looks broken to software). A posture flag distinguishing
"all packets analyzed" vs. "packets were discarded, logs may be incomplete"
vs. "checksum validation on, nothing flagged" is the right pattern for any
packet-analysis pipeline to adopt, independent of Zeek specifically.

Reconstruction procedure (harness-agnostic): establish which logs a capture
actually produced and how many connections exist → use the connection table
to find the specific `uid` of interest → every per-protocol log shares that
same connection identifier, so following one `uid` across dns/http/ssl/etc.
logs is an exact pivot, not a heuristic guess → check the "weird" log
separately for protocol anomalies the tool couldn't otherwise classify →
always report under what checksum-handling posture the analysis was run,
especially before concluding a given protocol was absent.

Following an alert (from `nsm-ids-triage`) into its session: match the
alert's IP/port pair to find its connection identifier, retrieve that
connection's protocol logs, and report the alert together with its session
context — `conn_state` values like "no reply" vs. "completed" materially
change what an alert means.

## Stripped glue (not carried over)

- `nsm-mcp` tool names and the specific pinned Zeek container image.
- `$NSM_HOME`/`$NSM_TIMEOUT` environment variable convention.
- GAIT audit-trail references.

## Security review

Strictly read-only against an existing file, no live capture, no writes. No
unsafe-automatic-behavior found.
