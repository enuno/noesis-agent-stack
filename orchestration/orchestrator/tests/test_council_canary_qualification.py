import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

try:
    import jsonschema  # noqa: F401

    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

from app.council import CouncilError  # noqa: E402
from app.council_bridge import build_handoff  # noqa: E402
from app.council_dispatch import (  # noqa: E402
    AdmissionError,
    CouncilSeatDispatch,
    MalformedLauncherResult,
    RevokedError,
)
from tests.fixtures.council_canary.synthetic_seam import (
    SeamCancelled,  # noqa: F401  (exported seam vocabulary)
    SeamChildError,
    SeamTimeout,
    SyntheticSeatProcessLauncher,
)

ALLOWED = {"KIMI_CODE"}
REPO_ROOT = Path(__file__).resolve().parents[3]
VERDICT_SCHEMA = REPO_ROOT / "contracts" / "orchestration" / "council-verdict.schema.json"
CLOSED_SET = {
    "orchestration/orchestrator/tests/fixtures/council_canary/__init__.py",
    "orchestration/orchestrator/tests/fixtures/council_canary/fake_seat.py",
    "orchestration/orchestrator/tests/fixtures/council_canary/synthetic_seam.py",
    "orchestration/orchestrator/tests/test_council_canary_qualification.py",
}


def _canary_session(**over):
    doc = {
        "schema_version": "noesis.council-session/v1",
        "session_id": "council-canary-duo-0001",
        "parent_task_id": "canary-parent",
        "council_revision": {
            "upstream_repo": "0xNyk/council-of-high-intelligence",
            "upstream_rev": "14d398f44771be1fc49488ab1b8a348ed76ca172",
            "protocol_mode_version": "duo@1",
            "vendored_docs_digest": "pending-phase-c-vendoring",
        },
        "mode": "duo",
        "fencing": {"task_version": 0, "epoch": 0, "attempt_id": "attempt-canary-0001"},
        "decision": {
            "question": "Canary qualification: choose option A or option B.",
            "alternatives": ["A", "B"],
            "constraints": ["advisory only; synthetic process seam"],
            "reversible": True,
        },
        "evidence_manifest": [],
        "seats": [
            {
                "seat_id": "s1",
                "profile": "noesis-skeptic",
                "lens": "socrates",
                "inference_route": "KIMI_CODE",
                "budget": {"max_output_tokens": 512, "round_timeout_s": 30},
                "write_scope": ["verdict-artifact"],
            },
            {
                "seat_id": "s2",
                "profile": "noesis-architect",
                "lens": "aristotle",
                "inference_route": "KIMI_CODE",
                "budget": {"max_output_tokens": 512, "round_timeout_s": 30},
                "write_scope": ["verdict-artifact"],
            },
        ],
        "chairman": {"profile": "noesis-quill", "excluded_from_panel": True},
        "limits": {
            "rounds": 1,
            "max_concurrent_seats": 2,
            "cost_ceiling": {
                "unit": "tokens",
                "estimated_tokens": 1024,
                "observed_tokens": 0,
                "currency_value": None,
                "currency_note": "currency unknown; tokens per lane only",
            },
            "session_timeout_s": 600,
        },
        "stop_conditions": ["split_verdict", "budget_exhausted", "lease_expiry", "operator_cancel"],
        "retention": {"artifact_ttl_days": 90, "sensitivity_class": "internal"},
        "created_at": "2026-11-08T00:00:00Z",
    }
    doc.update(over)
    return doc


class _RecordingObserver:
    def __init__(self):
        self.records = []

    def observe_budget(self, task_id, requests=0, output_tokens=None,
                       input_tokens=None, cache_read_tokens=None,
                       cache_write_tokens=None):
        self.records.append({
            "task_id": task_id,
            "requests": requests,
            "output_tokens": output_tokens,
            "input_tokens": input_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        })


def _observer_matches_calls(observer, dispatch):
    """Q12: each recorded call observed exactly once, in order."""
    if len(observer.records) != len(dispatch.calls):
        return False
    for rec, call in zip(observer.records, dispatch.calls):
        if rec["output_tokens"] != call["output_tokens"]:
            return False
        if rec["input_tokens"] != call["input_tokens"]:
            return False
        if rec["cache_read_tokens"] != call["cache_read_tokens"]:
            return False
        if rec["cache_write_tokens"] != call["cache_write_tokens"]:
            return False
    return True


