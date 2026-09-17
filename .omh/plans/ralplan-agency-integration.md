# Ralplan: Agency Agents → Noesis Hermes Bot Profiles — Consensus Plan

- **Slug**: agency-integration
- **Date**: 2026-09-16
- **Process**: OMH Ralplan (Planner → Architect → Critic consensus)
- **Rounds**: 2 (consensus reached Round 2)
- **Scope**: PLAN ONLY. Zero live Hermes state is created or modified by this plan. Deployment happens only after the operator review gate (T17).

---

## 1. Consensus Status

| Round | Planner | Architect | Critic |
|-------|---------|-----------|--------|
| 1 | Proceed — 3-tier (28 live / 279 committed catalog / router plugin) | APPROVE_WITH_NITS (A1–A9 + O1–O3) | REQUEST_CHANGES (C1–C3 + W1–W4) |
| 2 | Revised — adopted C1 2-tier restructure; answered all 20 IDs | APPROVE_WITH_NITS — 20/20 prior concerns RESOLVED; nits N1–N6 | APPROVE_WITH_RESERVATIONS — C1b/C2b confirmed resolved; W1b–W7b |

**CONSENSUS: REACHED (Round 2).** All three roles in the APPROVE family; remaining items are clarifying
amendments folded into §5 below — none block execution.

## 2. Revision Summary (Round 1 → Round 2)

The Critic's simplicity test (C1) changed the architecture: **Tier B (279 committed generated spec dirs,
~5 MB) was deleted entirely.** The repo now holds only control files; specs generate on demand into a
gitignored scratch dir. This eliminated the plan's largest liabilities (forever-bloat, catalog drift
surface, unreviewable 5 MB commits) and shrank the B2 pause-gate commit to ~12 files.

Round 2 also added: the three-tree real-mode parity gates for the noesis apply-script migration
(A1 + C2b), the `--verify-idempotent` canary as a hard precondition of the first live wave (C2a),
the 18-agent 1-per-division cap with routing smoke-test exit (C3), two-field model/provider
representation (A3), a three-layer reviewer-guard (W4), and a named drift-check cadence (O1/W1).

## 3. Final Architecture

**Two tiers.** Tier A = exactly **18 live Hermes profiles** (`agency-<slug>`, one per division across
all 18 divisions; wave 1 = 8 core divisions, wave 2 = 10), curated in `agency/curation.yaml`.
Tier C = the **vendored upstream lazy-router plugin** (`agency-agents-router`, built by upstream
`scripts/build-hermes-plugin.py` then vendored byte-verified) covering the full 279-agent catalog via
search/inspect/load/delegate — bodies live once in `data/agents.json`, never duplicated in specs.

**Single generator.** `agency/convert.py` (stdlib only) is the only producer of specs
(`--promote`, `--preview`, `--full-tree` into gitignored `agency/.scratch/`), the extraction-coverage
report, and the cross-reference layer. `--check` proves the committed control files match the pinned
upstream commit + a fresh plugin build.

**Join key = slug identity** across curation, specs, overlay, and router.

**Apply layer.** New roster-driven `scripts/apply-agency-profiles.sh` (runtime roster emitted from
`curation.yaml` + pinned upstream — never hardcoded) shares `scripts/lib/apply-common.sh` with the
migrated `apply-noesis-profiles.sh`. Migration gated by three byte-identical tree diffs (dry-run
parity; A1 pre/post scratch-HOME real-mode; C2b old-inline vs new-lib extraction-agnostic) plus a
rollback tag + recorded sha256.

**Ansible.** `hermes_profiles` role parameterized around one var `hermes_profiles_fleets` driving both
configure and validate with a cross-check task (A5); agency toggle default-off; agency-only fleets
rejected at entry (A7).

## 4. Task Graph (renamed to kill the task-ID/feedback-ID collision, N5/W5b)

> Phase letters are kept for readability; task IDs are now T-numbers in dependency order.
> `depends_on` uses T-numbers.

