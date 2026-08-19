# Charter Baseline & Gap Assessment — 2026-08-19

**Status:** Baseline (Phase 1 of charter implementation)
**Author:** Noesis Praxis (Hermes supervisor session)
**Scope:** `noesis-agent-stack` + `noesis-ansible` vs. the Secure Hermes + OpenClaw Agent Stack charter

---

## 1. Charter summary (canonical contract)

- Two persistent agents only: **Noesis Praxis** (Hermes, master/supervisor/policy decision point) and **Noesis ClawDev** (OpenClaw, persistent local development/execution worker). All others ephemeral.
- `noesis-agent-stack` = behavioral/policy contract; `noesis-ansible` = deployment/operations. NoosphereOS is explicitly **not** the active target.
- Secrets: Bitwarden Secrets Manager project `72974d0e-81af-4678-bab7-b46000985859` is the authoritative store. No plaintext secrets anywhere.
- Providers: subscription-first (Claude, ChatGPT/Codex, Kimi Code, Nous), metered exceptions (OpenRouter, Venice-private-only).
- Risk tiers R0–R3 with mandatory human approval for R3 via canonical action manifest + signed grant.
- Model catalog automation: discovery → candidate → validation → evaluation → scorecard → PR → shadow → canary → approved signed catalog.
- Telemetry, circuit breakers, last-known-good rollback.

## 2. Repository inventory (verified 2026-08-19)

### noesis-agent-stack (`~/projects/noesis-agent-stack`, origin git@github.com:enuno/noesis-agent-stack.git)
Present:
- `shared/models.yaml` (v0.1, 274 lines) — provider catalog + profiles; **pre-charter provider set** (anthropic, openai, minimax, ollama, local)
- `shared/policy/global.yaml`, `shared/policy/guardrails.yaml` — existing policy (broker-era)
- `shared/tools.yaml`, `shared/schemas/` (job, event, artifact)
- `platform/routing.yaml` (v0.2.0), `platform/orchestrator.yaml`, `platform/agent-registry.yaml`, `platform/workflows/`
- `agents/noesis-praxis/` — SOUL.md, config.yaml (provider `kimi-coding`, model `kimi-k2-thinking`), HEARTBEAT.md, MEMORY.md, mempalace-SKILL.md, systemprompt.md
- `agents/main-hermes/`, `agents/research-openclaw/`, `agents/subconscious-openclaw/` — legacy broker topology
- `EVALS.platform.yaml`, `SPEC.md`, `WORKFLOWS.md`, `DEVELOPMENT_PLAN.md`, `TODO.md`, `contracts/` (broker, handoffs, ledgers, mempalace), `workspace/`
- `config/stack.yaml` already references `shared/POLICY.global.md` + `shared/GUARDRAILS.global.yaml` — **files do not exist yet**

Missing vs. charter:
- `shared/model-aliases.yaml` — MISSING
- `shared/provider-policies.yaml` — MISSING
- `shared/POLICY.global.md` — MISSING (referenced by config/stack.yaml!)
- `shared/GUARDRAILS.global.yaml` — MISSING (referenced by config/stack.yaml!)
- `platform/profiles.yaml` — MISSING
- `platform/risk-tiers.yaml` — MISSING
- `platform/approval-manifest.schema.json` — MISSING
- `agents/noesis-clawdev/` — MISSING (only research/subconscious OpenClaw exist)
- `catalog/` — MISSING
- `evals/` — MISSING (only root EVALS.platform.yaml, broker-era)

### noesis-ansible (`~/projects/noesis-ansible`, origin present)
Present:
- 35 playbooks, 38 roles, 6 custom modules (`noesis_bws_secret`, `noesis_registry_sync`, `noesis_mcpjungle_onboard`, `noesis_clawvisor_policy`, `noesis_macos_service`, `noesis_vault_rotate`)
- `group_vars/all.yml` — Bitwarden project ID `7173d0ef-…` (noesis_universe) — **differs from charter project ID `72974d0e-…`**
- `inventory/{local,tailscale,production}`, `ansible.cfg` (vault_password_file .vault_pass), `.vault_pass` present + gitignored
- `group_vars/secrets.yml` — stub with comments only (no plaintext secrets; not yet vault-encrypted)
- Recent work: muxd (hub+daemon), moshi/here-herdr, Tailscale auth from Bitwarden, grafana-stack role (uncommitted), OpenClaw docker reset flow
- Uncommitted: README.md, group_vars/all.yml, master-stack.yml, grafana-stack.yml, roles/grafana_stack/

## 3. Live host state (verified 2026-08-19)

