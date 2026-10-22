---
name: praxis-firewall-change
description: Prepare and, only under explicit per-change approval, execute a minimal firewall rule change with baseline capture and tested rollback. Use when an approved firewall change (add/remove/modify a specific rule) needs to be planned and safely applied. Never resets or flushes tables; never assumes a dry-run proves safety.
version: 1.0.0
license: internal (Noesis Praxis operational skill)
---

# praxis-firewall-change

Prepare and execute ONLY explicitly approved, minimal firewall changes. This
skill assumes `praxis-firewall-audit` has already established current state
and ownership — do not skip that investigation and go straight to a change.

## Required before any change is prepared

1. **Exact host** the change applies to (never "the firewall" generically).
2. **Backend** confirmed active on that host (per `praxis-firewall-audit`'s
   detection) — the change must target the layer actually in effect, not
   whichever tool happens to be convenient.
3. **Owner** of the affected rule set/chain (per the audit's ownership
   attribution) — a change to a Docker-managed or CNI-managed chain needs
   different handling than a hand-maintained UFW/firewalld rule.
4. **Exact rule delta**: the precise rule(s) being added/removed/modified,
   stated unambiguously (source, destination, port, protocol, direction,
   action) — never an approval for "tighten up the firewall" in the
   abstract.
5. **Explicit authorization** for that exact delta, from the person who owns
   the decision — a plan or a recommendation is not that authorization.

## Management-path protection — check this for every change, every time

Before applying any change, explicitly verify the change does not remove
reachability to:
- The current SSH/management session's own path (source IP/interface).
- Tailscale's management path, if present.
- Any cluster (k3s) control-plane or node-to-node paths currently in use.
- Monitoring/collection paths currently relied on.

**Do not treat "I'm connected over SSH right now" as proof the new policy
preserves that connectivity** — the current session's existing connection
can outlive a policy change that would block a *new* connection attempt
(many connection-tracking setups allow established connections through even
after a rule is removed). Verify the policy itself permits a *fresh*
connection on that path, not just that today's session hasn't dropped yet.

## Required sequence

1. **Baseline capture**: save the exact current rule state (full ruleset
   dump for the active backend) before changing anything, with a timestamp
   and the host/backend identified — this is the rollback baseline.
2. **Feasible tested recovery method identified BEFORE applying the change**
   — e.g. a scheduled/out-of-band revert mechanism, console/IPMI access, or
   a known-safe window — not invented after something breaks. If no such
   recovery method is actually available for this host, say so and treat
   that as a blocker, not a detail to skip.
3. **Syntax validation** using whatever the backend actually supports
   (e.g. `nft -c` check mode, `iptables-restore --test`, UFW/firewalld's own
   validation) before any live apply.
4. **Apply the minimal delta** — never a blanket reset/flush/restore-from-
   scratch to achieve a small change.
5. **Independent connection/probe verification** of the specific thing the
   change was meant to affect, from a vantage point that would actually be
   affected by the change (not just "the apply command exited 0").
6. **IPv6 and persistence handled explicitly** — if the intended rule has an
   IPv6 analog, state whether it was also applied or deliberately scoped to
   v4 only; state explicitly whether the change was made persistent across
   reboot and how.
7. **Reconciliation through noesis-ansible**: once verified, the change
   needs to be reflected in the noesis-ansible-managed configuration so it
   survives the next managed run, not just exist as a live, undocumented
   drift from the IaC source of truth.

## Absolutely prohibited

- Unapproved firewall resets or whole-table/whole-chain flushes, ever, for
  any reason, as a way to "start clean" before a small change.
- Blindly mixing management layers (e.g. adding raw `iptables` rules on a
  host actively managed by UFW or firewalld) — this creates exactly the kind
  of silent-shadowing/conflict state `praxis-firewall-audit` exists to
  detect; don't create more of it.
- Assuming current SSH connectivity, by itself, proves a new policy is safe
  (see management-path section above).
- Treating a syntax-check/dry-run pass as proof the change preserves
  connectivity — a dry-run validates syntax, not live reachability; step 5's
  independent verification is what actually proves that.

## Rollback scheduling — documented here, not built or run

This skill documents HOW a rollback-scheduling mechanism (e.g. "revert this
rule automatically if I don't confirm within N minutes") would be verified
before it could be trusted: it would need to be tested against a disposable
target first, confirmed to actually fire within its stated window, confirmed
to not itself require the connectivity it's supposed to restore, and logged
so a missed/failed rollback is detectable. **No such mechanism is built,
scheduled, or executed as part of this skill or this installation task** —
this section exists purely as a design requirement for if/when that
capability is explicitly requested and authorized separately.

## Source material

Same backend-specific official docs as `praxis-firewall-audit`
(`man iptables`/`man nft`, UFW, firewalld, nftables wiki) plus this
environment's own noesis-ansible repository for the actual reconciliation
mechanism — consult that repo directly rather than inventing a playbook,
role, or variable name here.
