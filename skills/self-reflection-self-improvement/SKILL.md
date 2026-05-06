---
name: self-reflection-self-improvement
version: 4
description: Enables Hermes to run a full self-reflection and self-improvement cycle using its Memory Palace, task history, error logs, and electric-sheep outputs; distill durable lessons; execute approved improvements; document the cycle in the LLM-Wiki; and archive both reflection details and generalized lessons for future behavior.
agents: [hermes, autonomous-agent, long-running-agent, multi-agent-coordinator]
dependencies:
  - mempalace
  - electric-sheep
  - llm-wiki
---

# Skill: Hermes Self-Reflection & Self-Improvement

This skill enables Hermes to conduct a structured introspection cycle on itself. Hermes reviews its operational behavior, evaluates competency and execution efficiency, analyzes recurring failures and frictions, integrates insights from `electric-sheep`, distills reusable lessons, updates its own prompts/skills/configuration where appropriate, and records the full cycle in both the LLM-Wiki and the Memory Palace.

**Important:** This skill REVIEWS outputs from the electric-sheep skill (which runs via hermes-dreaming-cycle cron job). It does NOT trigger electric-sheep itself. The electric-sheep skill runs independently on its own schedule (daily at 00:00). This skill analyzes what electric-sheep has already recorded in MemPalace.

This is a **meta-operational skill**. It is not meant for normal user tasks. It is used when Hermes needs to improve how it works: better task execution, fewer repeated mistakes, better tool use, clearer handoffs, cleaner reasoning, and stronger long-term learning.

The design principle is simple: **not every incident becomes a permanent rule**. Reflection data stays detailed; lessons stay concise; permanent operating changes require evidence.

## When to Use This Skill

- When the operator explicitly asks Hermes to reflect, self-audit, self-improve, introspect, or review its recent performance.
- On a scheduled cadence, such as daily, weekly, or every N completed tasks.
- After a cluster of recurring failures, retries, escalations, or anomalous behaviors is detected.
- After one or more `hermes-dreaming` cycles produce warning, improvement, or pattern signals worth operational review.
- After a major workflow, migration, deployment, or skill change, when Hermes should validate whether the change improved outcomes.
- In partial/report-only mode when the operator wants analysis and planning without automatic execution.

## Prerequisites

- **MemPalace skill** — Must be installed and functional with MCP server access
- **Electric Sheep skill** — Should have run at least once to generate outputs (check for diary entries from the hermes-dreaming-cycle cron job)
- **LLM-Wiki** — Must be accessible for documentation
- Read/write access to the **Memory Palace**, including episodic, semantic, procedural, and archival namespaces
- Access to task history, tool execution logs, error/anomaly logs, retry records, and escalation records
- Access to outputs from the `electric-sheep` skill (run by hermes-dreaming-cycle cron job), including recent cycle sessions and archives
- Ability to read and modify Hermes skill files, instruction blocks, configs, tool wrappers, prompts, monitoring rules, and workflow definitions
- Ability to write or update entries in the **LLM-Wiki**
- Ability to create backups before any self-modification
- Optional but recommended: operator notification channel for approvals and cycle summaries

### Pre-Execution Validation

Before starting a reflection cycle, validate:
1. `mcp_mempalace_status` returns successfully
2. At least one wing exists in the palace
3. `electric-sheep` has run in the last 7 days (check `mcp_mempalace_diary_read` for `agent_name="electric-sheep"`)
4. Write access to `~/.hermes/skills/` is available

## Structural Overview

Hermes self-improvement operates on seven persistent objects. Hermes must keep them distinct.

1. **Task History** — factual record of attempted work, outcomes, timing, retries, and completion quality.
2. **Error & Anomaly Log** — failures, tool errors, hallucination flags, uncertainty events, escalation triggers, and silent degradations.
3. **Electric Sheep Log** — outputs from the `electric-sheep` skill (run by hermes-dreaming-cycle cron job): memory consolidation reports, skill gap analyses, authored skills, and diary entries.
4. **Reflection Archive** — full per-cycle analysis packet with evidence, metrics, plans, and execution details.
5. **Lessons Ledger** — concise, generalized lessons extracted from repeated or meaningful patterns.
6. **Improvement Queue** — approved and sequenced development tasks for self-modification.
7. **LLM-Wiki** — durable narrative documentation for humans and agents.

