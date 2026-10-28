#!/usr/bin/env python3
"""Regression tests for the jev-routing tooling.

Every test here corresponds to a finding raised by an automated reviewer on
the initial pull request, or to a behaviour the scripts promise in the
runbook. They are offline and deterministic: no provider catalogue is
fetched, and nothing outside the temporary directory is touched.

Exit 0 = all passed, 1 = at least one failed.

    ./scripts/test_jev_routing.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRATCH = Path(os.environ.get("TMPDIR", "/tmp"))
APPLY = REPO / "scripts" / "apply-jev-routing.sh"
GENERATE = REPO / "scripts" / "generate-jev-routing-config.py"
VALIDATE = REPO / "scripts" / "validate_jev_routing.py"
PINNED_REF = "06a53646587c33174a0fbfbb3713eca90bbb8586"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: object = "") -> None:
    results.append((name, bool(ok), "" if detail == "" else str(detail)))


def load_module(path: Path, alias: str):
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


gen = load_module(GENERATE, "jev_gen")


# ---------------------------------------------------------------------------
# 1. the drift gate must compare the COMPLETE config
# ---------------------------------------------------------------------------
def test_drift_detects_every_setting() -> None:
    base = {
        "budget": {"dailyUsd": 30, "monthlyUsd": 900},
        "pricing": {"m/M": {"input": 0.3, "output": 1.2, "cache_read": 0.06}},
        "routes": {"quick": [{"provider": "m", "model": "M", "thinkingLevel": "low"}]},
        "confidenceThreshold": 0.34,
    }

    def mutate(fn):
        c = json.loads(json.dumps(base))
        fn(c)
        return c

    cases = {
        "budget value": lambda c: c["budget"].__setitem__("dailyUsd", 10),
        "pricing RATE (same key set)": lambda c: c["pricing"]["m/M"].__setitem__("input", 0.4),
        "thinkingLevel": lambda c: c["routes"]["quick"][0].__setitem__("thinkingLevel", "high"),
        "confidenceThreshold": lambda c: c.__setitem__("confidenceThreshold", 0.5),
        "new top-level key": lambda c: c.__setitem__("minPromptChars", 40),
    }
    for name, fn in cases.items():
        check(f"drift detects a changed {name}", gen.diff_report(base, mutate(fn), "t") is True)
    check("drift reports no change for an identical config",
          gen.diff_report(base, json.loads(json.dumps(base)), "t") is False)


# ---------------------------------------------------------------------------
# 2. --install must give a profile ONLY its own provider's config
# ---------------------------------------------------------------------------
def test_install_selects_the_bound_provider() -> None:
    ladder = {
        "profiles": {"default": "minimax", "terrahash-intel": "openai-codex"},
    }
    targets = [
        {"lead_provider": "minimax", "output": "hermes-jev-routing.json"},
        {"lead_provider": "openai-codex", "output": "hermes-jev-routing.codex.json"},
    ]

    t, err = gen.select_target_for_profile(ladder, targets, "terrahash-intel")
    check("codex-bound profile resolves to the codex-led target",
          err is None and t is not None and t["output"] == "hermes-jev-routing.codex.json",
          f"target={t} err={err}")

    t, err = gen.select_target_for_profile(ladder, targets, "default")
    check("minimax-bound profile resolves to the minimax-led target",
          err is None and t is not None and t["output"] == "hermes-jev-routing.json",
          f"target={t} err={err}")

    t, err = gen.select_target_for_profile(ladder, targets, "misjustice-advocacy")
    check("a profile with no bound provider is refused, not guessed",
          t is None and err is not None, f"err={err}")

    # the ladder as checked in must actually carry the map
    import yaml
    real = yaml.safe_load((REPO / "docs/hermes-jev-routing/config/tier-ladder.yaml").read_text()) or {}
    pmap = real.get("profiles") or {}
    check("the checked-in ladder declares a bound provider for every eligible profile",
          pmap.get("default") == "minimax"
          and pmap.get("builder-ventures") == "openai-codex"
          and pmap.get("terrahash-intel") == "openai-codex",
          f"profiles={pmap}")
    check("the ineligible profile has no bound provider in the ladder",
          "misjustice-advocacy" not in pmap, f"profiles={pmap}")


# ---------------------------------------------------------------------------
# 3/5/6. the apply script's contract with the hermes CLI
# ---------------------------------------------------------------------------
STUB = """#!/usr/bin/env bash
printf 'HERMES_HOME=%s\\n' "${HERMES_HOME:-unset}" >> "$STUB_LOG"
printf 'ARGS: %s\\n' "$*" >> "$STUB_LOG"

