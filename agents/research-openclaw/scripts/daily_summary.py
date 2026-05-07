#!/usr/bin/env python3
"""Generate a daily operator brief from recent findings.

Aggregates findings from the last 24 hours into a concise markdown brief
for Hermes review.

Usage:
    python daily_summary.py --vault-dir workspace/research-vault \
                            --output-dir workspace/research-vault/output/operator-briefs
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from lib.ledger import Ledger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate daily operator brief")
    parser.add_argument(
        "--vault-dir",
        type=Path,
        default=Path("workspace/research-vault"),
        help="Path to vault directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("workspace/research-vault/output/operator-briefs"),
        help="Path to write briefs",
    )
    parser.add_argument(
        "--since",
        type=str,
        default="",
        help="ISO-8601 timestamp (default: 24h ago)",
    )
    return parser.parse_args(argv)


def aggregate_findings(vault_dir: Path, since: datetime.datetime) -> list[dict]:
    """Load findings created since the given timestamp."""
    findings_ledger = Ledger(vault_dir / "knowledge" / "findings.jsonl")
    all_findings = findings_ledger.read_all()
    recent: list[dict] = []
    for f in all_findings:
        created = f.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt >= since:
                recent.append(f)
        except ValueError:
            continue
    return recent


def generate_brief(findings: list[dict], date: datetime.date) -> str:
    """Generate a markdown brief from findings."""
    lines = [
        f"# Operator Brief — {date.isoformat()}",
        "",
        f"**Findings:** {len(findings)}",
        "",
    ]

    if not findings:
        lines.append("No new findings in the last 24 hours.")
        return "\n".join(lines)

    # Group by signal value
    high = [f for f in findings if f.get("signal_value") == "high"]
    medium = [f for f in findings if f.get("signal_value") == "medium"]
    low = [f for f in findings if f.get("signal_value") == "low"]
    noise = [f for f in findings if f.get("signal_value") == "noise"]

    if high:
        lines.append("## ⚠️ High-Signal Findings")
        lines.append("")
        for f in high:
            lines.append(f"### {f.get('title', 'Untitled')}")
            lines.append(f"- **Confidence:** {f.get('confidence', 'unknown')}")
            lines.append(f"- **Topic:** {f.get('topic', 'general')}")
            lines.append(f"- **Summary:** {f.get('summary', 'No summary')}")
            lines.append("")

    if medium:
        lines.append("## 📊 Medium-Signal Findings")
        lines.append("")
        for f in medium:
            lines.append(f"- **{f.get('title', 'Untitled')}** ({f.get('confidence')}) — {f.get('summary', '')[:200]}")
        lines.append("")

    if low:
        lines.append(f"## Low-Signal ({len(low)} findings)")
        lines.append("")

    if noise:
        lines.append(f"## Noise ({len(noise)} findings)")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    output_dir = args.output_dir.resolve()

    if args.since:
        since = datetime.datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    else:
        since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)

    findings = aggregate_findings(vault_dir, since)
    brief = generate_brief(findings, datetime.date.today())

    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    output_path = output_dir / f"brief-{date_str}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"Daily brief written to {output_path}")
    print(f"  Findings: {len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
