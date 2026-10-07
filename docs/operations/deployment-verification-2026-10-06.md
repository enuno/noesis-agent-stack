# Deployment Verification — noesis-agent-stack

- Date (America/Denver): 2026-10-06
- Operator: Elvis (approvals recorded in-session)
- Branch/SHA: `main` @ `478fd75` (== origin/main; tree clean except untracked `profiles/live/.DS_Store`)
- Host: macOS 27.2, local; Python 3.11.13 via repo-local `uv` venv (`.venv/`); zero live inference spend (offline-only authorization)
- Verdict: **PARTIALLY DEPLOYED**

## Environment / versions

| Item | Observed |
|---|---|
| Hermes runtime | v0.21.5+8076.g85db7c3 at ~/.hermes |
| Repo venv | `.venv/` (uv 0.8.23, CPython 3.11.13) — created this run, approved |
| fastapi / pydantic / pytest | installed in venv only (not system Python) |
| Broker test suite | `pytest orchestration/broker/tests -q` → **28 passed**, 0.10s |
| Orchestrator test suite | `pytest orchestration/orchestrator/tests -q` → **82 passed**, 4.69s |
| Inference-routing validator | `scripts/validate_inference_routing.py` → PASSED gate; drift profile below |
| Honcho profile validator | `scripts/validate-honcho-profiles.py` → `ok: true`, all 16 roster profiles defined repo-side |
| Agency names check | `scripts/check-agency-names.py` → FAIL (missing `~/tools/agency-agents`) |

## Inference-routing reconciliation (repo declaration vs live runtime)

Repo `platform/inference-routing.yaml` validator output: 4 aligned / 13 drift / 1 missing
repo declaration / 4 runtime-not-observed; resolutions: 10 blocked, 12 needs_evidence.
Only `KIMI_CODE` lane is `approved`.

Live `~/.hermes/config.yaml` observed (sanitized):
- `model.default = z-ai/glm-5.2`, `model.provider = nous`
- `fallback_providers = [moa, kimi-coding, openai-codex]`

Conflicts (reported, NOT changed — live config edits are approval-gated):
1. Live default provider `nous` is declared dead in `profiles/noesis-roster.yaml`
   (T12a, 2026-09-16: "nous key dead"); roster migrated core/scribe/grid lanes to kimi.
2. `~/.hermes/profiles/model-profiles.yaml` declares anthropic lanes
   (claude-3-5-haiku, claude-sonnet-4-5, …) with cost guardrails; none of these
   providers appear in live fallback config. `VENICE_PRO`, `XAI_GROK`,
   `CHATGPT_PRO` lanes are `blocked_missing_configuration` per validator.
3. Anthropic lanes in model-profiles.yaml conflict with the repo-approved-lane
   model (only KIMI_CODE approved). Either the live file is stale or the repo
   policy is; operator decision required.

## Broker runtime evidence (live localhost run)

Invocation (per README): `uvicorn app.main:app --host 127.0.0.1 --port 8787`
Run window: 2026-10-06 ~22:47–22:54 MDT. Log: `/tmp/broker-e2e.log`.

| Test | Command (shape) | Result | Status |
|---|---|---|---|
| Health | `GET /v1/health` | `{"status":"ok","workers_healthy":4,"workers_total":4}` | PASS |
| Worker registry | `GET /v1/workers` | 4 workers with read/write scopes enumerated | PASS |
| Valid job submit | `POST /v1/jobs` (research-openclaw, vault-scoped) | HTTP 202, job_id `e14fb662-…` returned | PASS |
| Job status | `GET /v1/jobs/{id}` | 200, state persisted | PASS |
| Idempotency | same `idempotency_key` resubmitted | HTTP 409 `Idempotency key conflict` | PASS |
| Unknown worker | worker=`rogue-agent` | HTTP 400 schema enum rejection | PASS |
| Schema violation | missing required fields | HTTP 400 | PASS |
| Scope violation | write_scope ⊄ read_scope | HTTP 422 `Write scope contains paths not in read scope` | PASS |
| Cancel | `POST /v1/jobs/{id}/cancel` | 200, status=`cancelled`, persisted | PASS |
| Event trail | `GET /v1/jobs/{id}/events` after submit+cancel | **empty array** | GAP |

