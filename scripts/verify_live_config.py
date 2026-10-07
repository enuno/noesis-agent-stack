#!/usr/bin/env python3
"""Live-configuration compliance check (read-only, sanitized).

Separates four layers that the repo-local inference-routing validator
cannot distinguish, because it never reads ~/.hermes by design:

  1. Repository policy/schema validation   -> validate_inference_routing.py
  2. Live configuration compliance         -> THIS SCRIPT
  3. Provider authentication               -> partial: credential presence only
  4. Actual inference execution            -> NOT tested here (requires calls)

Never prints secret values. Provider/model identifiers are configuration,
not secrets; credential pools are reported as counts only.

Exit codes: 0 = live default route is repo-approved and credentialed;
1 = compliance violations found; 2 = runtime error.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERMES_HOME = Path.home() / ".hermes"

# Lanes approved by repository policy (platform/inference-routing.yaml).
APPROVED_LANES = {"kimi-coding": {"kimi-k2.7-code"}}


def load_yaml(path: Path) -> dict:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


def main() -> int:
    config = load_yaml(HERMES_HOME / "config.yaml")
    auth_path = HERMES_HOME / "auth.json"
    auth = {}
    if auth_path.is_file():
        try:
            auth = json.loads(auth_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("FATAL: auth.json is not valid JSON", file=sys.stderr)
            return 2

    model = config.get("model") or {}
    default_model = model.get("default")
    default_provider = model.get("provider")
    fallbacks = config.get("fallback_providers") or []

    pool = auth.get("credential_pool") or {}
    pool_counts = {k: len(v) for k, v in pool.items() if isinstance(v, list)}

    approved = (
        default_provider in APPROVED_LANES
        and default_model in APPROVED_LANES.get(default_provider, set())
    )
    credentialed = pool_counts.get(default_provider, 0) > 0

    findings = []
    if not approved:
        findings.append(
            f"live default route '{default_provider}/{default_model}' is not a "
            f"repository-approved lane"
        )
    if not credentialed:
        findings.append(f"no credentials present for provider '{default_provider}'")

    # Profiles whose model routing contradicts an approved lane.
    drifted = []
    profiles_dir = HERMES_HOME / "profiles"
    if profiles_dir.is_dir():
        for cfg in sorted(profiles_dir.glob("*/config.yaml")):
            pmodel = (load_yaml(cfg).get("model") or {})
            p = pmodel.get("provider")
            m = pmodel.get("default")
            if p and p not in APPROVED_LANES:
                drifted.append({"profile": cfg.parent.name, "provider": p, "model": m})

    report = {
        "layer_1_repo_policy": "run scripts/validate_inference_routing.py (repo-local)",
        "layer_2_live_compliance": {
            "default_provider": default_provider,
            "default_model": default_model,
            "default_route_approved": approved,
            "fallback_providers": [f.get("provider") for f in fallbacks],
        },
        "layer_3_credentials": {
            "provider_pool_counts": pool_counts,
            "default_provider_credentialed": credentialed,
        },
        "layer_4_inference_execution": "NOT TESTED (requires billable calls)",
        "profiles_on_unapproved_lanes": drifted,
        "findings": findings,
    }
    print(yaml.safe_dump(report, sort_keys=False).rstrip())
    if findings:
        print(f"\nLIVE CONFIG COMPLIANCE: FAIL ({len(findings)} finding(s))")
        return 1
    print("\nLIVE CONFIG COMPLIANCE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
