---
name: noesis-runtime-qualification
description: Use when qualifying Noesis runtime on a pinned Linux target.
version: 1.0.0
author: noesis-orchestrator
license: Proprietary
metadata:
  hermes:
    tags: [noesis, qualification, linux, runtime]
    related_skills: [noesis-candidate-freeze, noesis-task-delegation]
---

# Noesis runtime qualification

Bounded, non-provider qualification of Noesis agent-stack components on a
named remote Linux target: disposable container, pinned runtime replicated
faithfully from CI, case harness against real launcher primitives, sanitized
evidence receipt, rollback-by-disposal.

## When to Use

Use when an operator authorization asks to qualify, requalify, or verify
Noesis runtime behavior (test suite, process control, attempt fencing,
launcher semantics) on a named Linux host or pinned revision — including
T11-style process-control packages and post-change spot requalification.
Do not use for live provider work (the canary path) or macOS-only
validation.

Recipes: `references/qualification-recipes.md`.

## Always-on rules

- Qualify inside a disposable container on a shared host. Do not install
  the pin on the host. Rollback is container removal plus the host temp
  files you created. A non-reaping container PID 1 does not establish
  systemd, bare-metal, or production PID-1 behavior.
- Replicate the CI hermetic HOME before calling a suite failure a runtime
  defect. An empty default HOME produces `profile_not_installed` /
  `no_eligible_specialist` on CLI and plugin-host tests. Preserve that run;
  the hermetic rerun is the valid baseline.
- Match the CI Python pin (`uv venv --python <ci-version>`). A newer system
  Python fails `pip check` because dependency pins are version-gated.
  Invoke `hermes` by the venv absolute path inside the container; the
  harness process does not inherit the venv on `PATH`.
- An unconfirmed process-group signal is not proof the child is still
  running and is never permission to retry or duplicate execution. On Linux
  `killpg(pgid, 0)` succeeds against zombies until the caller reaps, so a
  False confirmation during the grace window includes an already-dead group.
  Classify callers before calling the observation harmless: every consumer
  must treat False as uncertain (quarantine, close the attempt, no retry).
- Read the implementation constant before asserting a grace duration. If
  the package document and the code disagree, classify drafting error versus
  requirement versus defect before changing either side. Do not change
  runtime behavior to match a draft number, and do not rewrite the
  measurement.
- A CI pin does not inherit qualification of a different pin. A later
  source revision is behavior-compatible only after the diff is inspected.
  Docs and docstring only is not a new qualification. If a contract and a
  preflight allowlist disagree on which revisions are accepted, fix the
  contract to name the inspected exception. Do not invent a monetary or
  policy gate to paper over the disagreement.
- Scan retained artifacts with the agent-stack scanner
  (`agency.secretscan.scan_file`). The pinned runtime package may not export
  a scanner; an import failure there is not a clean scan.