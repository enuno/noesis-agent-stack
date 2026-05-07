#!/usr/bin/env python3
"""Initialize hermes workspace state files.

Usage:
    python init_state.py [--workspace PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


def init_workspace(workspace: str) -> None:
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)

    sprint_id = str(uuid.uuid4())[:8]
    sprint_state = {
        "sprint_id": sprint_id,
        "status": "active",
        "build_intent_ref": None,
        "build_intent_status": None,
        "sprint_lock_on_subconscious": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "last_updated_at": datetime.now(timezone.utc).isoformat(),
        "operator_notes": None,
        "active_jobs": [],
        "completed_jobs": [],
        "failed_jobs": [],
    }
    (ws / "sprint_state.json").write_text(
        json.dumps(sprint_state, indent=2), encoding="utf-8"
    )

    # Create empty JSONL files
    for name in ("decision_log.jsonl", "cost_ledger.jsonl", "signal_inbox.jsonl"):
        path = ws / name
        if not path.exists():
            path.write_text("", encoding="utf-8")

    print(f"Initialized workspace: {ws}")
    print(f"  sprint_id: {sprint_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize Hermes workspace state")
    parser.add_argument(
        "--workspace",
        default=os.environ.get("HERMES_WORKSPACE", "workspace/hermes"),
        help="Path to workspace directory",
    )
    args = parser.parse_args()
    init_workspace(args.workspace)


if __name__ == "__main__":
    main()
