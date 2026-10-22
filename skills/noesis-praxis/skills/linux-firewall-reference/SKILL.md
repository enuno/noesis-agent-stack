---
name: linux-firewall-reference
description: Noesis-adapted firewall-only reference (UFW/firewalld/raw nftables/iptables) for inspecting and changing Linux host firewall policy. Adapted from linux-skills' linux-firewall-ssl package with the Certbot/SSL-certificate material removed (out of scope for this skill tree). Use alongside praxis-firewall-audit (investigation) and praxis-firewall-change (execution) for backend-specific command reference.
license: MIT
metadata:
  portable: true
  compatible_with: [claude-code, codex, hermes]
  author: Peter Bamuhigire
  author_url: techguypeter.com
  adapted_by: noesis-praxis
  adaptation_note: >
    Adapted from upstream linux-firewall-ssl (peterbamuhigire/linux-skills).
    All Certbot/SSL/TLS-certificate content (the "SSL Certificates (Certbot)"
    and "Troubleshoot Renewal Failure" sections, and the ssl-config.md /
    certbot-reference.md references) was removed -- it is unrelated to
    firewall management and out of scope for this skill tree per the parent
    task's explicit instruction not to import certificate-management
    procedures merely because they share a source package with firewall
    content. All remaining content is the original author's firewall
    material, otherwise unchanged. See provenance/manifest.yaml for the
    pinned upstream commit.
---
# Linux Firewall Reference (UFW / firewalld / raw netfilter)

## Distro support

Two-family skill. **UFW** is the Debian/Ubuntu firewall; the RHEL family
(Fedora, RHEL, CentOS Stream, Rocky, Alma, Oracle) uses **firewalld** — a
zone-based model, not a flat allow-list. The body below uses UFW/Debian; full
RHEL detail is in
[`references/firewalld-reference.md`](references/firewalld-reference.md).

| Concept | Debian/Ubuntu | RHEL family |
|---|---|---|
| Firewall | `ufw` | `firewalld` (`firewall-cmd`) |
| Show rules | `ufw status verbose` | `firewall-cmd --list-all` |
| Allow HTTP/HTTPS | `ufw allow 80,443/tcp` | `firewall-cmd --permanent --add-service={http,https}` |
| Allow a raw port | `ufw allow 9100/tcp` | `firewall-cmd --permanent --add-port=9100/tcp` |
| Apply changes | immediate | `firewall-cmd --reload` (permanent vs runtime!) |
| Enable on boot | `ufw enable` | `systemctl enable --now firewalld` |
| Backend (raw netfilter) | nftables (`nft`); `iptables` = `iptables-nft` shim | nftables (`nft`); `iptables` = `iptables-nft` shim |
| nftables persistence | `nftables.service` → `/etc/nftables.conf` | `nftables.service` → `/etc/sysconfig/nftables.conf` |
| iptables persistence | `netfilter-persistent` → `/etc/iptables/rules.v4` | `iptables-save` (legacy retired on RHEL 9+) |

Both UFW and firewalld emit **nftables** rules through the kernel's `nf_tables`
subsystem — they are front-ends over the same backend. Drop to raw `nft` /
`iptables` only for rules a front-end can't express (custom NAT, port
forwarding), to read what a front-end produced, or on hosts managed directly.
Full detail in
[`references/nftables-and-iptables.md`](references/nftables-and-iptables.md).

## Use when

- Managing UFW/firewalld rules on a server.
- Reading raw nftables/iptables state underneath either front-end.

## Do not use when

- The task is certificate/TLS management — out of scope for this adapted
  package; use your own TLS tooling's documentation directly (the upstream
  `certbot-reference.md`/`ssl-config.md` were deliberately not imported here).
- The task is broader web stack tuning; that's outside firewall scope.
- The task is user access or SSH key management.

## Required Inputs

| Artefact | Source | Required? | If absent |
|---|---|---|---|
| Host, management path, and distro | Operator or inventory | yes | Inspect only; do not select UFW/firewalld by guesswork |
| Required services, sources, ports, and zones | Network/application owner | for firewall change | Do not open a port or range |
| Change window and rollback access | Operations owner | for mutation | Return a proposed rule plan instead |

## Capability Contract

Read/search inspection may be read-only. Firewall mutation requires explicit
change authority — see `praxis-firewall-change` for this skill tree's actual
authorization/execution procedure; this reference package documents backend
commands, it does not itself grant authority to run them.

## Decision Rules

| Condition | Action | Failure avoided |
|---|---|---|
| Front-end firewall is active | Change rules through that front end | Reload overwriting hand-written nftables rules |
| Remote default-deny change | Preserve SSH and established traffic; test from a second session | Administrator lockout |

