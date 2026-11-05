# Operator-mediated launch, static readiness, and route verification

Depth for the case where the reviewer session is launched outside the
orchestrator's own delegation lifecycle — an operator-mediated qualification
round, or any launch where the orchestrator must not mutate shared state to
make the launch possible.

Companion to `references/formal-qualification-rounds.md` (the lifecycle) and
`references/bounded-session-launch.md` (the ordinary in-fleet invocation).

---

## 1. Launch shape

The governing form for a bounded reviewer session: explicit route pin, no
inline prompt, bounded turns, narrow tool scope, and a machine-readable
session log.

```
cd <disposable scratch dir>
HERMES_STREAM_RETRIES=0 \
hermes -p <reviewer-profile> \
  --provider <authorized-lane> --model <authorized-model> \
  --ignore-user-config \
  --max-turns 300 \
  -t file,terminal \
  chat --query-file <contract-or-prompt.md> \
  --format stream-json
```

| element | why |
|---|---|
| `--provider` + `--model` | the explicit route. CLI route flags beat the profile's `model:` section, so the profile's default model does not leak into the launch. Preserve model identifiers literally — a normalised or substituted id is an undeclared route change |
| `--ignore-user-config` | keeps the profile's config layer out of the launch without editing the profile file. It does NOT by itself prove the profile's fallback chain is inert — verify the route afterwards (§3) |
| `--query-file` | the contract is too long and too structured for a `-q` argument; rich-markup-shaped tokens and `${{ }}` expressions crash or expand in the shell. Never inline it |
| `--max-turns` | bounds tool-calling iterations. It does NOT bound wall clock — say so in the route amendment rather than implying a bound that does not exist |
| `-t file,terminal` | the narrow tool scope. The reviewer can still write via the terminal, so the control is verification, not the scope list |
| `--format stream-json` | the session log carries the init event, which is where the route is positively confirmed |
| `HERMES_STREAM_RETRIES=0` | the one retry mechanism with a supported per-invocation switch that touches no file |
| cwd = scratch | the reviewer starts outside the candidate worktree |

A monitor that supervises the session must not be the code under review.
Review the candidate with the fleet's existing supervisor; do not install or
activate the candidate's own launcher to police its own review.

---

## 2. Static route readiness — costs no inference call

Use these before launching when the envelope does not budget a probe
inference call. A launch that dies pre-delivery costs nothing and is itself
the decisive readiness test.

1. **The named profile's source manifest re-hashes to the packet's expected
   values** — `SOUL.md`, `config.yaml`, `honcho.json`. A changed manifest
   means the profile is not the one the packet describes; stop.
2. **The provider appears in the global auth store's provider and
   credential-pool lists** — `hermes auth list` prints credential labels,
   priority and exhaustion/cooldown state without secret values. A provider
   can resolve globally even when the profile's own auth file lacks it, so
   absence at profile level is not refusal evidence; presence at both is.
3. **The model appears in the runtime model cache for that provider.**

If the lane died on an entitlement or quota block, read the provider's own
refusal fields (`plan_type`, `limit_window_minutes`, `resets_at`) and read
the child's captured error text. Static receipt fields describe contract
shape, not live provider state.

---

## 3. Positive route verification

Excluding forbidden providers proves nothing: it cannot distinguish "on the
authorized lane" from "on some lane you did not think to forbid". Verify the
route positively.

### The alias → billing identity mapping

The runtime records a provider alias and a billing identity that may differ
from the configured provider string. Learn the mapping from prior REAL
sessions on that lane:

```
configured provider        openai-codex
recorded billing_provider  openai-codex
recorded billing_base_url  https://chatgpt.com/backend-api/codex/
recorded billing_mode      subscription_included
recorded session model     gpt-5.6-sol
```

Where to read each field:

- session row: `sessions.model`
- usage rows: `session_model_usage.billing_provider`,
  `.billing_base_url`, `.billing_mode`, and `.model`
- the conversation row is the one with `task = ''`; auxiliary rows
  (`title_generation`, `compression`) carry the same provider and model and
  are checked for consistency but are not the route

### The checklist

