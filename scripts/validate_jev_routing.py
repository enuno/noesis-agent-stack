#!/usr/bin/env python3
"""Validate the hermes-jev-routing artifacts in this repo.

Offline by default: checks the policy, the tier tables, the provider policy
entry, and the catalog entry against each other. With --live it also checks
every referenced model id against the provider's live /v1/models catalogue.

Exit 0 = valid, 1 = failures, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO / "docs" / "hermes-jev-routing" / "config"
POLICY = REPO / "platform" / "hermes-jev-routing.yaml"
PROVIDER_POLICIES = REPO / "shared" / "provider-policies.yaml"
CATALOG = REPO / "catalog" / "typesafe-models.yaml"
PLUGIN_DIR = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "plugins" / "hermes-jev-routing"

TIERS = ("quick", "standard", "high", "premium", "xpremium")
PLUGIN_KEYS = {
    "enabled", "confidenceThreshold", "minPromptChars", "routes", "kindMinimumTier",
    "kindModels", "confirm", "quota", "budget", "cache", "pricing", "free",
    "ranking", "endpoint", "endpointEnv", "jevModel", "timeoutMs", "historyTurns",
    "taskKinds",
}

failures: list[str] = []
notes: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def note(msg: str) -> None:
    notes.append(msg)


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        print("PyYAML required", file=sys.stderr)
        raise SystemExit(2)
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception as e:
        fail(f"{path.relative_to(REPO)}: cannot parse: {e}")
        return {}


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        fail(f"{path.relative_to(REPO)}: cannot parse: {e}")
        return {}


def referenced_rows(cfg: dict) -> list[tuple[str, str, str]]:
    """(label, provider, model) for every configured row."""
    rows = []
    for tier, chain in (cfg.get("routes") or {}).items():
        for t in chain or []:
            rows.append((f"routes.{tier}", t.get("provider", ""), t.get("model", "")))
    for kind, chain in (cfg.get("kindModels") or {}).items():
        for t in chain or []:
            rows.append((f"kindModels.{kind}", t.get("provider", ""), t.get("model", "")))
    for t in (cfg.get("free") or {}).get("pool") or []:
        rows.append(("free.pool", t.get("provider", ""), t.get("model", "")))
    return rows


def validate_config(path: Path) -> dict:
    cfg = load_json(path)
    if not cfg:
        return {}

    extra = set(cfg) - PLUGIN_KEYS
    if extra:
        fail(f"{path.name}: keys the plugin does not define: {sorted(extra)}")
    if not cfg.get("enabled", True):
        note(f"{path.name}: enabled=false — the plugin will not load")

    for tier in TIERS:
        if tier not in (cfg.get("routes") or {}):
            fail(f"{path.name}: routes.{tier} missing (the loader only reads these five tiers)")

    for label, provider, model in referenced_rows(cfg):
        if not provider or not model:
            fail(f"{path.name}: {label} has an empty provider/model")
        if provider == "opencode-go" and model in ("iceman-contributor-free", "muse-spark-1.3-contributor"):
            fail(f"{path.name}: {label} routes to {model}, which consents to training on prompts")

    # pricing card must cover exactly the rows that should be priced
    priced = set((cfg.get("pricing") or {}).keys())
    referenced = {f"{p}/{m}" for _, p, m in referenced_rows(cfg)}
    orphan = priced - referenced
    if orphan:
        fail(f"{path.name}: pricing entries no row references: {sorted(orphan)}")
    missing = {r for r in referenced if r not in priced}
    if missing:
        note(f"{path.name}: referenced but unpriced (subscription providers -> no dollars invented): {sorted(missing)}")

    # the first row of each tier decides the outcome; later rows are not fallback
    for tier, chain in (cfg.get("routes") or {}).items():
        if chain:
            first = chain[0]
            note(f"{path.name}: {tier} leads with {first.get('provider')}/{first.get('model')}")

    b = cfg.get("budget") or {}
    if b.get("dailyUsd") and b.get("monthlyUsd"):
        if b["dailyUsd"] * 30 < b["monthlyUsd"] * 0.1:
            fail(f"{path.name}: budget caps are implausible (daily {b['dailyUsd']} vs monthly {b['monthlyUsd']})")
    return cfg


def validate_policy() -> dict:
    pol = load_yaml(POLICY)
    if not pol:
        return {}
    if pol.get("policy_mode") != "proposed_not_live":
        note(f"platform/hermes-jev-routing.yaml: policy_mode={pol.get('policy_mode')!r} (expected proposed_not_live)")

    dc = pol.get("data_classification") or {}
    if "internal" not in (dc.get("classification_allowed") or []):
        fail("platform/hermes-jev-routing.yaml: data_classification.classification_allowed must include 'internal'")
    if dc.get("confidential_redacted") != "denied":
        fail("platform/hermes-jev-routing.yaml: confidential_redacted must be 'denied' — the plugin sends prompt text")

    modes = pol.get("modes") or {}
    if "auto" not in modes:
        fail("platform/hermes-jev-routing.yaml: modes.auto missing")
    else:
        reqs = modes["auto"].get("requires") or []
        for need in ("explicit_human_approval", "routing_eval_coverage", "security_and_secret_egress_review"):
            if need not in reqs:
                fail(f"platform/hermes-jev-routing.yaml: modes.auto.requires missing {need!r}")

    elig = pol.get("profile_eligibility") or {}
    ineligible = {e.get("profile") for e in (elig.get("ineligible") or []) if isinstance(e, dict)}
    if "misjustice-advocacy" not in ineligible:
        fail("platform/hermes-jev-routing.yaml: misjustice-advocacy must be listed as ineligible")
    for key, block in elig.items():
        if key in ("ineligible", "reviewer_only") or not isinstance(block, dict):
            continue
        cfg_rel = block.get("config")
        if cfg_rel and not (REPO / cfg_rel).is_file():
            fail(f"platform/hermes-jev-routing.yaml: profile_eligibility.{key}.config -> {cfg_rel} does not exist")

    pre = pol.get("required_before_route_activation") or {}
    for name in ("canonical_provider_policy", "canonical_model_catalog_entry",
                 "data_classification_policy", "security_and_secret_egress_review",
                 "cost_and_latency_budget", "explicit_human_approval"):
        if name not in pre:
            fail(f"platform/hermes-jev-routing.yaml: required_before_route_activation missing {name!r}")
    return pol


def validate_provider_policy() -> None:
    pp = load_yaml(PROVIDER_POLICIES)
    ts = (pp.get("providers") or {}).get("typesafe")
    if not ts:
        fail("shared/provider-policies.yaml: providers.typesafe missing")
        return
    allowed = ((ts.get("data_policy") or {}).get("classification_allowed") or [])
    if "confidential" in allowed:
        fail("shared/provider-policies.yaml: providers.typesafe must not allow 'confidential' — prompt text egress")
    if not (ts.get("data_policy") or {}).get("prompt_text_egress"):
        fail("shared/provider-policies.yaml: providers.typesafe.data_policy.prompt_text_egress must be true")


def validate_catalog() -> None:
    cat = load_yaml(CATALOG)
    if not cat:
        return
    models = cat.get("models") or {}
    if "jev-latest" not in models:
        fail("catalog/typesafe-models.yaml: models.jev-latest missing")
    for name, row in models.items():
        if row.get("produces_task_output") is not False:
            fail(f"catalog/typesafe-models.yaml: models.{name}.produces_task_output must be false")
        if row.get("classification_allowed") and "confidential" in row["classification_allowed"]:
            fail(f"catalog/typesafe-models.yaml: models.{name} must not allow 'confidential'")


def validate_live(configs: dict[str, dict]) -> None:
    """Check every referenced model id against the provider's live catalogue."""
    sys.path.insert(0, str(REPO.parent / "noesis-agent-stack" / ".git"))  # no-op, keeps import order stable
    src = Path.home() / ".hermes" / "hermes-agent"
    sys.path.insert(0, str(src))
    os.environ.setdefault("HERMES_HOME", str(Path.home() / ".hermes"))
    try:
        from hermes_cli.env_loader import load_hermes_dotenv
        from hermes_cli.models import provider_model_ids
    except Exception as e:
        fail(f"--live: cannot import the Hermes catalog resolver ({e}); "
             "the live check cannot be satisfied")
        return
    try:
        load_hermes_dotenv()
    except Exception as e:
        fail(f"--live: secret sources not applied ({e}); "
             "the live check cannot be satisfied")
        return

    cache: dict[str, list[str] | None] = {}
    for cname, cfg in configs.items():
        for label, provider, model in referenced_rows(cfg):
            if provider not in cache:
                try:
                    cache[provider] = provider_model_ids(provider, force_refresh=True)
                except Exception as e:
                    # A live check that could not RUN must not pass. An
                    # explicitly requested verification that verifies
                    # nothing is worse than one that fails loudly.
                    fail(f"--live: {provider} catalogue unavailable ({type(e).__name__}: {e}); "
                         "the live check cannot be satisfied")
                    cache[provider] = None
                else:
                    if not cache[provider]:
                        fail(f"--live: {provider} catalogue came back empty; "
                             "the live check cannot be satisfied")
            ids = cache[provider]
            if ids is None:
                continue
            if model not in ids:
                fail(f"{cname}: {label} -> {provider}/{model} is not served by {provider} today")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="also check model ids against live provider catalogues")
    ap.add_argument("--quiet", action="store_true", help="suppress notes")
    args = ap.parse_args()

    configs = {}
    for cfg_path in sorted(CONFIG_DIR.glob("*.json")):
        configs[cfg_path.name] = validate_config(cfg_path)
    validate_policy()
    validate_provider_policy()
    validate_catalog()
    if args.live:
        validate_live(configs)

    if not args.quiet:
        for n in notes:
            print(f"  note: {n}")
    for f in failures:
        print(f"  FAIL: {f}")
    if failures:
        print(f"\nFAILED: {len(failures)} problem(s)")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
