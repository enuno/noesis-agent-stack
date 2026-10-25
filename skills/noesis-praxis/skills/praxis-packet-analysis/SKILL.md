---
name: praxis-packet-analysis
description: Analyze an already-collected, authorized packet-capture artifact (pcap/pcapng) with bounded, reproducible queries. Use when asked to investigate a specific capture file, extract flows/protocols, or summarize traffic from an existing artifact. Does not collect live traffic.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-packet-analysis

Analysis of authorized, already-existing packet-capture artifacts. This
skill is **offline-analysis-by-default** and does not define or authorize
live traffic collection.

## Capture collection vs. analysis — kept strictly separate

- **Collection** (running `tcpdump`/`dumpcap`/a span/mirror port to produce a
  new .pcap) is a *different, more privileged* activity with its own
  requirements (interface access, elevated privileges, storage, retention,
  and usually a separate explicit authorization per capture window). This
  skill does **not** perform collection and does not grant it.
- **Analysis** (this skill's actual scope) operates on an artifact that
  already exists and was already authorized to be collected, with a defined
  investigation scope.

If asked to "capture traffic," say explicitly that this skill only covers
analysis of an existing artifact, and that any future capture task needs:
privilege level required (packet capture typically needs elevated access),
exact interface/vantage point, time window, storage location with
appropriate permissions, and a stated retention/disposal plan — record this
as a requirement for a *future, separately authorized* task, not something
this skill performs.

## Required before analyzing any artifact

1. **Approved capture source** — where/how the pcap was collected, and
   confirmation it was itself an authorized capture.
2. **Time window** — the capture's actual time range, and the investigation
   window within it (don't silently analyze the whole file if only a
   narrower window was authorized to be reviewed).
3. **Investigation scope** — what question is being answered (a specific
   flow, a specific host pair, a specific protocol anomaly) — open-ended
   "look at everything" analysis of a large capture is a scope-creep risk
   and a privacy risk; narrow it.

## Privacy controls — apply by default, not only on request

- **Payloads**: do not dump raw application payload content into chat/output
  by default; summarize (protocol, size, direction, timing) unless the
  specific payload bytes are the explicit subject of the investigation, and
  even then redact anything that looks like a credential, token, or secret.
- **Credentials**: actively look for and redact credential-shaped strings
  (Basic-Auth headers, form fields named password/token/apikey, cookies)
  before they appear in any output.
- **DNS and identifiers**: hostnames, usernames, and other identifiers found
  in traffic are sensitive in aggregate even if individually mundane —
  summarize counts/patterns rather than enumerating every identifier seen,
  unless the investigation specifically requires naming one.
- **Bounded output**: cap how much raw traffic (packet count, byte count, or
  flow count) is surfaced in any single response; summarize and offer to
  drill into a specific flow on request rather than dumping everything.

## What this skill explicitly does NOT do

- It does not collect traffic, run a capture tool, or configure a mirror/span
  port.
- It does not import or commit packet-capture artifacts, or any content
  extracted from one, into this Git repository — pcaps and their derived
  findings are operational/investigative data, not documentation.
- It does not access production secrets or log data as part of its own
  procedure — it only analyzes the pcap artifact already provided for the
  specific authorized investigation.

## Source material

Wireshark's own display-filter and protocol-dissection documentation
(https://www.wireshark.org/docs/) is the authoritative reference for query
syntax and field semantics — use it directly rather than guessing filter
syntax.
