# Review Methodology — noesis-praxis Skill Tree

This file defines how every skill in `skills/noesis-praxis/skills/` is
reviewed before being packaged into this repository, and records the actual
review log for each batch of skills added or updated.

## Disposition taxonomy

Every reviewed skill gets exactly one disposition:

- **A — Reviewed and installed unchanged.** The skill's content is used
  verbatim from upstream (byte-for-byte, aside from this repo's own
  provenance bookkeeping which lives outside the skill's own directory).
- **B — Reviewed, Noesis adaptation.** The skill's content was changed before
  inclusion — e.g. an auto-install step was rewritten to fail with an
  actionable prerequisite message instead of silently installing something,
  or a destructive step was separated behind an explicit confirmation. Every
  adaptation records: what changed, why, and where the diff lives
  (`provenance/patches/<skill>/`).
- **C — Staged and blocked.** The skill was retrieved and reviewed but is
  **not** installed into the runtime-discoverable tree. Blocked skills are
  recorded in `provenance/manifest.yaml` with `status: blocked` and a reason,
  but their reviewed source is not copied into `skills/noesis-praxis/skills/`.

## Finding classification

A security finding inside a skill is one of:

1. **Documentation / explicitly-labeled insecure example.** The skill shows
   an insecure pattern only to warn against it or as a worked example clearly
   marked as such. Not itself a reason to adapt or block.
2. **Negative / security test fixture.** Content that exists specifically to
   be caught by a scanner or test (e.g. a skill's own test suite). Not a real
   capability the skill performs.
3. **Legitimate operational capability requiring authorization.** The skill
   describes or can perform a real, consequential action (install software,
   change a cluster, open firewall rules) that a human would reasonably want
   to run themselves after explicit authorization. This is normal for an
   infrastructure skill and is not by itself a reason to block — it is a
   reason to make sure the skill does not perform that action automatically
   or silently, and that destructive variants require explicit confirmation.
4. **Unsafe automatic behavior.** The skill's own instructions have an agent
   perform something consequential (install, mutate, destroy) without a
   confirmation step or without being asked — this is the main trigger for
   disposition B (adapt: add a confirmation/prerequisite gate) or C (block,
   if the behavior cannot be reasonably separated from the skill's purpose).
5. **Suspicious or unresolved.** Anything that could not be explained from
   the skill's own stated purpose and documentation after a full read —
   obfuscated content, destinations unrelated to the skill's stated vendor or
   purpose, or logic that doesn't match its description. Always disposition
   C until resolved; never installed on good faith.

**A clean scanner verdict is not proof of safety, and a reputable vendor name
is not proof of safety.** Both are supporting context only. Conversely, a
scanner "blocked" verdict is not itself proof of malware — it is investigated
against the actual content and classified using the five categories above
before a disposition is assigned. `--force` is never used to bypass a
blocked verdict as a substitute for this review.

## What reviewers specifically check

- Download-and-execute installers (`curl | bash`, `wget | sh`, equivalents).
- Automatic package installation or upgrade run without being asked.
- Credential access, environment-variable dumping, and authenticated
  outbound requests — and exactly which destinations they talk to.
- Privilege escalation, sudoers edits, shell-profile edits, service/systemd
  changes.
- Destructive recovery procedures (resets, wipes, forced deletes).
- A "validator"/"diagnose"/"audit"-labeled skill that actually mutates state.
- Workflow execution, container builds using host credentials, Docker socket
  access.

Bundled scripts are read as text during review. They are never executed as
part of the review process.

## Review log

### Batch 2026-10-22 — initial 22-skill retrieval

See `provenance/manifest.yaml` for the authoritative per-skill table (source
repo, pinned commit, found/corrected path, disposition, deployed location).
Full per-skill review notes (the complete findings each skill was reviewed
against) live in `provenance/reviews/<skill>.md`.

### Batch 2026-10-22 (same day, second pass) — network/security/observability extension

Added: 7 Grafana first-party documentation skills (disposition A, 2 of them
renamed for routing disambiguation against pre-existing promql/logql-named
skills), 2 Grafana Cloud cardinality skills adapted for self-hosted use
(disposition B), 1 blocked Grafana Cloud skill (loki-label-analyzer,
disposition C — see provenance/reviews/grafana-loki-label-analyzer-blocked.md
for the unresolved instruction-injection finding behind that block), 1
firewall reference package adapted from linux-skills (disposition B, SSL/
Certbot content stripped, a sibling claude-dev-suite package deferred as
redundant), and 11 new Noesis-authored operational skills (disposition N —
authored directly against official tool documentation, not a review of
third-party content) covering network scanning, packet analysis, firewall
audit/change/container-interaction, fail2ban operations, and the full
observability lifecycle (deploy-discovery, metrics investigation, dashboard
management, alert management, stack self-health).

10 NetClaw (automateyournetwork/netclaw) packages were reviewed and found to
depend entirely on MCP tool integrations (nmap-mcp, nsm-mcp, analysis-mcp,
packet-buddy-mcp, mcp-grafana, prometheus-mcp-server) not installed in this
Hermes profile. None were installed into the discoverable skill tree. 5 of
the 10 (packet-analysis, nsm-ids-triage, nsm-session-pivot,
network-data-analysis, prometheus-monitoring) had genuinely valuable,
harness-agnostic procedural knowledge worth keeping even unexecutable, and
are preserved as reviewed reference material under
`provenance/reviews/netclaw/` (outside active skill discovery, per this
task's explicit instruction for exactly this situation). The other 5 (3
nmap-* packages with unverifiable safety claims or stealth/evasion
techniques presented as routine, gtrace-path-analysis with no backend to
even inspect, and grafana-observability whose default tool surface allows
unauthorized dashboard/alert mutation) were judged not worth preserving even
as inert text — see `provenance/reviews/blocked-and-deferred.md`.

One subagent-retrieval failure was caught and corrected mid-batch during
the *first* 22-skill batch: a delegated review of `dashed/claude-marketplace`
(k3s) returned corrupted output (verbatim content from an unrelated
tailscale-skill review task). That result was discarded entirely and the
retrieval/review was redone directly against the real clone on disk — see
that batch's manifest entry for the corrected branch (`master`, not `main`)
and commit. No equivalent failure occurred in this second batch's 3
subagents.