| Task | Was | Depends on | Complexity | Summary |
|------|-----|-----------|------------|---------|
| T01 | A0 | — | small | Pin upstream commit in `agency/upstream/SOURCE`; vendor MIT `LICENSE` verbatim; `ATTRIBUTION.md`; `README.md` skeleton (incl. O1 cadence, W2 estimate, O3 rollback appendix placeholder) |
| T02 | A2 | — | small | `scripts/check-agency-names.py` pre-flight audit: 279 unique slugs, zero collision with noesis fleet / `~/.hermes/profiles`; negative test |
| T03 | A1 | T01 | medium | `agency/curation.yaml`: exactly 18 agents, 1/division (wave 1: engineering, research, strategy, operations, security, data, product, finance; wave 2: remaining 10); tier class, toolset class, router-text description, rationale; reviewer-class default reviewer-only |
| T04 | E0 | T01 | small | **Build then vendor** plugin: run upstream `build-hermes-plugin.py`, vendor output to `agency/integrations/hermes-plugin/`; `.gitattributes linguist-generated` for `data/agents.json`; plugin README (install target, regen, coexistence contract) |
| T05 | B0 | T01,T02,T03 | large | `agency/convert.py`: fuzzy emoji-header section extraction → Noesis SOUL.md; per-agent `agent.yaml` (two-field model `deepseek/deepseek-v4-flash` + provider `nous`, provenance block, reviewer-guard mapping); verbatim `agency-persona.md` with provenance header; modes `--promote/--preview/--full-tree/--check/--materialize-plugin`; **Tier A summary** `extraction-coverage.md` (W6b: 18-row committed summary; full 279-row table only under `--full-tree` into scratch) |
| T06 | E1 | T04,T05 | small | `agency/integrations/prefer-live.yaml` overlay (18 slugs + instruction); `--promote` appends slug-specific roster note to Tier A SOUL.md; `--materialize-plugin` composes overlay into scratch plugin copy; `--check` asserts overlay == curation slugs |
| T07 | B1 | T05,T06 | medium | `agency/validate-specs.py`: schema, collisions, provenance, two-field model check, **one shared secret-scan regex** (N3/W4b), persona body identity modulo header (N2/W3b), per-tier required sections (Tier A 100% core), cosine > 0.85 description uniqueness, reviewer-guard, Tier A count == 18; `--full-tree` mode flags hollow-SOUL candidates without failing (W3) |
| T08 | C0 | — | medium | Extract `scripts/lib/apply-common.sh` (verify_lane taking model AND provider separately; run/dry-run wrapper; create/refresh primitives; path tokens); bash -n + shellcheck; 1:1 origin mapping |
| T09 | B2 | T05,T06,T07 | medium | **Commit + PAUSE GATE**: `.gitignore` (scratch, apps/* node_modules) before any `git add`; promote 18 + full-tree + validate both modes; spot-check ≥ 3 conversions; commit ONLY control files (~12 files); push + verify; **operator sign-off on the 18-agent shortlist before Phase 2** |
| T10 | C1 | T08,T09 | large | `scripts/apply-agency-profiles.sh`: runtime roster emitter (name\|profile\|wave\|model\|provider\|cwd); `--dry-run/--wave/--profile/--no-model-tuning/--verify-idempotent/--no-regen`; **staleness = per-agent spec existence vs curation live set, then content hash** (C1b); auto-invokes converter when stale (no-op under `--no-regen` for ansible, N6); O2 apply-side secret assertion; W4 apply filter (exit 3); create-then-surgical-config; verify_lane on exact two-field pair, failed lane keeps previous model; PLAN-ONLY dry-run evidence |
| T11 | C2 | T08 | medium | Migrate `apply-noesis-profiles.sh` onto the lib (hardcoded ROSTER kept in-scope). Gates in order: A9 tag `pre-apply-common-lib` + sha256 in commit message → A1 scratch-HOME real-mode pre/post byte-diff → C2b old-inline vs new-lib extraction-agnostic scratch diff; dry-run byte-parity as fast pre-gate |
| T12 | D0 | T10 | medium | Ansible: `hermes_profiles_fleets` var (fleet dicts) drives install + configure; A7 assert (agency requires noesis); defaults preserve today exactly |
| T13 | D1 | T12 | small | `validate.yml` derives expected sets from the same var (A5); **cross-check: hardcoded noesis ROSTER slugs == `noesis-roster.yaml` slugs** (W1b); configure-vs-validate disagreement fails loudly |
| T14 | D2 | T12 | small | Toggles: `noesispraxis_enable_agency_profiles: false` in group_vars + role defaults; role-internal gating; master-stack.yml unchanged except comments |
| T15 | D3 | T13,T14 | small | Non-mutating verification: `--syntax-check`, `--check` run; agency stage dir absent at default toggle; zero live writes |
| T16 | F0 | T06,T09,T10,T15 | small | Complete `agency/README.md` (converter/apply/ansible usage, O1 cadence = pre-commit hook + monthly cron 1st 09:00 + named owner, W2 ~30–45 min re-pin estimate, O3 rollback appendix with **numbered file-touch checklist** per W4b); `scripts/install-hooks.sh` + pre-commit hook (negative test); `ROUTING-SMOKE.md` template (18 divisions × query rows + winner column) |
| T17 | F1 | T16 | small | `agency/REVIEW-GATE.md`: checklist + referenced transcripts + **two hard deployment preconditions** — (1) C2a canary zero-change before wave 2; (2) C3 routing smoke test recorded before any expansion past 1/division; go/no-go section; proof of zero live mutation (`ls ~/.hermes/profiles`) |
| T18 | — | post-gate | small | **Post-review-gate (out of scope, named for ownership, N4/W2b):** run `--materialize-plugin` + stage into `HERMES_HOME` plugins dir + idempotent `plugins.enabled` update; `--check` extended to compare materialized output vs vendored+overlay; re-materialize required after every re-pin |

## 5. Consensus Amendments (accepted clarifications folded into the tasks above)

| ID | Source | Amendment |
|----|--------|-----------|
| N1/W7b | Architect/Critic | E0/E1 run before the B2 commit: T09 now depends on T04+T05+T06+T07; the pause-gate commit provably contains the vendored plugin and overlay |
| N2/W3b | Architect/Critic | Persona identity check defined as: strip the single provenance header block, then byte-compare the body to upstream; header must contain the pinned commit |
| N3/W4b | Architect/Critic | One secret-scan regex in one sourced location (`(?i)\b(api[_-]?key\|access[_-]?token\|password\|secret\|bearer)\b\s*[:=]` with placeholder allowlist), used identically by validator and apply |
| N4/W2b | Architect/Critic | Plugin materialization/install owns task T18 (post-gate); `--check` covers materialized-vs-vendored drift |
| N5/W5b | Architect/Critic | Task IDs remapped to T-numbers (§4); feedback ledger keeps A/C/O/W/N IDs |
| N6 | Architect | Ansible-materialized scratch → apply script `--no-regen`; precedence documented in T10/T12 |
| W1b | Critic | validate.yml cross-checks hardcoded noesis ROSTER against `noesis-roster.yaml` (T13) |
| W6b | Critic | `extraction-coverage.md` = committed Tier A 18-row summary; full 279-row table is `--full-tree` scratch output only |
| C1b | Critic | Scratch staleness keys on per-agent spec **existence** vs curation live set before input-hash freshness (T10) |
| W4b | Critic (recovered) | F0 promotion runbook is a numbered file-touch checklist (T16) |

Critic's minimum-viable-test eliminations (monthly cron, materialize mode, prefer-live as separate file,
noesis roster derivation) are recorded as **post-consensus simplification candidates** — non-binding,
revisit at the review gate.

## 6. Risks (severity-ranked)

1. **high** — Live-profile pollution via promotion beyond the curated 18 → apply consumes only converter
   scratch specs keyed to curation.yaml; validator asserts count == 18; per-wave explicit go at review gate.
2. **high** — Stale/hand-edited scratch specs (secret injection, reviewer toolset escalation) →
   converter auto-invoke on staleness; O2 two-layer secret scan; W4 three-layer reviewer-guard.
3. **high** — Regression in the live 16-profile noesis fleet from lib extraction / Ansible
   parameterization → three byte-identical tree gates; `pre-apply-common-lib` tag + sha256 rollback.
4. **medium** — First real-mode apply misbehaving in an idempotently-undetectable way → C2a canary
   hard precondition; failure aborts and triggers the O3 runbook.
5. **medium** — Router/profile double-recall for Tier A → prefer-live overlay + SOUL.md roster notes,
   both generated from curation.yaml, `--check`-enforced.
6. **medium** — Unvalidated model IDs (prior incident class) → proven two-field pair only; verify_lane
   smoke before any model write.
7. **medium** — Upstream drift vs vendored plugin → pinned commit; monthly `--check` re-runs builder
   and byte-compares; W2-documented re-pin (~30–45 min).
8. **low** — Description homogeneity degrading router quality → cosine > 0.85 validator failure;
   wave-2 routing smoke test.
9. **low** — apps/ node_modules git noise → app-level .gitignore before any add (prior incident).

## 7. Open Questions — RESOLVED via ~/open-questions.md (operator decision record, 2026-09-16)

| # | Question | Decision | Consequence for the plan |
|---|----------|----------|--------------------------|
| 1 | Tier A reporting structure | **Yes — `reports_to: noesis-core`** on all 18. Tier A = subordinate advisory specialists; structured outputs (recommendation, confidence, assumptions, requested tools, risk class, escalation requirement); no autonomous sibling dispatch; no financial/deployment/credential/destructive tools without separate capability grant | Converter emits the reporting contract into every Tier A SOUL.md + agent.yaml `collaboration` block; validator asserts `reports_to: noesis-core` on all 18 |
| 2 | Router install scope | **Fleet-wide, default/base profile only** — never copied into the 18 profiles | T18 stages the materialized plugin once into the default profile's plugins dir; per-profile install explicitly out of scope (drift + audit-boundary rationale) |
| 3 | `specialized/`/`security/` exclusions | **No blanket exclusion — include in catalog, advisory default, policy-gated activation** | Converter emits a `risk:` label block on every generated spec (class: advisory, privileged_tools/secret_access/autonomous_execution: false, requires_supervisor: true, requires_human_approval_for: [production_changes, security_policy_changes, credential_rotation, wallet_operations, financial_transactions, data_exfiltration]); validator asserts the block on all specs |
| 4 | Retire noesis hardcoded ROSTER | **Yes — in-scope completion criterion, not deferred.** Controlled migration: extract to declarative source behind the three parity gates, retire the inline array in the same bounded change set once gates are green | T11 scope EXTENDS: after gates pass, remove the hardcoded ROSTER (rendered from `profiles/noesis-roster.yaml`); validator gains the no-CI analog — fails if any apply script contains a profile list not derived from a declared roster source (T07/T13) |

Additional acceptance gates adopted from the decision record:
- Router `prefer-live` is a **deterministic pre-ranking resolver** (normalize intent → match live profiles first → suppress router candidates whose slug/alias/division/capability overlaps a live profile → router recall only when no live match or explicit `router_exploration: true`), not prompt-text guidance. Suppression enforced in the materialized plugin layer (T06/T18).
- Router output is provenance-tagged: upstream URL, pinned commit SHA, source path, converter version, generated timestamp.
- Plugin build verification: pinned revision + build-script checksum + rebuilt byte hash vs vendored artifact + no generated catalog in Git except review fixtures.
- Apply runs write structured audit records: input roster hash, upstream pin, installed profile list, plugin hash, rollback target.
- Secret-shape scan hard-fails (no redact-and-continue) on imported source AND generated artifacts (already O2; extended to source material).
- Wave composition is frozen: wave 1 = 8, wave 2 = 10; additions require recorded smoke-test artifact + explicit curation change.
- Ansible role fails when agency-enabled and fleet/profile cross-check is inconsistent, and fails for agency-only fleets (A7 — already in plan).

## 8. Amendment A — operator-directed, 2026-09-16 (post-T09 gate)

**Finding (raised at the pause gate, ruled in-scope by operator):** the
noesis fleet's own model lanes are collateral damage of the dead
NOUS_API_KEY (2026-09-16). `scripts/apply-noesis-profiles.sh` hardcodes
`deepseek/deepseek-v4-flash @ nous` for **noesis-core, noesis-scribe, and
noesis-grid**; `profiles/noesis-roster.yaml` `model_routing.default` records
the same dead lanes. Live profile configs under `~/.hermes/profiles/` set in
August 2026 still point at those lanes and will fail until migrated.

**Scope added:**
- **T12a (extends T12):** when the hardcoded ROSTER is retired, migrate the
  three dead nous lanes in `profiles/noesis-roster.yaml` to the proven
  `kimi-k2.7-code @ kimi-coding` lane. OpenRouter lanes (already working)
  are untouched. The dead-key migration is a **roster-source fix only** —
  live `~/.hermes` profile configs change solely through the verified apply
  path (verify_lane gate); no direct live edits.
- **T12b:** the lane migration rides the same three parity gates as the
  ROSTER retirement (a model-lane change must not alter apply behavior for
  the 13 unaffected profiles; gates detect any drift).

## 9. Plan-Level Acceptance Criteria

- agency/ subtree contains ONLY: convert.py, curation.yaml (18), extraction-coverage summary,
  attribution/licensing, upstream pin, vendored byte-verified plugin, prefer-live.yaml overlay,
  README (O1/W2/O3), REVIEW-GATE.md. Zero committed per-agent spec dirs.
- Converter `--promote/--preview/--full-tree/--check/--materialize-plugin` all work from pinned
  upstream + curation.yaml; Tier A core-section coverage 100%.
- Apply script runtime-roster-driven, dry-run clean, O2 + W4 + C2a enforced; noesis migration passes
  all three gates with rollback artifacts.
- Ansible: one var both sides + cross-check, agency default-off, agency-only rejected, syntax +
  check-mode clean.
- **Plan-only constraint honored end to end: zero live profiles created or modified.**

---

*Source plans archived: Round 1 at
`~/.hermes/cache/delegation/subagent-summary-0-20260916_134049_064448.txt` (35.5 KB);
Round 2 at `~/.hermes/cache/delegation/subagent-summary-0-20260916_140320_985068.txt` (55 KB).
Review transcripts under `~/.hermes/cache/delegation/live/deleg_*/task-0.log`.*
