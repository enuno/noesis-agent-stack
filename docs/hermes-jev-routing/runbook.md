# hermes-jev-routing — runbook

## Install and configure

```bash
cd ~/projects/noesis-agent-stack

# dry run first — writes nothing
./scripts/apply-jev-routing.sh --all --dry-run

# real apply (shadow mode is the ceiling this script will set)
./scripts/apply-jev-routing.sh --all
```

Single profile:

```bash
./scripts/apply-jev-routing.sh --profile terrahash-intel
```

The script installs the plugin at the pinned ref
`06a53646587c33174a0fbfbb3713eca90bbb8586`, copies the profile's routing
config into the profile home, writes the settings block, adds the plugin to
`plugins.enabled`, and then **parses the stored `config.yaml` and compares
key sets and values** — it does not trust the CLI's echo.

It refuses `mode=auto` outright (exit 3) and refuses ineligible profiles.

### What it touches

| Path | Change |
|---|---|
| `~/.hermes/profiles/<p>/plugins/hermes-jev-routing/` | plugin install (pinned) |
| `~/.hermes/profiles/<p>/hermes-jev-routing.json` | the routing table |
| `~/.hermes/profiles/<p>/config.yaml` | `plugins.enabled` + `plugins.entries.hermes-jev-routing.settings` |
| `~/.hermes/profiles/<p>/hermes-jev-routing-state.json` | spend ledger, written by the plugin |

For the `default` profile the home is `~/.hermes` itself.

## Regenerate the routing tables

The tier tables are generated, not hand-edited. Edit the ladder, not the
JSON.

```bash
cd ~/projects/noesis-agent-stack

# see what a fresh generation would produce, without writing
./scripts/generate-jev-routing-config.py --check

# reconcile the checked-in configs
./scripts/generate-jev-routing-config.py --write

# then push the new tables to the profiles
./scripts/apply-jev-routing.sh --all
```

The generator:

1. reads `config/tier-ladder.yaml` (which model for which tier, and the
   chain order) and `config/rate-card.yaml` ($/Mtok);
2. asks each provider what it serves **today** — via the same resolver the
   agent uses, with the Bitwarden-backed secrets applied;
3. keeps the first candidate the provider actually serves, so a retired
   model is dropped automatically instead of failing at request time;
4. copies the rates for exactly the models the chains reference;
5. runs the plugin's own `load_router_config` over the result, so a config
   the plugin would reject never reaches a profile;
6. reports the diff against the checked-in file.

It exits non-zero on drift, so `--check` works as a CI gate.

Run it when a provider announces a model retirement, when the ladder
changes, or before any `auto` activation.

### Rules the generator will not break

- **No training-consent models.** `iceman-contributor-free` and
  `muse-spark-1.3-contributor` are refused as candidates, and the ladder
  does not list them.
- **One row per provider per chain.** The first row of a chain decides the
  outcome; a second row for the same provider is documentation at best.
- **No invented dollars.** Only the rate card is used, and only for models
  the chains reference. Subscription providers stay unpriced on purpose.

## Verify

Three independent signals — a plugin that is loaded but inert produces none
of them, so check all three:

```bash
# 1. the plugin's own status
hermes -p <profile> plugins show hermes-jev-routing
hermes -p <profile> plugins doctor hermes-jev-routing

# 2. the routing decision, in the log
grep 'hermes_jev_routing' ~/.hermes/logs/agent.log | tail -5
#   INFO hermes_plugins.hermes_jev_routing: hermes-jev-routing pick <model> status=<offered|applied>

# 3. the spend ledger
cat ~/.hermes/profiles/<profile>/hermes-jev-routing-state.json
#   "jev": { "requests": N, ... }   and a "days" block once a turn is priced
```

And the plugin's own command (not available in the CLI transport for a
remote session; run it in a local session):

```
/jev-routing
/jev-routing why
/jev-routing route <text>
```

### The gateway will not pick up a new plugin by itself

A long-running gateway holds the plugin registry it built at startup.
Enabling the plugin after the gateway started leaves it **loaded but
inert**: `plugins doctor` passes, the manifest parses, and the hook never
fires.

Two ways to force a rebuild:

```bash
# a) toggle a plugin — the gateway reloads its plugin registry
hermes plugins disable <some-other-plugin>

# b) restart the gateway (must be run from a shell OUTSIDE the gateway;
#    Hermes refuses it from inside, because SIGTERM would kill the command
#    mid-restart)
hermes gateway restart
```

`hermes plugins disable` prints the honest scope note: platform hooks it
already wired up stay until a gateway restart.

## Roll back

```bash
# 1. stop routing
hermes -p <profile> plugins disable hermes-jev-routing
hermes -p <profile> config unset plugins.entries.hermes-jev-routing.settings.config_path
hermes -p <profile> config unset plugins.entries.hermes-jev-routing.settings.mode

# 2. drop the plugin
hermes -p <profile> plugins remove hermes-jev-routing

# 3. remove the config and ledger (optional — the ledger is the spend record)
rm -f ~/.hermes/profiles/<profile>/hermes-jev-routing.json
rm -f ~/.hermes/profiles/<profile>/hermes-jev-routing-state.json
```

To reverse a repo-side change: `git -C ~/projects/noesis-agent-stack revert <sha>`.

## Before activating `auto`

`auto` rewrites the model on the wire. It is gated on explicit human
approval. The sequence:

1. Run `shadow` long enough to observe the tier distribution:
   `grep 'hermes_jev_routing' ~/.hermes/logs/agent.log | grep 'pick'`
2. Confirm the ladder matches the real task mix — the tier that fires most
   often should be the one you expected.
3. Check the ledger for the volume you signed up for.
4. Re-verify every model id against the provider's live catalogue
   (`scripts/validate_jev_routing.py --live`). The catalog edition does not
   filter unavailable rows, so a retired model id fails at request time
   rather than at load time.
5. Write the approval record to
   `docs/operations/jev-routing-activation-YYYY-MM-DD.md`.
6. Then: `hermes -p <profile> config set plugins.entries.hermes-jev-routing.settings.mode auto`

## Failure modes

| Symptom | Likely cause | Action |
|---|---|---|
| `plugins doctor` OK, no `pick` line in the log | Gateway plugin registry is stale | Toggle a plugin, or restart the gateway from an outside shell |
| `blocked: cross-provider` on every turn | The config's first tier row names a different provider than the session's bound provider | Use the config that leads with the bound provider for that profile |
| `/jev-routing` is an unknown command | Plugin command registration did not take in that process | Verify in a fresh local session; a remote session cannot see the command |
| `Jev hosted request failed (validation_failure)` | The key lacks `jev-latest` access, or the request shape is rejected | Check the key entitlement; confirm the endpoint and `jevModel` |
| Ledger `jev.requests` not incrementing | The hook returned before `classify()` | Check `config_path` resolves, and that `mode` is not `off` |
| Spend ledger flat at zero | The bound model is unpriced (subscription provider) | Expected for codex/anthropic/opencode-go; the ledger prices per-token-billed providers only |
