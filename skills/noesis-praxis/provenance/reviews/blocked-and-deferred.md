# Blocked packages — no reference material staged (manifest-only record)

These packages were reviewed but neither installed into the discoverable
skill tree NOR staged as reference material in `provenance/reviews/` —
unlike the 5 NetClaw packages with their own reference docs in this
directory, these are judged too unsafe-by-default or too incomplete
(missing backend entirely, not even inspectable) to be worth preserving
even as inert reference text. Full detail in `provenance/manifest.yaml`.

## automateyournetwork/netclaw @ 45a333ed18b75643c2d1589eb884be7b303817c1

- **nmap-network-scan** (`workspace/skills/nmap-network-scan/SKILL.md`) —
  backing MCP server (`sbmilburn/nmap-mcp`) is external and unvendored in
  this repo, so its claimed CIDR-allowlist/audit-logging safety mechanism
  could not be verified at all. Documents a stealth SYN scan as a routine
  step. Blocked.
- **nmap-service-detection** (`workspace/skills/nmap-service-detection/SKILL.md`) —
  same unverifiable backend, plus a tool exposing arbitrary NSE script
  execution (including active-recon scripts like `ftp-anon`/`dns-brute`) and
  a CVE-category vulnerability scanner, presented as routine with no
  authorization gate beyond the unverifiable allowlist claim. Blocked.
- **nmap-scan-management** (`workspace/skills/nmap-scan-management/SKILL.md`) —
  same unverifiable backend; documents an **idle/"zombie" scan** (`-sI`, a
  classic source-spoofing evasion technique) as a plain example alongside
  benign ones, with zero authorization/legality caveat. Blocked — this is
  the single most concerning example found across any reviewed package in
  this batch.
- **gtrace-path-analysis** (`workspace/skills/gtrace-path-analysis/SKILL.md`) —
  backing binary (`hervehildenbrand/gtrace`) is external and not vendored in
  this repo at all; nothing to inspect beyond the SKILL.md prose, and no
  Hermes tool exists to run it. Blocked purely on missing interface — the
  generic traceroute/MTR methodology itself is unremarkable and not a safety
  concern, there is simply nothing to install.
- **grafana-observability** (`workspace/skills/grafana-observability/SKILL.md`) —
  wraps the real upstream `grafana/mcp-grafana` server, whose default tool
  surface includes `create_alert_rule`/`update_alert_rule`/`delete_alert_rule`/
  `update_dashboard` — write/destructive operations enabled by default unless
  the operator explicitly passes `--disable-write` at launch. The skill's own
  "approval required" language is prose riding on NetClaw's ServiceNow/GAIT
  systems, which Hermes does not have to enforce it. This skill tree's own
  `praxis-dashboard-management`/`praxis-alert-management`/
  `praxis-metrics-investigate` cover the equivalent read-oriented operational
  need without assuming a write-capable tool is installed. Blocked/superseded.

## No separate claude-dev-suite firewall reference staged

`claude-dev-suite`'s `skills/infrastructure/firewall` package (commit
`c9145f88f077e4fb279e8c8632f62e73af8c6a0d`) was reviewed and found safe
(disposition A-quality content, no unsafe findings) but substantially
redundant with the installed `linux-firewall-reference` package (same core
UFW/iptables/nftables guidance). Per the reviewing subagent's explicit
recommendation and this task's instruction to avoid redundant/conflicting
generic firewall guidance, it is deferred rather than installed as a second
firewall skill. Its one genuinely distinct asset (a fail2ban jail-config
walkthrough) is not duplicated by `praxis-fail2ban-operations` (which covers
*investigation and change procedure*, not jail-config authoring) — if that
gap is ever felt in practice, this deferred package is the citable source
for it, pinned at the commit above.
