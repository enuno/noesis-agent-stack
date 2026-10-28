#!/usr/bin/env python3
"""Generate the hermes-jev-routing JSON configs from a declarative ladder.

WHY THIS EXISTS
---------------
The plugin's config lists concrete model ids. Providers retire models, and a
retired id does not fail at load time -- it fails at request time, on a live
session, as an opaque provider error. The catalog edition of the plugin does
not consult the provider catalogue, so nothing upstream would catch it.

This script closes that gap: it reads the ladder, asks each provider what it
serves TODAY, keeps the first candidate the provider actually serves, and
writes a config that can only reference live models.

INPUTS
------
  docs/hermes-jev-routing/config/tier-ladder.yaml   (which model for which tier)
  docs/hermes-jev-routing/config/rate-card.yaml      ($/Mtok; never invented here)

OUTPUTS
-------
  one JSON config per target in the ladder, each leading with its target's
  provider.

USAGE
-----
  ./generate-jev-routing-config.py --check      # fail if the checked-in
                                               # configs differ from a fresh
                                               # generation
  ./generate-jev-routing-config.py --write      # rewrite them
  ./generate-jev-routing-config.py --write --out-dir ~/.hermes
  ./generate-jev-routing-config.py --write --install --profile terrahash-intel

Exit 0 = clean, 1 = failure, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO / "docs" / "hermes-jev-routing" / "config"
LADDER = CONFIG_DIR / "tier-ladder.yaml"
RATE_CARD = CONFIG_DIR / "rate-card.yaml"
TIERS = ("quick", "standard", "high", "premium", "xpremium")

# Models that consent to training on prompts. Never routed to, never priced.
TRAINING_CONSENT_MODELS = ("iceman-contributor-free", "muse-spark-1.3-contributor")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


# ---------------------------------------------------------------------------
# provider catalogue access
# ---------------------------------------------------------------------------
def _load_hermes():
    home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
    src = home / "hermes-agent"
    if src.is_dir():
        sys.path.insert(0, str(src))
    os.environ.setdefault("HERMES_HOME", str(home))
    from hermes_cli.env_loader import load_hermes_dotenv
    from hermes_cli.models import provider_model_ids
    try:
        load_hermes_dotenv()
    except Exception as e:  # noqa: BLE001 - secret sources are best-effort here
        warn(f"secret sources not applied ({type(e).__name__}); authenticated providers may be empty")
    return provider_model_ids


def scan_catalogues(providers: list[str], allow_unavailable: bool = False) -> dict[str, list[str]]:
    provider_model_ids = _load_hermes()
    out: dict[str, list[str]] = {}
    for prov in providers:
        try:
            ids = provider_model_ids(prov, force_refresh=True) or []
        except Exception as e:  # noqa: BLE001 - provider catalogues fail in many ways
            ids = []
            if not allow_unavailable:
                err(f"catalogue unavailable for {prov}: {type(e).__name__}: {e}")
            else:
                warn(f"catalogue unavailable for {prov}: {type(e).__name__} — rows for it will be dropped")
        out[prov] = list(ids)
    return out


def serves(catalogue: list[str], model: str) -> bool:
    """True if the provider currently serves this model id."""
    if not catalogue:
        return False
    tail = model.split("/")[-1]
    return model in catalogue or tail in catalogue


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------
def pick_model(prov: str, tier: str, ladder: dict, catalogues: dict) -> str | None:
    for cand in ((ladder.get("providers") or {}).get(prov) or {}).get(tier) or []:
        if cand in TRAINING_CONSENT_MODELS:
            err(f"{prov}/{tier}: candidate {cand} consents to training on prompts — refusing")
            continue
        if serves(catalogues.get(prov) or [], cand):
            return cand
    return None


def build_config(ladder: dict, rate_card: dict, catalogues: dict, lead: str) -> tuple[dict, list[str]]:
    chains = ladder.get("chain_order") or {}
    think = ladder.get("thinking_levels") or {}
    notes: list[str] = []

    routes: dict[str, list[dict]] = {}
    for tier in TIERS:
        order = list(chains.get(tier) or [])
        if lead in order:
            order = [lead] + [p for p in order if p != lead]
        else:
            order = [lead] + order
        chain: list[dict] = []
        for prov in order:
            model = pick_model(prov, tier, ladder, catalogues)
            if model is None:
                notes.append(f"{lead}-led {tier}: no served candidate for {prov} — dropped")
                continue
            chain.append({
                "provider": prov,
                "model": model,
                "thinkingLevel": think.get(tier, "medium"),
            })
        if not chain:
            err(f"{lead}-led {tier}: chain is empty — the profile would have no route")
        routes[tier] = chain

    # kind models: hoist the lead provider's entry to the front
    kind_models: dict[str, list[dict]] = {}
    for kind, entries in (ladder.get("kind_models") or {}).items():
        picked: list[dict] = []
        for e in entries:
            model = e.get("model")
            prov = e.get("provider")
            if not serves(catalogues.get(prov) or [], model):
                notes.append(f"kindModels.{kind}: {prov}/{model} is not served today — dropped")
                continue
            picked.append({
                "provider": prov,
                "model": model,
                "minTier": e.get("min_tier", "standard"),
                "priority": e.get("priority", 0),
            })
        picked.sort(key=lambda x: (x["provider"] != lead, -x["priority"]))
        if picked:
            kind_models[kind] = picked

    # pricing: only models the generated chains actually reference, and only
    # from the curated rate card
    referenced: set[str] = set()
    for chain in routes.values():
        for row in chain:
            referenced.add(f"{row['provider']}/{row['model']}")
    for entries in kind_models.values():
        for row in entries:
            referenced.add(f"{row['provider']}/{row['model']}")

    pricing: dict[str, dict] = {}
    for prov, models in (rate_card.get("providers") or {}).items():
        for model, rates in models.items():
            key = f"{prov}/{model}"
            if key in referenced:
                pricing[key] = {
                    "input": rates.get("input", 0.0),
                    "output": rates.get("output", 0.0),
                    "cache_read": rates.get("cache_read", 0.0),
                }

    unpriced = sorted(referenced - set(pricing))
    if unpriced:
        notes.append(f"unpriced (subscription providers — no dollars invented): {unpriced}")

    free = dict((ladder.get("defaults") or {}).get("free") or {})
    pool = []
    for row in free.get("pool") or []:
        if serves(catalogues.get(row.get("provider")) or [], row.get("model")):
            pool.append(row)
        else:
            notes.append(f"free.pool: {row.get('provider')}/{row.get('model')} is not served today — dropped")
    free["pool"] = pool
    if not pool:
        free["enabled"] = False

    cfg: dict = {
        "enabled": (ladder.get("defaults") or {}).get("enabled", True),
        "confidenceThreshold": (ladder.get("defaults") or {}).get("confidenceThreshold", 0.34),
        "minPromptChars": (ladder.get("defaults") or {}).get("minPromptChars", 12),
        "routes": routes,
        "kindMinimumTier": ladder.get("kind_minimum_tier") or {},
        "kindModels": kind_models,
        "confirm": (ladder.get("defaults") or {}).get("confirm") or {},
        "quota": (ladder.get("defaults") or {}).get("quota") or {},
        "budget": (ladder.get("defaults") or {}).get("budget") or {},
        "cache": (ladder.get("defaults") or {}).get("cache") or {},
        "pricing": pricing,
        "free": free,
        "ranking": (ladder.get("defaults") or {}).get("ranking") or {},
    }
    return cfg, notes


def validate_with_plugin(cfg: dict, label: str) -> None:
    """Let the plugin's own loader judge the config, if it is installed."""
    plugin_cfg = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "plugins" / "hermes-jev-routing" / "config.py"
    if not plugin_cfg.is_file():
        warn("plugin not installed — skipped the plugin's own loader check")
        return
    try:
        import importlib.util
        # the plugin's modules import each other by bare name, so its own
        # directory must be importable
        plugin_dir = str(plugin_cfg.parent)
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        spec = importlib.util.spec_from_file_location("jev_config", plugin_cfg)
        if spec is None or spec.loader is None:
            err(f"{label}: cannot load the plugin's config module")
            return
        mod = importlib.util.module_from_spec(spec)
        # @dataclass resolves its own module through sys.modules, so the
        # module must be REGISTERED before it is executed
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"jev-gen-{label}.json"
        tmp.write_text(json.dumps(cfg))
        try:
            router, settings = mod.load_router_config(str(tmp))
            routes = getattr(router, "routes", None) or {}
            missing = [t for t in TIERS if t not in routes]
            if missing:
                err(f"{label}: the plugin's loader produced no route for tier(s) {missing}")
            models = mod.models_from_config(router)
            if not models:
                err(f"{label}: the plugin's loader produced no available models")
            for m in models or []:
                if not getattr(m, "provider", "") or not getattr(m, "id", ""):
                    err(f"{label}: the plugin's loader produced a model with no provider/id")
                    break
            print(f"  plugin loader OK: {label} -> {len(routes)} tiers, {len(models or [])} model(s)")
        finally:
            tmp.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        err(f"{label}: the plugin's loader rejected the generated config: {type(e).__name__}: {e}")