Use this separation strictly:
- Reflection Archive stores detail.
- Lessons Ledger stores compressed, reusable learning.
- LLM-Wiki stores readable cycle documentation.
- Permanent operating rules belong in skill/config/prompt artifacts, not only in narrative text.

## Concrete Execution Commands

This section provides the actual tool calls for each phase. Use these as templates.

### Phase 0 — Trigger Classification

```python
# Generate cycle ID
import uuid
from datetime import datetime
cycle_id = f"reflect-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"

# Classify trigger and mode
trigger_type = "scheduled"  # or: manual, error-triggered, post-dream, post-change-validation, baseline
execution_mode = "full"  # or: partial, validation

# Record cycle start
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room="cycle-meta",
    content=f"CYCLE_START: {cycle_id}\nTRIGGER: {trigger_type}\nMODE: {execution_mode}\nTIMESTAMP: {datetime.now().isoformat()}"
)
```

### Phase 1 — Operational Data Harvest

```python
# Query task history from session search
session_search(query="task completed OR task failed OR error", limit=20)

# Query recent errors
mcp_mempalace_search(query="error failure retry escalation", limit=10)

# Query electric-sheep outputs
mcp_mempalace_diary_read(agent_name="electric-sheep", last_n=10)

# Query prior reflections for comparison
mcp_mempalace_search(query="reflection cycle competency", wing="hermes-reflection", limit=5)

# Store raw data
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="RAW_DATA: <consolidated evidence from above queries>"
)
```

### Phase 2 — Competency & Operations Analysis

```python
# List active skills
skills_list()

# Query skill usage patterns
mcp_mempalace_search(query="skill invoked used called", limit=20)

# Store competency profile
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="COMPETENCY_PROFILE: <analysis results>"
)
```

### Phase 3 — Dream Integration & Pattern Synthesis

```python
# Retrieve dream diary entries
mcp_mempalace_diary_read(agent_name="hermes-dreaming", last_n=10)

# Query knowledge graph for recurring issues
mcp_mempalace_kg_query(entity="hermes", direction="outgoing")

# Store synthesis report
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="SYNTHESIS_REPORT: <tiered findings>"
)
```

### Phase 3.5 — Lesson Distillation

```python
# Check for duplicate lessons before creating new ones
mcp_mempalace_check_duplicate(content="<lesson text>", threshold=0.87)

# Add lesson to ledger
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room="lessons-ledger",
    content="LESSON: <structured lesson data>"
)

# Update knowledge graph with lesson relationships
mcp_mempalace_kg_add(
    subject="hermes",
    predicate="learned",
    object="<lesson_id>",
    source_closet=f"hermes-reflection/cycle-{cycle_id}"
)
```

### Phase 4 — Improvement Planning

```python
# Create improvement plan record
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="IMPROVEMENT_PLAN: <active and deferred tasks>"
)
```

### Phase 5 — Improvement Execution

```python
# Before modifying any skill, create backup
import shutil
import os
backup_dir = f"~/.hermes/skills/.backups/{cycle_id}"
os.makedirs(backup_dir, exist_ok=True)
shutil.copytree("~/.hermes/skills/<target-skill>", f"{backup_dir}/<target-skill>")

# Apply skill patch
skill_manage(action="patch", name="<skill-name>", old_string="...", new_string="...")

# Log execution
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="EXECUTION_LOG: <task results>"
)
```

### Phase 6 — Post-Change Validation

```python
# Query for validation evidence
mcp_mempalace_search(query="<improvement topic>", limit=10)

# Store validation status
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room=f"cycle-{cycle_id}",
    content="VALIDATION_STATUS: <validation results>"
)
```

### Phase 7 — Documentation & Archival

