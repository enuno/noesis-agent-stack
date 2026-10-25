#!/usr/bin/env python3
"""validate_mcpjungle_readme.py — check that config/mcpjungle/README.md agrees with the artifacts.

Documentation drifts silently. This validator extracts the factual claims from the
README and compares them against tool-inventory.json, tool-groups.json and the group
files, so a stale number or a renamed group is caught in CI rather than by a reader.

Offline, deterministic, non-mutating. Exits non-zero on any mismatch.

Usage
    python3 scripts/validate_mcpjungle_readme.py [-v]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCPJUNGLE_DIR = ROOT / "config" / "mcpjungle"
README = MCPJUNGLE_DIR / "README.md"

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    if not README.exists():
        print(f"FATAL: README missing: {README}", file=sys.stderr)
        return 2

    readme = README.read_text(encoding="utf-8")
    try:
        inv = json.loads((MCPJUNGLE_DIR / "tool-inventory.json").read_text(encoding="utf-8"))
        cat = json.loads((MCPJUNGLE_DIR / "tool-groups.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FATAL: cannot read artifacts: {exc}", file=sys.stderr)
        return 2

    tools = inv["tools"]
    groups = {g["name"]: g for g in cat["groups"]}

    # ── 1. headline counts ────────────────────────────────────────────────
    checks = [
        (rf"\*\*(\d+)\*\*\s*\|\n", None),  # placeholder, handled below
    ]
    del checks

    m = re.search(r"\*\*Unique tools\*\*\s*\|\s*\*\*(\d+)\*\*", readme)
    if not m:
        fail("README: 'Unique tools' headline not found")
    elif int(m.group(1)) != len(tools):
        fail(f"README: Unique tools says {m.group(1)}, inventory has {len(tools)}")

    m = re.search(r"\*\*Source servers\*\*\s*\|\s*\*\*(\d+)\*\*", readme)
    servers = len(set(t["source_server"] for t in tools))
    if not m:
        fail("README: 'Source servers' headline not found")
    elif int(m.group(1)) != servers:
        fail(f"README: Source servers says {m.group(1)}, inventory has {servers}")

    m = re.search(r"Discovery timestamp\s*\|\s*`?([^`|]+)`?\s*\|", readme)
    if not m:
        fail("README: discovery timestamp not found")
    elif m.group(1).strip() != inv["generated_at"]:
        fail(f"README: discovery timestamp {m.group(1).strip()} != inventory "
             f"{inv['generated_at']}")

    # ── 2. the group table ───────────────────────────────────────────────
    # Rows look like: | `group-name` | 12 | medium | consumers | purpose |
    row_re = re.compile(
        r"^\|\s*`([a-z0-9-]+)`\s*\|\s*(\d+)\s*\|\s*\*{0,2}(low|medium|high|review-required)\*{0,2}\s*\|",
        re.M)
    seen = set()
    for name, count, risk in row_re.findall(readme):
        if name not in groups:
            fail(f"README: group table lists {name!r}, which is not in the catalog")
            continue
        seen.add(name)
        g = groups[name]
        if int(count) != g["tool_count"]:
            fail(f"README: group {name} says {count} tools, catalog says {g['tool_count']}")
        if risk != g["risk_level"]:
            fail(f"README: group {name} says risk {risk}, catalog says {g['risk_level']}")

    missing = set(groups) - seen
    if missing:
        fail(f"README: group table omits {len(missing)} catalog group(s): {sorted(missing)}")

    # ── 2b. group table consumer lists ───────────────────────────────────
    # The README renders consumers as short names ("forge", "sentinel", ...).
    # Verify each row's consumer set against the catalog.
    cons_row_re = re.compile(
        r"^\|\s*`([a-z0-9-]+)`\s*\|\s*(\d+)\s*\|\s*\*{0,2}(low|medium|high|review-required)\*{0,2}"
        r"\s*\|\s*([^|]+?)\s*\|", re.M)
    for name, _count, _risk, cons in cons_row_re.findall(readme):
        g = groups.get(name)
        if not g:
            continue
        cell = cons.strip()
        if "none proposed" in cell:
            claimed = set()
        else:
            claimed = {c.strip().replace("noesis-", "") for c in cell.split(",") if c.strip()}
        actual = {c.replace("noesis-", "") for c in (g.get("suggested_consumers") or [])}
        if claimed != actual:
            fail(f"README: group {name} consumer list mismatch; "
                 f"only_in_readme={sorted(claimed - actual)} "
                 f"only_in_catalog={sorted(actual - claimed)}")

    # ── 3. reviewer-only consumer lists ──────────────────────────────────
    for profile in ("noesis-sentinel", "noesis-skeptic"):
        actual = {g["name"] for g in cat["groups"] if profile in (g.get("suggested_consumers") or [])}
        # The README lists them as `sentinel` / `skeptic`; accept either spelling.
        short = profile.split("-", 1)[1]
        m = re.search(rf"`{profile}`:|`{short}`:", readme)
        if not m:
            fail(f"README: no consumer list found for {profile}")
            continue
        tail = readme[m.end():]
        # take the backticked group names that follow, stopping at a blank line
        block = tail.split("\n\n", 1)[0]
        claimed = set(re.findall(r"`([a-z0-9-]+)`", block))
        if claimed != actual:
            fail(f"README: {profile} list mismatch; "
                 f"only_in_readme={sorted(claimed - actual)} "
                 f"only_in_catalog={sorted(actual - claimed)}")

    # ── 4. review-required and unassigned lists ───────────────────────────
    rr = {e["tool"] for e in cat.get("review_required_summary", {}).get("tools", [])}
    for tool in rr:
        if tool not in readme:
            fail(f"README: review-required tool {tool} is not mentioned")
    unassigned = {e["tool"] for e in cat.get("unassigned_review_required", [])}
    for tool in unassigned:
        if tool not in readme:
            fail(f"README: unassigned tool {tool} is not mentioned")

    # ── 5. coverage-gap categories ───────────────────────────────────────
    # The README renders these as table cells with backticks and parenthetical
    # qualifiers, so compare on a normalised form.
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    readme_norm = norm(readme)
    for entry in cat.get("unsupported_requested_categories", []):
        cat_name = entry["category"]
        if norm(cat_name) not in readme_norm:
            fail(f"README: coverage-gap category {cat_name!r} is not mentioned")

    # ── 6. the YWCA corpus requirement ───────────────────────────────────
    ywca_server = "misjusticeallinace-ywcaofmissoula-pub"
    ywca_tools = [t["name"] for t in tools if t.get("source_server") == ywca_server]
    if not ywca_tools:
        fail(f"README: the MISJustice/YWCA corpus server {ywca_server} is absent from the "
             f"inventory")
    else:
        legal = set(groups.get("legal-research", {}).get("tools", []))
        for t in ywca_tools:
            if t.endswith(("getPage", "searchDocumentation")) and t not in legal:
                fail(f"README: YWCA corpus read tool {t} is not in the legal-research group")
        for t in ywca_tools:
            if t not in readme:
                fail(f"README: YWCA corpus tool {t} is not mentioned")
    if "https://www.ywcaofmissoula.com/~gitbook/mcp" not in readme:
        fail("README: the YWCA GitBook MCP endpoint URL is not stated")

    # ── 7. no invented CLI flags ─────────────────────────────────────────
    # Every `mcpjungle ...` command line in the README must use a subcommand that
    # the installed CLI actually offers.
    known_subcommands = {
        "start", "register", "list", "usage", "invoke", "deregister", "version",
        "get", "disable", "enable", "create", "delete", "init-server", "login",
        "update", "export",
    }
    for cmd in re.findall(r"mcpjungle\s+([a-z][a-z-]*)", readme):
        if cmd in ("groups", "tools", "servers", "clients", "users", "group", "mcp-clients",
                   "prompts", "resources", "conf"):
            continue
        if cmd not in known_subcommands:
            fail(f"README: uses unknown mcpjungle subcommand {cmd!r}")

    # ── 8. no credentials in the README ──────────────────────────────────
    for pattern, label in (
        (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"), "bearer token"),
        (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{16,}"), "github token"),
        (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws access key"),
        (re.compile(r"://[^/\s:@]+:[^/\s:@]+@"), "credential in url"),
    ):
        if pattern.search(readme):
            fail(f"README: contains a possible {label}")

    # ── 9. consumer names must be roster profiles ────────────────────────
    # "noesis-praxis" is a persona/host naming convention, not a deployed
    # profile; STANDING-GOAL-FINAL-DELIVERABLE.md records it as absent from
    # profiles/noesis-roster.yaml. It must not appear as a CONSUMER. It may
    # still be named in prose that explains why it is not used.
    for g in cat["groups"]:
        if "noesis-praxis" in (g.get("suggested_consumers") or []):
            fail(f"catalog group {g['name']!r} uses 'noesis-praxis' as a consumer; it is "
                 f"not a profile in profiles/noesis-roster.yaml")

    print("validate_mcpjungle_readme.py")
    print(f"  README claims checked against {len(groups)} catalog groups "
          f"and {len(tools)} inventory tools")
    if args.verbose:
        print(f"  review-required tools referenced : {len(rr)}")
        print(f"  unassigned tools referenced      : {len(unassigned)}")
        print(f"  coverage-gap categories          : "
              f"{len(cat.get('unsupported_requested_categories', []))}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    print("PASS: README agrees with the artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