def diff_report(old: dict, new: dict, label: str) -> bool:
    """Compare the COMPLETE generated config against the stored one.

    Comparing only route tuples and pricing key SETS would miss a changed
    budget, a changed thinking level, a changed kind-model pin, or a changed
    RATE on a model that is still present -- and the gate would then report
    stale spend settings as current.
    """
    changed = False
    for key in sorted(set(old) | set(new)):
        o = old.get(key)
        n = new.get(key)
        if o == n:
            continue
        changed = True
        print(f"  {label} {key}:")
        if isinstance(o, dict) and isinstance(n, dict):
            for sub in sorted(set(o) | set(n)):
                if o.get(sub) != n.get(sub):
                    print(f"    {key}.{sub}: {o.get(sub)!r} -> {n.get(sub)!r}")
        else:
            print(f"    {o!r} -> {n!r}")
    return changed


def select_target_for_profile(ladder: dict, targets: list, profile: str) -> tuple[dict | None, str | None]:
    """Return (target, error) for the config a profile must receive.

    The plugin can only rewrite the model on the provider a turn is already
    bound to, so a profile MUST receive the config that leads with its own
    provider. Resolving that from the ladder's `profiles` map -- rather than
    installing every target -- is what keeps a profile from ending up on a
    config it cannot use (the plugin reports those as
    `blocked: cross-provider`, which is no routing at all).
    """
    bound = (ladder.get("profiles") or {}).get(profile)
    if not bound:
        return None, f"profile {profile!r} has no bound provider in the ladder's profiles map"
    target = next((t for t in targets if t.get("lead_provider") == bound), None)
    if not target:
        return None, f"no target leads with {bound!r} for profile {profile!r}"
    return target, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write the generated configs")
    ap.add_argument("--check", action="store_true", help="fail if the checked-in configs differ (default)")
    ap.add_argument("--out-dir", default=None, help="write somewhere other than the repo config dir")
    ap.add_argument("--install", action="store_true", help="also copy to the target profile homes")
    ap.add_argument("--profile", action="append", default=[], help="profile to install into (repeatable)")
    ap.add_argument("--allow-unavailable", action="store_true", help="continue when a provider catalogue cannot be read")
    args = ap.parse_args()

    try:
        import yaml
    except ImportError:
        print("PyYAML required", file=sys.stderr)
        return 2

    ladder = yaml.safe_load(LADDER.read_text()) or {}
    rate_card = yaml.safe_load(RATE_CARD.read_text()) or {}
    targets = ladder.get("targets") or []
    if not targets:
        err(f"{LADDER.name}: no targets defined")
        return 1

    providers = sorted({t["lead_provider"] for t in targets} |
                       set((ladder.get("chain_order") or {}).get("quick") or []))
    print(f"scanning live catalogues for: {', '.join(providers)}")
    catalogues = scan_catalogues(providers, allow_unavailable=args.allow_unavailable)
    for prov in providers:
        n = len(catalogues.get(prov) or [])
        print(f"  {prov}: {n} model(s) served")
        if n == 0:
            warn(f"{prov}: catalogue came back empty — its rows will be dropped")

    out_dir = Path(args.out_dir).expanduser() if args.out_dir else CONFIG_DIR
    generated: dict[Path, dict] = {}
    for target in targets:
        lead = target["lead_provider"]
        cfg, notes = build_config(ladder, rate_card, catalogues, lead)
        label = target["output"]
        print(f"\n{label} (lead: {lead})")
        for tier in TIERS:
            chain = (cfg.get("routes") or {}).get(tier) or []
            if chain:
                print(f"  {tier:<9} -> {chain[0]['provider']}/{chain[0]['model']}  ({len(chain)} row(s))")
        for n in notes:
            warn(f"{label}: {n}")
        validate_with_plugin(cfg, label)
        generated[CONFIG_DIR / label] = cfg

    print("")
    for w in warnings:
        print(f"  WARN: {w}")

    drift = False
    for path, cfg in generated.items():
        old = {}
        if path.is_file():
            try:
                old = json.loads(path.read_text())
            except Exception as e:  # noqa: BLE001
                err(f"{path.name}: existing file is not valid JSON ({e})")
        if diff_report(old, cfg, path.name):
            drift = True

    if errors:
        print("")
        for e in errors:
            print(f"  FAIL: {e}")
        print(f"\nFAILED: {len(errors)} problem(s)")
        return 1

    if args.write:
        for path, cfg in generated.items():
            dest = (out_dir / path.name) if out_dir != CONFIG_DIR else path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(cfg, indent=2) + "\n")
            print(f"  wrote {dest}")
        if args.install:
            # Resolve the profile's bound provider EXPLICITLY. Installing
            # every target would leave the profile holding a config that
            # leads with a different provider, which the plugin reports as
            # `blocked: cross-provider` -- no routing at all.
            profile_map = ladder.get("profiles") or {}
            for profile in args.profile:
                target, err_msg = select_target_for_profile(ladder, targets, profile)
                if target is None:
                    err(f"--install: {err_msg}")
                    continue
                cfg = generated[CONFIG_DIR / target["output"]]
                home = (Path.home() / ".hermes" if profile == "default"
                        else Path.home() / ".hermes" / "profiles" / profile)
                # The ACTIVE filename is what settings.config_path points at.
                # Any other name would leave the profile on a config it does
                # not read.
                dest = home / "hermes-jev-routing.json"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(json.dumps(cfg, indent=2) + "\n")
                print(f"  installed {dest} (bound provider: {target.get('lead_provider')})")
        if errors:
            for e in errors:
                print(f"  FAIL: {e}")
            print(f"\nFAILED: {len(errors)} problem(s)")
            return 1
        print("\nOK")
        return 0

    if drift:
        print("\nDRIFT: the checked-in configs differ from a fresh generation.")
        print("Re-run with --write to reconcile.")
        return 1
    print("\nOK — checked-in configs match a fresh generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