```python
# Write LLM-Wiki page
# (Use write_file or appropriate wiki tool)

# Write diary entry
mcp_mempalace_diary_write(
    agent_name="hermes-reflection",
    entry=f"REFLECTION_CYCLE: {cycle_id}|completed.phases.0-7|lessons.distilled:N|improvements.executed:M|★★★",
    topic="self-improvement"
)

# Update reflection index
mcp_mempalace_add_drawer(
    wing="hermes-reflection",
    room="index",
    content=f"CYCLE_COMPLETE: {cycle_id} at {datetime.now().isoformat()}"
)
```

### Phase 0 — Trigger Classification

Goal: determine why this cycle is running and what level of autonomy is allowed.

1. Classify the trigger as one of:
- `scheduled`
- `manual`
- `error-triggered`
- `post-dream`
- `post-change-validation`
- `baseline`

2. Classify the execution mode as one of:
- `full` — analysis, lesson extraction, planning, execution, documentation
- `partial` — analysis, lesson extraction, planning, documentation only
- `validation` — focused review of whether previous improvements worked

3. Set the cycle window:
- From last completed reflection cycle end time to now, or
- A user/operator-specified range, or
- Initialization to now if no prior cycle exists

4. Create the cycle root in Memory Palace:
- `reflection/{cycle_id}/meta`
- `reflection/{cycle_id}/phase_status`

### Phase 1 — Operational Data Harvest

Goal: gather the evidence base before making judgments.

1. Query Task History for the cycle window. Extract:
- Task types
- Completion status
- Runtime and latency indicators if available
- Retry counts
- Escalations
- User/operator corrections
- Confidence markers if recorded

2. Query Error & Anomaly Log. Extract:
- Error classes and counts
- Recurring errors, defined by same or similar root cause occurring 2+ times in the cycle
- Critical errors, defined by causing failed work, corrupted output, unsafe action, or escalation
- Latent errors, defined by being worked around without a real fix
- Slow failures, defined by repeated retries, stalls, or degraded outputs without hard failure

3. Query tool usage telemetry. Extract:
- Tool call counts by task type
- High-friction tools
- Over-called tools
- Tools with poor yield, high failure, or repeated retries
- Tool combinations that correlate with poor outcomes

4. Query Dream Log from `hermes-dreaming`. Extract:
- Dream entries since last cycle
- Dream entries tagged as warning, improvement, blockage, repetition, memory, drift, or identity
- Repeated motifs or themes
- Any explicit dream hypotheses about weaknesses, blind spots, or underused capabilities

5. Query prior reflection cycles. Extract:
- Prior findings
- Prior lessons
- Prior improvement tasks
- Prior validations
- Previously chronic issues
- Prior tasks marked ineffective, reverted, or deferred

6. Build the raw evidence packet and store it at:
- `reflection/{cycle_id}/raw_data`

### Phase 2 — Competency & Operations Analysis

Goal: evaluate how effectively Hermes is operating across domains.

1. Enumerate active skills and operational modules. For each one, determine:
- Invocation count
- Success rate
- Failure rate
- Escalation frequency
- Retry burden
- Average task friction if measurable
- Whether the skill is strong, acceptable, underperforming, or dormant

2. Evaluate task efficiency. Look for:
- Tasks taking more tool calls than expected
- Repeat clarification loops
- Excessive planning for simple work
- Repeated context loss
- Tool thrashing, where Hermes alternates tools without making progress

3. Evaluate reasoning quality. Look for:
- Incorrect confident outputs
- Missing clarifications when ambiguity was high
- Unnecessary clarifications when context was already sufficient
- Shallow diagnosis followed by premature action
- Plans that did not match the task scope

4. Evaluate orchestration quality. Look for:
- Failed handoffs between skills
- Conflicting instructions across skills
- Missing capability coverage between adjacent skills
- Duplicate capabilities creating routing ambiguity

5. Produce a **Competency Profile** with at minimum:
- `strong_domains`
- `weak_domains`
- `dormant_skills`
- `efficiency_issues`
- `tool_issues`
- `reasoning_gaps`
- `handoff_failures`
- `suspected_capability_gaps`

Store it at:
- `reflection/{cycle_id}/competency_profile`

### Phase 3 — Electric Sheep Integration & Pattern Synthesis

Goal: test whether electric-sheep outputs reveal, confirm, or broaden real operational patterns.