Broker gaps: (a) submit/cancel produced **no events** in the event stream —
HEARTBEAT.platform.md requires a typed event trail per job; (b) 400 responses
echo the full JSON schema document (verbose error surface, no secrets observed,
but should be trimmed); (c) deprecation warning: FastAPI `regex=` → `pattern=`.

## Orchestrator control-plane evidence (offline, tmp ledger)

Driver: `Orchestrator(tmp/tasks.jsonl)` via app API. All policy refusals raised
`PolicyViolation` as designed.

| Test | Result | Status |
|---|---|---|
| propose → approve → enqueue → claim → start → handoff → succeed | full lifecycle succeeded | PASS |
| Idempotent re-propose (same idempotency_key) | same task_id returned, no duplicate | PASS |
| r3 + `destructive_data_operation`, no approval | `approval_required=True`; claim blocked pre-approval | PASS |
| Unknown irreversible op vocabulary | rejected at task construction (`ValueError`) | PASS |
| Claim by wrong profile (`noesis-scribe` on forge task) | blocked (`claim_by_wrong_profile`) | PASS |
| Capability mismatch (`code_execution` for forge) | blocked at admission (`capability_mismatch`) | PASS |
| Succeed with no handoff | blocked (`handoff_required`) | PASS |
| Handoff missing `verification_result` | blocked (`handoff_incomplete`) | PASS |
| Emergency stop → dispatch | blocked (`dispatch_blocked`) | PASS |
| Ledger replay after restart | task state `succeeded` persisted; 7 ledger events | PASS |
| **E-stop persistence across replay** | **breaker reads `manually_tripped=False` after restart** | **FAIL** |

