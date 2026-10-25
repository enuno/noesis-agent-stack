# NetClaw reference review — packet-analysis

**Status: reference-only, outside active skill discovery. Execution blocked.**

Source: `automateyournetwork/netclaw`, commit `45a333ed18b75643c2d1589eb884be7b303817c1`,
path `workspace/skills/packet-analysis/SKILL.md`. License: Apache-2.0.
Upstream disposition from review: B (procedure separable from harness glue).
Noesis disposition: preserved as reviewed reference material only — **not**
copied into `skills/noesis-praxis/skills/`, because the backing tool
(`packet-buddy-mcp`, a `tshark` subprocess wrapper) is not installed as an
MCP server in this Hermes profile and this installation task does not
install system packages, run installers, or stand up new MCP servers.

## Missing interface

The upstream skill invokes a local MCP server (`packet-buddy-mcp/server.py`)
that wraps `tshark -nlr <pcap> ...` and exposes tools:
`list_pcaps`, `pcap_summary`, `pcap_protocol_hierarchy`, `pcap_conversations`,
`pcap_endpoints`, `pcap_filter`, `pcap_packet_detail`, `pcap_to_json`,
`pcap_expert_info`, `pcap_dns_queries`, `pcap_http_requests`. None of these
tools exist in this Hermes profile. **Do not invent them or pretend they are
available.** `praxis-packet-analysis` (this skill tree's own Noesis skill)
covers the same operational need by citing Wireshark/tshark's official
documentation directly, with no invented tool interface — use that skill for
actual guidance; this document is preserved only as a reviewed reference for
what a future real `tshark`-backed MCP tool integration could look like.

## Preserved reusable procedure (stripped of harness-specific glue)

The upstream triage workflow, with its Slack-file-upload step and
`$MCP_CALL`/GAIT-logging specifics removed, reduces to a genuinely reusable
pcap-analysis sequence:

1. Get the big picture first (packet count, duration, size).
2. Check protocol-hierarchy breakdown — any unexpected protocol present?
3. Look at conversations/endpoints — who is talking to whom, and who are the
   top talkers by volume?
4. **Check tshark's own expert-info output before anything else** — it
   already flags retransmissions, resets, and malformed-packet warnings; read
   that before manually hunting for problems.
5. Apply a display filter to narrow to the traffic of interest.
6. Only then drop to full per-packet decode for the specific packets that
   matter.

Useful display filters carried over as-is (these are standard Wireshark
syntax, not NetClaw-specific):

| Filter | Purpose |
|---|---|
| `tcp.analysis.retransmission` | TCP retransmissions |
| `tcp.flags.reset==1` | TCP RST packets |
| `dns` | All DNS traffic |
| `icmp` | Ping and ICMP errors |
| `tcp.port==22` | SSH traffic |
| `http` | HTTP requests/responses |
| `tls.handshake` | TLS handshakes |
| `arp` | ARP requests/replies |
| `ip.addr==10.0.0.1` | Traffic to/from a specific host |

## Stripped glue (not carried over)

- The Slack file-upload workflow (`save_pcap_from_base64`) — Slack-specific,
  not applicable here.
- `$MCP_CALL`/`$PACKET_BUDDY_MCP_SCRIPT` invocation convention — NetClaw's own
  launcher, not present in Hermes.
- GAIT audit-trail references — NetClaw's own audit mechanism, not present
  in Hermes.

## Security review (restated from the retrieval subagent's findings)

Genuinely read-only, offline analysis of a file already on disk — no live
capture, no packet injection, no exploit/credential-attack content. The
`tshark` subprocess call uses an argument list (not `shell=True`), so no
shell-injection vector was observed in the backing server's source. No
unsafe-automatic-behavior found.
