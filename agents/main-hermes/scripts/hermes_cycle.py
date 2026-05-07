#!/usr/bin/env python3
"""Main Hermes planning and dispatch loop.

Usage:
    python hermes_cycle.py [--once] [--workspace PATH]

Loop:
  1. Read signal inbox.
  2. Evaluate each signal (authority matrix).
  3. Resolve route (routing table).
  4. Apply approval gates.
  5. Dispatch via broker client (typed BrokerJob).
  6. Monitor active jobs.
  7. Log all decisions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add lib/, tools/, and project root to path
_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR / "lib"))
sys.path.insert(0, str(_SCRIPT_DIR.parent))  # agents/main-hermes/ contains tools/

from approval import ApprovalEngine, AuthorityLevel
from broker_client import BrokerClient, BrokerJob
from routing import load_routing_table, RoutingTable
from state import StateManager
from workflows import load_workflow, WorkflowBinding, WorkflowDef
from tools.palace_query import enrich_signal_with_palace


DEFAULT_WORKSPACE = "workspace/hermes"
DEFAULT_CYCLE_INTERVAL_S = 30


class HermesCycle:
    """Orchestrates the main-hermes supervisor loop."""

    def __init__(
        self,
        workspace: str,
        broker_url: Optional[str] = None,
        routing_path: Optional[str] = None,
    ) -> None:
        self.workspace = workspace
        self.state = StateManager(workspace)
        self.routing = load_routing_table(routing_path)
        self.approval = ApprovalEngine()
        self.broker = BrokerClient(base_url=broker_url)
        self.workflows: Dict[str, WorkflowDef] = {}
        self._load_workflows()

    def _load_workflows(self) -> None:
        root = os.environ.get("NOESIS_STACK_ROOT", ".")
        wf_dir = Path(root) / "platform" / "workflows"
        for wf_file in wf_dir.glob("*.yaml"):
            try:
                wf = load_workflow(str(wf_file))
                self.workflows[wf.workflow_id] = wf
            except Exception as e:
                print(f"Warning: failed to load workflow {wf_file}: {e}")

    def run_once(self) -> None:
        """Execute a single cycle."""
        sprint = self.state.load_sprint()
        signals = self.state.read_signals(processed=False, limit=50)

        if not signals:
            print("No new signals.")
            return

        for sig in signals:
            print(f"Processing signal {sig.signal_id} from {sig.source} ({sig.event_type})")
            self._process_signal(sig)
            self.state.mark_signal_processed(sig.signal_id)

        # Monitor active jobs
        self._monitor_jobs(sprint)
        self.state.save_sprint(sprint)

    def _process_signal(self, sig: Any) -> None:
        objective = sig.payload.get("objective", sig.event_type)
        payload = sig.payload

        # MemPalace pre-flight query before routing/approval decisions
        enriched_payload = enrich_signal_with_palace(payload)
        if "_palace_context" in enriched_payload:
            print(f"  Palace context: {enriched_payload['_palace_context']['findings_count']} findings for '{enriched_payload['_palace_context']['query']}'")

        # Route resolution
        route = self.routing.resolve(objective, enriched_payload)
        print(f"  Route: {route.target_agent} mode={route.mode} approval={route.approval_required}")

        # Authority evaluation
        action = f"{sig.source}.{sig.event_type}"
        operator_override = enriched_payload.get("operator_override", False)
        est_cost = enriched_payload.get("estimated_cost_usd", 0.0)
        est_tokens = enriched_payload.get("estimated_tokens", 0)

        # Hard cap from routing table
        if est_cost > route.cost_limit_usd:
            print(f"  COST_CAP: estimated {est_cost} exceeds route limit {route.cost_limit_usd}")
            decision = self.approval.log_decision(
                action, AuthorityLevel.ESCALATE,
                f"Cost {est_cost} exceeds route limit {route.cost_limit_usd}",
                job_id=sig.signal_id, category="cost_cap",
            )
            self.state.log_decision(decision)
            return

        level, reason = self.approval.evaluate(
            action,
            payload=enriched_payload,
            estimated_cost_usd=est_cost,
            estimated_tokens=est_tokens,
            operator_override=operator_override,
        )

        # Routing table can force escalation even if matrix says autonomous
        if route.approval_required and level != AuthorityLevel.FORBIDDEN:
            level = AuthorityLevel.ESCALATE
            reason = f"Route requires approval: {reason}"

        print(f"  Authority: {level.value} ({reason})")

        # Halt other jobs if critical override
        if route.halt_other_jobs and level != AuthorityLevel.FORBIDDEN:
            sprint = self.state.load_sprint()
            if sprint.active_jobs:
                print(f"  HALT: pausing {len(sprint.active_jobs)} active jobs for critical route")
                # In production, emit halt signals to broker
                sprint.operator_notes = (sprint.operator_notes or "") + f"\n[HALT] {sig.signal_id}: halted {len(sprint.active_jobs)} jobs"
                self.state.save_sprint(sprint)

        # Log decision
        category = "override" if operator_override else "dispatch"
        decision = self.approval.log_decision(
            action, level, reason,
            job_id=sig.signal_id,
            category=category,
            operator_involved=operator_override,
        )
        self.state.log_decision(decision)

        if level == AuthorityLevel.FORBIDDEN:
            print(f"  BLOCKED: {reason}")
            return

        if level == AuthorityLevel.ESCALATE:
            print(f"  ESCALATED: awaiting approval for {action}")
            # In a full implementation, this would emit an escalation event
            # and wait for operator input before proceeding.
            return

        # Sprint lock check (POLICY safety invariant #5)
        sprint = self.state.load_sprint()
        if sprint.sprint_lock_on_subconscious:
            if route.target_agent == "research-openclaw" and not operator_override:
                # Critical/high signals may still pass
                severity = enriched_payload.get("severity", "low")
                if severity not in ("critical", "high"):
                    print(f"  SUPPRESSED: research-openclaw blocked by sprint lock")
                    decision = self.approval.log_decision(
                        action, AuthorityLevel.ESCALATE, "Sprint lock suppresses non-critical research job",
                        job_id=sig.signal_id, category="sprint_lock",
                    )
                    self.state.log_decision(decision)
                    return
            if route.target_agent == "subconscious-openclaw" and route.mode != "drift-from-research":
                print(f"  MODE_LOCKED: subconscious-openclaw forced to drift-from-research by sprint lock")
                route.mode = "drift-from-research"

        # Autonomous dispatch
        job = BrokerJob(
            job_id=sig.signal_id,
            correlation_id=sig.signal_id,
            traceparent=enriched_payload.get("traceparent", ""),
            target_agent=route.target_agent,
            mode=route.mode,
            objective=objective,
            context=enriched_payload.get("context", {}),
            allowed_capabilities=enriched_payload.get("allowed_capabilities", []),
            denied_capabilities=enriched_payload.get("denied_capabilities", []),
            workspace=enriched_payload.get("workspace", {}),
            constraints=enriched_payload.get("constraints", {}),
            callback=enriched_payload.get("callback", {}),
            priority=enriched_payload.get("priority", "normal"),
            idempotency_key=enriched_payload.get("idempotency_key", f"{route.target_agent}:{route.mode}:{objective}"),
            hermes_notes=enriched_payload.get("hermes_notes", ""),
        )

        resp = self.broker.submit_job(job)
        print(f"  Broker response: {resp.status_code}")
        if resp.error:
            print(f"  Broker error: {resp.error}")

        # Update sprint active jobs
        sprint = self.state.load_sprint()
        if sig.signal_id not in sprint.active_jobs:
            sprint.active_jobs.append(sig.signal_id)
        self.state.save_sprint(sprint)

        # Log cost estimate
        est_cost = payload.get("estimated_cost_usd", 0.0)
        if est_cost > 0:
            self.state.log_cost(
                job_id=sig.signal_id,
                agent=route.target_agent,
                mode=route.mode,
                cost_usd=est_cost,
                note="estimated at dispatch",
            )

    def _monitor_jobs(self, sprint: Any) -> None:
        still_active: List[str] = []
        for job_id in sprint.active_jobs:
            resp = self.broker.get_job(job_id)
            if resp.status_code == 200:
                status = resp.body.get("status", "unknown")
                print(f"  Job {job_id} status: {status}")
                if status in ("completed", "archived"):
                    sprint.completed_jobs.append(job_id)
                elif status in ("failed", "rejected"):
                    sprint.failed_jobs.append(job_id)
                else:
                    still_active.append(job_id)
            else:
                print(f"  Job {job_id} broker query failed: {resp.error}")
                still_active.append(job_id)
        sprint.active_jobs = still_active

    def run(self, interval: int = DEFAULT_CYCLE_INTERVAL_S) -> None:
        """Run the loop continuously."""
        print(f"Hermes cycle started. Workspace: {self.workspace}")
        try:
            while True:
                self.run_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Shutting down.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes supervisor planning/dispatch loop")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE, help="Hermes workspace path")
    parser.add_argument("--broker-url", default=None, help="Broker base URL")
    parser.add_argument("--interval", type=int, default=DEFAULT_CYCLE_INTERVAL_S, help="Cycle interval seconds")
    args = parser.parse_args()

    cycle = HermesCycle(
        workspace=args.workspace,
        broker_url=args.broker_url,
    )
    if args.once:
        cycle.run_once()
    else:
        cycle.run(interval=args.interval)


if __name__ == "__main__":
    main()