Orchestrator gaps: (a) **emergency-stop does not survive process restart** —
manual circuit-breaker trip is not written to the append-only ledger, so a
restarted control plane resumes dispatch despite an operator e-stop; (b)
admission validates profiles **only** against `profiles/noesis-roster.yaml` —
the deployed Hermes profile `coder` (in `platform/agent-registry.yaml` and live
at `~/.hermes/profiles/coder`) is rejected as `unknown_profile`, and
`claude-code-worker` is likewise not roster-visible. Cross-registry unification
needed (registry.py is described as roster+agents/*/agent.yaml but behavior
observed is roster-only for admission).

## Bridge contract evidence (offline schema validation)

`contracts/bridge/task.schema.json` + `result.schema.json` exercised with
jsonschema Draft2020-12:
- Valid task/result payloads: both VALID.
- Negatives (missing `type`, `description` minLength, additionalProperties,
  incomplete result): all correctly REJECTED.
- Live bridge execution (real Claude Code worker inbox/outbox): **NOT TESTED** —
  blocked by offline-only authorization (would invoke a paid/lane executor).

## Security / recovery summary

- r3 gating, approval gates, capability/scope enforcement, idempotency: PASS (evidence above).
- Bounded retries + circuit breaker: covered by 82-test suite (`test_timeout_retry_breaker_escalation`).
- Recovery: ledger replay PASS; **breaker state loss on restart = FAIL**.
- Credential handling: no secrets printed during any test; validators are
  repo-local by design. Live credential verification: NOT TESTED (blocked).
- Worker restart durable-state test: NOT TESTED beyond ledger replay (no live workers authorized).

## Documentation drift (report, do not silently fix)

1. `README.md` "Status" and `TODO.md` Phase 2–6 marked NOT STARTED, but
   `platform/orchestrator.yaml`, `platform/routing.yaml`, `platform/workflows/`,
   orchestrator control plane, and CI workflow `.github/workflows/inference-routing-policy.yml`
   all exist and post-date the docs. TODO/README are stale.
2. `EVALS.platform.yaml` BROKER-001 expects `"state": "queued"`; broker returns
   `"status": "pending"` for a submitted job. Field name/state vocabulary mismatch.
3. `ROUTING-SMOKE.md`: 0/18 rows recorded — no routing smoke evidence exists.

## Approvals obtained

1. Full mission Phases B+C — approved.
2. Repo-local uv venv + dependency install — approved.
3. Live inference spend: **offline-only** — live agent tests (routing smoke,
   bridge execution, live broker worker run) remain BLOCKED.

## Rollback / emergency-stop

- Broker test instance: `kill <uvicorn pid>` (already stopped; no persistent state — in-memory store).
- Venv: `rm -rf /Users/elvis/projects/noesis-agent-stack/.venv` (reproducible via `uv venv .venv && uv pip install -r …/requirements.txt`).
- Orchestrator test ledgers: temp dirs under `$TMPDIR/orch-e2e-*`, disposable.
- Live host changes: **none made**. `~/.hermes` untouched. Git: no commits, no pushes.
- Emergency stop for the orchestrator control plane (when deployed):
  `Orchestrator.emergency_stop(operator=…, reason=…)` — note the persistence
  gap above; verify breaker state after any restart.

## Exact next actions (operator decisions required)

1. Decide live default model/provider: keep nous `z-ai/glm-5.2` (contradicts
   roster T12a) or cut over to kimi per repo-approved lane. Then re-run
   `validate_inference_routing.py` and reconcile `model-profiles.yaml`.
2. Decide whether `coder` + `claude-code-worker` enter the noesis roster or the
   orchestrator admits from `platform/agent-registry.yaml` as well.
3. Approve a fix change-set for: broker event trail on submit/cancel/transition;
   e-stop persistence in orchestrator ledger; error-response trimming.
4. Approve an inference spend cap to unblock: ROUTING-SMOKE 18 rows, bridge
   live run, broker live worker execution.
5. Restore `~/tools/agency-agents` checkout or re-scope `check-agency-names.py`.
6. Update README/TODO status sections to match implemented Phases 1–2 + platform configs.

---

# Remediation Pass — 2026-10-06/07 (America/Denver)

Authorization received: repository remediation + live Noesis host deployment.
Explicitly still blocked: paid inference calls, remote hosts, public exposure,
git commits/pushes. Baseline re-verified: `main` @ `478fd75` (unchanged), zero
tracked modifications at start; untracked = this report + `profiles/live/.DS_Store`.

## Baseline reconciliation corrections

- Roster actually defines **17** profiles (header claims 16): wave 1 = 7
  (core→default, steward, cartographer, forge, sentinel, scribe, signal),
  wave 2 = 5 (substrate, tracer, ledger, grid, quill), wave 3 = 5
  (orchestrator, advocate, herald, architect, skeptic). Earlier "8 applied /
  9 staged" conflated identities: applied = 7 roster identities (6 dirs +
  default-as-core) **plus** the non-roster `coder` profile = 8 profile dirs.
- `~/.hermes/profiles/noesis-orchestrator` does **not** exist (wave 3, correctly
  unapplied). Honcho validator covers 16 of 17 (orchestrator has no honcho
  profile definition; validator still reports ok — its expected set is derived
  from `honcho/profiles/`, not the roster; recorded as a coverage note, not a pass).
- "Clean tree" vs report: report was untracked (never committed); no tracked
  file was modified in the previous pass.

## Defect 1 — Emergency stop lost on restart (Priority 0)

| Field | Value |
|---|---|
| Original finding | Orchestrator breaker trip held in memory only; restart silently reopened dispatch |
| Reproduction | `emergency_stop()` → new `Orchestrator(ledger)` → `manually_tripped=False` (observed previous pass) |
| Root cause | `emergency_stop`/`resume` never wrote to the append-only ledger; startup never reconstructed breaker state |
| Changed files | `orchestration/orchestrator/app/store.py` (durable control events, fail-closed replay, `replay_error`), `orchestration/orchestrator/app/control_plane.py` (`_restore_breaker_state`, durable stop/resume, operator-identity requirement), `orchestration/orchestrator/tests/test_breaker_persistence.py` (new, 8 tests) |
| Regression tests | 8/8 pass: stop→restart blocked; stop→resume→restart dispatch works; last-event-wins; malformed ledger fails closed; stop write-failure raises AND fails closed; operator identity required; running work completes after stop while new dispatch blocked |
| Runtime evidence | 101/101 orchestrator tests; ledger replay verified with breaker events interleaved with task records |
| Remaining limitations | Consecutive-failure counter still not persisted (only manual stop/resume); acceptable per lease semantics |
| Status | **FIXED** |

Stop semantics (documented in code): stop blocks NEW dispatch (`claim`);
`enqueue` remains allowed (queueing is planning); already-running work is left
to its lease and completes normally.

## Defect 2 — Registry admission rejected deployed lanes

| Field | Value |
|---|---|
| Original finding | `coder` (and bridge worker) rejected as `unknown_profile`; admission read only the roster |
| Root cause | Single-source registry; no lane concept from `platform/agent-registry.yaml` |
| Changed files | `orchestration/orchestrator/app/registry.py` (roster+lane merge, alias resolution, fail-closed conflict detection, activation states), `orchestration/orchestrator/app/policy.py` (`lane_not_activated` gate; updated `unknown_profile` message), `platform/agent-registry.yaml` (`orchestration_lanes` allowlist, `aliases`, `claude-code-worker` entry), `orchestration/orchestrator/tests/test_registry_admission.py` (new, 11 tests) |
| Regression tests | 11/11 pass: coder/bridge admitted with declared capabilities; wrong capability rejected; registered-but-not-allowlisted → unknown; disabled lane → not activated; alias resolution; alias shadowing/unknown target → load fails closed; roster-lane name collision fails closed; supervisor-role lane cannot execute; real repo config admits both lanes |
| Runtime evidence | Real-repo-config test drives propose→approve→enqueue→claim for `coder`; 101/101 suite |
| Remaining limitations | Roster staged (wave 2/3) profiles remain admissible by design (tests exercise them); wave gating enforced at profile-application time, not admission |
| Status | **FIXED** |

## Defect 3 — Broker event stream empty

| Field | Value |
|---|---|
| Original finding | `GET /v1/jobs/{id}/events` returned `[]` after submit and cancel |
| Root cause | `main.py` never called `store.append_event`; additionally the `Event` model did not conform to `events.schema.json` (had `message`/`metadata`, lacked required `type`/`payload`) |
| Changed files | `orchestration/broker/app/models.py` (Event conformed to contract), `orchestration/broker/app/main.py` (`_emit` with contract validation + `exclude_none`; events on submitted/cancelling/cancelled/completed/failed; structured errors; bounded rejection audit + `GET /v1/audit/rejections`; FastAPI `regex`→`pattern`), `orchestration/broker/app/store.py` (rejection audit), `orchestration/broker/tests/test_events.py` (new, 8 tests), `orchestration/broker/tests/test_broker.py` (event assertion updated from the defective empty-stream expectation) |
| Regression tests | 35/35 broker tests; events conform to `events.schema.json` (validated in-test); rejection audit sanitized; duplicate submission creates no phantom job or events |
| Runtime evidence | Live localhost run 2026-10-07T00:16Z: ordered stream `broker.job.submitted → cancelling → cancelled` with correlation IDs; 409 duplicate; structured 400 `{"code":"schema_validation_failed",...}`; audit recorded `idempotency_key_conflict` |
| Remaining limitations | **Durability: events are in-memory, per-process.** Stated in code and report — not restart-durable. Durable records remain palace receipts + supervisor ledgers |
| Status | **FIXED** (with honestly-stated durability guarantee) |

## Defect 4 — Verbose 400 responses

| Field | Value |
|---|---|
| Original finding | 400 responses embedded the full JSON Schema document |
| Root cause | Raw exception string passed as `detail` |
| Changed files | `orchestration/broker/app/main.py` (structured `{code, message, correlation_id}`; schema dumps, stack traces, and raw payloads excluded) |
| Runtime evidence | HTTP check: `{"detail":{"code":"schema_validation_failed","message":"job payload failed schema validation: ValidationError","correlation_id":null}}` |
| Status | **FIXED** |

## Defect 5 — EVALS BROKER-001 contract drift

| Field | Value |
|---|---|
| Original finding | Eval expected `state: queued`; broker returns `status: pending` |
| Root cause trace | Authoritative `contracts/broker-api/job.schema.json` defines `status` (enum includes `pending`), no `state` field → implementation contract-conformant; eval text stale. No consumers of the eval text found |
| Changed files | `EVALS.platform.yaml` (BROKER-001 criterion corrected with rationale) |
| Compatibility impact | None — no automated consumers; contract unchanged |
| Status | **FIXED** (eval aligned to contract, not vice versa) |

## Defect 6 — Live config drift + conflated validation layers

| Field | Value |
|---|---|
| Original finding | Validator PASSED while live default ran dead nous route |
| Root cause | `validate_inference_routing.py` is repo-local by design; nothing checked live compliance |
| Changed files | `scripts/verify_live_config.py` (NEW, read-only, sanitized; separates repo-policy / live-compliance / credential-presence / inference-execution layers) |
| Live changes applied | `~/.hermes/config.yaml`: `model.default/provider` → `kimi-k2.7-code`/`kimi-coding` via `hermes config set` (platform-enforced path; direct file edit refused by tool guardrail — correct behavior). `~/.hermes/profiles/noesis-scribe/config.yaml`: `deepseek/deepseek-v4-flash`@nous → `kimi-k2.7-code`@kimi-coding per roster T12a. Backups: `~/.hermes/backups/deployment-20261006-2355/` (mode 700) |
| Verification | `verify_live_config.py` → **PASS** (default route approved + credentialed); `nous` credential pool count = 0 with recorded `last_auth_error` — dead-key claim corroborated |
| Remaining limitations | Per-profile drift surfaced for operator decision: `coder` (anthropic claude-sonnet-5), `live` (nous solar-pro4:free), `noesis-cartographer/sentinel/signal` (openrouter claude-sonnet-5) — anthropic/openrouter lanes explicitly left unresolved pending approval |
| Status | **FIXED** (default route); profile-level lanes pending approval |

## Defect 7 — Missing agency-agents checkout

| Field | Value |
|---|---|
| Original finding | `check-agency-names.py` FAIL: `~/tools/agency-agents` absent |
| Verification of intent | `agency/SOURCE` + `agency/ATTRIBUTION.md`: upstream `https://github.com/msitarzewski/agency-agents`, pinned commit `ad9264e309bd5e5422c04784372d7841b1e5d604` |
| Change applied | Restored checkout at `~/tools/agency-agents`, exact pinned commit (detached HEAD) |
| Verification | `check-agency-names.py` → **OK** |
| Status | **FIXED** |

## Documentation drift

- `README.md` Status: rewritten to distinguish implemented+offline-verified /
  deployed / inference-verified-live / staged (was: "specification and scaffold
  phase").
- `TODO.md` header: status banner added noting phase checklists lag the
  implementation; Phases 3–7 remain scaffolded.

## Post-remediation verification sweep (2026-10-07T00:10–00:18Z)

| Check | Result |
|---|---|
| `pytest orchestration/broker/tests` | 35 passed |
| `pytest orchestration/orchestrator/tests` | 101 passed |
| `scripts/validate_inference_routing.py` | PASSED (repo-policy layer) |
| `scripts/validate-honcho-profiles.py` | ok: true (16 profiles defined) |
| `scripts/check-agency-names.py` | OK (pinned upstream restored) |
| `scripts/verify_live_config.py` | PASS (live-compliance layer) |
| Broker live HTTP (loopback) | submit 202 + event, 409 dup, cancel 200 + 2 events, structured 400, audit trail |
| Broker/orchestrator processes left running | none (test instances stopped) |

## Evidence classification

- **OFFLINE evidence:** all pytest suites, validators, schema validations.
- **Non-billable live host evidence:** loopback broker HTTP run; live config
  reads; `hermes config` writes; agency checkout restore.
- **Inference-tested evidence:** NONE — remains blocked on budget approval.
  No ROUTING-SMOKE rows recorded; no live bridge/worker execution.
