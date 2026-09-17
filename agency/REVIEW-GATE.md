# REVIEW GATE — Agency Tier A wave deployment (T17)

> **Status: PENDING OPERATOR REVIEW.** Nothing in this file authorizes a
> live apply. Waves apply only after an explicit operator go (Amendment A).
>
> Plan: `.omh/plans/ralplan-agency-integration.md` (§4 T-tasks, §8/§9
> amendments). Rollback: `agency/README.md` § "Rollback appendix (O3)".

## Delivered evidence (all committed + pushed)

| Item | Where | Commit |
|------|-------|--------|
| Curation (18 agents, 2 waves) + rationale | `agency/curation.yaml` | `d0f751d` |
| Converter + vendored lazy-router plugin + prefer-live overlay | `agency/convert.py`, `agency/integrations/` | `d0f751d` |
| Three-layer validator + secret scan + cosine guard | `agency/validate-specs.py`, `agency/secretscan.py` | `d0f751d`, `7930b60` |
| Roster-driven apply scripts (noesis + agency) + shared lib | `scripts/apply-*.sh`, `scripts/lib/apply-common.sh` | `7930b60` |
| Roster lane migration (kimi), `terminal_cwd: .` ground truth | `profiles/noesis-roster.yaml` | `7930b60` |
| Parity tag | `pre-apply-common-lib` @ `d0f751d` | pushed |
| Ansible fleet layer (A5/A7/W1b, agency default-off) | `~/projects/noesis-ansible` `b8cd3ed` | pushed |
| Ops docs, hooks (negative-tested), routing template | `agency/README.md`, `scripts/hooks/pre-commit`, `scripts/install-hooks.sh`, `ROUTING-SMOKE.md` | this change set |

## Verification record

- **Gates 1–3 (noesis apply parity)**: dry-run stdout+stderr byte-identical
  old-vs-new; real-mode tree parity (content-only, timestamped backup
  filenames excluded); idempotent re-apply. Gate trees under `/tmp` (not
  durable); transcripts under `~/.hermes/cache/delegation/live/deleg_*/task-0.log`.
- **Wave-1 smoke (disposable home `/tmp/agency-real`)**: 8/8 profiles
  created, SOUL.md installed, descriptions persisted in `profile.yaml`.
  Audit record: ts `2026-09-17T00:25:24Z`, status ok,
  roster_sha256 `c56f9dbe5fd9110d7027729434d6f02270ae9500b0d5a41b96572e8d2b009bdc`,
  plugin_sha256 `1ae6e0e9c1c0b3f7a9af95ed3dd76a36db406b345588f8c8999fd60b40a5ee08`.
- **Validator**: exit 0; description-uniqueness cosine < 0.85.
- **Ansible (T15)**: `--syntax-check` OK; `--check` 0 failed; role validate
  derived the 16-profile expected set and matched `hermes profile list`;
  zero live writes (17 → 17 profiles); agency stage dir absent at default
  toggle.

## Proof of zero live mutation (refresh before signing)

```bash
ls ~/.hermes/profiles | wc -l            # expect 17
ls ~/.hermes/profiles | grep -c '^agency-' || echo "0 agency profiles live"
git -C ~/projects/noesis-agent-stack status --short   # expect clean
```

Current reading at gate preparation: **17 profiles, 0 agency, tree clean.**

## Checklist (operator)

- [ ] Read `agency/curation.yaml` — all 18 agents + rationale acceptable.
- [ ] Confirm gates 1–3 + wave-1 smoke evidence above (or re-run
      `scripts/apply-agency-profiles.sh --home /tmp/review-probe --wave 1 --dry-run`).
- [ ] Confirm T15 ansible evidence (or re-run the two `--check` commands).
- [ ] Re-run the zero-mutation proof block above.
- [ ] Decide GO/NO-GO below.

## Hard deployment preconditions

1. **C2a canary zero-change before wave 2.** After wave 1 is live and
   soaked, re-apply wave 1 (`--wave 1`) and require a zero-change result
   (`created=0 refreshed=0 skipped=8` — all skipped). Any drift aborts
   wave 2 and triggers the O3 rollback appendix.
2. **C3 routing smoke test before any expansion past 1/division.** All 18
   rows of `ROUTING-SMOKE.md` recorded with Tier A winners ≥16/18 and
   cosine < 0.85. This is a precondition for *expansion*, not for wave 2;
   wave 2 (the remaining 10 curated agents) does not require it.

## Go / No-Go

- [ ] **GO wave 1** (8 agents) → run:
      `env HERMES_HOME=$HOME/.hermes ./scripts/apply-agency-profiles.sh --wave 1 --no-model-tuning --yes`
      (or via ansible: `-e noesispraxis_enable_agency_profiles=true` with the
      noesis fleet enabled, A7).
- [ ] **GO wave 2** (10 agents) — only after precondition 1 is recorded here.
- [ ] **NO-GO** → record reason: ______________________

Operator: ____________   Date: ____________
