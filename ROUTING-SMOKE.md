# ROUTING-SMOKE.md — Tier A routing smoke test record

> **Purpose**: before expanding Tier A past 1 profile per division, run one
> representative query per division through the lazy router and record which
> profile won. This file is the committed evidence (C3 / Operating rule 1).
>
> **How to run**: with the Tier A fleet live (at minimum wave 1 applied),
> issue each query in a fresh `hermes` session against the router-enabled
> profile and record the winning profile. All 18 rows must have a winner
> before any expansion past 1/division.
>
> **Pass criteria**: (a) every row has a winner; (b) winners are Tier A
> profiles for ≥16/18 divisions; (c) validator description-uniqueness cosine
> < 0.85 at run time; (d) no live profile outside the declared rosters wins.

Date: ____-____-____   Operator: ____________   Fleet: wave __ + noesis
Router plugin: integrations/hermes-plugin (sha256 recorded in apply audit)

| # | Division | Representative query | Winner profile | Notes |
|---|----------|----------------------|----------------|-------|
| 1 | engineering | "Design the module boundaries for a sync engine with offline conflict resolution" | | |
| 2 | research | "Synthesize the last 3 years of CRDT vs OT literature into a decision matrix" | | |
| 3 | security | "Threat-model a public upload endpoint that serves files back to other users" | | |
| 4 | product | "Prioritize the Q3 roadmap for a 2-person team with 400 active users" | | |
| 5 | finance | "Build a rolling 13-week cash forecast from our Stripe + payroll exports" | | |
| 6 | project-management | "Plan the migration of 12 cron jobs into the orchestrator without missing a beat" | | |
| 7 | sales | "Draft the outreach sequence for infra teams at Series A devtool startups" | | |
| 8 | marketing | "Audit our blog for the queries an AI search engine would cite us for" | | |
| 9 | academic | "Check this ANOVA setup for the reviewer-facing methods section" | | |
| 10 | design | "Final-pass review of this settings screen before it ships" | | |
| 11 | game-development | "Balance the economy loop for a 20-minute roguelite run" | | |
| 12 | gis | "Pick a tiling scheme for serving cadastral parcels at city scale" | | |
| 13 | healthcare | "Grade the evidence quality behind this supplement-dosing claim" | | |
| 14 | paid-media | "Audit this ad account for wasted spend and creative fatigue" | | |
| 15 | spatial-computing | "Design the interaction model for a wrist-mounted AR settings panel" | | |
| 16 | specialized | "Map this legacy repo's undocumented module graph before we touch it" | | |
| 17 | support | "Write the runbook for the on-call rotation covering these three alerts" | | |
| 18 | testing | "List the assumptions in this test plan that reality will violate first" | | |

## Outcome

- Rows recorded: ____ / 18
- Tier A winners: ____ / 18
- Cosine guard: ______ (< 0.85 required)
- Verdict: GO / NO-GO   Signature: ____________

**NO-GO →** do not expand past 1/division; file an issue with the losing
rows and revisit after router/plugin adjustments (re-run
`convert.py --full-tree` + `validate-specs.py` before retrying).
