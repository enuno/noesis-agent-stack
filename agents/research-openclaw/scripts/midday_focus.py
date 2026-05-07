#!/usr/bin/env python3
"""Generate a midday focus brief on high-signal topics.

Re-queries high-signal findings and produces a focused brief for
Hermes review.

Usage:
    python midday_focus.py --vault-dir workspace/research-vault \
                           --output-dir workspace/research-vault/output/operator-briefs
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

from lib.ledger import Ledger


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate midday focus brief")
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
        "--topics",
        type=str,
        nargs="+",
        default=[],
        help="Topics to focus on (default: auto-detect high-signal)",
    )
    return parser.parse_args(argv)


def detect_high_signal_topics(vault_dir: Path) -> list[str]:
    """Auto-detect high-signal topics from recent findings."""
    findings_ledger = Ledger(vault_dir / "knowledge" / "findings.jsonl")
    findings = findings_ledger.read_all()

    # Get findings from last 48h with signal_value >= medium
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=48)

    topic_signals: dict[str, int] = {}
    for f in findings:
        created = f.get("created_at")
        if not created:
            continue
        try:
            dt = datetime.datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt < cutoff:
                continue
        except ValueError:
            continue

        if f.get("signal_value") in ("high", "medium"):
            topic = f.get("topic", "general")
            topic_signals[topic] = topic_signals.get(topic, 0) + 1

    # Sort by signal count, take top 3
    sorted_topics = sorted(topic_signals.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_topics[:3]]


def generate_focus_brief(topics: list[str], vault_dir: Path) -> str:
    """Generate a focused markdown brief for the given topics."""
    findings_ledger = Ledger(vault_dir / "knowledge" / "findings.jsonl")
    all_findings = findings_ledger.read_all()

    lines = [
        f"# Midday Focus Brief — {datetime.date.today().isoformat()}",
        "",
        f"**Topics:** {', '.join(topics)}",
        "",
    ]

    for topic in topics:
        topic_findings = [f for f in all_findings if f.get("topic") == topic]
        topic_findings.sort(
            key=lambda f: {"high": 3, "medium": 2, "low": 1, "noise": 0}.get(
                f.get("signal_value", "noise"), 0
            ),
            reverse=True,
        )
        lines.append(f"## {topic}")
        lines.append("")
        if not topic_findings:
            lines.append("No findings for this topic.")
        else:
            for f in topic_findings[:5]:
                signal_emoji = {"high": "⚠️", "medium": "📊", "low": "🔍", "noise": "💬"}.get(
                    f.get("signal_value", "noise"), "💬"
                )
                lines.append(f"{signal_emoji} **{f.get('title', 'Untitled')}** ({f.get('confidence')})")
                lines.append(f"   {f.get('summary', 'No summary')[:300]}")
                lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    vault_dir = args.vault_dir.resolve()
    output_dir = args.output_dir.resolve()

    topics = args.topics if args.topics else detect_high_signal_topics(vault_dir)
    if not topics:
        print("No high-signal topics detected.")
        topics = ["general"]

    brief = generate_focus_brief(topics, vault_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    time_str = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M")
    output_path = output_dir / f"focus-{datetime.date.today().isoformat()}-{time_str}.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"Midday focus brief written to {output_path}")
    print(f"  Topics: {', '.join(topics)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
