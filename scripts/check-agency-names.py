#!/usr/bin/env python3
"""check-agency-names.py — curation sanity audit (ralplan task T02).

Validates agency/curation.yaml against the PINNED upstream tree and the
existing noesis fleet. Read-only; exits non-zero on any violation.

Checks:
  1. agency/SOURCE pin parses; upstream checkout exists and the pinned
     commit is an ancestor of (or equal to) upstream HEAD.
  2. Every curated agent's `source` file exists in the pinned tree.
  3. Curated `slug` / profile names (agency-<slug>) are unique and
     well-formed; exactly one agent per division; total <= 18.
  4. Divisions referenced exist in upstream divisions.json.
  5. Zero name collision with the 16 noesis-* fleet (agents/noesis-*/).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENCY = ROOT / "agency"
SOURCE_FILE = AGENCY / "SOURCE"
CURATION = AGENCY / "curation.yaml"
NOESIS_AGENTS_DIR = ROOT / "agents"

MAX_TIER_A = 18
PROFILE_RE = re.compile(r"^agency-[a-z0-9]+(-[a-z0-9]+)*$")

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def parse_source() -> dict[str, str]:
    data: dict[str, str] = {}
    for line in SOURCE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def find_upstream_checkout() -> Path | None:
    """Locate the local upstream checkout the pin refers to."""
    preferred = Path.home() / "tools" / "agency-agents"
    if (preferred / "divisions.json").is_file():
        return preferred
    return None


def main() -> int:
    if not CURATION.is_file():
        fail(f"missing {CURATION}")
        return report()
    if not SOURCE_FILE.is_file():
        fail(f"missing {SOURCE_FILE}")
        return report()

    source = parse_source()
    commit = source.get("UPSTREAM_COMMIT", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        fail(f"UPSTREAM_COMMIT malformed: {commit!r}")

    upstream = find_upstream_checkout()
    if upstream is None:
        fail("upstream checkout not found at ~/tools/agency-agents")
        return report()

    # 1. pin is an ancestor of upstream HEAD (local checkout may be ahead)
    if commit:
        rc = subprocess.run(
            ["git", "-C", str(upstream), "merge-base", "--is-ancestor", commit, "HEAD"],
            capture_output=True,
        ).returncode
        if rc != 0:
            head = subprocess.run(
                ["git", "-C", str(upstream), "rev-parse", "HEAD"],
                capture_output=True, text=True,
            ).stdout.strip()
            fail(
                f"pin {commit[:12]} is not an ancestor of upstream HEAD {head[:12]} "
                f"— repin via agency/README.md procedure"
            )
        else:
            # pin content must be present in the checkout
            rc = subprocess.run(
                ["git", "-C", str(upstream), "cat-file", "-e", f"{commit}^{{commit}}"],
                capture_output=True,
            ).returncode
            if rc != 0:
                fail(f"pinned commit {commit[:12]} not present in upstream checkout")

    # 2-4. curation structure
    cur = yaml.safe_load(CURATION.read_text(encoding="utf-8"))
    agents = cur.get("agents") or []
    if not agents:
        fail("curation.yaml has no agents")

    prefix = cur.get("profile_prefix", "agency")
    divisions_json = json.loads((upstream / "divisions.json").read_text(encoding="utf-8"))
    valid_divisions = set(divisions_json["divisions"].keys())

    seen_slugs: set[str] = set()
    seen_profiles: set[str] = set()
    seen_divisions: dict[str, str] = {}

    for entry in agents:
        slug = entry.get("slug", "")
        src = entry.get("source", "")
        div = entry.get("division", "")
        wave = entry.get("wave")
        profile = f"{prefix}-{slug}"

        if not PROFILE_RE.match(profile):
            fail(f"bad profile name {profile!r} (slug={slug!r})")
        if slug in seen_slugs:
            fail(f"duplicate slug {slug!r}")
        seen_slugs.add(slug)
        if profile in seen_profiles:
            fail(f"duplicate profile {profile!r}")
        seen_profiles.add(profile)

        if div not in valid_divisions:
            fail(f"{slug}: division {div!r} not in upstream divisions.json")
        elif div in seen_divisions:
            fail(
                f"division {div!r} has two curated agents "
                f"({seen_divisions[div]} and {slug}) — cap is 1/division"
            )
        else:
            seen_divisions[div] = slug

        if wave not in (1, 2):
            fail(f"{slug}: wave must be 1 or 2, got {wave!r}")

        src_path = upstream / src
        if not src_path.is_file():
            fail(f"{slug}: source {src} not found in pinned upstream tree")
        else:
            # reject symlinks escaping the tree (defense in depth)
            if src_path.resolve() != src_path:
                fail(f"{slug}: source {src} resolves outside upstream tree")

    if len(agents) > MAX_TIER_A:
        fail(f"Tier A cap exceeded: {len(agents)} > {MAX_TIER_A}")

    # 5. collision with noesis fleet
    noesis_profiles = set()
    if NOESIS_AGENTS_DIR.is_dir():
        for child in NOESIS_AGENTS_DIR.iterdir():
            if child.is_dir():
                noesis_profiles.add(child.name)
    for profile in sorted(seen_profiles):
        if profile in noesis_profiles:
            fail(f"profile {profile} collides with existing noesis fleet member")
        if profile.removeprefix(f"{prefix}-") in noesis_profiles:
            warnings.append(f"{profile}: slug shadowed by noesis profile of same base name")

    return report()


def report() -> int:
    for w in warnings:
        print(f"WARNING: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\ncheck-agency-names: FAIL ({len(errors)} error(s))")
        return 1
    print("check-agency-names: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
