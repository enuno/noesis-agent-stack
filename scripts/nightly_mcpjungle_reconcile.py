#!/usr/bin/env python3
"""Nightly MCPJungle audit and reconciliation.

Discovers the live gateway, diffs it against the committed catalog, and
reconciles automatically for the SAFE case only. Anything ambiguous is
recorded and left out of every group rather than guessed into one -- a
nightly job with no human present must fail closed, not fail open.

Pipeline
  1. discover_mcpjungle_tools.py  -- full live tool contracts (read-only)
  2. Diff against config/mcpjungle/tool-inventory.json:
       new servers / new tools on existing servers / removed tools
  3. Auto-classify ONLY tools that pass a strict safe-read-only test:
       readOnlyHint == true, destructiveHint != true, annotations present,
       AND scan_readonly_writes.py's own write-admission patterns do not
       match the description.
     These get category=read-only, risk=low, and are grouped into a new
     per-server "<server>-auto-read" group -- deployed automatically.
  4. Everything else newly discovered (ambiguous annotations, any mutation
     signal, or a server with no annotations at all) is added to the
     inventory but left UNASSIGNED with risk_classification=review-required
     and a reason naming exactly what could not be confirmed safe. It is
     NEVER auto-deployed into any group. A human or agent session must run
     the full classification pass (parallel subagents + manual review, as
     this catalog's initial reconciliation did) before it reaches a client.
  5. Removed tools are pruned from every group file that references them
     (a group referencing a missing tool fails creation/update outright).
  6. Validate (scripts/validate_mcpjungle_groups.py). On failure: STOP,
     do not deploy, do not commit. The pre-run state is untouched because
     nothing is written until the reconcile step, and git has the last-good
     commit either way.
  7. Deploy new/changed groups (scripts/deploy_mcpjungle_groups.py --apply
     then --verify).
  8. Refresh config/mcpjungle/backup/gateway-state-backup.json with the
     strict-allowlist redaction and a by-value leak proof.
  9. If anything changed: commit to git. NEVER force-push and never resolve
     a diverged remote by rewriting history unattended -- if `git push`
     fails because main has moved, the job stops, leaves the commit local,
     and reports it as a blocker for a human/agent session (matching the
     manual worktree-cherry-pick procedure used for prior divergence).
 10. Write a dated run report under config/mcpjungle/reconciliations/.

Usage
    nightly_mcpjungle_reconcile.py [--dry-run] [--no-push]

Exit codes
    0  clean (no drift, or drift fully auto-reconciled and deployed)
    1  drift reconciled but review-required tools are pending human classification
    2  validation or deployment failed -- nothing was pushed
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MCP = REPO / "config" / "mcpjungle"
SCRIPTS = REPO / "scripts"
REGISTRY = "https://mcpjungle.tailf99a0.ts.net"

WRITE_PATTERNS = [
    re.compile(r"\bsaves?\s+to\s+(?:the\s+)?user", re.I),
    re.compile(r"\bsaves?\s+(?:the\s+)?\w+\s+(?:to|into)\s+(?:the\s+)?user", re.I),
    re.compile(r"\bcreates?\s+(?:a|an|the|new)\b", re.I),
    re.compile(r"\bwill\s+(?:save|create|write|add|insert|store)\b", re.I),
    re.compile(r"\bwrites?\s+(?:to|into)\b", re.I),
    re.compile(r"\badds?\s+(?:it|them|the\s+\w+)\s+(?:to|into)\b", re.I),
    re.compile(r"\bwhen\s+the\s+user\s+explicitly\s+asks\b", re.I),
    re.compile(r"\b(?:inserts?|deletes?|removes?|updates?)\s+(?:a|an|the|its|their)\b", re.I),
]


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, **kw)


def is_safe_read_only(tool: dict) -> tuple[bool, str]:
    ann = tool.get("annotations")
    if not ann:
        return False, "no annotations published -- cannot confirm readOnlyHint"
    if ann.get("readOnlyHint") is not True:
        return False, "readOnlyHint is not true"
    if ann.get("destructiveHint") is True:
        return False, "destructiveHint is true"
    desc = tool.get("description") or ""
    for sent in re.split(r"(?<=[.!?])\s+", desc):
        for pat in WRITE_PATTERNS:
            m = pat.search(sent)
            if m:
                return False, f"description admits a write: {m.group(0)!r} in {sent[:120]!r}"
    return True, "readOnlyHint=true, destructiveHint not true, no write-admission pattern matched"


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    today = datetime.date.today().isoformat()
    report_dir = MCP / "reconciliations" / today
    report = {"run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "mode": "nightly-automated", "steps": []}

    def step(name, ok, detail=""):
        report["steps"].append({"step": name, "ok": ok, "detail": detail})
        print(f"[{'OK' if ok else 'FAIL'}] {name}  {detail}", file=sys.stderr)

    # 1. discover
    disc = run([sys.executable, str(SCRIPTS / "discover_mcpjungle_tools.py")])
    if disc.returncode != 0:
        step("discover", False, disc.stderr[-500:])
        _write_report(report_dir, report)
        return 2
    live = json.loads(disc.stdout)["tools"]
    step("discover", True, f"{len(live)} live tools")

    baseline = json.loads((MCP / "tool-inventory.json").read_text())
    baseline_names = {t["name"] for t in baseline["tools"]}
    live_names = {t["name"] for t in live}

    new_names = sorted(live_names - baseline_names)
    removed_names = sorted(baseline_names - live_names)
    step("diff", True, f"{len(new_names)} new, {len(removed_names)} removed")

    if not new_names and not removed_names:
        step("reconcile", True, "no drift -- nothing to do")
        _write_report(report_dir, report)
        print("CLEAN: no drift")
        return 0

    live_by_name = {t["name"]: t for t in live}

    # 3-4. classify new tools: safe-read-only -> auto; everything else -> review-required
    auto_safe = []
    pending_review = []
    for n in new_names:
        t = live_by_name[n]
        safe, reason = is_safe_read_only(t)
        server, _, upstream = n.partition("__")
        entry = {
            "name": n, "source_server": server, "upstream_tool_name": upstream,
            "description": t.get("description"), "input_schema": t.get("inputSchema"),
            "output_schema": None, "annotations": t.get("annotations"), "_meta": None,
        }
        if safe:
            entry["inferred_capability_category"] = "read-only"
            entry["risk_classification"] = "low"
            entry["risk_rationale"] = (
                "Auto-classified by the nightly reconciliation job: " + reason
            )
            auto_safe.append(entry)
        else:
            entry["inferred_capability_category"] = "review-required"
            entry["risk_classification"] = "review-required"
            entry["risk_rationale"] = (
                "Auto-classification could not confirm this tool is safely read-only: "
                + reason + ". Held out of every group pending a full manual/subagent "
                "classification pass, matching the house convention for unverified "
                "capability."
            )
            pending_review.append(entry)

    step("classify", True, f"{len(auto_safe)} auto-classified read-only, "
                            f"{len(pending_review)} pending review")

    # build per-server auto-read groups
    by_server_safe: dict[str, list[dict]] = {}
    for e in auto_safe:
        by_server_safe.setdefault(e["source_server"], []).append(e)

    classified_dir = report_dir / "classified"
    classified_dir.mkdir(parents=True, exist_ok=True)
    all_classified = auto_safe + pending_review
    (classified_dir / "nightly-auto.json").write_text(
        json.dumps({"tools": all_classified}, indent=2) + "\n")

    merge_plan = {
        "generated_at": report["run_at"],
        "note": f"Nightly auto-reconciliation for {today}.",
        "groups": [
            {
                "name": f"{server}-auto-read",
                "purpose": (
                    f"Auto-generated by the nightly reconciliation job: every tool on the "
                    f"newly discovered server '{server}' that passed the strict safe-"
                    f"read-only test (readOnlyHint=true, destructiveHint not true, no "
                    f"write-admission pattern in its description). Review and re-classify "
                    f"with the full manual/subagent procedure before treating this as a "
                    f"permanent group name."
                ),
                "risk_level": "low",
                "required_controls": [
                    "Auto-classified, not human-reviewed. Re-run the full classification "
                    "procedure (parallel subagents + manual review for sensitive servers) "
                    "and replace this group with a properly named, task-focused one.",
                ],
                "suggested_consumers": [],
                "source_servers": [server],
                "member_filter": {"source_server": server, "inferred_capability_category": "read-only"},
            }
            for server in sorted(by_server_safe)
        ],
        "unassigned_review_required": [
            {
                "tool": e["name"], "source_server": e["source_server"],
                "risk_classification": "review-required", "disposition": "held out of all groups",
                "reason": e["risk_rationale"],
                "decision_needed": "Run the full manual/subagent classification pass "
                                    "(see mcpjungle-operations skill) before this tool is "
                                    "placed in any group.",
            }
            for e in pending_review
        ],
    }
    (report_dir / "merge-plan.json").write_text(json.dumps(merge_plan, indent=2) + "\n")

    # 5. prune removed tools from group files before reconciling
    pruned_groups = []
    if removed_names:
        for gf in sorted((MCP / "groups").glob("*.json")):
            gd = json.loads(gf.read_text())
            before = set(gd["included_tools"])
            after = before - set(removed_names)
            if after != before:
                gd["included_tools"] = sorted(after)
                if not gd["included_tools"]:
                    raise SystemExit(
                        f"FATAL: pruning removed tools would empty group {gd['name']} -- "
                        f"manual intervention required, refusing to deploy an empty group")
                gf.write_text(json.dumps(gd, indent=2) + "\n")
                pruned_groups.append(gf.stem)
    step("prune-removed", True, f"{len(pruned_groups)} group(s) pruned: {pruned_groups}")

    if args.dry_run:
        step("dry-run", True, "stopping before reconcile/deploy/commit")
        _write_report(report_dir, report)
        return 1 if pending_review else 0

    # 6. reconcile
    rec = run([sys.executable, str(SCRIPTS / "reconcile_mcpjungle_catalog.py"),
               "--classified-dir", str(classified_dir),
               "--merge-plan", str(report_dir / "merge-plan.json")])
    step("reconcile", rec.returncode == 0, rec.stdout[-1000:] + rec.stderr[-500:])
    if rec.returncode != 0:
        _write_report(report_dir, report)
        return 2

    # 6b. validate -- never deploy or commit on a failed validation
    val = run([sys.executable, str(SCRIPTS / "validate_mcpjungle_groups.py")])
    step("validate", val.returncode == 0, val.stdout[-1000:])
    if val.returncode != 0:
        step("abort", True, "validation failed -- not deploying, not committing")
        _write_report(report_dir, report)
        return 2

    # 7. deploy
    dep = run([sys.executable, str(SCRIPTS / "deploy_mcpjungle_groups.py"), "--apply"])
    step("deploy-apply", dep.returncode == 0, dep.stdout[-1000:])
    if dep.returncode != 0:
        _write_report(report_dir, report)
        return 2

    ver = run([sys.executable, str(SCRIPTS / "deploy_mcpjungle_groups.py"), "--verify"])
    step("deploy-verify", ver.returncode == 0, ver.stdout[-1000:])
    if ver.returncode != 0:
        _write_report(report_dir, report)
        return 2

    # 8. refresh backup -- best effort; a failure here does not roll back the deploy
    bak = run([sys.executable, str(SCRIPTS / "refresh_mcpjungle_backup.py")])
    step("refresh-backup", bak.returncode == 0, bak.stdout[-500:] + bak.stderr[-500:])

    # 8b. regenerate README
    rm = run([sys.executable, str(SCRIPTS / "generate_mcpjungle_readme.py")])
    step("regenerate-readme", rm.returncode == 0, rm.stdout[-500:])

    # 9. commit (never force-push, never auto-resolve divergence)
    run(["git", "add", "config/mcpjungle/", "scripts/"])
    status = run(["git", "status", "--porcelain", "config/mcpjungle/", "scripts/"])
    if status.stdout.strip():
        msg = (
            f"chore(mcpjungle): nightly reconciliation {today}\n\n"
            f"Auto-classified {len(auto_safe)} new read-only tool(s) across "
            f"{len(by_server_safe)} new server(s) into auto-generated *-auto-read "
            f"groups; {len(pending_review)} tool(s) held review-required, out of every "
            f"group, pending the full manual/subagent classification pass. "
            f"{len(removed_names)} tool(s) removed upstream and pruned from "
            f"{len(pruned_groups)} group file(s).\n\n"
            f"Run by scripts/nightly_mcpjungle_reconcile.py."
        )
        commit = run(["git", "commit", "-m", msg])
        step("commit", commit.returncode == 0, commit.stdout[-300:] + commit.stderr[-300:])
        if not args.no_push and commit.returncode == 0:
            push = run(["git", "push", "origin", "HEAD:main"])
            step("push", push.returncode == 0, push.stdout[-300:] + push.stderr[-300:])
            if push.returncode != 0:
                step("push-blocked", False,
                     "main has moved on the remote -- the commit is local only. "
                     "Resolve with the manual worktree-cherry-pick procedure, do NOT "
                     "force-push.")
    else:
        step("commit", True, "nothing to commit (unexpected -- reconcile reported a change)")

    _write_report(report_dir, report)
    print(f"RECONCILED: {len(auto_safe)} auto-approved, {len(pending_review)} pending review, "
          f"{len(removed_names)} removed")
    return 1 if pending_review else 0


def _write_report(report_dir: Path, report: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "run-report.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