## Anti-Patterns

- Opening a broad port range for convenience. Fix: map each listener to an approved service.
- Mixing raw nftables rules with an active UFW/firewalld owner. Fix: use one control plane.
- Enabling default-deny over the only SSH session. Fix: preserve and test a second session.

## References

- [`references/ufw-reference.md`](references/ufw-reference.md)
- [`references/firewalld-reference.md`](references/firewalld-reference.md)
- [`references/nftables-and-iptables.md`](references/nftables-and-iptables.md)

**This skill is self-contained.** Every command below is a standard tool on its
family — `ufw` on Debian/Ubuntu, `firewall-cmd` (firewalld) on the RHEL family.

## UFW Firewall

```bash
sudo ufw status verbose                 # current rules
sudo ufw status numbered                # numbered for easy deletion

# Standard web server rule set:
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable

# Add a rule
sudo ufw allow <port>/tcp
sudo ufw allow from <ip> to any port 22   # restrict SSH to trusted IP

# Remove a rule
sudo ufw status numbered
sudo ufw delete <number>

# Rate limiting (brute-force protection)
sudo ufw limit 22/tcp

# Logging
sudo ufw logging on
sudo tail -f /var/log/ufw.log
```

---

## Raw netfilter (nftables / iptables)

UFW and firewalld are the recommended front-ends; both compile down to
**nftables**. Manage rules through the front-end on a normal host. Drop to raw
`nft`/`iptables` only for what a front-end can't express (custom NAT, port
forwarding), to read what a front-end produced, or on directly-managed hosts.
**Do not mix hand-written rules with an active front-end** — it owns its
tables and overwrites them on reload.

```bash
# View — works regardless of front-end (shows ufw/firewalld output too)
sudo nft list ruleset
sudo nft -a list chain inet filter input    # -a = rule handles (needed to delete)
sudo iptables -S                             # legacy command surface (nft shim)

# A safe default-deny inet/filter ruleset (loopback + established + SSH + web).
# Load atomically; `flush ruleset` makes it idempotent:
sudo nft -c -f /etc/nftables.conf            # -c = syntax check only (dry run)
sudo nft -f /etc/nftables.conf               # apply (replaces live ruleset)

# Delete one rule by handle; flush a chain
sudo nft delete rule inet filter input handle 7
sudo nft flush chain inet filter input

# NAT / masquerade / port forward
sudo nft add rule ip nat postrouting oifname "eth0" masquerade
sudo nft add rule ip nat prerouting tcp dport 80 dnat to 192.0.2.10:8080

# Persist: Debian → /etc/nftables.conf, RHEL → /etc/sysconfig/nftables.conf
sudo sh -c 'nft list ruleset > /etc/nftables.conf' && sudo systemctl enable --now nftables

# IP routing table
ip route show
sudo ip route add 10.20.0.0/16 via 192.0.2.1 dev eth0
```

> Default-deny on a remote host can lock you out: always keep an `accept` rule
> for SSH and for `ct state established,related` **above** the drop, and test
> in a second session before disconnecting.

Full detail — iptables vs nftables, NAT, sets/maps, the front-end backend
relationship, `iptables-save`/`netfilter-persistent`, migration, and
`ip route` persistence — is in
[`references/nftables-and-iptables.md`](references/nftables-and-iptables.md).

---

## Scripts — included as reference only, execution blocked

The upstream `sk-nft-show`/`sk-nft-apply` scripts are included below as
**read-only reference material, not as runnable tools in this profile.**
Both scripts (per their own `common.sh` sourcing convention) depend on a
shared `/usr/local/lib/linux-skills/common.sh` distro-detection library
installed by that repo's own `install-skills-bin` mechanism — **neither the
library nor that installer is vendored into this skill tree** (per this
skill tree's maintenance policy: reusable dependency provisioning belongs in
noesis-ansible, not inside this skill tree, and this installation task does
not install system packages or run upstream installers).

| Script | Core? | Purpose (as documented upstream) |
|---|---|---|
| `scripts/sk-nft-show` | yes | Read-only view of the raw netfilter layer: active front-end, live nftables ruleset, iptables backend mode, persistence state, IP routing table. Both families. |
| `scripts/sk-nft-apply` | no | Apply a raw nftables ruleset from a built-in profile (web-server/ssh-only) or a `.nft` file; syntax-checks, dry-run-capable, asks before replacing the live ruleset; refuses while ufw/firewalld is active unless `--force`. |

If this capability is wanted, it belongs as a noesis-ansible-managed
dependency + role, not as a script run directly from this skill tree.
