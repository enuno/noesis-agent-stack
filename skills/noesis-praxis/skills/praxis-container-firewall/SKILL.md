---
name: praxis-container-firewall
description: Investigate Docker/k3s packet paths, published-port forwarding, and how container/cluster networking interacts with the host firewall. Use when container or cluster traffic exposure needs to be understood or when a published port's actual reachability is unclear. Read-only; does not edit container-runtime or CNI-managed chains.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-container-firewall

Investigate Docker/k3s packet paths and firewall interaction. This is an
investigation skill, not a change skill — see `praxis-firewall-change` (host
firewall) for actual rule changes; this skill's output feeds that process
when a container/cluster-related firewall change is needed.

## What to check, and in what order

1. **Published ports and the actual forwarding path**: for each
   `-p host:container` (or Compose/Kubernetes Service equivalent), confirm
   what's actually forwarded (TCP/UDP, which host interface it binds) —
   `0.0.0.0:PORT` publishes on every interface regardless of what the host
   firewall's default policy claims, because Docker inserts its own
   forwarding/NAT rules ahead of most generic host policy in its default
   iptables mode.
2. **Docker-managed rules and backend differences**: identify which iptables
   backend Docker is actually manipulating (legacy vs nftables-backed) —
   this must match what `praxis-firewall-audit` found for the host, or the
   two are managing different rule sets and neither sees the other's state.
   Also check whether Docker's `iptables` integration is enabled at all
   (`"iptables": false` in daemon.json is a real, if unusual, configuration
   that changes everything about this analysis).
3. **UFW interaction specifically**: Docker's default behavior bypasses UFW
   rules for published ports in common configurations — do not assume "UFW
   denies this port" means a published container port is actually blocked;
   verify directly rather than trusting UFW's stated policy alone when
   Docker is present.
4. **Cluster behavior — only when k3s/Kubernetes is actually present and
   running on this host.** Do not produce CNI/NetworkPolicy analysis for a
   host that doesn't have a cluster; check for it first (`systemctl status
   k3s`/`kubectl get nodes` equivalent) and report "not present" plainly if
   so rather than a generic answer. When present: identify the CNI in use
   (k3s defaults to flannel), whether any NetworkPolicy objects exist and
   what they actually restrict (absence of any NetworkPolicy generally
   means "all pod traffic allowed" for most CNIs, which is itself a finding
   worth stating), and Service type (ClusterIP/NodePort/LoadBalancer) for
   anything in scope.
5. **External exposure verification from an approved vantage point**:
   confirming a published port is actually reachable from outside is a
   scan-like action and goes through `praxis-network-scan`'s authorization
   requirements — this skill can state what *should* be reachable per
   config; verifying it empirically from an external vantage point is a
   separate, separately-authorized action.

## Absolutely prohibited

- Blindly editing container-runtime-managed chains (`DOCKER`, `DOCKER-USER`,
  `DOCKER-ISOLATION-STAGE-*`) or CNI-managed chains — these are
  regenerated/overwritten by their owning component and hand-edits are both
  fragile and likely to be silently reverted or to break the component's
  own logic.
- Assuming `DOCKER-USER` (or any other specific chain) exists for every
  backend/version — verify its actual presence before referencing it; some
  Docker versions/configurations don't create it, and nftables-backed
  Docker uses different chain names than the legacy-iptables mode.

## Source material

Docker's own networking and iptables documentation
(https://docs.docker.com/engine/network/packet-filtering-firewalls/) is the
authoritative reference for Docker's specific interaction with the host
firewall — consult it directly for whichever Docker version/mode is
actually in use, since this behavior has changed across Docker releases.
