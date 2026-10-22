# Decision layer evaluation: offline runner pattern

Use this when building a standalone evaluation script for the Jev decision layer
(`app/specialist_decision.py`) that runs outside pytest, produces a machine-readable
event log, and can be reviewed before any live provider call.

## When to use

- Phase III verification of a decision layer candidate (SHADOW mode, no mutation)
- Operator review of routing hypothesis measurement before ACTIVE promotion
- Drift detection: rerunning the same script against the baseline vs candidate

## Required imports

```python
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "orchestration" / "orchestrator"))

from app.specialist_decision import (
    CandidateInput, DecisionConfig, DecisionLayer, DecisionMode,
    DecisionProvider, FallbackReason,
)
from app.specialist_decision import CONTRACT_VERSION, CONTRACT_DIGEST

# FakeReplayProvider lives in the test suite, not the app package
from tests.test_decision_layer_evaluation import (
    DecisionScenario, SCENARIOS, FakeReplayProvider,
)
```

The test file imports `pytest`; running the script outside pytest works because
the import happens after `sys.path` is set and the script uses the venv Python
interpreter directly (see Python environment note below).

## Python environment

Do NOT use `uv run` from the repo root — it resolves to the system Python which
lacks pytest. The correct pattern:

```bash
# Find the venv python in the repo root
/Users/elvis/projects/noesis-agent-stack/.venv/bin/python

# Run from the orchestrator subdirectory with PYTHONPATH set
cd orchestration/orchestrator
PYTHONPATH=. /Users/elvis/projects/noesis-agent-stack/.venv/bin/python tests/eval_decision_layer.py
```

Or in a Python script:
```python
import subprocess, sys
venv_python = Path("/Users/elvis/projects/noesis-agent-stack/.venv/bin/python")
result = subprocess.run([str(venv_python), script_path], env={**os.environ, "PYTHONPATH": "."})
```

## Correct `decide()` call signature

The `candidate_records` parameter is `Mapping[str, CandidateInput]`, not a list:

```python
candidate_records: dict[str, CandidateInput] = {
    cid: CandidateInput(
        candidate_id=cid,
        capabilities=("plan_artifact", "code_modify"),
        mandate=f"{cid} mandate",
    )
    for cid in scenario.candidate_ids
}

outcome = layer.decide(
    baseline_candidate_id=scenario.baseline,
    tied_candidates=list(scenario.candidate_ids),
    required_capability="code_modify",        # NOT "coding"
    classification="implementation",           # NOT "routine"
    risk_tier="r1",
    candidate_records=candidate_records,        # NOT []
    registry_digest="r" * 32,
    policy_digest="p" * 32,
    rubric_digest="b" * 32,
    snapshot_digest="s" * 32,
    question=scenario.scenario_id,
    correlation_id=f"eval-{scenario.scenario_id}",
    task_id=f"eval-{scenario.scenario_id}",
    attempt_id="1",
    requested_model="fake-replay-model",       # NOT None
)
```

## SCENARIOS is a tuple

`SCENARIOS` from `test_decision_layer_evaluation` is a `tuple[DecisionScenario, ...]`.
Pass it to a function expecting `list[DecisionScenario]` by converting:
```python
results = _run_all_shadow(list(SCENARIOS))
```

## Distribution field type

`DecisionScenario.distribution` is `Mapping[str, float] | None`. Convert to `dict` for
`ScenarioResult` dataclass which expects `dict[str, float] | None`:
```python
distribution=dict(scenario.distribution)   # required: Mapping → dict
```

## Event log path

Write to a `tempfile.TemporaryDirectory()` first, then copy to a durable location:
```python
from pathlib import Path
import shutil

durable_path = Path.home() / ".hermes" / "profiles" / "noesis-orchestrator" / "cache" / "scratch" / "decision-shadow-events.jsonl"
durable_path.parent.mkdir(parents=True, exist_ok=True)
if event_log_path.exists():
    shutil.copy(event_log_path, durable_path)
```

## FakeReplayProvider usage

```python
# One distribution replayed N times (enough for all internal calls)
provider = FakeReplayProvider(
    [scenario.distribution] * 5,
    raw_distribution=False,
)
```

- `raw_distribution=False` (default): normalizes the distribution, adds missing
  candidate keys, sets `ABSTAIN_KEY` if absent.
- `raw_distribution=True`: returns the distribution verbatim, exercises the
  malformed-distribution validation path.

## SHADOW mode behavior

- `DecisionMode.SHADOW`: calls the provider, records recommendation in event log,
  but always applies the baseline candidate (no mutation).
- In SHADOW mode the `applied_candidate_id` equals `baseline_candidate_id` unless
  an error occurs — this is correct behavior, not a bug.
- SHADOW is the **operational default**: `DecisionConfig.mode` defaults to
  `DecisionMode.SHADOW`. OFF mode is still available via explicit config.

## Live SHADOW with real Jev backend

