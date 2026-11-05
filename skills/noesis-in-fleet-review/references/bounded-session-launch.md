# Bounded session launch recipe

The exact `hermes chat` invocation that worked for in-fleet Sentinel,
Skeptic, and bounded Forge (implementer) sessions. All of them are
one-shot child sessions isolated to the worktree, on a single
authorized provider/model lane, with the same `--ignore-user-config`
flag to prevent inherited profile-side fallback chains.

## The canonical command shape

```bash
hermes -p <profile> chat \
  --query-file <contract.md> \
  --oneshot \
  --provider <authorized-lane> \
  -m <authorized-model> \
  -t file,terminal \
  --ignore-user-config \
  --in <worktree> \
  --max-turns <turns> \
  --format stream-json \
  --reasoning <level>
```

Note: `--run-budget <seconds>` is NOT in the canonical shape — the
installed gateway CLI rejects the flag, so a wall-clock cap cannot be
flag-enforced on this runtime. Bound the session with `--max-turns`,
tool scope, and external supervision (background process + exit
notification + operator-visible session log), and record the disclosure
in the route amendment. Never describe such a session as time-bounded
or unattended.

## Per-argument notes

- `--query-file <contract.md>`: NEVER use `-q '<long prompt>'` for
  the review contract. The contract is multi-page and contains
  shell-meta characters (`{`, `}`, `(`, `)`, `<`, `>`, `|`,
  backticks, dollar signs) that the CLI parses before passing to
  the model. Even with careful quoting, long contracts lose
  formatting, and unquoted tokens crash the CLI before the model is
  invoked. Write the contract to a file and pass it via
  `--query-file`. The file path must be absolute; relative paths
  resolve against the cwd at run time, which differs from the
  worktree cwd.

- `--oneshot`: required. Without it, `chat` opens an interactive
  REPL that waits for stdin. The bounded review/implementer session
  is a single-shot read-run-write-exit.

- `--provider <lane>`: the *exact* provider identifier the
  implementer used, or the operator's explicit authorization for
  reviewers. Do not let the reviewer's profile-side default lane
  take over. A reviewer on a different lane than the implementer is
  an undeclared configuration change.

- `-m <model>`: the *exact* model identifier matching `--provider`.
  `claude-sonnet-5` and `MiniMax-M3` are model identifiers, not
  family names. Do not pass `sonnet` or `minimax`.

- `-t file,terminal`: minimum tool scope for a reviewer. `web`,
  `delegation`, and `cron` are unnecessary and broaden the attack
  surface. For an implementer you may add `web` if the contract
  requires fetching external docs.

- `--ignore-user-config`: drops the profile-side
  `config.yaml` inheritance (including the configured fallback
  chain). This is what makes the bounded session actually bounded:
  the implementer or reviewer cannot silently fall through to a
  different model when the requested one is rate-limited. Without
  it, a slow or failed primary causes the runtime to retry on
  fallback routes, which is exactly the undeclared configuration
  change the bounded contract is meant to forbid.

- `--in <worktree>`: changes the session's cwd before launch. All
  relative paths the agent sees are inside the worktree. This is
  what makes the worktree isolation real. Without it, the session
  inherits the operator's `$HOME` and `HERMES_HOME` and may touch
  files outside the worktree.

