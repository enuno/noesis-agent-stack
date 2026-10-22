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
  --run-budget <seconds> \
  --max-turns <turns> \
  --format stream-json \
  --reasoning <level>
```

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

- `--run-budget <seconds>`: hard wall-clock cap. For a Sentinel or
  Skeptic review of ~5 in-scope files and a focused + full test
  pair, 1800 s is enough. For a bounded implementer that must write
  tests + production code + implementer result, 5400 s is enough.
  Do not under-budget; running out of budget mid-test leaves the
  worktree in a half-edited state and the verdict files unwritten.

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
  from `--run-budget`. Set it slightly above `--run-budget` so
  the foreground process does not cut the bounded session off
  mid-cleanup. For `--run-budget 1800`, `timeout=1800` or
  `timeout=1850` is right.

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

## Failure modes

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
