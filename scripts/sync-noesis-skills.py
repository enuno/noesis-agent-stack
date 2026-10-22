#!/usr/bin/env python3
"""Sync noesis-* skills from the live Hermes fleet into this repository.

The local Hermes profile skill directories are the *working copy*. This repo is
the *durable, reviewable, versioned* copy required by the skill-sync policy in
`shared/POLICY.global.md` §12.

Usage:
    scripts/sync-noesis-skills.py --check     # drift detection, no writes (CI/pre-commit)
    scripts/sync-noesis-skills.py --sync      # copy drifted skills into skills/, write manifest
    scripts/sync-noesis-skills.py --status     # human-readable table of every tracked skill

Exit codes:
    0  in sync (or nothing to do)
    2  drift detected (with --check)
    3  divergent duplicate copies requiring operator resolution
    4  scan found nothing at all (misconfigured environment)
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST_ROOT = REPO / "skills"
MANIFEST = DEST_ROOT / "noesis-skills.manifest.json"
def resolve_hermes_root() -> Path:
    """Find the Hermes *root* (the dir containing `profiles/` and `skills/`).

    HERMES_HOME is not reliable: inside a fleet profile session it points at the
    profile dir (e.g. ~/.hermes/profiles/noesis-orchestrator), which has no
    `profiles/` child. Scanning that as a root silently sees only one profile's
    skills, so resolve the true root instead of trusting the env var.
    """
    candidates = []
    env = os.environ.get("HERMES_HOME")
    if env:
        candidates.append(Path(env))
    candidates.append(Path.home() / ".hermes")

    for cand in candidates:
        if (cand / "profiles").is_dir():
            return cand
        # HERMES_HOME is a profile home -> its parent is the real root.
        parent = cand.parent
        if (cand / "skills").is_dir() and (parent / "profiles").is_dir():
            return parent
    # Last resort: first profile-shaped path under ~/.hermes.
    default = Path.home() / ".hermes"
    if (default / "profiles").is_dir():
        return default
    return default


HERMES_ROOT = resolve_hermes_root()

SKILL_PREFIX = "noesis-"

# Local bookkeeping artifacts that must never enter the durable repo copy.
EXCLUDED_NAMES = {"_skill_library_update.json", ".DS_Store"}
EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def iter_skill_files(root: Path) -> list[Path]:
    """Every file that is part of the skill content, sorted, dirs excluded."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
        for fn in sorted(filenames):
            if fn in EXCLUDED_NAMES or fn.startswith("._"):
                continue
            out.append(Path(dirpath) / fn)
    return sorted(out)


def digest_tree(root: Path) -> str:
    """Content digest over the whole tree: path + bytes, order-stable."""
    h = hashlib.sha256()
    for fp in iter_skill_files(root):
        h.update(str(fp.relative_to(root)).encode())
        h.update(b"\0")
        h.update(fp.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def scan_roots() -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    profiles_dir = HERMES_ROOT / "profiles"
    if profiles_dir.is_dir():
        for prof in sorted(p for p in profiles_dir.iterdir() if p.is_dir()):
            sp = prof / "skills"
            if sp.is_dir():
                roots.append((prof.name, sp))
    default = HERMES_ROOT / "skills"
    if default.is_dir():
        roots.append(("default", default))
    return roots


def discover() -> dict[str, list[dict]]:
    """Map skill name -> every on-disk copy found across the fleet."""
    found: dict[str, list[dict]] = {}
    for profile, root in scan_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                d for d in dirnames if d not in EXCLUDED_DIRS and not d.startswith(".")
            )
            name = os.path.basename(dirpath)
            if not name.startswith(SKILL_PREFIX):
                continue
            if "SKILL.md" not in filenames:
                continue
            p = Path(dirpath)
            found.setdefault(name, []).append(
                {
                    "name": name,
                    "source_profile": profile,
                    "source_path": str(p),
                    "source_relpath": os.path.relpath(p, root),
                    "source_digest_sha256": digest_tree(p),
                    "file_count": len(iter_skill_files(p)),
                }
            )
    for recs in found.values():
        recs.sort(key=lambda r: (r["source_profile"] == "noesis-orchestrator",
                                 r["source_profile"] != "default",
                                 r["source_profile"]))
    return found


def load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {"skills": []}
    with MANIFEST.open() as fh:
        return json.load(fh)


def build_plan(found: dict[str, list[dict]], ts: str) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    conflicts: list[str] = []
    for name in sorted(found):
        recs = found[name]
        primary = recs[0]
        digests = {r["source_digest_sha256"] for r in recs}
        entry = {
            "name": name,
            "repo_path": f"skills/{name}",
            "source_profile": primary["source_profile"],
            "source_path": primary["source_path"],
            "source_relpath": primary["source_relpath"],
            "file_count": primary["file_count"],
            "source_digest_sha256": primary["source_digest_sha256"],
            "synced_at": ts,
        }
        if len(digests) > 1:
            entry["conflicting_sources"] = [
                {"source_profile": r["source_profile"],
                 "source_path": r["source_path"],
                 "source_digest_sha256": r["source_digest_sha256"]}
                for r in recs
            ]
            conflicts.append(name)
        elif len(recs) > 1:
            entry["duplicate_copies"] = [
                {"source_profile": r["source_profile"], "source_path": r["source_path"]}
                for r in recs[1:]
            ]
        entries.append(entry)
    return entries, conflicts


def copy_skill(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*EXCLUDED_DIRS, *_EXCLUDE_GLOBS))


_EXCLUDE_GLOBS = EXCLUDED_NAMES


