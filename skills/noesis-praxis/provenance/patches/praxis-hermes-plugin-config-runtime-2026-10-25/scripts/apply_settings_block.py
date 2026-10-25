#!/usr/bin/env python3
"""Apply a plugin settings block to a Hermes profile config, then verify it.

Applies every key of a JSON settings file with its own `hermes config set`
call (one key per call, so a failure is attributable to a single key), then
re-reads config.yaml with a YAML parser and diffs the stored mapping against
the requested one.

The values are passed as ARGV elements, never as a shell string. That is the
whole point of this script: quoting an empty string in a shell command stores
the two-character token `''` instead of an empty value, and the resulting
config.yaml line (`browser_executable: "''"`) is read by the plugin as a
non-empty path.

Usage:
    apply_settings_block.py <settings.json> [--plugin-id ID] [--profile P]
                             [--config PATH] [--dry-run]

Exit code 0 only when every requested key is stored with exactly the
requested value.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

DEFAULT_PLUGIN = "hermes-switchyard"
BASE = "plugins.entries.{pid}.settings"


def run_config_set(plugin_id: str, key: str, value, profile: str | None) -> tuple[int, str]:
    """One `hermes config set` call. `value` is passed as an argv element."""
    path = f"{BASE.format(pid=plugin_id)}.{key}"
    argv = ["hermes"]
    if profile:
        argv += ["-p", profile]
    argv += ["config", "set", path]
    if isinstance(value, bool):
        argv.append("true" if value else "false")
    elif isinstance(value, (int, float)):
        argv.append(repr(value))
    elif isinstance(value, list):
        argv.append(json.dumps(value))
    elif value is None:
        argv.append("")  # a real empty argv element, NOT "''"
    else:
        argv.append(str(value))
    proc = subprocess.run(argv, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def load_yaml(path: str):
    try:
        import yaml
    except ImportError:
        sys.exit(
            "PyYAML is required to verify the result. Install it, or run this "
            "script with an interpreter that has it."
        )
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("settings", help="JSON file holding the settings mapping")
    ap.add_argument("--plugin-id", default=DEFAULT_PLUGIN)
    ap.add_argument("--profile", default=None, help="Hermes profile name (omit for the default)")
    ap.add_argument("--config", default=None, help="config.yaml path (default: `hermes config path`)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be set, change nothing")
    args = ap.parse_args()

    with open(args.settings, encoding="utf-8") as fh:
        requested = json.load(fh)
    if not isinstance(requested, dict):
        sys.exit("settings file must contain a JSON object")

    config_path = args.config
    if not config_path:
        argv = ["hermes"] + (["-p", args.profile] if args.profile else []) + ["config", "path"]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f"could not resolve config path: {proc.stderr.strip()}")
        config_path = proc.stdout.strip().splitlines()[-1]

    if args.dry_run:
        for key, value in requested.items():
            print(f"would set {BASE.format(pid=args.plugin_id)}.{key} = {value!r}")
        return 0

    failures = []
    for key, value in requested.items():
        code, out = run_config_set(args.plugin_id, key, value, args.profile)
        if code != 0:
            failures.append(key)
            print(f"FAIL {key}: {out}")
        else:
            print(f"ok   {key} = {value!r}")

    # Verify against the stored bytes, not the CLI's echo.
    cfg = load_yaml(config_path)
    entry = ((cfg.get("plugins") or {}).get("entries") or {}).get(args.plugin_id) or {}
    stored = entry.get("settings") or {}

    missing = [k for k in requested if k not in stored]
    extra = [k for k in stored if k not in requested]
    mismatched = {k: (requested[k], stored[k]) for k in requested if k in stored and stored[k] != requested[k]}

    print()
    print(f"config: {config_path}")
    print(f"missing:   {missing or 'none'}")
    print(f"extra:     {extra or 'none'}")
    if mismatched:
        print("mismatched:")
        for k, (want, got) in mismatched.items():
            print(f"  {k}: want {want!r} got {got!r}")
    else:
        print("mismatched: none")

    if failures or missing or extra or mismatched:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: OK — {len(requested)} setting(s) stored exactly as requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