def _validate_verdict_schema(verdict):
    """Q4: validate against the repo's council-verdict contract.

    Uses jsonschema + referencing when importable (the repo convention from
    tests/test_council_contracts.py); otherwise falls back to manual
    required-key/type assertions so the harness stays stdlib-portable.
    """
    if _HAS_JSONSCHEMA:
        import jsonschema
        from referencing import Registry, Resource

        schema = json.loads(VERDICT_SCHEMA.read_text(encoding="utf-8"))
        registry = Registry().with_resource(schema["$id"], Resource.from_contents(schema))
        validator = jsonschema.Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(verdict), key=lambda e: list(e.path))
        return [f"{'/'.join(str(p) for p in e.path)}: {e.message}" for e in errors]
    required = {
        "schema_version": str,
        "session_id": str,
        "parent_task_id": str,
        "mode": str,
        "positions": list,
        "tally": dict,
        "consensus": dict,
        "usage": dict,
        "session_metadata": dict,
    }
    problems = []
    for key, typ in required.items():
        if key not in verdict:
            problems.append(f"missing required key '{key}'")
        elif not isinstance(verdict[key], typ):
            problems.append(f"'{key}' is not {typ.__name__}")
    return problems


def _wait_dead(pid, timeout_s=10.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return True
        time.sleep(0.05)
    return False


def _reap_if_alive(pid):
    """Cleanup only. Call after the liveness observation, never before it."""
    if pid is None:
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    _wait_dead(pid, timeout_s=2.0)


class TestQ1AdmissionRefusal:
    """Q1: AdmissionError BEFORE any launch; the seam recorded ZERO spawns."""

    @pytest.mark.parametrize("mutate", [
        lambda s: s["limits"]["cost_ceiling"].pop("estimated_tokens"),
        lambda s: s["limits"]["cost_ceiling"].update(estimated_tokens=0),
        lambda s: s["limits"]["cost_ceiling"].update(estimated_tokens=-5),
        lambda s: s["seats"][0].update(inference_route="GPTY"),
        lambda s: s["fencing"].pop("attempt_id"),
    ])
    def test_refusal_precedes_any_spawn(self, mutate):
        session = _canary_session()
        mutate(session)
        seam = SyntheticSeatProcessLauncher()
        with pytest.raises(AdmissionError):
            CouncilSeatDispatch(
                session, seam,
                allowed_routes=ALLOWED,
                fencing_required=True,
            )
        assert seam.events == []

    def test_empty_allowlist_refuses(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        with pytest.raises(AdmissionError, match="allowlist"):
            CouncilSeatDispatch(session, seam, allowed_routes=set())
        assert seam.events == []


class TestQ2IdentityPropagation:
    def test_identity_recorded_per_call(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] is None
        assert len(seam.events) == 4  # 2 seats x 2 rounds
        seats = {s["seat_id"]: s for s in session["seats"]}
        for event in seam.events:
            seat = seats[event["seat_id"]]
            assert event["profile"] == seat["profile"]
            assert event["inference_route"] == seat["inference_route"]
        assert dispatch.parent_task_id == "canary-parent"


class TestQ3OutputLimitPropagation:
    def test_max_output_tokens_reaches_launcher(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        dispatch.run(ALLOWED)
        assert {e["max_output_tokens"] for e in seam.events} == {512}
        assert {e["round_timeout_s"] for e in seam.events} == {30}


class TestQ4NormalExit:
    def test_full_duo_run_valid_verdict(self):
        """Q4: full duo run completes and the verdict validates against
        contracts/orchestration/council-verdict.schema.json (jsonschema when
        importable — see _validate_verdict_schema docstring for the manual
        fallback this module uses when it is not)."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        verdict = dispatch.run(ALLOWED)
        assert verdict["consensus"]["reached"] is True
        assert verdict["consensus"]["position"] == "A"
        problems = _validate_verdict_schema(verdict)
        assert problems == [], problems


class TestQ5NonZeroExit:
    def test_nonzero_child_exit_typed_error_preserved(self):
        """Q5: scenario nonzero on s2 -> SeamChildError surfaces through the
        adapter's engine-exception path with type/args preserved; usage for
        the completed round is reported exactly once."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s2": "nonzero"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        with pytest.raises(SeamChildError) as excinfo:
            dispatch.run(ALLOWED)
        assert excinfo.value.rc == 3
        assert "partial synthetic envelope" in excinfo.value.stdout_tail
        # s1 completed round 1 (one adapter record); s2's single spawn
        # raised SeamChildError before any adapter record.
        assert len(dispatch.calls) == 1
        assert len(seam.events) == 2  # one spawn attempt per seat, no retry
        assert seam.events[0]["outcome"] == "ok"
        assert seam.events[1]["outcome"] == "child_error"
        # usage reported for completed rounds exactly once
        assert _observer_matches_calls(observer, dispatch)
        assert len(observer.records) == 1


class TestQ6MalformedResult:
    def test_malformed_stdout_refused_no_invented_zeros(self):
        """Q6: malformed (non-JSON) child stdout -> adapter refuses with
        typed MalformedLauncherResult; no usage record is invented."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s1": "malformed"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        with pytest.raises(MalformedLauncherResult, match="output_tokens"):
            dispatch.run(ALLOWED)
        assert dispatch.calls == []
        assert observer.records == []

    def test_missing_usage_key_refused_no_invented_zeros(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s1": "missing_usage"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        with pytest.raises(MalformedLauncherResult, match="refusing to invent zeros"):
            dispatch.run(ALLOWED)
        assert dispatch.calls == []
        assert observer.records == []


class TestQ7ZeroOutputTokens:
    def test_zero_output_tokens_accepted(self):
        """Q7: output_tokens 0 is a reported value, not a refusal; it is
        recorded and observed as 0, never as None."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s1": "zero_output_tokens"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        verdict = dispatch.run(ALLOWED)
        assert verdict["consensus"]["reached"] is True
        s1_calls = [c for c in dispatch.calls if c["seat_id"] == "s1"]
        assert s1_calls and all(c["output_tokens"] == 0 for c in s1_calls)
        s1_records = [r for r in observer.records if r["output_tokens"] == 0]
        assert len(s1_records) == 2  # both rounds observed, as 0


class TestQ8TimeoutAndProcessGroup:
    def test_timeout_kills_child(self):
        session = _canary_session()
        session["seats"][0]["budget"]["round_timeout_s"] = 2
        session["seats"][1]["budget"]["round_timeout_s"] = 2
        seam = SyntheticSeatProcessLauncher({"s1": "timeout"})
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        with pytest.raises(SeamTimeout) as excinfo:
            dispatch.run(ALLOWED)
        assert excinfo.value.pgid is not None
        assert seam.events[0]["outcome"] == "timeout"
        # the whole process group is gone: killpg probe must fail
        with pytest.raises(ProcessLookupError):
            os.killpg(excinfo.value.pgid, 0)

    def test_timeout_kills_descendant_group(self):
        """Q8 descendant scenario: the seat spawns a grandchild in its own
        process group; the seam's killpg must take down the grandchild too.
        Asserted portably via kill(pid, 0) polling for ProcessLookupError."""
        session = _canary_session()
        session["seats"][0]["budget"]["round_timeout_s"] = 2
        session["seats"][1]["budget"]["round_timeout_s"] = 2
        seam = SyntheticSeatProcessLauncher({"s1": "descendant"})
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        with pytest.raises(SeamTimeout) as excinfo:
            dispatch.run(ALLOWED)
        # the fake seat reports the grandchild pid on stderr
        grandchild_pid = None
        for line in excinfo.value.stderr_tail.splitlines():
            if line.startswith("grandchild_pid="):
                grandchild_pid = int(line.split("=", 1)[1])
        try:
            assert grandchild_pid is not None
            # Observe death before any cleanup. A 10s poll cannot be
            # satisfied by the grandchild's 120s sleep.
            assert _wait_dead(grandchild_pid), (
                f"grandchild {grandchild_pid} survived the killpg"
            )
            with pytest.raises(ProcessLookupError):
                os.killpg(excinfo.value.pgid, 0)
        finally:
            _reap_if_alive(grandchild_pid)


class TestQ9CancellationBeforeLaunch:
    def test_abort_before_run_operator_cancel(self):
        """Q9: abort() before run() -> RevokedError path -> schema-valid
        partial verdict stop_condition operator_cancel; zero spawns."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        dispatch.abort()
        verdict = dispatch.run(ALLOWED)
        assert seam.events == []
        assert dispatch.calls == []
        assert observer.records == []
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        assert verdict["consensus"]["reached"] is False
        assert verdict["session_metadata"]["rounds_run"] == 0


class TestQ10RevocationBetweenRounds:
    def test_revocation_after_round_one(self):
        """Q10: execution_revoked False for round 1, True afterwards -> no
        further spawns; partial verdict operator_cancel; usage reported for
        the completed round exactly once."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        observer = _RecordingObserver()
        calls = {"n": 0}

        def revoked():
            calls["n"] += 1
            return calls["n"] > 2  # after round 1 (2 seat calls)

        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
            execution_revoked=revoked,
        )
        verdict = dispatch.run(ALLOWED)
        assert len(seam.events) == 2  # round 1 only, no further spawns
        assert len(dispatch.calls) == 2
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"
        assert verdict["session_metadata"]["rounds_run"] == 1
        assert _observer_matches_calls(observer, dispatch)
        assert len(observer.records) == 2


class TestQ11DelayedOrAbsentUsage:
    def test_partial_usage_fields_stay_none(self):
        """Q11: scenario partial_usage omits optional usage fields; the
        adapter records and the observer receives None for them — unknown
        stays unknown, never an invented 0."""
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s1": "partial_usage"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
        )
        verdict = dispatch.run(ALLOWED)
        assert verdict["consensus"]["reached"] is True
        s1_records = observer.records[:1]  # round-1 record for s1
        # identify s1 records by matching the dispatch call order
        s1_call_indices = [i for i, c in enumerate(dispatch.calls) if c["seat_id"] == "s1"]
        for i in s1_call_indices:
            rec = observer.records[i]
            assert rec["output_tokens"] == 100
            assert rec["input_tokens"] is None
            assert rec["cache_read_tokens"] is None
            assert rec["cache_write_tokens"] is None
        # sanity: s2's records carry the full synthetic usage
        s2_call_indices = [i for i, c in enumerate(dispatch.calls) if c["seat_id"] == "s2"]
        assert s2_call_indices
        for i in s2_call_indices:
            rec = observer.records[i]
            assert rec["input_tokens"] == 50
            assert rec["cache_read_tokens"] == 20
            assert rec["cache_write_tokens"] == 0


class TestQ12NoDuplicateAccounting:
    def test_observer_count_matches_completed_calls(self):
        """Q12: across the Q5/Q9/Q10 exit paths, observer call count equals
        the completed launcher call count and each call is observed exactly
        once per run."""
        # nonzero path (engine exception path)
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s2": "nonzero"})
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED, observer=observer)
        with pytest.raises(SeamChildError):
            dispatch.run(ALLOWED)
        assert len(observer.records) == len(dispatch.calls) == 1
        assert _observer_matches_calls(observer, dispatch)

        # abort path
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        observer = _RecordingObserver()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED, observer=observer)
        dispatch.abort()
        dispatch.run(ALLOWED)
        assert len(observer.records) == len(dispatch.calls) == 0

        # mid-session revocation path
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        observer = _RecordingObserver()
        seen = {"n": 0}

        def revoked():
            seen["n"] += 1
            return seen["n"] > 2

        dispatch = CouncilSeatDispatch(
            session, seam, allowed_routes=ALLOWED, observer=observer,
            execution_revoked=revoked,
        )
        dispatch.run(ALLOWED)
        assert len(observer.records) == len(dispatch.calls) == 2
        assert _observer_matches_calls(observer, dispatch)