1. For each relevant electric-sheep signal, classify it as:
- `confirmatory` — clearly matches observed operational evidence
- `novel` — introduces a plausible issue not yet visible elsewhere
- `speculative` — no current evidence match
- `resolved` — references a problem that prior cycles already fixed

2. Identify convergence patterns where both electric-sheep signals and operational data point to the same issue.

3. Identify divergence patterns where electric-sheep indicates a concern but operational evidence is absent. Do not act on these directly; monitor them.

4. Compare current findings with prior cycles and determine whether each issue is:
- `new`
- `recurring`
- `chronic` — appears across 2+ cycles
- `improved`
- `validated_resolved`
- `ineffective_prior_fix`

5. Produce a prioritized **Synthesis Report**:
- Tier 1 — critical recurring failures, chronic issues, confirmed convergence signals, unsafe behaviors
- Tier 2 — important underperformance, friction, weak reasoning patterns, tool inefficiencies
- Tier 3 — opportunities, dormant capabilities, speculative electric-sheep themes, possible but unproven improvements

Store it at:
- `reflection/{cycle_id}/synthesis_report`

### Phase 3.5 — Lesson Distillation

Goal: convert evidence into concise, reusable lessons without polluting permanent operating rules with noise.

For each Tier 1
and Tier 2 finding, and for any Tier 3 finding with strong evidence:

1. Determine the promotion level:
- `note` — keep only in Reflection Archive
- `lesson` — add to Lessons Ledger as reusable learning
- `standing_rule_candidate` — eligible to become a skill/config/prompt/workflow rule

2. A finding should become a **lesson** only if at least one of these is true:
- It recurred within the cycle
- It resembles a prior-cycle issue
- It materially affected task quality, efficiency, or safety
- It changes how Hermes should behave in future situations

3. A lesson should become a **standing rule candidate** only if:
- The evidence is strong and repeated
- The lesson is broadly applicable beyond one incident
- The required behavior is concrete enough to encode in an artifact
- A prior fix attempt did not already prove ineffective

4. **Do not promote electric-sheep-only speculative signals into standing rules without corroborating operational evidence.**

5. Each Lessons Ledger entry must use this structure:
- `lesson_id`
- `created_in_cycle`
- `status: active | monitor | deprecated | superseded | promoted`
- `trigger_or_symptom`
- `what_happened`
- `root_cause`
- `generalized_lesson`
- `required_behavior_change`
- `evidence_refs`
- `promotion_status: note | lesson | standing_rule_candidate | standing_rule`
- `review_date`
- `supersedes` (optional)

5. Lesson writing rules:
- Keep each lesson concise, ideally under 120 words.
- Prefer generalized patterns over incident narration.
- Merge duplicates instead of creating near-identical lessons.
- If a lesson is outdated, mark it `deprecated` or `superseded`; do not delete history.
- **Do not create a lesson from electric-sheep-only speculative signals without corroboration.**

7. Maintain the **Lessons Ledger Index** in Memory Palace:
- `memory/lessons/index`
- Link each active lesson to related skills, prompts, tools, or workflows.

8. Store cycle-created lessons at:
- `reflection/{cycle_id}/lessons_extracted`

### Phase 4 — Improvement Planning

Goal: convert findings and lessons into a safe, executable improvement plan.

1. For each Tier 1 finding, each Tier 2 finding, and each promoted lesson, define one or more improvement tasks.

2. Each task must include:
- `task_id`
- `source_ref` — finding and/or lesson reference
- `type: skill_patch | prompt_update | tool_fix | new_skill | config_change | knowledge_update | monitoring_addition | workflow_patch`
- `description`
- `expected_outcome`
- `risk_level: low | medium | high`
- `dependencies`
- `estimated_scope: trivial | small | medium | large`
- `operator_approval_required: true | false`
- `validation_method`
- `success_signal`
- `rollback_required: true | false`

3. Mapping rules:
- If the issue is local to one skill, prefer `skill_patch`.
- If the issue is mostly instruction ambiguity, prefer `prompt_update`.
- If the issue is execution friction around a tool, prefer `tool_fix`.
- If the issue is missing visibility, prefer `monitoring_addition`.
- If the issue recurs between multiple skills, prefer `workflow_patch`.
- If the issue reflects a missing capability, consider `new_skill`, but require approval before activation.

