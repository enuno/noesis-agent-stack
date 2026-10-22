#!/usr/bin/env python3
"""Static validation for the noesis-praxis managed skill tree.

Stdlib-only, no network, never executes any file under skills/. Safe to run
locally with no runtime Hermes access -- checks that need a live profile
degrade to "not verified" instead of failing.

Usage:
    python3 tests/validate_skill_tree.py [--runtime-root PATH]

Exit code 0 = no hard failures (warnings are still printed and summarized).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - degrade gracefully, don't hard-fail the whole run
    yaml = None


def _fallback_parse_manifest(text: str) -> dict:
    """Minimal dependency-free parser for this repo's own manifest.yaml shape only.

    Handles: a top-level `skills:` list of flat `key: value` mappings, where a
    value is null/~, a bareword/number, a single- or double-quoted string, or a
    YAML folded block scalar (`key: >` followed by indented continuation
    lines). This is NOT a general YAML parser -- it exists only so the
    validator still runs something useful when PyYAML isn't installed and no
    system package install is permitted. Install PyYAML for full robustness.
    """
    skills: list[dict] = []
    current: dict | None = None
    folded_key: str | None = None
    folded_lines: list[str] = []

    def flush_folded() -> None:
        nonlocal folded_key, folded_lines
        if current is not None and folded_key is not None:
            current[folded_key] = " ".join(line.strip() for line in folded_lines if line.strip())
        folded_key, folded_lines = None, []

    for raw_line in text.splitlines():
        if raw_line.strip().startswith("#") or not raw_line.strip():
            if folded_key is None:
                continue
        if folded_key is not None:
            if raw_line.startswith("      ") or (raw_line.strip() == "" and current is not None):
                folded_lines.append(raw_line)
                continue
            flush_folded()
        stripped = raw_line.strip()
        if stripped.startswith("- requested_identifier:") or (stripped.startswith("-") and "requested_identifier" in stripped):
            if current is not None:
                skills.append(current)
            current = {}
            stripped = stripped[1:].strip()
        if current is None:
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value == ">":
            folded_key = key
            folded_lines = []
            continue
        if value in ("null", "~", ""):
            current[key] = None
        else:
            current[key] = value.strip('"').strip("'")
    flush_folded()
    if current is not None:
        skills.append(current)
    return {"skills": skills}


TREE_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = TREE_ROOT / "skills"
PROVENANCE = TREE_ROOT / "provenance"
MANIFEST = PROVENANCE / "manifest.yaml"
CHECKSUMS = PROVENANCE / "checksums.sha256"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
LOCAL_REF_RE = re.compile(r"\((?:\./)?((?:scripts|references|templates|assets)/[^\s)]+)\)")


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors


def iter_skill_dirs() -> list[Path]:
    if not SKILLS_ROOT.is_dir():
        return []
    return sorted(p for p in SKILLS_ROOT.iterdir() if p.is_dir())


def check_required_metadata(result: Result) -> None:
    for skill_dir in iter_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            result.error(f"{skill_dir.name}: missing SKILL.md")
            continue
        text = skill_md.read_text(errors="replace")
        m = FRONTMATTER_RE.match(text)
        if not m:
            result.error(f"{skill_dir.name}: SKILL.md has no YAML frontmatter block")
            continue
        fm = m.group(1)
        for field in ("name", "description"):
            if not re.search(rf"^{field}:", fm, re.MULTILINE):
                result.error(f"{skill_dir.name}: SKILL.md frontmatter missing '{field}:'")


def check_duplicate_names(result: Result) -> None:
    names: dict[str, list[str]] = {}
    for skill_dir in iter_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(errors="replace")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        name_m = re.search(r"^name:\s*(\S+)", m.group(1), re.MULTILINE)
        if not name_m:
            continue
        name = name_m.group(1).strip().strip('"').strip("'")
        names.setdefault(name, []).append(skill_dir.name)
    for name, dirs in names.items():
        if len(dirs) > 1:
            result.error(f"duplicate skill name '{name}' used by directories: {dirs}")


def check_local_references(result: Result) -> None:
    for skill_dir in iter_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(errors="replace")
        for ref in LOCAL_REF_RE.findall(text):
            ref_path = ref.split("#", 1)[0]  # strip a markdown anchor fragment, e.g. file.md#heading
            if not ref_path:
                continue
            target = skill_dir / ref_path
            if not target.exists():
                result.error(f"{skill_dir.name}: SKILL.md references missing file '{ref_path}' (from link '{ref}')")


def check_symlink_escapes(result: Result) -> None:
    if not SKILLS_ROOT.is_dir():
        return
    for path in SKILLS_ROOT.rglob("*"):
        if path.is_symlink():
            try:
                resolved = path.resolve()
            except OSError:
                result.error(f"unresolvable symlink: {path}")
                continue
            try:
                resolved.relative_to(SKILLS_ROOT.resolve())
            except ValueError:
                result.error(f"symlink escapes skill tree: {path} -> {resolved}")


def _load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {}
    text = MANIFEST.read_text()
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _fallback_parse_manifest(text)


def check_manifest_completeness(result: Result) -> dict:
    manifest = _load_manifest()
    if not manifest:
        result.warn("provenance/manifest.yaml missing or unparsable -- manifest-dependent checks skipped")
        return {}
    if yaml is None:
        result.warn("PyYAML not installed -- using this script's minimal built-in manifest "
                    "parser (less robust than real YAML); install pyyaml for full coverage")
    entries = manifest.get("skills", [])
    by_dir = {e.get("repository_directory"): e for e in entries if isinstance(e, dict)}
    for skill_dir in iter_skill_dirs():
        entry = by_dir.get(skill_dir.name)
        if entry is None:
            result.error(f"{skill_dir.name}: no provenance/manifest.yaml entry")
            continue
        for field in ("requested_identifier", "upstream_source", "upstream_commit",
                      "disposition", "license"):
            if not entry.get(field):
                result.error(f"{skill_dir.name}: manifest entry missing '{field}'")
    for name, entry in by_dir.items():
        if entry.get("status") == "blocked":
            continue
        if name and not (SKILLS_ROOT / name).is_dir():
            result.error(f"manifest entry '{name}' has no corresponding skills/ directory")
    return manifest


def _iter_payload_files() -> list[Path]:
    files: list[Path] = []
    for skill_dir in iter_skill_dirs():
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file():
                files.append(f)
    return sorted(files)


def check_checksums(result: Result, write: bool = False) -> None:
    files = _iter_payload_files()
    lines = []
    for f in files:
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        rel = f.relative_to(TREE_ROOT)
        lines.append(f"{digest}  {rel.as_posix()}")
    computed = "\n".join(lines) + ("\n" if lines else "")

    if write:
        CHECKSUMS.write_text(computed)
        return

    if not CHECKSUMS.is_file():
        result.warn("provenance/checksums.sha256 missing -- run with --write-checksums to generate")
        return
    recorded = CHECKSUMS.read_text()
    if recorded != computed:
        result.error(
            "provenance/checksums.sha256 does not match current skill payload files "
            "(re-run with --write-checksums after an intentional change, then review the diff)"
        )


def check_runtime_drift(result: Result, runtime_root: Path | None) -> None:
    if runtime_root is None or not runtime_root.is_dir():
        result.warn("no --runtime-root given or path does not exist -- runtime/repo drift not verified")
        return
    manifest = _load_manifest()
    entries = {e.get("repository_directory"): e for e in manifest.get("skills", []) if isinstance(e, dict)}
    for skill_dir in iter_skill_dirs():
        entry = entries.get(skill_dir.name, {})
        deployed_rel = entry.get("deployed_path")
        if not deployed_rel:
            result.warn(f"{skill_dir.name}: no deployed_path in manifest -- drift not verified")
            continue
        deployed = runtime_root / deployed_rel
        if not deployed.is_dir():
            result.warn(f"{skill_dir.name}: deployed path {deployed} not found -- not deployed or not verified")
            continue
        for src_file in sorted(skill_dir.rglob("*")):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(skill_dir)
            dst_file = deployed / rel
            if not dst_file.is_file():
                result.error(f"{skill_dir.name}: runtime missing {rel}")
                continue
            if hashlib.sha256(src_file.read_bytes()).hexdigest() != hashlib.sha256(dst_file.read_bytes()).hexdigest():
                result.error(f"{skill_dir.name}: runtime copy of {rel} differs from repository -- drift")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=None,
                         help="A Hermes profile's skills/ root to check for drift, e.g. ~/.hermes/skills")
    parser.add_argument("--write-checksums", action="store_true",
                         help="Regenerate provenance/checksums.sha256 instead of checking it")
    args = parser.parse_args()

    result = Result()
    check_required_metadata(result)
    check_duplicate_names(result)
    check_local_references(result)
    check_symlink_escapes(result)
    check_manifest_completeness(result)
    check_checksums(result, write=args.write_checksums)
    if not args.write_checksums:
        check_runtime_drift(result, args.runtime_root)

    for w in result.warnings:
        print(f"WARN: {w}")
    for e in result.errors:
        print(f"ERROR: {e}")

    if args.write_checksums:
        print(f"checksums written to {CHECKSUMS}")
        return 0

    print(f"\n{len(result.errors)} error(s), {len(result.warnings)} warning(s)")
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
