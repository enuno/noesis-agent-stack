# Hermes/OpenClaw Research Agent Design Doc

## Overview

This document translates the article "I run 6 AI agents. Only this one makes the other 5 smarter" into a practical design for a Hermes/OpenClaw stack centered on a dedicated research agent.
The core idea is to make research a durable evidence service for the rest of the agent system rather than a summarizer, scraper, or news bot.
In this model, the research agent continuously collects signals, separates findings from claims, preserves source trails, and routes implications to downstream agents without collapsing judgment, execution, and publishing into one role.
![[research_agent_design.png]]


## Design Goals

The stack should treat the research agent as an evidence operator whose job is to turn external change into reusable intelligence for the rest of the system.
The design should preserve explicit boundaries between raw captures, findings, claims, verified knowledge, and downstream tasks so the system does not convert weak signals into overconfident actions.
The implementation should also produce operator-facing artifacts such as briefs, handoff queues, health checks, and run receipts so that research becomes inspectable and operational rather than hidden in chat logs.

## Agent Roles

The reference architecture separates responsibilities across multiple agents: research as evidence collector, main as conscious operator, coder as builder, QA as auditor, and content as publishing operator.
For a Hermes/OpenClaw deployment, this means the research agent should be upstream of execution-oriented profiles and should provide evidence packets and routing cues instead of owning end-to-end actions.
If a subconscious or strategy profile does not exist in the stack, its handoff lane should be omitted rather than left as a dead path.

| Role | Responsibility | Inputs | Outputs |
|---|---|---|---|
| Research agent | Collect, score, structure, and route evidence. | Shared workspace state, source plan, prior vault state. | Findings, claims, source ledgers, dossiers, handoffs, briefs. |
| Main/Hermes | Interpret research output and decide what matters operationally. | Operator briefs, dossiers, verified claims, handoff queues. | Decisions, priorities, delegations. |
| Coder | Build approved tools, automations, or product changes. | Buildroom handoff, specifications, verified research context. | Code, scripts, services, integrations. |
| QA | Validate outputs and catch regressions or unsupported claims. | Builds, validation rules, evidence trails. | Test results, audit notes, release gates. |
| Content | Convert approved insights into publishable material. | Content handoff, dossiers, approved claims. | Posts, articles, briefs, media drafts. |

## Operating Model

The article defines the research loop as: observe, infer priorities, gather evidence, deepen one question, update vault, route implications, and repeat.
For Hermes/OpenClaw, that loop should be implemented as a reusable skill with named modes such as bootstrap, refresh, daily summary, backup, restore, and recover so that refresh, delivery, and survivability are kept distinct.
This separation matters because bootstrap builds state, refresh mutates evidence, summary renders human-facing output, and recovery protects operational continuity.

A suitable contract for the research profile is a `SOUL.md` file that defines identity, write boundaries, and the rule that research may collect and route information but may not make irreversible decisions such as purchases, public publishing, or partnership commitments.
The profile should treat shared workspace context as upstream read-only evidence and the research vault as its canonical write surface.
The profile should also report stale or degraded collectors explicitly rather than silently pretending freshness.

## Vault Structure

The article argues that a research agent should not rely on chat transcripts as memory and instead should write into a structured vault containing context, config, dossiers, ledgers, raw captures, queues, notes, wiki pages, health checks, and operator surfaces.
That structure matters because it enforces separation between unprocessed material, machine-readable knowledge, human-readable synthesis, and downstream routing surfaces.
The minimal recommended shape below is a practical starting point for a Hermes/OpenClaw deployment.

