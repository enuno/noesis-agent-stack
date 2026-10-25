#!/usr/bin/env python3
"""validate_mcpjungle_groups.py — offline validator for the Noesis MCPJungle group catalog.

This validator is repository-local, deterministic and non-mutating. It never contacts
the MCPJungle gateway, never reads ~/.hermes, never invokes a tool, and never creates or
updates a group. It checks the committed artifacts under config/mcpjungle/ against each
other and against the MCPJungle 0.4.6 constraints.

Checks
  1.  Every JSON artifact parses.
  2.  Every group file uses only MCPJungle-supported fields.
  3.  Every group name satisfies the verified MCPJungle name pattern.
  4.  No group is empty.
  5.  No group contains duplicate tool names.
  6.  Every membership resolves to a tool observed in tool-inventory.json.
  7.  Catalog membership matches the individual group files exactly.
  8.  Every discovered tool is assigned to at least one group, or is explicitly listed as
      unassigned/review-required with a reason.
  9.  A group whose risk level is 'low' contains no member classified above 'low'.
  10. Group files use included_tools allowlists only, never included_servers.
  11. No secret-shaped value appears in any committed artifact.
  12. File and member ordering is deterministic (sorted).

Usage
    python3 scripts/validate_mcpjungle_groups.py [--root REPO_ROOT] [-v]

Exit codes
    0  all checks pass
    1  one or more checks failed
    2  a required input is missing or unreadable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCPJUNGLE_DIR = ROOT / "config" / "mcpjungle"
INVENTORY = MCPJUNGLE_DIR / "tool-inventory.json"
CATALOG = MCPJUNGLE_DIR / "tool-groups.json"
GROUPS_DIR = MCPJUNGLE_DIR / "groups"
BACKUP = MCPJUNGLE_DIR / "backup" / "gateway-state-backup.json"

# Verified against MCPJungle 0.4.6 pkg/types/tool_group.go (ToolGroup struct).
SUPPORTED_FIELDS = {"name", "description", "included_tools", "included_servers",
                    "excluded_tools"}

# Verified against MCPJungle 0.4.6 internal/service/toolgroup/toolgroup.go
# (ValidGroupName).
VALID_GROUP_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")

# Canonical tool name is "<server>__<tool>", split on the FIRST "__"
# (MCPJungle 0.4.6 internal/service/mcp/util.go, serverToolNameSep).
CANONICAL_SEP = "__"

RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "review-required": 3}

# Patterns for values that must never be committed.
SECRET_PATTERNS = {
    "bearer token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9._\-]{20,}"),
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"),
    "aws access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai-style key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    "credential assignment": re.compile(
        r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|bearer)\b\s*[:=]\s*"
        r"[\"'][^\"']{8,}[\"']"),
    "credential in url": re.compile(r"://[^/\s:@]+:[^/\s:@]+@"),
    "mcpjungle user token": re.compile(r"\b[a-zA-Z0-9]{43}\b"),
}

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        print(f"FATAL: required input missing: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        fail(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return {}


def roster_profile_keys() -> set[str] | None:
    """Return the profile keys declared in profiles/noesis-roster.yaml.

    Parsed with a minimal reader so the validator has no third-party dependency
    (PyYAML is not guaranteed to be installed for the interpreter in use).
    Returns None if the roster cannot be read.
    """
    roster = ROOT / "profiles" / "noesis-roster.yaml"
    try:
        text = roster.read_text(encoding="utf-8")
    except OSError:
        return None
    keys: set[str] = set()
    in_profiles = False
    for line in text.splitlines():
        if re.match(r"^profiles:\s*$", line):
            in_profiles = True
            continue
        if in_profiles:
            if line and not line.startswith(" "):
                break
            m = re.match(r"^  ([a-z0-9][a-z0-9-]*):\s*$", line)
            if m:
                keys.add(m.group(1))
    return keys or None


def main() -> int:
    global ROOT, MCPJUNGLE_DIR, INVENTORY, CATALOG, GROUPS_DIR, BACKUP

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root")
    ap.add_argument("-v", "--verbose", action="store_true", help="print per-check detail")
    args = ap.parse_args()

    ROOT = args.root.resolve()
    MCPJUNGLE_DIR = ROOT / "config" / "mcpjungle"
    INVENTORY = MCPJUNGLE_DIR / "tool-inventory.json"
    CATALOG = MCPJUNGLE_DIR / "tool-groups.json"
    GROUPS_DIR = MCPJUNGLE_DIR / "groups"
    BACKUP = MCPJUNGLE_DIR / "backup" / "gateway-state-backup.json"

    if not GROUPS_DIR.is_dir():
        print(f"FATAL: group directory missing: {GROUPS_DIR}", file=sys.stderr)
        return 2

    inventory = load_json(INVENTORY)
    catalog = load_json(CATALOG)
    if not inventory or not catalog:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    # ── 1. inventory integrity ────────────────────────────────────────────
    inv_tools = inventory.get("tools", [])
    inv_by_name = {t["name"]: t for t in inv_tools}
    if len(inv_by_name) != len(inv_tools):
        fail("tool-inventory.json contains duplicate tool names")
    for t in inv_tools:
        name = t.get("name", "")
        if CANONICAL_SEP not in name:
            fail(f"tool-inventory.json: tool {name!r} is not a canonical "
                 f"'<server>{CANONICAL_SEP}<tool>' name")
        for key in ("source_server", "risk_classification", "risk_rationale",
                    "inferred_capability_category"):
            if not t.get(key):
                fail(f"tool-inventory.json: tool {name!r} is missing {key}")
    if args.verbose:
        print(f"  inventory: {len(inv_tools)} tools, "
              f"{len(set(t['source_server'] for t in inv_tools))} source servers")

    # ── 2. group files ────────────────────────────────────────────────────
    group_files = sorted(GROUPS_DIR.glob("*.json"))
    if not group_files:
        fail("groups/ contains no group files")

    file_groups: dict[str, dict] = {}
    for path in group_files:
        doc = load_json(path)
        if not doc:
            continue
        extra = set(doc.keys()) - SUPPORTED_FIELDS
        if extra:
            fail(f"{path.relative_to(ROOT)}: uses fields that MCPJungle 0.4.6 does not "
                 f"support: {sorted(extra)}")
        missing = {"name", "included_tools"} - set(doc.keys())
        if missing:
            fail(f"{path.relative_to(ROOT)}: missing required field(s) {sorted(missing)}")
            continue
        name = doc["name"]
        if not VALID_GROUP_NAME.match(name):
            fail(f"{path.relative_to(ROOT)}: group name {name!r} violates the verified "
                 f"MCPJungle pattern ^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
        if name != path.stem:
            fail(f"{path.relative_to(ROOT)}: group name {name!r} does not match the "
                 f"filename {path.stem!r}")
        if name in file_groups:
            fail(f"duplicate group name across files: {name!r}")
        tools = doc["included_tools"]
        if not isinstance(tools, list) or not tools:
            fail(f"{path.relative_to(ROOT)}: included_tools is empty or not a list")
            continue
        dupes = [n for n, c in Counter(tools).items() if c > 1]
        if dupes:
            fail(f"{path.relative_to(ROOT)}: duplicate tool name(s) {sorted(dupes)}")
        if tools != sorted(tools):
            fail(f"{path.relative_to(ROOT)}: included_tools is not in sorted order")
        if "included_servers" in doc and doc["included_servers"]:
            fail(f"{path.relative_to(ROOT)}: uses included_servers; every Noesis group must "
                 f"use an explicit included_tools allowlist so new upstream tools cannot "
                 f"silently widen the group")
        for t in tools:
            if t not in inv_by_name:
                fail(f"{path.relative_to(ROOT)}: tool {t!r} does not resolve to a tool "
                     f"observed in tool-inventory.json")
        file_groups[name] = doc

    # ── 3. catalog vs group files ─────────────────────────────────────────
    cat_groups = catalog.get("groups", [])
    cat_by_name = {g["name"]: g for g in cat_groups}
    if len(cat_by_name) != len(cat_groups):
        fail("tool-groups.json contains duplicate group names")
    if set(cat_by_name) != set(file_groups):
        only_cat = sorted(set(cat_by_name) - set(file_groups))
        only_file = sorted(set(file_groups) - set(cat_by_name))
        if only_cat:
            fail(f"catalog lists group(s) with no group file: {only_cat}")
        if only_file:
            fail(f"group file(s) not present in the catalog: {only_file}. A stale group file "
                 f"would be deployable by accident; delete it or re-add it to the catalog.")
    for name, doc in file_groups.items():
        g = cat_by_name.get(name)
        if not g:
            continue
        if g.get("tools") != doc["included_tools"]:
            fail(f"catalog membership does not match {name}.json")
        if g.get("tool_count") != len(doc["included_tools"]):
            fail(f"catalog tool_count for {name} disagrees with the group file")
        if g.get("deployable_file") != f"groups/{name}.json":
            fail(f"catalog deployable_file reference for {name} is wrong")

    # ── 4. coverage ───────────────────────────────────────────────────────
    assigned: set[str] = set()
    for doc in file_groups.values():
        assigned.update(doc["included_tools"])
    unassigned = set()
    for entry in catalog.get("unassigned_review_required", []):
        t = entry.get("tool")
        if not t:
            fail("unassigned_review_required entry has no tool name")
            continue
        if t not in inv_by_name:
            fail(f"unassigned_review_required references unknown tool {t!r}")
        if t in assigned:
            fail(f"tool {t!r} is listed as unassigned but also appears in a group")
        if not entry.get("reason"):
            fail(f"unassigned_review_required entry for {t!r} has no reason")
        unassigned.add(t)

    missing = set(inv_by_name) - assigned - unassigned
    if missing:
        fail(f"{len(missing)} discovered tool(s) are neither in a group nor explicitly "
             f"unassigned/review-required: {sorted(missing)[:10]}")

    # every review-required tool must be visible in the review-required summary
    rr_expected = {n for n, t in inv_by_name.items()
                   if t.get("risk_classification") == "review-required"}
    rr_listed = {e.get("tool") for e in catalog.get("review_required_summary", {}).get("tools", [])}
    if rr_expected - rr_listed:
        fail(f"review-required tool(s) missing from review_required_summary: "
             f"{sorted(rr_expected - rr_listed)}")
    if rr_listed - rr_expected:
        fail(f"review_required_summary lists non-review-required tool(s): "
             f"{sorted(rr_listed - rr_expected)}")

    # ── 5. risk boundaries ────────────────────────────────────────────────
    for name, doc in sorted(file_groups.items()):
        g = cat_by_name.get(name)
        if not g:
            continue
        level = g.get("risk_level")
        if level not in RISK_ORDER:
            fail(f"{name}: catalog risk_level {level!r} is not a recognised level")
            continue
        if level == "low":
            offenders = [t for t in doc["included_tools"]
                         if inv_by_name[t].get("risk_classification") not in (None, "low")]
            if offenders:
                fail(f"{name}: declared low risk but contains non-low-risk tool(s): "
                     f"{offenders}")
        member_max = max(
            (RISK_ORDER.get(inv_by_name[t].get("risk_classification"), 1)
             for t in doc["included_tools"]), default=0)
        if RISK_ORDER[level] < member_max:
            fail(f"{name}: catalog risk_level {level!r} is lower than the highest member "
                 f"risk ({[t for t in doc['included_tools'] if RISK_ORDER.get(inv_by_name[t].get('risk_classification'), 1) == member_max][:3]})")
        if not g.get("required_controls"):
            fail(f"{name}: no required_controls recorded in the catalog")
        if "suggested_consumers" not in g:
            fail(f"{name}: catalog has no suggested_consumers key")

    # reviewer-only profiles must not be offered any group that can act
    REVIEWER_ONLY = {"noesis-sentinel", "noesis-skeptic"}
    # Capability categories that mean the tool can write, delete, publish,
    # spend or delegate. A reviewer-only profile must never hold a group
    # containing one of these: reviewing requires reading, not acting.
    ACTING_CATEGORIES = {
        "mutating", "unannotated-mutation", "destructive", "external-communication",
        "persistent-or-autonomous", "configuration-change", "access-control-change",
        "external-publication", "broad-capability",
    }
    for name, g in sorted(cat_by_name.items()):
        consumers = set(g.get("suggested_consumers") or [])
        if not consumers & REVIEWER_ONLY:
            continue
        if g.get("risk_level") in ("high", "review-required"):
            fail(f"{name}: suggested for reviewer-only profile(s) "
                 f"{sorted(consumers & REVIEWER_ONLY)} but has risk_level "
                 f"{g.get('risk_level')!r}; reviewer-only profiles must receive read-only "
                 f"groups only")
        # Risk level alone is too coarse: a group can be 'medium' overall and
        # still contain a mutating member. Check the members themselves.
        acting = [t for t in (g.get("tools") or [])
                  if inv_by_name.get(t, {}).get("inferred_capability_category")
                  in ACTING_CATEGORIES]
        if acting:
            fail(f"{name}: suggested for reviewer-only profile(s) "
                 f"{sorted(consumers & REVIEWER_ONLY)} but contains tool(s) that can act: "
                 f"{acting}. A reviewer-only profile must hold groups whose members only "
                 f"read.")

    # ── 5a. non_low_risk_members must list EVERY non-low member ──────────
    # Naming only the high ones hides the medium members from a reviewer
    # auditing which members of a group carry any elevated risk.
    for name, g in sorted(cat_by_name.items()):
        members = g.get("tools") or []
        expected = [t for t in members
                    if inv_by_name.get(t, {}).get("risk_classification") != "low"]
        listed = []
        for entry in (g.get("non_low_risk_members") or []):
            listed.append(entry.split(":", 1)[0].strip())
        if sorted(listed) != sorted(expected):
            fail(f"{name}: non_low_risk_members does not match the members whose risk is "
                 f"not low (expected {len(expected)}, listed {len(listed)})")
        if g.get("non_low_risk_member_count") != len(expected):
            fail(f"{name}: non_low_risk_member_count does not match the non-low member count")

    # ── 5b. suggested consumers must be real roster profiles ─────────────
    # The authoritative list is profiles/noesis-roster.yaml. A consumer name that
    # is not a roster profile would be a profile that does not exist.
    roster_profiles = roster_profile_keys()
    if roster_profiles is None:
        warn(f"could not read profiles/noesis-roster.yaml; consumer names not verified")
    else:
        for name, g in sorted(cat_by_name.items()):
            unknown = sorted(set(g.get("suggested_consumers") or []) - roster_profiles)
            if unknown:
                fail(f"{name}: suggested_consumer(s) {unknown} are not profiles in "
                     f"profiles/noesis-roster.yaml")
        all_consumers = {c for g in cat_by_name.values()
                         for c in (g.get("suggested_consumers") or [])}
        print(f"  roster profiles       : {len(roster_profiles)} "
              f"({', '.join(sorted(roster_profiles))})")
        print(f"  consumer profiles used: {len(all_consumers)}")
        unknown_all = sorted(all_consumers - roster_profiles)
        if unknown_all:
            fail(f"catalog references non-roster profile(s) as consumers: {unknown_all}")

    # ── 6. simulate MCPJungle 0.4.6 create-time validation ───────────────
    # Mirrors internal/service/toolgroup/toolgroup.go CreateToolGroup:
    #   - name must match ValidGroupName
    #   - the resolved tool set must be non-empty
    #   - every listed tool must exist and be enabled
    # Mirrors pkg/types/tool_group.go for the bindable field set.
    bindable = {"name", "included_tools", "included_servers", "excluded_tools", "description"}
    registered_servers = {t["source_server"] for t in inv_tools}
    for name, doc in sorted(file_groups.items()):
        if set(doc) - bindable:
            fail(f"{name}: contains a field MCPJungle cannot bind "
                 f"({sorted(set(doc) - bindable)})")
        if not VALID_GROUP_NAME.match(doc.get("name", "")):
            fail(f"{name}: name fails MCPJungle's ValidGroupName")
        resolved = set(doc.get("included_tools", []))
        for s in doc.get("included_servers", []):
            if s not in registered_servers:
                fail(f"{name}: included_servers names an unregistered server {s!r}")
        resolved -= set(doc.get("excluded_tools", []))
        if not resolved:
            fail(f"{name}: resolves to an empty tool set; MCPJungle rejects such a group")
        for t in sorted(resolved):
            if t not in inv_by_name:
                fail(f"{name}: MCPJungle would reject this group because tool {t!r} does not "
                     f"exist or is disabled")

    # ── 7. secret scan ────────────────────────────────────────────────────
    for path in [INVENTORY, CATALOG, *group_files, BACKUP]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SECRET_PATTERNS.items():
            for m in pattern.finditer(text):
                snippet = m.group(0)
                fail(f"{path.relative_to(ROOT)}: possible {label} committed "
                     f"(offset {m.start()}, length {len(snippet)})")

    # ── 7b. backup integrity ──────────────────────────────────────────────
    # The backup must be faithful to the live registry and must not carry
    # recoverable upstream credentials.
    if BACKUP.exists():
        backup = load_json(BACKUP)
        if backup.get("artifact_type") != "mcpjungle-gateway-state-backup":
            fail(f"{BACKUP.relative_to(ROOT)}: unexpected artifact_type")
        for key in ("captured_at", "target", "main_gateway_servers",
                    "server_configs_redacted", "tool_groups", "restore_procedure"):
            if key not in backup:
                fail(f"{BACKUP.relative_to(ROOT)}: missing required key {key!r}")
        bgroups = {g.get("name"): g for g in backup.get("tool_groups", {}).get("groups", [])}
        if set(bgroups) != set(file_groups):
            fail(f"{BACKUP.relative_to(ROOT)}: backed-up group set does not match the "
                 f"deployable group files")
        for name, doc in file_groups.items():
            bg = bgroups.get(name) or {}
            if set(bg.get("included_tools") or []) != set(doc["included_tools"]):
                fail(f"{BACKUP.relative_to(ROOT)}: group {name} membership differs from "
                     f"the deployable file")
        # the redacted view must contain no bare secret-shaped value
        redacted = json.dumps(backup.get("server_configs_redacted", {}))
        for label, pattern in SECRET_PATTERNS.items():
            for m in pattern.finditer(redacted):
                fail(f"{BACKUP.relative_to(ROOT)}: server_configs_redacted contains a "
                     f"possible {label}")
        if args.verbose:
            print(f"  backup             : {BACKUP.relative_to(ROOT)} "
                  f"({len(bgroups)} groups, "
                  f"{len(backup.get('main_gateway_servers', {}).get('servers', []))} servers)")

    # ── 7. deterministic ordering ─────────────────────────────────────────
    if inv_tools != sorted(inv_tools, key=lambda t: t["name"]):
        fail("tool-inventory.json tools are not sorted by name")
    if cat_groups != sorted(cat_groups, key=lambda g: g["name"]):
        fail("tool-groups.json groups are not sorted by name")

    # ── report ────────────────────────────────────────────────────────────
    print("validate_mcpjungle_groups.py")
    print(f"  inventory          : {len(inv_tools)} tools")
    print(f"  source servers     : {len(set(t['source_server'] for t in inv_tools))}")
    print(f"  group files        : {len(file_groups)}")
    print(f"  catalog groups     : {len(cat_groups)}")
    print(f"  tools in groups    : {len(assigned)}")
    print(f"  tools unassigned   : {len(unassigned)}")
    if args.verbose:
        counts = Counter(g.get("risk_level") for g in cat_groups)
        print(f"  groups by risk     : {dict(sorted(counts.items(), key=lambda kv: RISK_ORDER.get(kv[0], 9)))}")
    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