4. Approval rules:
- `high` risk always requires operator approval.
- `new_skill` always requires operator approval before activation.
- Any modification to Memory Palace schema or core self-governance rules requires approval.
- `low` and `medium` risk tasks may proceed automatically in full mode unless local policy says otherwise.

5. Produce two outputs:
- `improvement_plan_active` — approved or auto-approvable tasks
- `improvement_plan_deferred` — blocked or approval-pending tasks

Store at:
- `reflection/{cycle_id}/improvement_plan`

### Phase 5 — Improvement Execution

Goal: carry out safe, approved changes and verify them.

For each task in `improvement_plan_active`, in dependency order:

1. Pre-execution safeguards:
- Confirm dependencies are complete.
- Confirm target artifacts exist.
- Create a backup/snapshot before any modification.
- Store backup at `reflection/{cycle_id}/backups/{task_id}`.

2. Execute according to task type:
- `skill_patch` — revise relevant SKILL.md sections, preserving structure and examples
- `prompt_update` — revise prompt/instruction text with tighter behavior rules
- `tool_fix` — adjust retry logic, fallback behavior, parameter defaults, or call sequencing
- `new_skill` — draft complete skill file and hold for approval if not yet approved
- `config_change` — edit thresholds, timeouts, limits, or routing defaults
- `knowledge_update` — update semantic or procedural memory entries, but never delete historical evidence
- `monitoring_addition` — add counters, alerts, heuristics, or recurring issue detectors
- `workflow_patch` — fix routing, handoffs, sequencing, or state transitions across multiple skills

3. Verification after each task:
- Run the specified validation method.
- Check whether the expected outcome is observable.
- Confirm no dependent skill or workflow is broken.
- If verification fails, revert to backup immediately.

4. Log execution result:
- `status: complete | failed | reverted | deferred`
- `actual_changes`
- `verification_result`
- `follow_up_check`
- `linked_lesson_refs`

5. Update lesson status if appropriate:
- If the task encoded a lesson into Hermes behavior, change lesson `promotion_status` to `standing_rule` or `promoted`.
- If the task failed or was reverted, keep the lesson active but annotate the failed implementation path.

Store execution details at:
- `reflection/{cycle_id}/execution_log`

### Phase 6 — Post-Change Validation

Goal: determine whether executed improvements actually improved behavior.

1. For every completed task from Phase 5, define a validation window such as:
- next 5 invocations
- next 10 relevant tool calls
- next reflection cycle
- operator-confirmed observation window

2. Record what Hermes must watch:
- reduction in error recurrence
- lower retry burden
- better task completion rates
- fewer escalations
- better response quality
- faster completion with equal or better quality

3. If evidence already exists during the cycle, classify each improvement as:
- `validated`
- `partially_validated`
- `not_yet_validated`
- `ineffective`
- `regressive`

4. Write these outcomes to:
- `reflection/{cycle_id}/validation_status`

5. If a change is clearly regressive, revert if safe and mark the linked lesson implementation path as ineffective.

### Phase 7 — Documentation & Archival

Goal: document the cycle clearly for humans and agents, then archive everything in durable form.

1. Produce the LLM-Wiki reflection page using this structure:

```markdown
# Hermes Reflection Cycle: {cycle_id}
**Date:** {ISO timestamp}
**Period Covered:** {start_date} to {end_date}
**Cycle Type:** {scheduled | manual | error-triggered | post-dream | post-change-validation | baseline}
**Mode:** {full | partial | validation}
**Trigger:** {trigger description}

## Executive Summary
[2–4 sentences on what Hermes learned, what mattered, and what changed]

## Operational Health Snapshot
| Domain | Invocations | Success Rate | Escalations | Status |
|--------|-------------|--------------|-------------|--------|
| ... | ... | ... | ... | ... |

## Key Findings
### Tier 1 — Critical
- ...

### Tier 2 — Important
- ...

### Tier 3 — Opportunity
- ...

## Dream Integration
[What dreams confirmed, suggested, or failed to support]

## Lessons Distilled
| Lesson ID | Generalized Lesson | Promotion Status | Status |
|-----------|--------------------|------------------|--------|
| ... | ... | ... | ... |

## Improvement Actions Taken
| Task ID | Type | Description | Status | Verified |
|---------|------|-------------|--------|----------|
| ... | ... | ... | ... | ... |

## Deferred Improvements
- ...

## Validation Status
| Task ID | Validation Window | Current Status | Notes |
|---------|-------------------|----------------|-------|
| ... | ... | ... | ... |

## Metrics Delta
[Current vs prior cycle changes in success rate, error recurrence, retries, escalations, latency if available]

## Next Cycle Targets
- ...

## Archive References
- reflection/{cycle_id}/raw_data
- reflection/{cycle_id}/competency_profile
- reflection/{cycle_id}/synthesis_report
- reflection/{cycle_id}/lessons_extracted
- reflection/{cycle_id}/improvement_plan
- reflection/{cycle_id}/execution_log
- reflection/{cycle_id}/validation_status
```

2. Store the LLM-Wiki page at the appropriate reflection namespace, such as:
- `wiki/reflection/{cycle_id}.md`

3. Archive the full cycle in Memory Palace, including:
- raw evidence
- competency profile
- synthesis report
- extracted lessons
- improvement plan
- backups
- execution log
- validation status

4. Update these long-lived indexes:
- Reflection Index
- Lessons Ledger Index
- Chronic Issues Tracker
- Improvement Validation Tracker

5. Notify the operator if a notification channel exists. Include:
- cycle ID
- cycle window
- counts of Tier 1/Tier 2/Tier 3 findings
- number of new lessons
- number of promoted lessons
- number of executed improvements
- number of deferred/high-risk tasks
- any regressive or reverted changes

6. Self-verify closure:
- all phase statuses recorded
- LLM-Wiki page written
- archive paths valid
- indexes updated
- approval-pending tasks preserved

## Output Format

Primary output:
- A complete **LLM-Wiki reflection page** for the cycle.

Persistent secondary outputs:
- `reflection/{cycle_id}/raw_data`
- `reflection/{cycle_id}/competency_profile`
- `reflection/{cycle_id}/synthesis_report`
- `reflection/{cycle_id}/lessons_extracted`
- `reflection/{cycle_id}/improvement_plan`
- `reflection/{cycle_id}/backups/`
- `reflection/{cycle_id}/execution_log`
- `reflection/{cycle_id}/validation_status`
- updated `memory/lessons/index`
- updated Reflection Index and Chronic Issues Tracker

## Rules & Constraints

### Hard Rules
- Never skip final documentation and archival.
- Never modify skills, prompts, workflows, or config without creating a backup first.
- **Never promote electric-sheep-only speculative signals into a standing rule without corroborating operational evidence.**
- Never delete historical reflection data or lessons; deprecate or supersede instead.
- Never repeat an implementation path previously marked ineffective without a materially different approach.
- Never execute high-risk changes without operator approval.
- Never let the Lessons Ledger become a dump of incident notes; keep it concise and generalized.
- **Never run a full reflection cycle without validating prerequisites first.**
- **Always use `mcp_mempalace_check_duplicate` before creating new lessons to avoid redundancy.**
- **Always verify MemPalace is accessible before starting Phase 1.**

### Decision Rules
- If a problem happened once and evidence is weak, store it as a note in the Reflection Archive only.
- If a problem happened more than once or materially degraded outcomes, create or update a lesson.
- If a lesson holds across cycles and implies a stable behavior change, convert it into a standing rule candidate.
- If a standing rule candidate can be encoded safely, create a patch task.
- If evidence is mixed, monitor instead of patching.
- If a change improves one area but harms another, prefer rollback and redesign over silent acceptance.

### Memory Discipline
- Reflection Archive is for evidence-heavy cycle details.
- Lessons Ledger is for compressed reusable learning.
- Skill files, prompts, configs, and workflow definitions are the only valid homes for durable operating behavior.
- LLM-Wiki is for readable synthesis, not as the sole source of truth for operational rules.