# Emulate `hermes config set <dotted.path> <value>` persisting to the
# profile's config.yaml, so the apply script's own verification has
# something real to read.
if [[ "$1" == "config" && "$2" == "set" ]]; then
  /usr/bin/python3 - "$STUB_CONFIG" "$3" "$4" <<'PY'
import sys, yaml
path, key, val = sys.argv[1:4]
try:
    cfg = yaml.safe_load(open(path)) or {}
except Exception:
    cfg = {}
node = cfg
parts = key.split(".")
for p in parts[:-1]:
    nxt = node.get(p)
    if not isinstance(nxt, dict):
        nxt = {}
        node[p] = nxt
    node = nxt
try:
    parsed = yaml.safe_load(val)
except Exception:
    parsed = val
node[parts[-1]] = parsed
with open(path, "w") as fh:
    yaml.safe_dump(cfg, fh)
PY
  exit 0
fi
exit 0
"""


def make_stub(tmp: Path) -> tuple[Path, Path]:
    bindir = tmp / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "hermes"
    stub.write_text(STUB)
    stub.chmod(0o755)
    log = tmp / "hermes-calls.log"
    return bindir, log


def make_profile_home(tmp: Path, home: Path, sha: str | None, enabled: list[str] | None) -> None:
    home.mkdir(parents=True, exist_ok=True)
    plugins = home / "plugins" / "hermes-jev-routing"
    plugins.mkdir(parents=True, exist_ok=True)
    if sha is not None:
        (plugins / ".hermes-catalog.json").write_text(
            json.dumps({"catalog_name": "hermes-jev-routing", "sha": sha}))
    cfg = {"plugins": {"enabled": enabled if enabled is not None else []}}
    (home / "config.yaml").write_text(json.dumps(cfg))


def run_apply(tmp: Path, home: Path, extra: list[str], enabled: list[str] | None = None,
              sha: str | None = PINNED_REF) -> subprocess.CompletedProcess:
    bindir, log = make_stub(tmp)
    make_profile_home(tmp, home, sha, enabled)
    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["STUB_LOG"] = str(log)
    env["STUB_CONFIG"] = str(home / "config.yaml")
    # HOME is redirected so nothing can reach the real profile home, and
    # HERMES_HOME is deliberately NOT preset: the --home argument must be
    # what the child process ends up seeing. NOESIS_STACK_DIR points the
    # script back at the repo, which the redirected HOME would otherwise
    # hide.
    env["HOME"] = str(tmp)
    env["NOESIS_STACK_DIR"] = str(REPO)
    env.pop("HERMES_HOME", None)
    return subprocess.run(
        ["bash", str(APPLY), "--profile", "default", "--home", str(home), *extra],
        capture_output=True, text=True, env=env, cwd=str(tmp))


def test_apply_exports_the_selected_home() -> None:
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as td:
        tmp = Path(td)
        home = tmp / "alt-home"
        # NOT --dry-run: a dry run never invokes the child process, so it
        # could not observe what the child sees.
        r = run_apply(tmp, home, [])
        logs = list(tmp.glob("hermes-calls.log"))
        content = logs[0].read_text() if logs else ""
        check("the child hermes process sees the selected --home",
              f"HERMES_HOME={home}" in content,
              content.splitlines()[:3])
        check("the apply against an alternate home succeeds", r.returncode == 0,
              f"rc={r.returncode} out={r.stdout[-400:]} err={r.stderr[-200:]}")


def test_apply_stops_after_a_pin_mismatch() -> None:
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as td:
        tmp = Path(td)
        home = tmp / "alt-home"
        r = run_apply(tmp, home, [], sha="deadbeef" * 5)
        logs = list(tmp.glob("hermes-calls.log"))
        content = logs[0].read_text() if logs else ""
        check("a pin mismatch is reported as a failure", r.returncode != 0, f"rc={r.returncode}")
        check("a pin mismatch does NOT write the settings block",
              "config set plugins.entries" not in content,
              [ln for ln in content.splitlines() if "config set" in ln])
        check("a pin mismatch does NOT enable the plugin",
              "config set plugins.enabled" not in content,
              [ln for ln in content.splitlines() if "plugins.enabled" in ln])
        check("the routing table is not copied for an unverified revision",
              not (home / "hermes-jev-routing.json").exists())


def test_apply_handles_an_empty_allow_list() -> None:
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as td:
        tmp = Path(td)
        home = tmp / "alt-home"
        r = run_apply(tmp, home, [], enabled=[])
        logs = list(tmp.glob("hermes-calls.log"))
        content = logs[0].read_text() if logs else ""
        check("an empty plugins.enabled does not abort the apply",
              r.returncode == 0, f"rc={r.returncode} out={r.stdout[-400:]} err={r.stderr[-200:]}")
        check("an empty plugins.enabled is replaced with a valid list",
              "config set plugins.enabled [hermes-jev-routing]" in content,
              [ln for ln in content.splitlines() if "plugins.enabled" in ln])


def test_apply_does_not_abort_on_a_missing_pin_file() -> None:
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as td:
        tmp = Path(td)
        home = tmp / "alt-home"
        r = run_apply(tmp, home, [], sha=None)
        logs = list(tmp.glob("hermes-calls.log"))
        content = logs[0].read_text() if logs else ""
        check("missing pin metadata is a verification failure", r.returncode != 0,
              f"rc={r.returncode}")
        check("missing pin metadata does not enable the plugin",
              "config set plugins.enabled" not in content,
              [ln for ln in content.splitlines() if "plugins.enabled" in ln])


# ---------------------------------------------------------------------------
# 4. a live check that could not run must fail
# ---------------------------------------------------------------------------
def test_live_check_fails_when_it_cannot_run() -> None:
    with tempfile.TemporaryDirectory(dir=str(SCRATCH)) as td:
        tmp = Path(td)
        env = dict(os.environ)
        # a HERMES_HOME with no hermes-agent source: the resolver cannot be
        # imported, so the live check cannot be satisfied
        env["HERMES_HOME"] = str(tmp / "no-hermes")
        env["PYTHONPATH"] = str(tmp / "empty")
        r = subprocess.run([sys.executable, str(VALIDATE), "--live"],
                           capture_output=True, text=True, env=env, cwd=str(REPO))
        check("a live check that cannot import the resolver fails",
              r.returncode != 0, f"rc={r.returncode}")
        check("the failure says the check could not be satisfied",
              "cannot be satisfied" in (r.stdout + r.stderr),
              (r.stdout + r.stderr)[-400:])


def main() -> int:
    for fn in (
        test_drift_detects_every_setting,
        test_install_selects_the_bound_provider,
        test_apply_exports_the_selected_home,
        test_apply_stops_after_a_pin_mismatch,
        test_apply_handles_an_empty_allow_list,
        test_apply_does_not_abort_on_a_missing_pin_file,
        test_live_check_fails_when_it_cannot_run,
    ):
        try:
            fn()
        except Exception as e:  # noqa: BLE001 - a raising test is a failing test
            check(f"{fn.__name__} (raised)", False, f"{type(e).__name__}: {e}")

    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