def do_sync(found: dict[str, list[dict]]) -> int:
    ts = utc_now()
    entries, conflicts = build_plan(found, ts)
    if not entries:
        print("ERROR: no noesis-* skills discovered under "
              f"{HERMES_ROOT}/profiles/*/skills or {HERMES_ROOT}/skills", file=sys.stderr)
        return 4

    for e in entries:
        rec = found[e["name"]][0]
        dst = DEST_ROOT / e["name"]
        copy_skill(Path(rec["source_path"]), dst)
        got = digest_tree(dst)
        if got != rec["source_digest_sha256"]:
            print(f"ERROR: post-copy digest mismatch for {e['name']}", file=sys.stderr)
            print(f"  expected {rec['source_digest_sha256']}", file=sys.stderr)
            print(f"  got      {got}", file=sys.stderr)
            return 5
        e["repo_digest_sha256"] = got
        e["verified"] = True

    manifest = {
        "version": 2,
        "generated_at": ts,
        "generated_by": "scripts/sync-noesis-skills.py --sync",
        "repo": "noesis-agent-stack",
        "source_scan_roots": [
            str(HERMES_ROOT / "profiles/*/skills"),
            str(HERMES_ROOT / "skills"),
        ],
        "selection_rule": (
            "Skill name must start with 'noesis-' and contain SKILL.md. "
            "On tie the noesis-orchestrator copy wins, then the default-profile copy."
        ),
        "excluded_from_repo_copy": sorted(EXCLUDED_NAMES),
        "skills": entries,
    }
    with MANIFEST.open("w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")

    print(f"synced {len(entries)} noesis-* skills -> {DEST_ROOT}")
    for e in entries:
        dup = f"  (+{len(e['duplicate_copies'])} identical dup)" if e.get("duplicate_copies") else ""
        conf = "  [DIVERGENT]" if e.get("conflicting_sources") else ""
        print(f"  {e['name']:44s} <- {e['source_profile']}/{e['source_relpath']}"
              f"  {e['source_digest_sha256'][:12]}{dup}{conf}")
    if conflicts:
        print(f"\nDIVERGENT copies needing operator resolution: {', '.join(conflicts)}",
              file=sys.stderr)
        return 3
    return 0


def do_check(found: dict[str, list[dict]]) -> int:
    """Fail when the durable copy does not match the live fleet working copy."""
    if not found:
        print("ERROR: no noesis-* skills discovered; cannot verify sync", file=sys.stderr)
        return 4
    manifest = load_manifest()
    tracked = {e["name"]: e for e in manifest.get("skills", [])}
    drifted: list[str] = []
    missing: list[str] = []
    conflicts: list[str] = []

    for name, recs in sorted(found.items()):
        digests = {r["source_digest_sha256"] for r in recs}
        if len(digests) > 1:
            conflicts.append(name)
            continue
        live = recs[0]["source_digest_sha256"]
        rec = tracked.get(name)
        if rec is None:
            missing.append(name)
            continue
        if rec.get("source_digest_sha256") != live:
            drifted.append(name)
            continue
        repo_dir = DEST_ROOT / name
        if not repo_dir.is_dir() or digest_tree(repo_dir) != live:
            drifted.append(name)

    for name in sorted(set(tracked) - set(found)):
        print(f"  ORPHANED  {name} — tracked in manifest, no longer on disk")

    if missing:
        for n in missing:
            print(f"  UNSYNCED  {n} — present in fleet, absent from manifest", file=sys.stderr)
    if drifted:
        for n in drifted:
            print(f"  DRIFTED   {n} — fleet copy differs from repo copy", file=sys.stderr)
    if conflicts:
        for n in conflicts:
            print(f"  DIVERGENT {n} — multiple fleet copies disagree; operator must resolve",
                  file=sys.stderr)

    if missing or drifted or conflicts:
        print("skills-sync: FAIL — run scripts/sync-noesis-skills.py --sync "
              "and commit the result", file=sys.stderr)
        return 3 if conflicts else 2

    print(f"skills-sync: OK — {len(found)} noesis-* skills in sync with the fleet")
    return 0


def do_status(found: dict[str, list[dict]]) -> int:
    manifest = load_manifest()
    tracked = {e["name"]: e for e in manifest.get("skills", [])}
    rows = []
    for name, recs in sorted(found.items()):
        live = recs[0]["source_digest_sha256"]
        rec = tracked.get(name)
        repo_dir = DEST_ROOT / name
        repo_d = digest_tree(repo_dir) if repo_dir.is_dir() else None
        if len({r["source_digest_sha256"] for r in recs}) > 1:
            state = "DIVERGENT"
        elif repo_d == live:
            state = "in-sync"
        elif rec is None:
            state = "unsynced"
        else:
            state = "drifted"
        rows.append((name, recs[0]["source_profile"], live[:12],
                     (repo_d or "-")[:12], state, recs[0]["source_relpath"]))
    w = max((len(r[0]) for r in rows), default=10)
    print(f"{'SKILL'.ljust(w)}  {'PROFILE':20s}  {'FLEET':12s}  {'REPO':12s}  STATE")
    for name, prof, live, repo_d, state, rel in rows:
        print(f"{name.ljust(w)}  {prof:20s}  {live:12s}  {repo_d:12s}  {state}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="detect drift, write nothing")
    ap.add_argument("--sync", action="store_true", help="copy drifted skills into skills/")
    ap.add_argument("--status", action="store_true", help="print a status table")
    args = ap.parse_args()

    found = discover()
    if args.status:
        return do_status(found)
    if args.sync:
        return do_sync(found)
    return do_check(found)


if __name__ == "__main__":
    sys.exit(main())