class TestQ13NoBlindRetry:
    def test_timeout_spawns_exactly_once(self):
        """Q13: the timeout path spawns the seat exactly once — no automatic
        re-spawn of an ambiguous outcome."""
        session = _canary_session()
        session["seats"][0]["budget"]["round_timeout_s"] = 2
        session["seats"][1]["budget"]["round_timeout_s"] = 2
        seam = SyntheticSeatProcessLauncher({"s1": "timeout"})
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        with pytest.raises(SeamTimeout):
            dispatch.run(ALLOWED)
        assert len(seam.events) == 1
        assert seam.events[0]["outcome"] == "timeout"


class TestQ14PartialVerdictLinkage:
    def test_operator_cancel_carries_parent_and_identity(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher()
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        dispatch.abort()
        verdict = dispatch.run(ALLOWED)
        assert verdict["parent_task_id"] == "canary-parent"
        assert verdict["session_id"] == session["session_id"]
        assert verdict["council_revision"]["protocol_mode_version"] == "duo@1"
        assert verdict["session_metadata"]["stop_condition"] == "operator_cancel"

    def test_quorum_shortfall_carries_parent_and_identity(self):
        session = _canary_session()
        seam = SyntheticSeatProcessLauncher({"s2": "invalid_position"})
        dispatch = CouncilSeatDispatch(session, seam, allowed_routes=ALLOWED)
        verdict = dispatch.run(ALLOWED)
        assert verdict["session_metadata"]["stop_condition"] == "quorum_shortfall"
        assert verdict["parent_task_id"] == "canary-parent"
        assert verdict["session_id"] == session["session_id"]
        # council_revision on the verdict is the 3-key projection the engine
        # records (vendored_docs_digest intentionally stays session-local)
        projected = {
            k: session["council_revision"][k]
            for k in ("upstream_repo", "upstream_rev", "protocol_mode_version")
        }
        assert verdict["council_revision"] == projected
        # the blocked seat is named, never silently substituted
        assert "s2" in verdict["synthesis_notes"]


class TestQ15ClosedSetOnly:
    def test_worktree_gained_only_closed_set_files(self):
        """Q15: the harness writes nothing outside pytest tmp dirs.

        Before publication, porcelain (pycache excluded) is exactly the four
        closed-set paths. After those paths are tracked, porcelain must be
        empty. Either shape is the closed set. Any other dirty path fails.
        """
        proc = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=str(REPO_ROOT), capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        paths = set()
        for line in proc.stdout.splitlines():
            entry = line[3:]
            if " -> " in entry:
                entry = entry.split(" -> ", 1)[1]
            paths.add(entry)
        non_pycache = {p for p in paths if "__pycache__" not in p.split("/")}
        if not non_pycache:
            missing = []
            for path in sorted(CLOSED_SET):
                tracked = subprocess.run(
                    ["git", "ls-files", "--error-unmatch", "--", path],
                    cwd=str(REPO_ROOT), capture_output=True, text=True,
                )
                if tracked.returncode != 0 or not (REPO_ROOT / path).is_file():
                    missing.append(path)
            assert not missing, (
                f"published tree missing closed-set paths: {missing}"
            )
            return
        assert non_pycache == CLOSED_SET, (
            f"worktree changed outside the closed set: {non_pycache - CLOSED_SET}"
        )


class TestQ16R1ResidualExposure:
    def test_missing_session_id_raw_keyerror_pinned(self):
        """Q16 (documentation-only, R-1 residual exposure): feeding the
        bridge build_handoff a verdict whose session lacks session_id leaks
        a RAW KeyError out of app.council_bridge.build_handoff (line 59,
        session['session_id']) instead of the CouncilError taxonomy. This
        test pins the CURRENT raw-KeyError behavior so the residual stays
        observable: if the taxonomy is later fixed to raise CouncilError,
        this test must be updated deliberately, not silently."""
        verdict = {
            "session_id": "council-canary-duo-0001",
            "parent_task_id": "canary-parent",
            "council_revision": _canary_session()["council_revision"],
        }
        session = {"parent_task_id": "canary-parent"}  # session_id absent
        with pytest.raises(KeyError) as excinfo:
            build_handoff(verdict, session)
        assert excinfo.value.args == ("session_id",)
        assert not isinstance(excinfo.value, CouncilError)