```text
profiles/
  research-agent/
    SOUL.md
    config.yaml
    cron/
      jobs.json
    scripts/
      research_agent_refresh.py
      research_agent_validate.py
      research_agent_daily_summary.py
      research_agent_midday_focus.py
    skills/
      research/
        research-agent-loop/
          SKILL.md
          scripts/
            research_agent_loop.py
            backup_research_agent.py
            restore_research_agent.py
            recover_research_agent.py
    workspace/
      research-vault/
        context/
          interest-profile.json
          interest-profile.md
          source-plan.md
        config/
          collector-config.json
          source-registry.json
          source-weights.json
          thresholds.json
        dossiers/
        knowledge/
          claims.jsonl
          findings.jsonl
          sources.jsonl
        raw/
          sources/
          topics/
        decisions/
        runs/
        indexes/
        queue/
          research-questions.md
          verification-review.md
          buildroom-handoff.json
          content-handoff.json
          verify-handoff.json
          watch-handoff.json
        notes/
          operator-brief.md
          daily-summary.md
        wiki/
          concepts/
          articles/
        health/
          latest-health-check.md
        ops/
          collector-health.md
          source-balance.md
          operator-cockpit.html
        tools/
        state/
          research-agent/
```

## Data Model

The core data model should preserve at least three separate machine-readable ledgers: findings, claims, and sources.
The article emphasizes that a finding is not a claim, a claim is not verified knowledge, and verified knowledge is not automatically a task; the data model should therefore encode state transitions explicitly instead of flattening them into prose.
A verification queue should hold under-evidenced or contradictory material so uncertainty is tracked rather than erased.

| Artifact | Purpose | Notes |
|---|---|---|
| `raw/sources/*.json` | Store collector output before synthesis. | Retain for replay and audit. |
| `knowledge/findings.jsonl` | Record observed signals extracted from raw input. | Should include source IDs, timestamps, and topic tags. |
| `knowledge/claims.jsonl` | Store candidate beliefs derived from findings. | Should track confidence, status, and contradiction links. |
| `knowledge/sources.jsonl` | Preserve citation trail and metadata for every evidence item. | Should support source weighting and freshness checks. |
| `queue/verification-review.md` | Hold weak or unresolved claims pending review. | Prevents premature downstream promotion. |
| `dossiers/*.md` | Maintain living topic summaries and implications. | Best for recurring themes and strategic lanes. |
| `decisions/*.md` or `.json` | Record what was decided and why. | Enables decision traceability over time. |
| `runs/*.json` | Store run receipts and validation results. | Required for replay and postmortem analysis. |

## Source Strategy

The article recommends bounded, high-signal collection instead of broad scraping, with sources chosen for their ability to change decisions rather than maximize volume.
In a Hermes/OpenClaw stack, the initial source plan should focus on a narrow set of operator-relevant surfaces such as owned posts, curated X lists, GitHub repositories, RSS feeds, official docs, selected blogs, and targeted domains.
Because your environment is highly technical and infrastructure-heavy, a tailored source plan should bias toward agent frameworks, orchestration systems, memory tooling, developer docs, cloud-native repos, crypto and DePIN infrastructure, and project-specific intelligence feeds rather than generic social trend capture.

A useful source strategy should assign each source a weight, trust tier, freshness threshold, collection cadence, and owning collector.
Social signals should be treated as early indicators unless validated by stronger surfaces such as official documentation, code repositories, release notes, or direct product artifacts.
If a collector degrades or becomes stale, the run output should mark that lane degraded and prevent that evidence from being silently treated as current.

## Interest Profiling

The article’s research agent does not start from generic trend detection; it rebuilds an explicit interest profile from durable notes, recent work, posting behavior, repeated questions, and prior outputs.
In a Hermes/OpenClaw stack, that same pattern should be used to infer active research lanes for the operator and the broader stack.
This is particularly useful when the system spans multiple simultaneous domains, because it gives the research layer a way to prioritize by current strategic relevance rather than public noise.

For your stack, a first-pass interest profile could include these lanes: multi-agent orchestration, memory systems, MCP/OpenClaw integrations, Kubernetes and Talos operations, Bitcoin mining optimization, liquid cooling and datacenter operations, crypto rails and treasury automation, legal-tech research automation, and self-hosted sovereign infrastructure.
Those categories should remain explicit and revisable rather than implicit in prompts.
The interest profile should be written to both machine-readable and human-readable formats so it can drive collectors while still being easy to inspect and tune.

