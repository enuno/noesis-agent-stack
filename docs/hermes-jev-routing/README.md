# hermes-jev-routing

Per-turn model routing for the Noesis stack, via the `hermes-jev-routing`
plugin (TypeSafe Jev). Each turn, Jev reads the message, a short excerpt, an
estimated context size, and the spend snapshot, and answers four typed
questions — task kind, complexity, capability demand, reasoning depth. Code
composes those into a **capability tier**, applies budget and cache policy,
and the plugin rewrites the model on the request that is about to go out.

This directory is the feature's documentation set. The machine-readable
artifacts live outside it:

| Artifact | Purpose |
|---|---|
| `platform/hermes-jev-routing.yaml` | Activation policy: which profiles may load the plugin, at what mode, with which data classes |
| `docs/hermes-jev-routing/config/tier-ladder.yaml` | Which model for which tier, per provider, and the chain order |
| `docs/hermes-jev-routing/config/rate-card.yaml` | $/Mtok for the per-token-billed providers |
| `docs/hermes-jev-routing/config/hermes-jev-routing.json` | Tier table — minimax-bound profiles (GENERATED) |
| `docs/hermes-jev-routing/config/hermes-jev-routing.codex.json` | Tier table — openai-codex-bound profiles (GENERATED) |
| `catalog/typesafe-models.yaml` | Canonical catalog entry for `jev-latest` |
| `shared/provider-policies.yaml` → `providers.typesafe` | Data classification, spend model, eligibility |
| `scripts/generate-jev-routing-config.py` | Regenerate the tier tables from the ladder and the LIVE provider catalogues |
| `scripts/apply-jev-routing.sh` | Install + configure + verify, into a profile home |
| `scripts/validate_jev_routing.py` | Validate the policy, the ladder, and the generated configs |
| `scripts/test_jev_routing.py` | Offline regression tests for the tooling |
| `docs/hermes-jev-routing/policy.md` | Egress review, activation preconditions |
| `docs/hermes-jev-routing/runbook.md` | Install, regenerate, verify, roll back |

## Keeping the config honest

A retired model id does not fail at load time. It fails at request time, on a
live session, as an opaque provider error — and the catalog edition of the
plugin does not consult the provider catalogue, so nothing upstream catches
it.

`scripts/generate-jev-routing-config.py` closes that gap. It reads the
ladder, asks each provider what it serves **today**, keeps the first
candidate the provider actually serves, and writes configs that can only
reference live models:

```bash
./scripts/generate-jev-routing-config.py --check   # fail on drift
./scripts/generate-jev-routing-config.py --write   # reconcile
```

The generator also runs the plugin's own `load_router_config` over its
output, so a config that the plugin would reject never reaches a profile.

It does **not** invent prices. Rates live in `rate-card.yaml`, sourced and
dated, and the generator only copies the entries the generated chains
actually reference.

## What it does, in one table

| Tier | Typical turn | Minimax-bound config | Codex-bound config |
|---|---|---|---|
| `quick` | chat, acknowledgement, a one-line question | `MiniMax-M2.5` | `gpt-6-luna` |
| `standard` | explain, operate, a scoped how-to | `MiniMax-M2.7` | `gpt-5.6-luna` |
| `high` | review, plan, implement | `MiniMax-M3` | `gpt-6-sol` |
| `premium` | deep reasoning, high-stakes plan | `MiniMax-M3` | `gpt-6.1-sol` |
| `xpremium` | maximal demand + high confidence | `MiniMax-M3` | `gpt-6-astra` |

Task-kind floors: `plan` and `review` floor at `high`; `implement` floors at
`standard` and is pinned to the flagship model via `kindModels`.

## Three behaviours that will surprise you

**1. The first row of a tier chain decides everything.**
The plugin picks the first chain entry it can find, and every configured row
is "findable". Later rows in a chain are **documentation, not fallback**.
The eligibility callback is a Codex-quota gate only; it does not filter by
provider.

**2. A pick on another provider is reported, not sent.**
The plugin rewrites the model on the provider client the turn is *already
bound to*. It cannot open a second provider client. A tier row naming a
different provider is reported as `blocked: cross-provider` and the turn
proceeds on the current model. Only the Desktop app's approve row can move a
session across providers — the CLI has no approve row.

> **This is why there are two config files.** A single global config can
> auto-route on exactly one provider. `hermes-jev-routing.json` leads with
> `minimax` rows (the `default` profile is minimax-bound);
> `hermes-jev-routing.codex.json` leads with `openai-codex` rows (the
> subscription profiles are codex-bound). The config is chosen per profile by
> `scripts/apply-jev-routing.sh` from the profile's bound provider.

**3. `shadow` is not egress-free.**
In `shadow` the plugin does not change the model — but it still transmits the
turn to TypeSafe. Shadow is a *routing* shadow, not a *data* shadow. See
[policy.md](policy.md).

## Cost model

The plugin's spend ledger is a per-token rate card written by the operator
(`pricing` in the routing JSON). On this host:

- `minimax` is **per-token billed** — priced, so its turns land in the ledger.
- `openai-codex`, `anthropic` (Claude Code OAuth) and `opencode-go` (Go
  subscription) are **flat subscriptions** — deliberately left unpriced, so
  the plugin records tokens but invents no dollars.
- TypeSafe itself is billed **per typed question**, which has no per-token
  representation; jev-routing turns are unpriced in the ledger.

`budget.dailyUsd` / `monthlyUsd` are sized against the measured run rate of
the one per-token-billed provider, so the `softRatio` / `hardRatio` knobs are
the operative control rather than an absolute dollar figure.

## Evidence

Routing behaviour is measured upstream in *Rethinking Verification in Agent
Harnesses* (arXiv:2610.34577v1) across 17 designs, 7 frontier coding models,
Terminal-Bench 2.1 and SWE-bench Verified, plus a visual benchmark. The
mechanism-level findings that shape this configuration:

- Only **6.2–13.6%** of editing turns are followed by any checking command —
  agents do not check their own work.
- A **separate critic** is the only design that consistently improves
  accuracy at modest cost: **+5.9–9.5 points** on Terminal-Bench and
  **+3.9–6.6** on SWE-bench at 1.13–1.25x and 1.00–1.04x baseline cost.
- A critic given the **task and the diff** beats one given the full
  trajectory while costing **29–43% less** — which is the model-scoped
  argument for diff-scoped review.
- On visual artifacts, self-directed verification scored **−3.2 net
  preference** — worse than no verification at all.

See [policy.md](policy.md) for the activation preconditions and the egress
review.

## Operational state

`platform/hermes-jev-routing.yaml` carries `policy_mode: proposed_not_live`.
The configuration is deployed in `shadow` mode: the plugin loads, classifies,
reports, and writes the spend ledger, and the model on the request is
unchanged. `auto` — the only mode that rewrites the model — is gated on
explicit human approval.