- `--run-budget <seconds>`: OPTIONAL wall-clock cap — supported only
  on runtimes whose gateway accepts the flag. The installed gateway
  CLI rejects it, so on this fleet the effective bounds are
  `--max-turns`, tool scope, and external supervision. Record the
  absence of a wall-clock bound in the route amendment ("wall-clock
  control not enforceable via supported flags; bounded by --max-turns
  plus supervision; not time-bounded or unattended") rather than
  implying a bound that does not exist. Do not under-budget where the
  flag IS supported; running out of budget mid-test leaves the
  worktree half-edited and verdict files unwritten.

- `--max-turns <turns>`: turn cap. For a reviewer, 300 turns is
  plenty (the reviewer does not write code, only reads and runs
  tests). For an implementer, 500 turns.

- `--format stream-json`: machine-parseable, line-delimited JSON
  events. Required when the bounded session is run as a background
  process and the orchestrator (or a follow-up reviewer) needs to
  consume the event stream. The default text format is harder to
  parse.

- `--reasoning <level>`: `high` for both implementer and reviewer.
  These tasks need the model to think about edge cases and
  cross-file effects; `low` or `medium` produces shallow verdicts
  that miss the kind of subtle bug Skeptic is meant to catch.

## Background-process parameters

When run as a background process via `terminal(background=true,
...)`, the following parameters matter:

- `notify=true`: receive one terminal notification when the
  process completes (or one mid-run heartbeat if a regex pattern
  is configured). The notification is what wakes the orchestrator
  up from a heartbeat wait, so do not skip it.

- `heartbeat=<seconds>`: minimum 60 (the runtime rejects below).
  For Sentinel/Skeptic 300 s is fine (5 min). For a bounded
  implementer 600 s (10 min). Heartbeat is rate-limited; setting
  it too low triggers "quiet ticks are skipped" warnings.

- `persist_on_release=true`: keeps the session across context
  compaction, `/new`, and other lifecycle events. Without it, the
  session dies and the verdict/implementer-result files are not
  written. This is the difference between "the bounded session
  existed" and "the bounded session produced its artifact".

- `pty=false`: do not allocate a pseudo-terminal. The bounded
  session does not need a TUI; PTY allocation just adds startup
  latency.

- `timeout=<seconds>`: the foreground call's own timeout, separate
  from `--run-budget` (which this runtime rejects). Set it generously
  above the expected session duration — reviewer sessions can run for
  hours under `--max-turns 300`, so use a background tracked process
  with exit notification rather than a tight foreground timeout; a
  foreground timeout that kills the session mid-verdict is not
  evidence about the review, and a killed reviewer writes no verdict.

## What to do with the output

The bounded session's stdout is line-delimited JSON when
`--format stream-json` is set. Each event has
`{type, name, input/output, duration_ms, timestamp}` plus a
final `result` event with `{session_id, exit_code, text}`. The
final `result.text` is a short summary; the actual artifacts
(verdict file, implementer result) are written to disk by the
session itself. Do not rely on the stdout to extract the verdict:
read the verdict file from disk and validate its schema
yourself (the skill's `noesis-in-fleet-review` step 5 covers
that).

## Selecting the contract file and naming the log in the launcher

When the freeze tool versions the review CONTRACT filename by candidate
identity (recommended — see `references/verdict-schema-and-digest-recipe.md`),
the launcher must resolve `--query-file` dynamically instead of naming one
file. Glob by the reviewer prefix and take the newest by mtime, and fail
loudly when the glob is empty or ambiguous:

```bash
CONTRACT="$(ls -t "$ART"/contracts/GOVERNED-ROUTING-${UPPER}-REVIEW-CONTRACT-*.md 2>/dev/null | sed -n '1p')"
[ -n "$CONTRACT" ] || { echo "no review contract for $PROFILE" >&2; exit 5; }
```

Use `sed -n '1p'` rather than `head -1` under `set -o pipefail`: `head`
closing the pipe early can make the upstream command fail with SIGPIPE and
turn a successful selection into a non-zero script exit.

Name the log per lane, not per reviewer: `review-<profile>-<provider>.log`.
A single per-reviewer log accumulates every attempt, so a later failed
dispatch is indistinguishable from an earlier delivered one — and a reader
who counts tool calls across the file attributes one attempt's calls to
another. Segment a shared log by `session_id` before counting; a failed
attempt's zero tool calls are the proof that nothing partial happened.

## Enforcing per-session ceilings externally

An envelope that authorises hard per-session ceilings — total tokens, tool
calls, wall clock — is not satisfied by recording the limits. A ceiling you
cannot enforce is an aspiration. `--run-budget` is rejected by the installed
gateway CLI, and `--max-turns` bounds API-call ITERATIONS, not tool calls and
not tokens. Enforce all three from a supervisor-side watchdog that wraps the
launch and kills the process group on breach.

### What the watchdog reads

  total tokens   the profile's `state.db`, table `session_model_usage`,
                 PRIMARY-task rows only (`task = ''`), summed as
                 `input_tokens + output_tokens + cache_read_tokens +
                 cache_write_tokens`. Cached tokens count toward the ceiling.
                 The CLI's reported `total` is `input + output` where
                 `input` already contains the cached portion, so sum the four
                 columns yourself rather than trusting one "total" field.
  tool calls     the live stream-json log, counting `"type": "tool_use"`
                 records. This is the HIGHER of the two available measures —
                 `state.db` reported 81 tool calls against 113 log records
                 for the same session — so it binds conservatively.
  wall clock     the watchdog's own deadline.

**Scope the token sum by the SAME model predicate that selects the
session.** Selecting the session by model but summing every model's rows
charges a second model's usage to your ceiling. A row for a different model
must be excluded by the query, not by a later subtraction.

### Prove the watchdog before dispatching with it

A watchdog shipped unproven is an assumption whose failure mode is a silent
overrun. Prove it against a synthetic database before the first real launch:

  - a cap the synthetic usage must breach — it must fire mid-run;
  - a cap the same usage must not breach — it must not fire;
  - a row for a DIFFERENT model — it must not be counted.

Re-read the live profile `state.db` read-only; never write to it.

### Kill semantics

SIGTERM to the process group, then SIGKILL after a short grace. The watchdog
never raises a ceiling, never extends a session, and never starts a
replacement. A breach is a reported fact, not something to negotiate around.

### A monitored ceiling is a threshold, not a hard limit

Say which of the four layers a ceiling actually is, because they carry
different guarantees and only one of them is a real maximum.

  provider/runtime-enforced maximum   the upstream refuses past the number,
                                     so the session cannot exceed it.
  locally monitored limit            a supervisor observes usage and kills
                                     the process group after crossing it.
                                     The ceiling is DETECTED, not PREVENTED.
  delayed or post-session reporting  the true total is not knowable at kill
                                     time; the accounting settles later.
  outstanding requests after cancel  requests already accepted by the
                                     provider finish and are billed after the
                                     process is gone.

A ceiling enforced only by monitoring is breached BY THE MONITOR. Expect the
measured total to exceed the nominal one, and never report a threshold as a
hard limit.

Why the overshoot is structural, not a tuning failure:

  - **Detection happens after the crossing.** The supervisor polls, so it
    observes the threshold already exceeded. The figure it reports at the
    moment of the kill is a LOWER BOUND.
  - **Usage accrues per API call, and cache reads dominate.** A long session
    can spend most of its budget on cached context re-reads, and one API
    call between two polls can carry a large increment. A short poll
    interval cannot land on the ceiling.
  - **In-flight requests finish after the kill.** The gateway completes and
    records the requests that were already in flight, and keeps updating the
    usage rows for minutes after the process group is gone. A session killed
    mid-flight can still add a large fraction of its budget afterwards.
  - **A signal cannot un-spend tokens.** SIGKILL stops new work; it does not
    refund tokens the provider already accepted, nor erase rows already
    written.

So: read the TRUE total from the usage table AFTER the session settles,
not the supervisor's reading at kill time, and report both when they
differ. Quote the ceiling, the value observed at termination, the final
recorded value, and the gap. An envelope that promised a hard ceiling and
was served by monitoring alone has been breached, and the report says so
with the overshoot measured.

### Token usage is not financial cost

Keep them apart in every report. The usage table records a cost status
per provider, and the two common states are: a metered lane whose actual
cost is unknown or unset, and a subscription lane whose usage is
`included` and carries no per-session dollar figure. In both cases the
recorded dollar amount is zero or absent while the tokens are large.

Report the token totals, the ceiling, and the utilization. Report the cost
fields only as the records state them, and when no per-session cost is
derivable, say that no cost figure is available rather than estimating one
from a token count. A token ceiling is a budget for consumption, and it
must never be presented as a money figure.

### Aggregate usage across sessions

Per-session figures do not add up to the envelope's consumption. When an
envelope covers several sessions, report the aggregate alongside the
per-session breakdown: sessions authorized versus sessions used, total
tokens and total tool calls against the sum of the per-session ceilings,
and the sessions that consumed nothing. A report that shows only the
largest single session understates what the envelope spent.

### The frozen-identity gate

Have the launcher recompute the candidate digest and refuse to dispatch on a
mismatch (distinct non-zero exit). A dispatch delayed by hours — a provider
quota window, a scheduled re-dispatch — must never review bytes that moved
after the freeze.

### A launch that dies at argument validation consumed nothing

`exit 2`, zero tokens on every axis, zero tool calls, and NO session row in
the profile `state.db` means the CLI refused the flags before any provider
call. That is neither a used session nor a verdict: the authorised session is
still outstanding, and the fix is to remove the unsupported flag. Check the
CLI's own unsupported-option table before authoring a launch line, so the
refusal never happens at all.

## Failure modes

- `Unsupported gateway CLI options: --run-budget`: the installed gateway CLI
  refuses this flag and relocates it to `agent.run_budget_seconds` in
  config.yaml. It is rejected in ARGUMENT VALIDATION, so the launch exits 2
  with zero tokens, zero tool calls and no session row — the authorised
  session is NOT consumed. Remove the flag and enforce the wall-clock
  ceiling externally, as described above.

- `hermes: the checkout cannot start after an interrupted
  'hermes update'...`: the runtime's update recovery code fires
  and the session never starts. Re-run with the same command; the
  recovery is idempotent.

- `hermes chat: error: unrecognized arguments: --source tool`:
  some Hermes versions do not support the `--source` flag. Drop
  it; the default source is fine.

- `process started, session_id=<id>, but no events`: the bounded
  session is alive but stuck. Check `--run-budget` and
  `--max-turns`; if both are reasonable, the session is probably
  waiting for stdin. `--oneshot` is required.

- `exit_code 0` but the verdict file does not exist: the bounded
  session completed without writing its artifact. This is a
  contract violation; the orchestrator should treat it as
  `BLOCKED` and re-dispatch with explicit guard on the
  `verdict_path` and `verdict_file` fields in the contract.