## Operator Surfaces

The article treats operator surfaces as first-class outputs, including an operator brief, action ledger, cockpit, dispatch file, and handoff queues.
That pattern fits Hermes/OpenClaw well because it converts research from passive storage into decision support for the operator and downstream agents.
The most important artifact is the operator brief, which should answer what changed, what deserves attention, what is blocked by weak evidence, and which downstream agent should receive each implication.

Suggested handoff lanes for a Hermes/OpenClaw implementation are listed below.

| Handoff lane | Destination | Typical trigger |
|---|---|---|
| `buildroom-handoff.json` | Coder / engineering agents | Clear build implication, automation opportunity, or integration task. |
| `content-handoff.json` | Content agent | Insight suitable for article, thread, report, or explainer. |
| `verify-handoff.json` | QA / verification agent | High-value claim still blocked by weak or conflicting evidence. |
| `watch-handoff.json` | Monitoring or alerting workflows | Early signal worth tracking but not acting on yet. |
| `ops-handoff.json` | Infrastructure / operations profile | Incident pattern, infrastructure change, deployment relevance, or vendor shift. |
| `treasury-handoff.json` | Treasury or strategy profile | Market, rails, or policy signals with potential treasury implications. |

## Quality Gates

The article recommends explicit source-balance and health artifacts so the system can measure whether a run is over-dependent on low-trust or stale surfaces.
This should be implemented as part of the refresh path rather than optional cleanup, and validation should run before downstream promotion.
The health lane should check for broken links, missing metadata, gaps in source trails, stale verification items, orphan claims, and wiki compile drift.

A practical validation flow for Hermes/OpenClaw should include four layers:

- Structural validation: required files, front matter, schemas, and directory expectations.
- Evidence validation: every claim resolves to findings and every finding resolves to sources.
- Freshness validation: collector timestamps and stale lane detection.
- Promotion validation: no downstream handoff for claims below threshold or with unresolved contradictions.

## Scheduling And Runtime

The article uses a recurring refresh cadence plus separate daily delivery jobs, and it notes that delivery jobs should rebuild surfaces from existing artifacts rather than surprise-scrape live data.
That pattern should be preserved in a Hermes/OpenClaw deployment because it decouples expensive evidence gathering from lightweight operator updates.
A simple initial schedule would be a four- or six-hour refresh, a daily summary, and a midday focus rebuild from prior artifacts.

Routine collection and parsing jobs can use cheaper or local models, while synthesis, judgment, and sensitive routing should use stronger models.
This separation reduces cost and keeps expensive reasoning focused on the narrowest possible context window.
The runtime configuration should therefore bind each mode to a model tier, timeout budget, tool policy, and allowed write scope.

## Guardrails

The article is explicit that the research agent should not make trading decisions, publish public posts, make purchases, touch secrets, or convert weak signals into approved work.
For Hermes/OpenClaw, the research profile should be read-heavy, write-bounded, and authority-limited; it may influence the system, but it should not hold execution authority over external systems without a second-stage decision agent.
That boundary is especially important in stacks touching treasury logic, infrastructure automation, or legal workflows.

Recommended guardrails include:

- No direct access to production credentials or wallet-signing surfaces.
- No autonomous publishing to public channels.
- No promotion of unverified claims into build tickets or strategy directives.
- No silent use of stale data when freshness checks fail.
- No modification of other agents’ state outside approved handoff surfaces.

## Implementation Checklist

### Phase 1: Foundation

- [ ] Create `profiles/research-agent/` with `SOUL.md`, `config.yaml`, `cron/jobs.json`, and a dedicated workspace vault.
- [ ] Define the research-agent operating contract in `SOUL.md`: identity, boundaries, allowed tools, write surfaces, and non-goals.
- [ ] Scaffold the minimal vault directories for context, config, dossiers, knowledge, raw, queue, notes, wiki, health, ops, runs, and decisions.
- [ ] Define JSON or JSONL schemas for findings, claims, sources, run receipts, and verification leads.
- [ ] Create `source-registry.json`, `source-weights.json`, and `thresholds.json` to support weighted evidence collection.

