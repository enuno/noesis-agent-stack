# Claim Verification Probes

Probe recipes for the behavioral and held-operation claims in a candidate
acceptance review. Each probe drives the **real** code path; none re-implements
the logic under test.

## Rules

- A probe lives in scratch, imports the candidate tree by path, and prints a
  PASS/FAIL line per check with a non-zero exit on failure.
- **Read the real signature first.** Grep `def <method>` and the exception
  classes before writing the call. A guessed kwarg makes the probe crash, and
  a crash is not a finding.
- **Distinguish probe error from real defect.** A `TypeError` in the probe means
  the probe is wrong; a typed refusal from the code under test means the guard
  works. Never report the first as the second.
- Every probe must restore state it changes, or run entirely in a temp dir.

## Claim-probe scaffold

```python
import sys, tempfile
from pathlib import Path

tree_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree_root / "orchestration" / "orchestrator"))

from app.control_plane import Orchestrator, PolicyViolation  # noqa: E402

failures = []

def check(label, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}{(' :: ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)
```

Run with the project's interpreter against the reconstructed tree:
`PYTHONPATH=<tree>/orchestration/orchestrator <project-venv>/bin/python probe.py <tree>`

## Probe 1 — stale-evidence rejection (epoch-scoped decisions)

Claim shape: "evidence recorded for one attempt epoch cannot authorize a
different epoch." Reproduce the scenario end to end, do not read the guard.

1. Create a task via the orchestrator's own propose path.
2. Run the configuration preflight → evidence recorded.
3. Dispatch, then grant a new attempt (epoch increments).
4. Submit a candidate **without** a fresh preflight.

Expected: a typed refusal naming the missing epoch. A clean acceptance means
the guard is absent.

Run the same probe against the base candidate and the fixed candidate. The
contrast is the finding.

## Probe 2 — report-only writer (write confinement)

Claim shape: "writes nothing outside the declared report/findings/lock paths."

Snapshot the target directory before and after, by relative path AND content
hash, then diff the two snapshots. Assert:

- the only new entries are the declared outputs (plus their parent directory);
- no pre-existing file's hash changed;
- the operation refuses when its typed contract is violated (e.g. a
  report-only flag set to false produces no output at all).

Snapshot the *whole sandbox*, not just the declared outputs — the point is to
prove nothing undeclared appeared.

## Probe 3 — admission gate (no temporary state)

Claim shape: "refuses to proceed without configured durable state, and never
constructs temporary state to route around the refusal."

1. Call the entry point with no configured ledger/state → expect a typed
   refusal code.
2. Assert the sandbox directory is byte-identical before/after (no file
   created, no `.jsonl` anywhere).
3. Grep the module source for temporary-construction primitives
   (`mkdtemp`, `TemporaryFile`, `TemporaryDirectory`, `NamedTemporaryFile`).
4. Call again WITH configured state → expect the real path to be reached and
   the configured (canonical) file to be the one written.

## Probe 4 — guard precedence and allowed exceptions

Claim shape: "a symlink / traversal / extra-file guard refuses X."

Drive the guard directly with each hostile input: a symlink in the source, a
broken symlink as the destination, a non-allowlisted extra file in the
destination, a path-traversal allowlist entry, an empty allowlist.

Report the **typed error code** each case raises. Note any input the guard
tolerates (e.g. a `.tmp` file exempted by design) as a disclosed allowance
rather than silently omitting it.

Check operator precedence on multi-clause conditions with `ast.unparse` —
`if a or b if c else d` parses as `(a or b) if c else d`, which is rarely what
the author meant even when the behavior happens to be correct.

## Probe 5 — credential non-capture

Claim shape: "credential values never reach evidence."

1. Serialize the evidence structure and scan the whole JSON string for
   provider-shaped secret tokens (`sk-`, `AKIA`, `Bearer `) and for the
   literal secret value.
2. Assert a `credential_value` field is always `None` while a
   `credential_reference_id` label survives.

Scan the **serialized bytes**, not the dataclass fields — a field that is
excluded from `to_dict()` is the real guarantee, and only serialization proves
it.

## Probe 6 — schema drift

Claim shape: "the persisted contract matches the published schema."

A permissive schema (`additionalProperties: true`) accepts BOTH the old and
the new shape, so a green conformance suite does NOT prove the schema
documents the runtime shape. Check both halves:

```python
schema = json.load(open("contracts/.../task-contract.schema.json"))
sub = Draft202012Validator(schema["properties"]["preflight_evidence"])
list(sub.iter_errors(old_shape))   # A1 shape
list(sub.iter_errors(new_shape))   # current runtime shape
```

Validate the stored VALUE against the property's own subschema — validating it
against the whole document reports a wall of unrelated "required property"
errors and hides the drift. Then compare the declared property names against
the runtime keys: declared-but-absent properties mean the schema no longer
documents the contract.

## Held-operation static scan

For each new/changed module, scan the import surface and the write surface:

```bash
rg -n "^import |^from " <modules>          # third-party/network surface
rg -n "requests|httpx|urllib|urlopen|aiohttp|socket|anthropic|openai|litellm|api_key" <modules>
rg -n "os\.environ|getenv|expanduser|Path\.home|\.aws|\.ssh|keyring|token|secret" <modules>
rg -n "subprocess|os\.system|check_call|pip |uv |poetry" <modules>
rg -n "cron|schedule|launchd|launchctl|systemctl|install|activate|register" <modules>
rg -n "open\(|\.write_text|\.write_bytes|mkdir|unlink|rmtree|rename|shutil\.|copy2" <modules>
```

Zero hits on the network and credential scans is meaningful evidence for
"no provider calls, no credential reads". Zero hits on the write scan is NOT
evidence of "no writes" — pair it with Probe 2.

## Held-operation dynamic scan

- **Live profile writes:** list files modified in the claimed implementation
  window and check that none are profile identity files (`config.yaml`,
  `SOUL.md`) under the live profiles root.
- **Dependency installs:** confirm no `requirements*`/`pyproject.toml`/
  lockfile changed, and that any new third-party import was already a
  dependency of the project before the change.
- **Duplicate authorities:** confirm no second roster, task store, scheduler,
  or dispatcher was introduced — grep the new modules for class definitions and
  confirm they derive from the canonical sources rather than duplicating them.
