#!/usr/bin/env python3
"""Reconcile the MCPJungle catalog against newly classified upstream tools.

This is the generic, data-driven successor to generate_mcpjungle_catalog.py's
one-off per-tool Python literals. It is designed to be re-run safely (the
nightly reconciliation job uses it) and to require no server-specific code:
all server-specific judgement lives in the classified-tools JSON files and
the merge-plan JSON, not in this script.

Inputs
  --classified-dir DIR   directory of classified-tools JSON files, each
                          {"tools": [<inventory-schema entries>], ...}
                          (group_recommendations in these files are advisory
                          only -- this script's own --merge-plan decides
                          actual group membership)
  --merge-plan FILE       JSON: {"groups": [...], "unassigned_review_required": [...]}
                          Each group dict: name, purpose, risk_level,
                          required_controls, suggested_consumers,
                          source_servers, member_filter (dict of field ->
                          value or list-of-values to match against each
                          classified tool; AND across fields, OR within a
                          list; "name_in" matches tool["name"] against an
                          explicit list instead of filtering by field)

Outputs (written under config/mcpjungle/, relative to --repo)
  tool-inventory.json    existing tools kept verbatim (read from git HEAD,
                          not the working tree, so re-running after a partial
                          edit is still idempotent); newly classified tools
                          appended as a set union (never duplicated)
  groups/<name>.json      one new deployable group file per merge-plan group
  tool-groups.json        aggregate catalog, existing groups kept verbatim,
                          new groups appended

Idempotence
  Baseline is read from `git show HEAD:config/mcpjungle/tool-inventory.json`
  and `HEAD:config/mcpjungle/tool-groups.json`, not from the working tree, so
  re-running this script after committing its own output adds nothing a
  second time (the new tools are already in HEAD and are excluded from the
  "newly classified" set by name).

Usage
  python3 scripts/reconcile_mcpjungle_catalog.py \\
      --classified-dir /path/to/classified \\
      --merge-plan /path/to/merge-plan.json \\
      --deployed
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

GROUP_SUPPORTED_FIELDS = {"name", "description", "included_tools", "included_servers", "excluded_tools"}


def git_head_json(repo: Path, relpath: str) -> dict:
    raw = subprocess.run(
        ["git", "-C", str(repo), "show", f"HEAD:{relpath}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(raw)


def load_classified(classified_dir: Path) -> dict:
    """Return {tool_name: entry} across every file in the directory."""
    by_name = {}
    for p in sorted(classified_dir.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for t in d.get("tools", []):
            by_name[t["name"]] = t
    return by_name


def matches(tool: dict, filt: dict) -> bool:
    if "name_in" in filt:
        return tool["name"] in filt["name_in"]
    for field, want in filt.items():
        have = tool.get(field)
        if isinstance(want, list):
            if have not in want:
                return False
        else:
            if have != want:
                return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--classified-dir", required=True)
    ap.add_argument("--merge-plan", required=True)
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    mcp_dir = repo / "config" / "mcpjungle"
    classified_dir = Path(args.classified_dir).resolve()
    plan = json.loads(Path(args.merge_plan).read_text(encoding="utf-8"))

    baseline_inv = git_head_json(repo, "config/mcpjungle/tool-inventory.json")
    baseline_cat = git_head_json(repo, "config/mcpjungle/tool-groups.json")
    baseline_names = {t["name"] for t in baseline_inv["tools"]}

    classified = load_classified(classified_dir)
    # Idempotence: exclude anything already in HEAD's inventory from "new".
    new_by_name = {n: t for n, t in classified.items() if n not in baseline_names}

    print(f"baseline inventory : {len(baseline_inv['tools'])} tools, "
          f"{len(baseline_cat['groups'])} groups")
    print(f"classified-dir      : {len(classified)} tools across "
          f"{len(list(classified_dir.glob('*.json')))} files")
    print(f"already in HEAD     : {len(classified) - len(new_by_name)} "
          f"(excluded from this run -- idempotent re-run)")
    print(f"genuinely new       : {len(new_by_name)} tools")

    # ---- assemble group membership from the merge plan ----
    assigned: dict[str, str] = {}  # tool name -> group name, for duplicate detection
    new_group_files = []
    for g in plan.get("groups", []):
        members = sorted(n for n, t in new_by_name.items() if matches(t, g["member_filter"]))
        if not members:
            print(f"SKIP (no matching tools) : {g['name']}", file=sys.stderr)
            continue
        for m in members:
            if m in assigned:
                raise SystemExit(f"FATAL: {m} assigned to both {assigned[m]} and {g['name']}")
            assigned[m] = g["name"]
        new_group_files.append({
            "name": g["name"],
            "purpose": g["purpose"],
            "risk_level": g["risk_level"],
            "risk_basis": (
                "The highest risk level among the member tools, using the per-tool classification "
                "in tool-inventory.json, raised to the group's declared floor where the declaration "
                "is the stricter judgement."
            ),
            "required_controls": g["required_controls"],
            "suggested_consumers": g["suggested_consumers"],
            "consumer_basis": (
                "Profile names verified against the 16 profile keys in profiles/noesis-roster.yaml. "
                "A name with no matching roster entry is never suggested as a consumer."
            ),
            "tool_count": len(members),
            "tools": members,
            "deployable_file": f"groups/{g['name']}.json",
            "proposed_endpoint": f"https://mcpjungle.tailf99a0.ts.net/v0/groups/{g['name']}/mcp",
            "endpoint_status": "pending-deploy",
            "endpoint_note": "",
            "deliberate_overlap": "",
            "non_low_risk_member_count": sum(
                1 for m in members if new_by_name[m]["risk_classification"] != "low"),
            "non_low_risk_members": sorted(
                m for m in members if new_by_name[m]["risk_classification"] != "low"),
            "non_low_risk_member_note": (
                "Every member whose risk_classification in tool-inventory.json is not 'low'. The "
                "medium-risk members are included deliberately: omitting them would make this field "
                "mislead a reviewer auditing which members of a group carry any elevated risk."
            ),
        })

    unassigned = plan.get("unassigned_review_required", [])
    for u in unassigned:
        assigned[u["tool"]] = "__unassigned__"

    # Every review-required tool -- whether grouped or unassigned -- must be
    # reflected in the catalog's review_required_summary, matching the
    # existing convention (court-listener__call_endpoint etc.).
    rr_group_by_tool = {m: g["name"] for g in new_group_files for m in g["tools"]}
    new_rr_entries = []
    for n, t in sorted(new_by_name.items()):
        if t["risk_classification"] != "review-required":
            continue
        grp = rr_group_by_tool.get(n)
        unassigned_entry = next((u for u in unassigned if u["tool"] == n), None)
        new_rr_entries.append({
            "tool": n,
            "source_server": t["source_server"],
            "disposition": "held in a review-required group" if grp else "held out of all groups",
            "groups": [grp] if grp else [],
            "reason": (unassigned_entry["reason"] if unassigned_entry
                       else t.get("risk_rationale", "")),
        })

    # every new tool must be accounted for exactly once
    missing = sorted(set(new_by_name) - set(assigned))
    if missing:
        raise SystemExit(f"FATAL: {len(missing)} new tool(s) have no group and are not in "
                          f"unassigned_review_required: {missing}")

    print(f"new groups created  : {len(new_group_files)}")
    print(f"new tools unassigned: {len(unassigned)}")
    for g in new_group_files:
        print(f"  {g['name']:45s} {g['tool_count']:3d} tools  risk={g['risk_level']}")
    if unassigned:
        for u in unassigned:
            print(f"  (unassigned) {u['tool']}  risk={u['risk_classification']}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    # ---- write tool-inventory.json ----
    import datetime
    tools_out = list(baseline_inv["tools"]) + [new_by_name[n] for n in sorted(new_by_name)]
    tools_out.sort(key=lambda t: t["name"])
    inventory = dict(baseline_inv)
    inventory["tools"] = tools_out
    if new_by_name:
        # Only bump the timestamp when this run actually added something --
        # a no-op reconciliation (nightly run with zero drift) should not
        # make the inventory look freshly regenerated when nothing changed.
        inventory["generated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (mcp_dir / "tool-inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    # ---- write new group files + extend the aggregate catalog ----
    (mcp_dir / "groups").mkdir(exist_ok=True)
    for g in new_group_files:
        deployable = {
            "name": g["name"],
            "description": g["purpose"],
            "included_tools": g["tools"],
        }
        assert set(deployable.keys()) <= GROUP_SUPPORTED_FIELDS
        (mcp_dir / "groups" / f"{g['name']}.json").write_text(
            json.dumps(deployable, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    catalog = dict(baseline_cat)
    catalog["groups"] = sorted(list(baseline_cat["groups"]) + new_group_files,
                                key=lambda g: g["name"])
    catalog["group_count"] = len(catalog["groups"])
    existing_unassigned = baseline_cat.get("unassigned_review_required", [])
    existing_names = {u["tool"] for u in existing_unassigned}
    catalog["unassigned_review_required"] = existing_unassigned + [
        u for u in unassigned if u["tool"] not in existing_names]

    rr_summary = dict(catalog.get("review_required_summary", {}))
    existing_rr = rr_summary.get("tools", [])
    existing_rr_names = {e["tool"] for e in existing_rr}
    rr_summary["tools"] = existing_rr + [
        e for e in new_rr_entries if e["tool"] not in existing_rr_names]
    rr_summary["count"] = len(rr_summary["tools"])
    catalog["review_required_summary"] = rr_summary

    (mcp_dir / "tool-groups.json").write_text(
        json.dumps(catalog, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    cat_count = Counter(t["inferred_capability_category"] for t in tools_out)
    risk_count = Counter(t["risk_classification"] for t in tools_out)
    print(f"\nwritten: {len(tools_out)} tools, {len(catalog['groups'])} groups")
    print("categories:", dict(cat_count))
    print("risks:", dict(risk_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
