---
name: praxis-network-scan
description: Plan, scope, and interpret authorized network discovery and port/service scans (nmap-based). Use when asked to discover hosts, enumerate open ports, identify services, or compare scan results over time against an explicitly authorized network range. Does not execute scans itself.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-network-scan

Authorized discovery, exposure assessment, and scan-result comparison. This
skill defines the **procedure and required authorization record** for a scan;
it does not grant the ability to run one, and loading it never performs a
scan. Actual execution requires a real `nmap` binary (or equivalent tool
integration) invoked by the operator or an explicitly authorized runtime
tool — none exists in this Hermes profile by default. If asked to run a scan
and no such tool is available, say so and stop; do not substitute another
action for a scan.

## Before any scan may run — required authorization record

Capture ALL of the following, explicitly, before treating any scan as
authorized. Missing any item blocks the scan, not just slows it down.

1. **Scope**: explicit authorized IP(s)/CIDR(s), explicit exclusions
   (addresses/ranges carved out even inside an authorized block), confirmed
   ownership or written authorization for that scope, and the stated
   business purpose.
2. **Origin and vantage point**: where the scan will run from (this host,
   a jump box, a specific network segment) — results differ by vantage
   point (NAT, firewall position, segmentation) and this must be recorded,
   not assumed.
3. **Port/protocol scope**: the approved port range and protocols (TCP/UDP);
   do not default to "all ports" without that being the explicit approval.
4. **Rate, concurrency, duration limits**: explicit timing/parallelism caps
   suitable for the target (a crowded host or OT device needs much more
   conservative limits than an isolated test VM) and a maximum run duration.
5. **Sensitive equipment carve-outs**: any OT/ICS/medical/production/safety
   equipment in or near the range gets separate, more conservative treatment
   (often: exclude entirely, or ping/ARP-only, never full port+service
   scans) — ask explicitly if any such equipment might be in scope before
   proceeding.
6. **Output and redaction/retention rules**: where scan output is stored,
   how long it is retained, and what must be redacted before results leave
   the immediate investigation (internal hostnames that double as PII,
   credentials accidentally exposed in banners, etc.). Scan artifacts are
   operational data, not documentation — never commit them to this
   repository or any git-tracked skill tree.

## Phase separation — do not collapse these into one undifferentiated "scan"

1. **Host discovery** (is anything alive at this address) — least intrusive,
   typically ICMP/ARP or a minimal TCP probe.
2. **Port identification** (which ports respond) — more visible on the wire,
   still generally low-risk against a well-behaved target.
3. **Service/version detection** (`-sV` and banner grabbing) — interacts more
   with the service, can occasionally affect fragile/embedded services.
4. **NSE / vulnerability-oriented scripts** — **requires separate, additional
   approval beyond the base scan authorization.** Nmap's own `safe` category
   label is nmap's own self-classification, not a verified safety guarantee.
   Before running ANY NSE script: read what that specific script actually
   does (nmap script documentation describes the exact probes/payloads it
   sends), not just its category tag. Several "safe"-tagged scripts still
   send unusual or malformed input that can affect fragile embedded
   services. Treat every NSE script individually.

## Structured output and before/after comparison

- Prefer machine-parseable output (`-oX`/`-oJ` equivalents) so comparisons
  are structural, not a diff of free text.
- A comparison run must use the same scope/ports/timing as the baseline, or
  the diff is meaningless — record what changed between runs if anything
  did, and call that out rather than silently normalizing it away.
- Flag new listening ports, newly-appeared hosts, and newly-closed ports
  distinctly — "new exposure" and "reduced exposure" need different
  follow-up (new exposure may need a firewall-change investigation via
  `praxis-firewall-audit`; the comparison itself does not fix anything).

## What this skill explicitly does NOT do

- It does not perform a scan during installation, review, or validation —
  no scan runs as a side effect of this skill existing or being loaded.
- It does not invent a scanning tool-call interface. If the operator wants
  an agent-executed scan, that requires its own explicit, separately
  authorized tool integration — this skill does not claim one exists.
- It does not authorize NSE/vulnerability scripts, credential attacks, or
  broad vulnerability automation — those require separate, explicit,
  scoped approval every time, never a standing default.

## Source material

Nmap's own documentation (https://nmap.org/book/) is the authoritative
reference for scan phases, NSE categories, and output formats — consult it
directly for exact flag behavior rather than relying on secondhand summaries.
