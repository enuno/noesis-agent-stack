# NetClaw reference review — nsm-ids-triage

**Status: reference-only, outside active skill discovery. Execution blocked.**

Source: `automateyournetwork/netclaw`, commit `45a333ed18b75643c2d1589eb884be7b303817c1`,
path `workspace/skills/nsm-ids-triage/SKILL.md`. License: Apache-2.0.
Upstream disposition from review: B (strong, genuinely reusable procedure;
needs a Docker+Suricata backend that doesn't exist here). Noesis disposition:
preserved as reviewed reference material only — **not** copied into
`skills/noesis-praxis/skills/`.

## Missing interface

The upstream skill invokes `nsm-mcp`, a NetClaw-authored MCP server that runs
pinned Suricata 8.0.6 and Zeek 8.2.1 **Docker containers** against an
existing pcap file (nothing sniffs a live interface). Tools: `nsm_status`,
`nsm_update_rules`, `nsm_alerts`, `nsm_analyze`. **None of this exists in this
Hermes profile** — no `nsm-mcp` server, and this installation task does not
stand up Docker containers, install Suricata, or install any MCP server. Do
not invent these tool names or claim this capability is available.

## Preserved reusable procedure and forensic insight (genuinely valuable, worth keeping even unexecutable)

**The single most important lesson in this package, independent of any
tooling:** zero alerts from an IDS is not a clean result by itself — it could
mean the detector loaded no signatures at all. The upstream measurement: a
stock Suricata config loads **0 signatures** and reports **0 alerts** with
only two non-fatal warnings on stderr — easy to silently misread as "no
threats found" when it actually means "nothing was inspected." After loading
a real ruleset, the same engine measured **52,205** signatures. This is a
real, non-obvious operational risk pattern (a detector that's technically
running but effectively off) applicable to any IDS deployment, not specific
to NetClaw or Suricata's container packaging.

The three-state posture model this package uses to prevent exactly that
misreading is worth preserving as a design pattern for any future detector
integration:

| Posture | Meaning | What may be said |
|---|---|---|
| Armed | signatures loaded, detector ran | "no alerts matched the loaded ruleset" |
| Inert | zero signatures loaded | "the detector was off" — never "the traffic is clean" |
| Unknown | count seen, no ruleset file found | treat with suspicion, re-check after a rule update |

Triage sequence (harness-agnostic): check detector/ruleset status and age
first → do not draw conclusions from an "inert" run → look at high-severity
alerts first, then the full unfiltered list, noting if results were
truncated → for any alert that matters, pivot to its full session context
(see `nsm-session-pivot` below) since an isolated signature match without
session context is a signature match, not a confirmed incident.

## Stripped glue (not carried over)

- `nsm-mcp` tool names and the specific pinned Suricata container image.
- `$NSM_HOME`/`$NSM_TIMEOUT` environment variable convention.
- GAIT audit-trail references.

## Security review

Strictly read-only against an existing file; the upstream doc itself states
"No writes, no live capture... must not be offered," which the review
confirmed is accurate to the tool's actual design, not just an unverified
claim. No scanning, evasion, or exploit automation. The one real operational
dependency worth flagging on its own: the (unavailable-here) implementation
runs specific pinned third-party container images, which is a supply-chain
trust question for whoever would eventually wire this up, not a flaw in the
skill's own content.
