# Qualification recipes — pinned-runtime containers and process-control harnesses

Concrete, re-runnable recipes for noesis-runtime-qualification. Distilled
from executed qualifications; verify counts/pins against the current repo
before reuse (they drift).

## Hermetic suite fixture (replicates CI exactly)

The agent-stack CI (`.github/workflows/orchestrator-tests.yml`) does NOT run
pytest in the runner's default HOME. It materializes an isolated home:

```
ISO_HOME=/tmp/ci-home
mkdir -p $ISO_HOME/.hermes/profiles $ISO_HOME/.hermes/hermes-agent
cp -R profiles/live/. $ISO_HOME/.hermes/profiles/
# CI asserts the tracked file count (was 33) — assert it too
SITE_PACKAGES=$(python -c "import hermes_cli, os; print(os.path.dirname(os.path.dirname(hermes_cli.__file__)))")
ln -s $SITE_PACKAGES/hermes_cli $ISO_HOME/.hermes/hermes-agent/hermes_cli
```

Then run:
```
env -i HOME=$ISO_HOME LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=<venv>/bin:/usr/bin:/bin \
  TMPDIR=/tmp PYTHONDONTWRITEBYTECODE=1 python -m pytest -q tests
```

Failure signature of skipping this: `no_eligible_specialist` /
`profile_not_installed` rejections in CLI, plugin-host, dispatch, and
identity tests (16 of them at one snapshot). That is a fixture gap, not a
runtime defect.

## Python version pinning with uv

CI pins a Python version (was 3.11). A newer system Python (was 3.14) makes
`pip check` fail because package pins are `python_version`-gated markers:

```
pip install uv
uv venv --python 3.11 /opt/qual/venv
. /opt/qual/venv/bin/activate
uv pip install -r .github/workflows/orchestrator-test-requirements.txt
uv pip install --no-deps -e <hermes-checkout>
pip check   # must pass before any case runs
```

## Pinned hermes clone with peeled-tag verification

```
git init -q hermes-agent
git -C hermes-agent remote add origin https://github.com/NousResearch/hermes-agent.git
git -C hermes-agent -c credential.helper= fetch -q --no-tags --depth 1 origin tag <tag>
PEELED=$(git -C hermes-agent rev-parse 'FETCH_HEAD^{commit}')
[ "$PEELED" = "<approved-full-sha>" ] || exit 1
git -C hermes-agent checkout -q --detach FETCH_HEAD
```

## Process-control harness rules

**Zombie-aware liveness.** On Linux, `os.killpg(pgid, 0)` succeeds against
zombie processes — a group whose members are all zombies reads as "alive".
Any liveness check must exclude zombies:

```python
def group_live(pgid):
    live = []
    for p in psutil.process_iter(["pid", "status"]):
        try:
            if os.getpgid(p.pid) == pgid and p.status() != psutil.STATUS_ZOMBIE:
                live.append(p.pid)
        except (psutil.NoSuchProcess, psutil.ZombieProcess, ProcessLookupError):
            continue
    return live
```

And reap every spawned child (`proc.wait()` / `proc.communicate()`) before
the verdict.

**Fork-safe orphan construction.** The `setsid(1)` binary forks when the
caller is a process-group leader, so a pid written by the inner command can
drift from the live orphan. Construct orphans with direct syscalls instead:

```python
ORPHAN = (
    "import os,sys\n"
    "p=os.fork()\n"
    "if p>0: sys.exit(0)\n"
    "os.setsid()\n"
    "open('/tmp/orphan.pid','w').write(str(os.getpid()))\n"
    "os.execvp('sleep',['sleep','30'])\n"
)
subprocess.Popen([sys.executable, "-c", ORPHAN], start_new_session=True, ...)
```

**Escalation-grace measurement.** Measure with `time.monotonic()` around the
signal call and compare against the implementation constant — don't assert
the document's number. If doc and code disagree, classify before fixing
(drafting error vs requirement vs defect).

**Cleanup hygiene between cases.** Leftover zombies from an earlier crashed
harness run persist under a non-reaping container PID 1; exclude them via
the zombie-aware check rather than trying to reap what isn't yours.
`psutil.Process` has no `pgid()` method — use `os.getpgid(pid)`.

## Evidence scan and file shipping

Scan the harness with the agent-stack scanner, not the pinned runtime:

```
PYTHONPATH=<agent-stack> python -c "from agency.secretscan import scan_file; ..."
```

`from hermes_cli import secretscan` fails when that module is absent on the
pinned checkout. Quote collisions in a remote `python -c` string are not a
scan result — write a small script and `docker cp` it.

If `scp` is denied, stream the harness over stdin:
`ssh host 'cat > /tmp/harness.py' < local.py`, then `docker cp` into the
container. Do not treat a transport denial as a qualification failure.