### Error Recovery
If any phase fails:
1. Record the failure in the cycle log with full error details
2. Mark the phase status as `failed` or `partial`
3. Continue to the next phase if safe to do so
4. If critical (Phase 1, 3, or 5), pause and notify operator
5. Document the failure in the final report

### Edge Cases
- **First cycle:** create baseline metrics and a baseline Lessons Ledger snapshot; there may be no prior comparisons.
- **No electric-sheep data available:** continue without error; mark electric-sheep integration as unavailable.
- **No significant issues found:** still produce a cycle report, validate healthy behavior, and extract positive lessons if reusable.
- **All improvements require approval:** complete analysis, lessons, plan, and documentation; defer execution.
- **Active long-running work in progress:** queue the reflection cycle unless policy allows low-impact background analysis.
- **Conflicting evidence:** prefer monitoring and smaller scoped changes over large patches.
- **MemPalace unavailable:** abort cycle and reschedule; do not proceed without memory access.
- **No prior cycles exist:** establish baseline without comparison metrics.

## Quick Start: Automated Execution

### Cron Setup

To run a full reflection cycle automatically:

```bash
# Daily at 4:00 AM
0 4 * * * hermes run-skill self-reflection-self-improvement --mode full

# Weekly on Sundays at 3:00 AM  
0 3 * * 0 hermes run-skill self-reflection-self-improvement --mode full
```

### Hermes Cron Job

Create via Hermes CLI:
```bash
hermes cron create \
  --name "hermes-self-reflection" \
  --schedule "0 4 * * *" \
  --skill self-reflection-self-improvement \
  --prompt "Run a full self-reflection and self-improvement cycle. Execute all phases 0-7. Mode: full. Trigger: scheduled. Review electric-sheep outputs from MemPalace diary (agent_name=electric-sheep). Do NOT trigger electric-sheep — it runs independently via hermes-dreaming-cycle cron job."
```

Or use the `cronjob` tool:
```python
cronjob_create(
    name="hermes-self-reflection",
    schedule="0 4 * * *",
    skills=["self-reflection-self-improvement", "mempalace", "electric-sheep"],
    prompt="Run a full self-reflection and self-improvement cycle. Execute all phases 0-7. Mode: full. Trigger: scheduled. Validate prerequisites before starting. Read electric-sheep diary entries via mcp_mempalace_diary_read(agent_name='electric-sheep', last_n=10) to review its outputs. Do NOT trigger or invoke electric-sheep directly — it runs independently via hermes-dreaming-cycle cron job daily at 00:00."
)
```

### Manual Invocation

For a one-time manual cycle:
```bash
hermes run-skill self-reflection-self-improvement --mode full --trigger manual
```

### Partial Mode (Analysis Only)

For analysis without execution:
```bash
hermes run-skill self-reflection-self-improvement --mode partial --trigger manual
```

Input: weekly scheduled trigger after 64 tasks.

Observed:
- Search tool rate-limit errors occurred 6 times.
- Summarization skill required repeated retries on large inputs.
- Electric-sheep analysis repeatedly identified fragmentation and looped paths as skill gaps.

Result:
- Search rate limiting becomes a Tier 1 finding and a lesson about backoff and query compaction.
- Summarization retry burden becomes a Tier 2 finding and a lesson about chunk-size control.
- Two tasks are created: `tool_fix` for retry/backoff behavior and `skill_patch` for summarization chunking.
- Both changes are executed, verified, documented, and linked to their lessons.

### Example 2 — Partial Mode Review

Input: operator says, “run a quick self-check, but do not change anything.”

Result:
- Hermes runs Phases 0–4 and Phase 7 only.
- Hermes creates findings, extracts lessons, writes the LLM-Wiki report, and queues improvement tasks without executing them.
- Deferred tasks remain pending for operator approval.

### Example 3 — Chronic Issue Promotion

Input: the same routing ambiguity appears across three reflection cycles.

Result:
- The issue is classified as chronic.
- Existing lessons are merged into one generalized lesson.
- A `workflow_patch` task is created to tighten routing rules between the affected skills.
- The lesson promotion status moves from `lesson` to `standing_rule_candidate`, and after successful patching to `standing_rule`.
