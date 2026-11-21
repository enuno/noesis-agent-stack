# Bounded runtime qualification on a pinned Linux host

Executing a published qualification package (e.g. the T11 process-control
package, or pre-canary runtime checks) against a named Linux host under a
bounded, non-provider authorization. This is the execution pattern that sits
between offline review and any live canary: it produces target-runtime
evidence, never live-inference evidence.

## Authorization inputs (never assume)

- Host identity comes from the operator (hostname, reachability, isolation
  expectation). A host named in the operator's ssh config is a candidate, not
  a selection — record the operator's explicit confirmation before use.
- The pinned runtime revision is a full SHA chosen by the operator. The
  fleet-installed stable revision is a sensible proposal, but the operator's
  word is the pin. Record the repo CI's own pin alongside it: they often
  differ (CI pins an older validated revision; the operator may pin the fleet
  runtime). Version-specific CI assertions (e.g. a pinned-file sha256 check
  baked into the workflow for the CI revision) do NOT apply to a different
  approved pin — record the deviation instead of forcing the check.

## Isolation model

- Disposable container on the host (docker run -d <base> sleep infinity),
  named per mission. The host must be left untouched: nothing installed on
  the host, host /tmp cleaned afterward. Rollback is container disposal —
  verify `docker ps -a` shows the container gone after evidence capture.
- Inside: provision Python with `uv venv --python <CI-pinned minor>` using
  the SAME minor the repo CI pins (3.11 in the agent stack). The system
  Python on a current distro (3.14) pulls dependency pins that fail
  `pip check` against the repo's test requirements, and silently different
  behavior may follow. `uv pip install -r <repo>/.github/workflows/
  orchestrator-test-requirements.txt` then `uv pip install --no-deps -e
  <hermes-checkout>`; require `pip check` clean before any case runs.
- Clone both repos inside the container and verify pins BEFORE executing:
  fetch the pinned tag with `--depth 1`, require the peeled commit to equal
  the operator's SHA, checkout --detach, `rev-parse HEAD` must reproduce it.

## The hermetic-fixture pitfall (biggest time sink)

The orchestrator suite's CLI/plugin/dispatch-integration tests construct
`HermesCliAdapter()` with its DEFAULT profiles root (`Path.home()/.hermes/
profiles`). A naive `pytest -q` in a fresh container therefore fails ~16
tests with `profile_not_installed` / `no_eligible_specialist` — this is a
FIXTURE GAP, not a runtime defect, and it exactly resembles a real
regression. Run the suite hermetically exactly as CI does:

1. `ISO_HOME=<tmp>/ci-home`; `mkdir -p $ISO_HOME/.hermes/profiles`
2. `cp -R <repo>/profiles/live/. $ISO_HOME/.hermes/profiles/` — assert the
   tracked file count (33 at package time) so a thinned fixture fails loud.
3. Symlink the venv's `hermes_cli` package into `$ISO_HOME/.hermes/hermes-agent/`
   and assert `plugins.py`/`fallback_config.py` resolve through the link.
4. `env -i HOME=$ISO_HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=<venv>:/usr/bin:/bin
   TMPDIR=<tmp> PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests`

Diagnose any residual failure by failure CLASS: profile_not_installed-shaped
rejections across many dispatch tests point back at the fixture; isolated
failures in one module are more likely genuine.

## Process-qualification harness pitfalls

These cost a full harness iteration each if not known in advance:

- **Zombies keep killpg(0) alive.** After SIGTERM, a child lingers as a
  zombie until reaped, and `killpg(pgid, 0)` succeeds on a zombie — so a
  naive group-liveness check reports "still running" after a successful
  kill. Liveness = no NON-ZOMBIE member of the group (psutil status
  filter), and every spawned child must be explicitly reaped (wait())
  before its verdict. A launcher that polls killpg(0) during a fixed grace
  window (e.g. 0.2 s) will return "unconfirmed" against a zombie that is
  in fact dead — treat such a confirmation flag as pessimistic, never as
  proof the group survived.
- **setsid(1) may fork; pid-file handles drift.** util-linux setsid forks
  when the caller is a process-group leader, so a pid written by the
  payload can be the dead parent while the live orphan runs at pid+1.
  For orphan cases, fork+setsid+exec directly (python: os.fork, child
  os.setsid(), write os.getpid(), os.execvp) so the recorded handle is
  the live process by construction.
- **Verify documented numbers by observation, not by the document.**
  Qualification exists to find doc/runtime mismatch: measure timeouts,
  grace windows, and escalation timings, and when the observed number
  differs from the published package (a 0.2 s measured grace vs a 5 s
  documented one), report it as a finding with both numbers — do not
  edit the doc or the runtime inside the qualification authorization.

## Evidence and receipt

- Receipt fields follow the deployment-runbook receipt convention: target
  environment (host, container, image digest, kernel, PID-1 identity),
  readiness class, repo + installed revisions, digests, commands +
  outcomes, findings, limitations, remaining gates, rollback reference.
- Scan every retained artifact with the REPO's scanner
  (`agency.secretscan.scan_file`, not the hermes_cli package — the module
  moved/is absent across hermes versions) before calling evidence clean;
  keep command transcripts synthetic (no env dumps, no credential-shaped
  strings).
- Preserve the harness script outside the repo (scratch cache) with its
  sha256 in the receipt; the container is destroyed, the script is the
  reproducible record.

## Remote execution mechanics

- Ship scripts to the host/container as FILES, never as inline
  python/bash through nested ssh+docker quoting (three levels of escaping
  mangle even simple strings). Pattern: write locally, `ssh host 'cat >
  /tmp/x.py' < local.py`, `docker cp` into the container, syntax-check
  with `python -c "import ast; ast.parse(...)"` before running.
- `scp` can fail with publickey denial where `ssh` succeeds (agent-socket
  constraints). Pipe file content over `ssh host 'cat > ...'` instead of
  debugging scp.
- ssh auth flakes transiently (one "Permission denied (publickey)" burst
  between two good connections). Retry once before diagnosing; only
  investigate on a sustained second failure.