When authorized to run SHADOW against the real TypeSafe/Jev API (not FakeReplayProvider):

**1. Retrieve TYPESAFE_API_KEY from Bitwarden SM:**

```bash
BWS="/Users/elvis/.hermes/tools/bws-2.0.0-darwin-arm64/bws"
source ~/.hermes/.env   # BWS_ACCESS_TOKEN
# List secrets to find TYPESAFE_API_KEY:
$BWS secret list 72974d0e-81af-4678-bab7-b46000985859 -o json \
  | python3 -c "import sys,json; [print(s['key'], s['id']) for s in json.load(sys.stdin) if 'type' in s['key'].lower()]"
# Get value:
$BWS secret list 72974d0e-81af-4678-bab7-b46000985859 -o json \
  | python3 -c "import sys,json; [print(s['value']) for s in json.load(sys.stdin) if s.get('key')=='TYPESAFE_API_KEY']"
```

Project ID `72974d0e-81af-4678-bab7-b46000985859` is the `noosphere` BWS project.
Secret ID and value come back in the same JSON list call.

**2. Install the SDK:**

```bash
/Users/elvis/projects/noesis-agent-stack/.venv/bin/pip3 install \
  /Users/elvis/projects/noesis-agent-stack/orchestration/orchestrator/requirements-jev.txt -q
```

The venv pip is at `.venv/bin/pip3`, not `.venv/bin/pip`.

**3. Discover API endpoints from SDK constants:**

```python
from typesafe_sdk import constants
print(constants.DEFAULT_BASE_URL)   # https://api.typesafe.ai
print(constants.DEFAULT_MODEL)      # jev-latest
```

**4. Build the adapter and run SHADOW:**

```python
from app.typesafe_decision_adapter import TypeSafeAdapterFactory

factory = TypeSafeAdapterFactory(
    api_key='<retrieved key>',
    model='jev-latest',        # from constants.DEFAULT_MODEL
    deadline_s=5.0,
)
adapter = factory.build()

config = DecisionConfig(mode=DecisionMode.SHADOW, max_concurrency=2)
layer = DecisionLayer(config=config, provider=adapter)
```

**5. Expected live SHADOW behavior:**

- Real Jev calls take ~190ms first call; subsequent calls may be faster.
- Jev may `abstain` on abstract candidate names (no rich task context).
- Circuit breaker (`circuit_failure_threshold=3`) opens after 3 abstentions;
  subsequent calls get `circuit_open` fallback — baseline is still preserved.
- Event log records `provider_name='typesafe-jev'` and `provider_latency_ms`.

## Freeze manifest template

For operator-mediated review, produce a freeze manifest with per-file SHA-256 hashes:

```bash
for f in <list of changed/new files>; do
  sha=$(openssl sha256 -r "$f" | awk '{print $1}')
  echo "$sha  $f"
done
```

The manifest should include:
- Candidate ID and frozen HEAD SHA
- Table: SHA-256 | relative file path
- Evaluation results (test counts, SHADOW agree/rerank rates)
- Command recipe for reviewers to reproduce

## G1–G4 gate fix patterns (for reference)

These are already verified in the test suite. When adding new gate tests:

| Pattern | Fix in control_plane.py |
|---|---|
| Missing enforcer on bounded launch | `if bounded and self.inference_enforcer is None: raise RoutingBlocked("enforcer_unavailable", ...)` at top of `_assert_spawn_gates` |
| Observe-deny should block | `if decision.action == "observe_deny": raise RoutingBlocked("observe_deny", ...)` before observe pass-through |
| Lane/model from resolved fields | Extract `resolved_lane`/`resolved_model` BEFORE the `if not decision.allowed` guard |
| Epoch check before enforcer | `if bounded and expected_epoch is None` check must be a standalone gate before the enforcer block — if enforcer denies first, its exception propagates before any subsequent check |
| `RoutingBlocked` not enum value | `pytest.raises(RoutingBlocked, ...)` — the exception class, NOT `RoutingContext.ProposalState.Blocked` (that is an enum value, not an exception type) |
| `requires_approved_pair` as `__init__` param | `HermesCliAdapter.__init__` must accept it as an explicit kwarg with default `True`; a class-level attribute alone cannot be overridden per-instance |

## Changing default values: test rename discipline

When changing a default value in a public-facing dataclass field (e.g.
`DecisionConfig.mode` from `OFF` to `SHADOW`):

1. Rename the test that asserts the old default — a test named `test_default_mode_is_off`
   asserting `layer.mode is DecisionMode.OFF` must become `test_default_mode_is_shadow`
   asserting `DecisionMode.SHADOW`. Do not keep the old test name with flipped assertions;
   the name misleads future readers.
2. Update docstrings: describe the new default behavior, not the old one.
3. Run the full suite — the old test failing is the signal that the default changed,
   and other tests that depend on the old default may also need updating.
4. Update `COMPLETION-REPORT.md` and `FREEZE-MANIFEST.md` with the change.
