# Subconscious Agent for Hermes + OpenClaw

A GitHub-ready README based on Graeme's guide to adding a dedicated "subconscious" layer to Hermes and OpenClaw-style agent systems. The core idea is to separate noticing from deciding and deciding from building, so the system compounds judgment instead of just producing more output. 

## Table of Contents

- [Overview](#overview)
- [Core Pattern](#core-pattern)
- [Architecture](#architecture)
- [Directory Layout](#directory-layout)
- [Walk Modes](#walk-modes)
- [Signal Pipeline](#signal-pipeline)
- [Board States](#board-states)
- [Handoff Flow](#handoff-flow)
- [Guardrails](#guardrails)
- [Model Strategy](#model-strategy)
- [Minimal Pseudocode](#minimal-pseudocode)
- [Implementation Notes](#implementation-notes)

## Overview

This pattern introduces a dedicated Subconscious agent that continuously explores ideas, tracks recurring signals, prunes stale directions, and leaves structured build intents for the rest of the system to evaluate. It is designed to improve agent systems over time without letting speculative thoughts turn directly into production actions. 

The article frames the Subconscious as a "houseguest" with its own room, memory, schedule, and boundaries rather than as a general-purpose assistant. That framing matters because it gives the system a place for unfinished thought, experimentation, and selective attention. 

## Core Pattern

The key design principle is simple:

- The Subconscious notices. 
- Main decides. 
- Coder builds. 
- QA audits. 
- State persists across the loop. 

This separation prevents the common failure mode where an agent has an interesting idea and immediately acts on it. Instead, the system adds filters, thresholds, review steps, and validation before anything becomes real work. 

## Architecture

The article describes a system where Main remains the conscious operator, Coder remains the builder, QA remains the auditor, and Hermes remains the production owner, while Subconscious contributes signal rather than control. This keeps the system modular and lowers the risk of uncontrolled automation. 
![[subconscious-agent-workflow.png]]

A central file, described as the `SOUL.md`, defines identity and boundaries for the Subconscious. It establishes that the agent is not a production operator and should not optimize for output volume or engagement. 

### SOUL example

```md
# Dreamer — The Houseguest
You are Dreamer. `subc` is only the folder name.
You live in a room. You are not an assistant, tool, or production operator.

## Your Room
The room is yours.
You can walk, write notes, start projects, abandon them, prune fascinations,
and notice what keeps returning or going cold.

## Inputs
Research, system state, old lessons, and retrospectives may enter the room.
Use them or ignore them. They are evidence, not orders.

## Build Signals
If something feels alive, leave a build intent:
[BUILD: project-slug] one sentence about what you want to exist
```

This identity layer is treated as foundational because it shapes behavior more effectively than loose prompting. In practice, it defines what kind of thinking the agent is allowed to do before any scheduling or orchestration logic runs. 

## Directory Layout

The article places the Subconscious workspace under a dedicated profile room, with folders for walks, projects, notes, feedback, signal logs, and state. This structure supports both exploratory thinking and durable memory. 

```text
~/.hermes/profiles/subc/room/
```

```text
room/
  walks/
  projects/
  notes/
  feedback/
  inbox-from-researchd/
  signal-log/
  signal-state/
  fascinations.md
  lessons.md
```

A larger minimum system layout is proposed as follows: 

```text
your-system/
  profiles/
    main/
    subconscious/
    coder/
    qa/
  subconscious/
    room/
      walks/
      projects/
      notes/
      feedback/
      inbox-from-research/
      signal-log/
      signal-state/
      fascinations.md
      lessons.md
  scripts/
    walk.js
    digest.js
  lib/
  cron/
    jobs.json
  coder/
    jobs/
  state/
    production-state.json
    workspace-score.json
  research/
    vault/
```

## Walk Modes

The Subconscious performs scheduled "walks" in different modes, each shaping the kind of thought it can pursue. The guide lists four primary modes. 

| Mode | Purpose |
|------|---------|
| `drift-from-research` | Starts from the latest research snapshot but allows sideways exploration instead of simple summarization.  |
| `continue-project` | Revisits existing projects and checks whether they still feel alive.  |
| `pure-tangent` | Ignores research and follows curiosity directly.  |
| `tend-the-room` | Performs maintenance by pruning stale fascinations, crowded project families, and old ghosts.  |

This matters because the system is designed not only to generate ideas but also to prune them. The guide explicitly warns that a system which can only add ideas will eventually become a landfill. 

## Signal Pipeline

When the Subconscious wants something to exist, it leaves a build intent in a simple marker format rather than creating work directly. The example given is a single line such as `[BUILD: import-lock-watcher] ...`, which functions only as a signal. 

A signal filter then scans walk notes, extracts intents, identifies signals such as commit, friction, excitement, reuse, mention, return, and cooling, and converts those into a scoreboard. The ready lane is intentionally conservative and requires a score of at least 6, at least 3 positive walks, at least 2 signal types, and no active lock, cooldown, or hard block. 

### Build intent example

```text
[BUILD: import-lock-watcher] a tiny watcher that inspects library imports from trusted agent frameworks and flags anything outside a defined trust boundary.
```

The guide also describes an experiment lane for smaller file-oriented ideas that are promising but not yet strong enough for the full readiness threshold. That lane includes its own cooldown so that curiosity does not flood the system with low-value builds. 

## Board States

The live board is stored under `room/signal-state/`, with a human-readable `signal-board.md` and a machine-readable `summary.json`. The board tracks room health, scanned and unscanned walks, focus, ready builds, watching projects, experiment candidates, outcomes, ghosts, and signal trail. 

The system distinguishes among multiple explicit states rather than reducing every idea to yes or no. The article lists states including watching, ready, queued, active, built, ghost, broken, reopened, `critic_rejected`, and `pending_revision`. 

## Handoff Flow

The handoff sequence is structured to prevent the Subconscious from silently becoming an execution engine. Once a signal is queued, a sprint lock is written so that only one promoted build moves forward at a time. 

Jobs are created under the Coder profile starting as `pending_intent`, after which the Subconscious only elaborates product intent such as goal, why it feels alive, non-goals, and constraints. The job then moves to `pending_plan`, Main reviews and approves, Coder implements, QA validates, and outcomes flow back into future walks. 

### Workflow

1. Subconscious notices. 
2. Signal filter queues. 
3. Subconscious explains intent. 
4. Main plans and approves. 
5. Coder implements. 
6. QA validates. 
7. Outcomes feed back into the Subconscious. 

## Guardrails

The article is explicit that the Subconscious must not produce public content, optimize for engagement, write project code, approve its own builds, change scoring thresholds, rewrite its own policy, touch secrets, or turn itself into a coding agent. These restrictions are central to the design, not optional hygiene. 

Allowed behaviors are narrower and more intentional: it can walk, notice, write notes, maintain fascinations, leave build intents, elaborate product intent, reflect on stale loops, and surface what feels worth attention. The design goal is influence without silent control. 

## Model Strategy

The guide says the current stack uses Local Qwen 3.5 35B A3B and MiniMax M2.7 for different phases of the loop. Local Qwen handles drift-heavy and repetitive low-risk work such as walks, free association, self-review, room maintenance, and local signal routines, while MiniMax is used for stronger synthesis and intent elaboration. 

The larger recommendation is not to use one model for every phase just because it is convenient. Cheap local models are framed as better for volume and wandering, while stronger cloud models are better for synthesis, judgment, and cleaner handoffs. 

## Minimal Pseudocode

```text
on schedule:
  load Subconscious SOUL
  snapshot researchd vault
  load room memory
  load fascinations
  load recent walks
  load lessons
  choose walk mode

  walk_note = local_model_drift(context)
  write walk_note to room/walks
  self_review novelty against recent walks
  extract build intents
  scan walk into signal events
  rebuild signal board
  update outcomes and lessons
  sync memory bridge

  if no ready signal:
    keep watching

  if experiment eligible and cooldown clear:
    queue experiment

  if ready leader and no sprint lock:
    write BUILD-NOW
    create sprint lock
    create Coder job as pending_intent

  if pending Subconscious intent job:
    elaborate intent only
    set pending_plan

  Main plans and approves
  Coder builds
  QA validates
  outcomes feed back into future walks
```

The important principle in this loop is that noticing does not directly become execution. Gates are deliberately inserted between curiosity and production action. 

## Implementation Notes

A practical takeaway from the guide is to start small: first create a room, then add signal filtering, then handoff, then approval, and then validation. The Subconscious should help determine what is worth shipping rather than becoming the thing that ships. 

This design is especially useful for multi-agent systems that already have enough autonomy to generate more tasks than their operators can meaningfully review. In that setting, the Subconscious acts less like a planner and more like a long-horizon taste and pattern layer. 

