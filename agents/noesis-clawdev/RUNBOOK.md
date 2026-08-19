# Noesis ClawDev — Operational Runbook

**Runtime:** OpenClaw · **Agent:** noesis-clawdev · **Parent:** noesis-praxis
**Version:** 1.0.0 · **Updated:** 2026-08-19

---

## 1. Startup / deployment

Deployment is owned by `noesis-ansible` (playbook: `noesis-openclaw.yml` /
role: `noesis_openclaw`). Local run:

```bash
# Start the OpenClaw instance (config injected from Bitwarden at deploy)
ansible-playbook -i inventory/local/hosts.ini playbooks/noesis-openclaw.yml --tags clawdev
```

## 2. Health check

```bash
# Service status
systemctl --user status openclaw-clawdev    # or container status
docker ps --filter name=clawdev

# Telemetry heartbeat (expected fields)
curl -s http://127.0.0.1:<port>/v1/health | jq .
```

Healthy = agent up, route assignment present for active job, telemetry
flowing to the observability endpoint, no policy denials in current window.

## 3. Receiving a delegated job

1. Noesis Praxis issues signed grant + immutable assignment.
2. ClawDev verifies: signature, expiry, nonce, action/target scope, tool
   permissions, budget, idempotency key.
3. ClawDev acknowledges receipt with structured metadata (task_id, grant_id).

If verification fails → return `failure_classification: policy_block` and do
NOT execute.

## 4. Execution

- Operate inside the isolated ephemeral workspace.
- Stay within tool allowlist, budget, timeout.
- Emit telemetry for every tool call/denial.
- On external side-effect boundary without grant → stop, classify, return.

## 5. Completion

Return structured result (see AGENT.md contract):

```json
{
  "task_id": "...",
  "status": "success|failed|blocked|rolled_back",
  "artifacts": [],
  "test_results": {},
  "telemetry": {},
  "failure_classification": "none|timeout|credential|tool_error|policy_block|validation|other",
  "notes": ""
}
```

## 6. Failure classification

| Class | Meaning | Supervisor action |
|-------|---------|-------------------|
| `timeout` | Exceeded assigned timeout | Retry with revised budget or investigate |
| `credential` | Missing/invalid scoped credential | Re-issue grant or check Bitwarden secret |
| `tool_error` | Tool failure within allowlist | Retry idempotent op; else escalate |
| `policy_block` | Grant/scope/guardrail violation | Do NOT retry; review policy |
| `validation` | Output failed schema/quality checks | Re-run with corrected inputs |
| `other` | Unclassified | Manual triage by Noesis Praxis |

## 7. Ephemeral sub-agents (ClawDev-spawned)

- One bounded task + success criteria each.
- task_id, trace_id, parent_agent_id=noesis-clawdev, expiry.
- Explicit route, risk tier, tool allowlist, cost limit, timeout.
- Isolated runtime, temp workdir, automatic teardown.
- No long-lived credentials; no Bitwarden; no provider secrets.
- Structured output + artifact refs returned to ClawDev → Praxis.

## 8. Teardown / cleanup

- Destroy ephemeral worker state after completion.
- Rotate task-scoped credentials.
- Confirm no containers/processes/volumes remain from the job.

## 9. Escalation

Escalate to Noesis Praxis on: repeated failures, policy blocks, budget
breach, suspected secret exposure, or any R2/R3 boundary encountered without
a grant. Never silently continue past a boundary.