- **Firewall:** `nftables.service` **failed**; `netfilter-persistent` **active**; `ufw` inactive. IPv4/IPv6 INPUT policy ACCEPT. → Known attention hotspot #4.
- **Tailscale:** up, `100.106.20.102 noesis-praxis`; DNS config fetch failing (health warning).
- **Public listeners (0.0.0.0/*):** `22` (SSH), `2022` (secondary SSH/ET), `3000` (dokploy), `3210` (jot-app), `8642` (hermes), `8765` (braiins-insights-mcp), `7946` (swarm), `4097` (muxd-hub), `:5900/:6080` localhost-only.
- **Tailscale-bound:** `3080` (logospraxis), `8787` (hermes-webui), `9119` (hermes), `443`, `3333`, `34012`.
- **Docker:** rootless/normal daemon present; containers incl. logospraxis, hermes-webui, otel-collector, braiins-insights-mcp, unifi-mcp, misjustice-*, dokploy, jot-app.
- **bws CLI:** installed v1.0.0; `BWS_ACCESS_TOKEN` not set in this shell; no bws config file. Bitwarden verification pending token.

## 4. Critical gaps (must resolve)

| # | Gap | Impact | Resolution |
|---|-----|--------|------------|
| G1 | Bitwarden project ID mismatch: charter `72974d0e-…` vs ansible `7173d0ef-…` (3 configs + 2 module defaults) | Secret fetches may target wrong project | **RESOLVED 2026-08-19** (operator decision: charter wins). All 5 refs updated to `72974d0e`; project name corrected to `noosphere` (verified via `bws project list`); bws CLI path corrected to `/usr/local/bin/bws` |
| G2 | `BWS_ACCESS_TOKEN` unavailable in shell | Cannot verify Bitwarden secret presence/rotation | **RESOLVED 2026-08-19** — token exists in `~/.zshrc`; verified access to project `72974d0e` (93 secrets, incl. TAILSCALE_AUTH_KEY, MISTRAL_API_KEY, NOUS_API_KEY, VENICE_API_KEY, KIMI_API_KEY) |
| G3 | `shared/POLICY.global.md` + `shared/GUARDRAILS.global.yaml` referenced but missing | config/stack.yaml broken reference | Author canonical files (this session) |
| G4 | No `platform/profiles.yaml`, `risk-tiers.yaml`, `approval-manifest.schema.json` | No machine-readable risk/approval contract | Author (this session) |
| G5 | No `agents/noesis-clawdev/` | Charter's second persistent agent undefined in repo | Author policy/config/runbook (this session) |
| G6 | No `catalog/`, no `evals/` | Model-governance loop has no substrate | Scaffold (this session) |
| G7 | `shared/models.yaml` pre-charter provider set | Provider strategy not reflected in catalog | Additive update (this session); full v2 catalog as follow-up |
| G8 | nftables failed, INPUT ACCEPT, public listeners on 22/2022/3000/3210/8642/8765/7946 | Live exposure | R3 hardening plan documented; **execution requires approval** (Tailscale stays open per operator preference) |
| G9 | Legacy broker topology (main-hermes/research/subconscious) vs charter 2-agent topology | Drift; charter says 2 persistent agents | Keep legacy docs for reference; new charter files are canonical for this phase |

## 5. Work completed this session

- [x] Full inventory of both repos + live host state
- [x] Baseline doc written (this file)
- [x] `shared/model-aliases.yaml`, `shared/provider-policies.yaml`, `shared/POLICY.global.md`, `shared/GUARDRAILS.global.yaml`
- [x] `platform/profiles.yaml`, `platform/risk-tiers.yaml`, `platform/approval-manifest.schema.json`
- [x] `agents/noesis-clawdev/` (AGENT.md, SOUL.md, RUNBOOK.md, config/)
- [x] `catalog/`, `evals/` scaffolding
- [x] `shared/models.yaml` additive charter provider set

## 6. Next actions (pending operator)

1. **Decision G1**: confirm authoritative Bitwarden project; update `noesis-ansible` configs/modules accordingly.
2. **Provide BWS_ACCESS_TOKEN** (or bws profile) so secret presence/rotation can be verified against project `72974d0e`.
3. **Approve R3 hardening plan** (see `docs/hardening-plan-2026-08-19.md` in noesis-ansible) — default-deny inbound, keep Tailscale open, close public listeners.
4. Review & merge this session's commits; then proceed to model-catalog automation (catalog/ + evals/ population) and observability wiring.

---
*Recorded by Noesis Praxis. Evidence: live `ls`/`find`/`ss`/`systemctl`/`docker`/`bws` checks, repo git state, charter text.*