| # | check | source | block condition |
|---|---|---|---|
| 1 | the init event's `"model"` names the authorized model | the stream-json session log | any other model |
| 2 | the session row's model | the profile's `state.db` | any other value |
| 3 | every `task=''` usage row carries the expected `billing_provider` | `session_model_usage` | any other provider — that is a substitution |
| 4 | every such row carries the expected `billing_base_url` | same | any other base URL |
| 5 | every such row carries the expected `billing_mode` | same | any other mode |
| 6 | no provider-fallback notice appears in the session log | the stream-json log | its presence names the substituted route |
| 7 | PID, session id and the first observed tool calls are recorded | launch evidence | not recorded → the launch evidence is incomplete |

Unknown, missing, or unmapped identity **blocks** the round. It is never
"probably fine".

### The trap this replaces

A provider-level refusal may leave zero usage rows. Absence of usage rows is
then not evidence of zero provider requests — the requests were made and
refused — and not proof of zero cost. State the refusal, the request count
the client reported, and that no cost is established either way.

---

## 4. Scheduling a single-fire attempt

Use the platform's own scheduler. Do not build one.

```
hermes -p <orchestrator-profile> cron create \
  --name "<descriptive-name>" \
  --repeat 1 \
  --no-agent \
  --script <script-filename.py> \
  --deliver local --failure-deliver local \
  "<ISO-8601 timestamp with an explicit UTC offset>"
```

- An ISO timestamp with an explicit offset parses to a **one-shot**
  schedule; a bare cron expression would recur. Verify the stored record's
  `schedule.kind` is `once` and `repeat.times` is `1`.
- `--no-agent` makes the script the job — no model takes any decision in it.
- The script path is resolved **relative to the profile's own `scripts/`
  directory**. An absolute path or a `~/.hermes/scripts/` path is refused;
  pass the bare filename.
- The timestamp's offset pins the instant. A naive timestamp is read in the
  configured Hermes zone and lands at the wrong hour.

### Disabling it and proving it cannot fire

`hermes cron pause <job-id>` is the supported verb. It sets `enabled: false`,
`state: "paused"` and `paused_at`; it preserves the record. There is no
`--reason` flag on `pause` and no `--paused` flag on `cron edit` — record the
reason in the ledger instead.

Prove it cannot fire by reading the gates, not by trusting the label:

- the due scan skips `not job.get("enabled", True)` and skips jobs carrying a
  pause marker;
- the claim path refuses a job that is not runnable, and its docstring states
  that external callbacks must not force, so a stale callback cannot
  resurrect a paused job;
- the operator-facing state is derived from the same `enabled` flag, so a
  job cannot display as paused while still firing.

The only override is an explicit force fire, which is an operator-initiated
action.

Before disabling, record whether execution started: `last_run_at`,
`last_status`, `repeat.completed`, and whether the run history contains a row
for that job id. If it never started, no cancellation was needed — do not
describe a disabled job as "cancelled", because cancellation requested is
not execution stopped.

---

## 5. Monitoring and accounting pitfalls

A supervisor's own exit code is not the worker's outcome, and the numbers it
reports at kill time are lower bounds.

- **Capture the at-termination snapshot BEFORE joining the child's stdout
  pipe.** The join blocks while a worker that outlived the child still holds
  the pipe open, so a snapshot taken after the join misreads late writes as
  pre-existing: late artifacts go unrecorded and late accounting is reported
  as settled.
- **Evaluate a ceiling against the LARGER of the runtime counter and the
  log-scraped counter.** Either can lead — the runtime row can lag a live
  stream — and using the smaller can miss a real breach. The larger value
  can only stop the supervisor earlier, never later. It is conservative, and
  it is not a complete aggregate; do not present it as one.
- **A kill-time token figure is a lower bound.** In-flight requests finish
  after the kill and are billed, and the accounting settles later. Never
  promise a hard ceiling from a delayed local counter.
- **Process-group termination is best-effort cancellation, not proof of
  global quiescence.** A worker in its own session survives it and keeps
  writing.
- **A late artifact is valid evidence but does not erase a limit breach**,
  and does not prove that execution stopped when the supervisor exited.
- **A quiet interval is not settlement.** Where reliable confirmation is
  unavailable, report the accounting as unresolved rather than assuming it
  settled.

---

## 6. Ledger discipline

The ledger is append-only. When a recorded number turns out to be wrong —
a miscounted run, an over-claimed figure — **append a correction row that
names the row it corrects**, and restore the corrected row's original
wording. Do not edit the earlier row in place, and do not leave a silently
amended entry whose correction history only exists in chat.

A historical failure of earlier code and a later passing candidate are not
contradictory. The failure describes the earlier state and is preserved as
evidence of it; the correction row carries the accurate number.
