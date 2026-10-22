---
name: praxis-firewall-audit
description: Read-only investigation of host firewall state, active management layer, exposure, and rule ownership. Use when asked to check what firewall is active, what rules exist, what's actually exposed, or to investigate before proposing a firewall change. Never modifies firewall state.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-firewall-audit

Read-only host exposure and firewall-state investigation. This skill never
proposes executing a change itself — see `praxis-firewall-change` for that,
which this skill's findings feed into.

## Step 1 — detect the active management layer and backend before anything else

Linux firewall tooling has several layers that can coexist, conflict, or
silently shadow each other. Identify ALL of the following before drawing any
conclusion about "the" firewall state:

- **Management layer in use**: UFW, firewalld, raw iptables (legacy, via
  `iptables`/`ip6tables` using the legacy backend), iptables-over-nftables
  (`iptables-nft`), or native nftables rules written directly (`nft list
  ruleset`). More than one can be present on the same host; a UFW install
  with firewalld also installed-but-inactive is common and NOT the same as
  "no conflict."
- **Which backend `iptables` actually resolves to** right now
  (`iptables --version`, or `update-alternatives --display iptables` on
  Debian-family hosts) — this matters because `iptables-legacy` and
  `iptables-nft` rule sets are NOT the same rule set and don't see each
  other's rules.
- **Persistence mechanism**: how rules survive a reboot for whatever backend
  is active (ufw's own persistence, `/etc/iptables/rules.v4`,
  `firewalld --permanent` zones vs. runtime, or an nftables config file
  loaded by systemd) — a rule with no persistence path is a rule that
  disappears on next reboot, which matters for both audit accuracy and for
  any future change via `praxis-firewall-change`.

## Step 2 — identify rule ownership before proposing anything

- Attribute rule blocks to their likely owner/source: Docker (look for
  `DOCKER`, `DOCKER-USER`, `DOCKER-ISOLATION-STAGE-*` chains), k3s/Kubernetes
  (CNI-managed chains, `KUBE-*` chains if present), Tailscale (its own
  accept rules on the tailscale interface), UFW's own chains
  (`ufw-user-input` etc.), and anything that looks hand-added outside all of
  those.
- Do not treat an unattributed rule as safe to touch — flag it as
  unidentified ownership and say so plainly rather than guessing.

## Step 3 — scope of inspection

- **IPv4 and IPv6 both** — an IPv4-only audit on a dual-stack host misses an
  entire attack surface; always check `ip6tables`/the v6 half of nftables/
  firewalld's v6 zones too, even if the host "mostly uses IPv4."
- **Forwarding and NAT**: `net.ipv4.ip_forward` / `net.ipv6.conf.*.forwarding`
  sysctls, NAT/MASQUERADE rules — these interact with container and VPN
  traffic paths and are a common source of surprising exposure.
- **Listening sockets**: cross-reference actual listening sockets
  (`ss -tulnp` equivalent) against what the firewall rules claim to allow —
  the two can disagree (a service listening on 0.0.0.0 with no firewall
  rule at all is still exposed if the default policy is ACCEPT).
- **Docker**: Docker manipulates iptables/nftables directly and this
  interacts with UFW in well-known, confusing ways (published container
  ports can bypass UFW rules entirely depending on Docker's iptables mode)
  — call this out explicitly when Docker is present, don't assume UFW's
  policy is the whole story for a container's exposure.
- **k3s**: k3s's embedded CNI (typically flannel) and any NetworkPolicy
  objects affect in-cluster traffic paths; only inspect/report on this when
  k3s is actually present and running — do not assume a generic host has it.
- **Tailscale**: tailscale's own accept-rule injection and whether the
  tailscale interface is exempted from or subject to the active firewall
  policy — report this explicitly since it's easy to assume "tailscale is
  always allowed" when that depends on the actual rule set.

## Step 4 — distinguish intended policy from observed exposure

- "What the rules say should be allowed" and "what's actually reachable from
  outside" are different questions — where possible, state both separately
  rather than conflating configuration-as-written with verified exposure.
  Verifying actual external reachability (e.g. probing from outside the
  host) is itself a scan-like action and falls under `praxis-network-scan`'s
  authorization requirements, not this skill's.

## What this skill explicitly does NOT do

- It never writes, adds, deletes, or flushes any firewall rule — that is
  `praxis-firewall-change`'s scope, under separate explicit authorization.
- It does not display secrets or dump unrelated sensitive state (e.g. full
  environment dumps, unrelated service configs) just because they happen to
  be near firewall config on disk.

## Source material

Cite the official docs for whichever backend is actually active:
`man iptables`/`man nft`, UFW's own documentation
(https://help.ubuntu.com/community/UFW), firewalld's documentation
(https://firewalld.org/documentation/), and the nftables wiki
(https://wiki.nftables.org/) — use the one matching the detected backend,
not a generic blend.
