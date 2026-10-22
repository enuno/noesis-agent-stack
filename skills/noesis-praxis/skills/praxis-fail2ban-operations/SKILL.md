---
name: praxis-fail2ban-operations
description: Inspect fail2ban jails, bans, and false positives; perform approved unban actions or jail/filter configuration changes under separate authorization. Use when investigating why an IP got banned, whether a ban is a false positive, or reviewing jail configuration. Does not install or enable fail2ban.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-fail2ban-operations

Inspect jails, bans, false positives, and perform approved configuration
changes. This skill assumes fail2ban is already installed and running on the
host it's used against — it does not install, enable, or configure fail2ban
as part of this skill's own packaging, and does not do so now.

## Three clearly separated activity tiers

1. **Read-only investigation** (default, no authorization needed beyond
   normal operational access):
   - List active jails and their status (`fail2ban-client status`,
     per-jail status).
   - List currently banned IPs per jail, and why (which filter/log line
     triggered the ban, how many failures, over what window).
   - Review jail configuration (`jail.local`/`jail.d/*.conf`, the filter
     regex in use) to understand what a jail actually matches — do not
     assume a jail's name describes its real matching behavior; read the
     actual filter.
   - Cross-reference a specific banned IP against known-legitimate sources
     (a monitoring prober, a load balancer health check, a known admin IP)
     to assess false-positive likelihood — state the assessment, don't
     silently act on it.

2. **Unban actions** (an operational action, needs its own explicit
   confirmation before executing, even though it's reversible/low-risk
   compared to a config change): confirm which specific IP, which specific
   jail, and the stated reason (false positive vs. temporary business need)
   before running `fail2ban-client set <jail> unbanip <ip>` or equivalent.

3. **Jail/filter/configuration changes** (requires explicit authorization,
   same bar as any other security-control change): changing a filter regex,
   ban time, retry threshold, or jail enable/disable state. State the exact
   delta and its effect (a loosened filter or longer `findtime`/shorter
   `bantime` reduces protection — say so explicitly) before applying.

## Preserve legitimate management access

- Before any unban or config change, confirm it won't itself lock out
  legitimate management access (e.g. don't propose a change that would ban
  the very session being used to manage the host, and check whether an
  "ignoreip" allowlist already covers management sources before assuming a
  ban is risky to management access).
- Record what was verified after any unban or config change (e.g. "confirmed
  <ip> can now reach <service> again" or "confirmed jail X is active with
  new findtime/bantime") — an action without a recorded verification is not
  a completed action.

## What this skill explicitly does NOT do

- It does not install fail2ban, enable its service, or create its initial
  configuration — that is an infrastructure-deployment action outside this
  skill's (read/investigate/approved-change) scope and outside this
  packaging task's authorization.

## Source material

fail2ban's own documentation (https://github.com/fail2ban/fail2ban/wiki) and
`man fail2ban-client`/`man jail.conf` are the authoritative reference for
jail/filter syntax and client commands.