### Phase 2: Collection

- [ ] Implement collectors for a small, bounded source set: owned feeds, curated lists, GitHub repos, RSS, official docs, and selected web domains.
- [ ] Store raw collector output in `raw/` with source IDs, retrieval timestamps, and collector metadata.
- [ ] Add source freshness and collector health reporting to each run.
- [ ] Build a source scoring layer that tags each input with trust tier, freshness, and decision relevance.

### Phase 3: Knowledge Pipeline

- [ ] Build extraction logic that converts raw captures into findings with normalized metadata.
- [ ] Build claim generation logic that clusters or promotes findings into candidate claims.
- [ ] Implement evidence linkage so each claim can be traced to its findings and each finding to its sources.
- [ ] Add contradiction flags, confidence values, and verification-needed status for weak claims.
- [ ] Generate topic dossiers for recurring research lanes and update them on every refresh.

### Phase 4: Operator Outputs

- [ ] Generate `notes/operator-brief.md` summarizing changes, important signals, blocked items, and routing recommendations.
- [ ] Generate `notes/daily-summary.md` as the human-facing digest for scheduled delivery.
- [ ] Create handoff artifacts for build, content, verify, watch, and any stack-specific lanes such as ops or treasury.
- [ ] Build an `operator-cockpit.html` or equivalent dashboard for scanning evidence quality, recent changes, and pending actions.

### Phase 5: Validation

- [ ] Implement schema validation for all knowledge and handoff artifacts.
- [ ] Implement health checks for stale collectors, missing trails, orphan claims, broken links, and wiki compile drift.
- [ ] Block downstream promotion when validation fails or claims remain under-evidenced.
- [ ] Save run receipts and validation outputs under `runs/` for replay and audit.

### Phase 6: Scheduling And Recovery

- [ ] Implement `bootstrap`, `refresh`, `daily_summary`, `midday_focus`, `backup`, `restore`, and `recover` modes as separate commands or skill actions.
- [ ] Configure a scheduled refresh cadence and separate lightweight delivery jobs.
- [ ] Ensure delivery jobs operate from existing artifacts and do not trigger unplanned scraping.
- [ ] Add timestamped backups of profile config, vault state, and local memory stores.
- [ ] Test restore and recovery flows before relying on the system operationally.

### Phase 7: Hermes/OpenClaw Integration

- [ ] Register the research loop as a reusable OpenClaw/Hermes skill with mode-specific entrypoints.
- [ ] Wire the Main/Hermes profile to consume operator briefs, dossiers, and handoff queues rather than raw scraped text.
- [ ] Wire Coder, QA, and Content profiles to accept only approved handoff artifacts instead of direct collector output.
- [ ] Add policy checks so no downstream agent treats a weak signal as an approved task without passing verification.

## Recommended First Sprint

A pragmatic first sprint should stop short of full autonomy and instead prove the evidence pipeline end to end.
The best milestone is a working refresh job that collects from three to five trusted source surfaces, writes raw captures, extracts findings, generates a small claim ledger, updates one or two dossiers, and produces an operator brief with at least one handoff lane.
That gives the stack a usable research spine before adding wiki compilation, dashboards, advanced ranking, or a larger collector footprint.

## Success Criteria

The system is working when a refresh produces durable artifacts that are auditable, freshness-aware, and useful to downstream agents without requiring them to parse the outside world from scratch.
The quality bar is not high output volume; it is traceable evidence, explicit uncertainty, and cleaner routing into build, verification, content, and operational decisions.
A successful Hermes/OpenClaw research layer should make future prompts start smarter because the stack inherits structured memory rather than recycled summaries.

