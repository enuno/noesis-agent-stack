"""Offline credential-contract tests. No provider process is started.

The synthetic transport records the spawn boundary. It does not call Hermes
and does not contact a model provider.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.launcher import HermesCliAdapter
from app.seat_credentials import (
    CredentialUnavailable,
    HermesCouncilSeatLauncher,
    SeatCredentialContract,
    SeatLaunchRefused,
    build_spawn_env,
    unsafe_parent_copy,
    validate_seat_credential_contract,
    write_seat_credential_files,
)
from app.store import TaskStore

PARENT_TASK = "11111111-1111-1111-1111-111111111111"


SECRET = "sk-" + "syntheticseatvalue0001"
UNRELATED = "sk-" + "syntheticunrelated0001"
OTHER_SECRET = "other-" + "synthetic-value"


def _expect_equal(left, right, what: str) -> None:
    """Compare without letting pytest introspection print credential values."""
    if left != right:
        raise AssertionError(f"{what} mismatch")


def _expect_absent(needle, haystack, what: str) -> None:
    if needle in haystack:
        raise AssertionError(f"{what} present")


class _Completed:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "", pid: int = 4242) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.pid = pid


class RecordingTransport:
    def __init__(self, stdout: str = "") -> None:
        self.calls: list[dict] = []
        self.inference_count = 0
        self.stdout = stdout
        self.saw_credential_file = False

    def __call__(self, cmd, **kwargs):
        env = dict(kwargs.get("env") or {})
        self.calls.append({"cmd": list(cmd), "env": env})
        if "profile" in cmd and "show" in cmd:
            profile = cmd[cmd.index("-p") + 1]
            return _Completed(0, f"Profile: {profile}\nPath: /offline/profiles/{profile}\n")
        self.inference_count += 1
        home = Path(env["HERMES_HOME"])
        cred = home / ".seat-credentials" / "seat.token"
        self.saw_credential_file = cred.is_file()
        return _Completed(0, self.stdout)


def _contract(**over) -> SeatCredentialContract:
    base = dict(
        scope="api-key-env",
        allowed_env=("SYNTHETIC_SEAT_TOKEN",),
        required_env=("SYNTHETIC_SEAT_TOKEN",),
        values={"SYNTHETIC_SEAT_TOKEN": SECRET},
        files={"seat.token": SECRET},
    )
    base.update(over)
    return SeatCredentialContract(**base)


def _adapter(tmp_path: Path, runner: RecordingTransport, store: TaskStore | None = None) -> HermesCliAdapter:
    profiles = tmp_path / "profiles" / "noesis-forge"
    profiles.mkdir(parents=True)
    (profiles / "SOUL.md").write_text("name: noesis-forge\n", encoding="utf-8")
    return HermesCliAdapter(
        hermes_bin="hermes",
        profiles_root=profiles.parent,
        process_runner=runner,
        task_store=store,
    )


def _launch(tmp_path: Path, runner: RecordingTransport, **overrides):
    store = TaskStore(tmp_path / "tasks.jsonl")
    adapter = _adapter(tmp_path, runner, store)
    kwargs = dict(
        profile_id="noesis-forge",
        prompt="offline credential probe",
        task_id=PARENT_TASK,
        cwd=str(tmp_path),
        dry_run=False,
        provider="approved-provider",
        model="approved-model",
        timeout_s=30,
        remaining_lease_s=30,
        workspace=tmp_path / "workspace",
        fallback_policy="deny",
        assignment_epoch=0,
    )
    kwargs.update(overrides)
    contract = kwargs.get("credential_contract")
    if contract is not None and getattr(contract, "files", None) and "budget_attempt_id" not in overrides:
        kwargs["budget_attempt_id"] = f"{kwargs['task_id']}|forge|round-1|attempt-1"
    (tmp_path / "workspace").mkdir(exist_ok=True)
    return adapter.launch(**kwargs)


def test_parent_copy_leaks_undeclared_secret():
    parent = {"PATH": "/usr/bin", "SYNTHETIC_UNRELATED_SECRET": UNRELATED}
    leaked = unsafe_parent_copy(parent)
    _expect_equal(leaked["SYNTHETIC_UNRELATED_SECRET"], UNRELATED, "parent copy leak")


def test_spawn_env_does_not_inherit_undeclared_secret():
    parent = {
        "PATH": "/usr/bin",
        "HOME": "/tmp/seat-home",
        "SYNTHETIC_UNRELATED_SECRET": UNRELATED,
        "HERMES_PROVIDER": "ambient-provider",
    }
    env = build_spawn_env(parent, _contract())
    assert env["PATH"] == "/usr/bin"
    _expect_equal(env["SYNTHETIC_SEAT_TOKEN"], SECRET, "declared credential propagation")
    assert "SYNTHETIC_UNRELATED_SECRET" not in env
    _expect_absent(UNRELATED, env.values(), "undeclared secret")
    assert "HERMES_PROVIDER" not in env
    assert env["NOESIS_CREDENTIAL_SCOPE"] == "api-key-env"


def test_missing_required_credential_names_the_variable_not_the_value():
    contract = _contract(values={})
    with pytest.raises(CredentialUnavailable) as raised:
        validate_seat_credential_contract(contract)
    message = str(raised.value)
    assert "SYNTHETIC_SEAT_TOKEN" in message
    _expect_absent(SECRET, message, "secret in refusal message")
    _expect_absent(UNRELATED, message, "secret in refusal message")


def test_launch_refuses_missing_credential_before_any_process(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHETIC_UNRELATED_SECRET", UNRELATED)
    runner = RecordingTransport()
    result = _launch(tmp_path, runner, credential_contract=_contract(values={}))
    assert result.ok is False
    assert result.blocker_code == "credential_unavailable"
    _expect_absent(SECRET, result.error or "", "secret in launch error")
    _expect_absent(UNRELATED, result.error or "", "secret in launch error")
    assert runner.calls == []
    assert runner.inference_count == 0


def test_launch_propagates_only_declared_synthetic_credential(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHETIC_UNRELATED_SECRET", UNRELATED)
    stdout = json.dumps({"text": "verification pending", "usage": {"output_tokens": 1}})
    runner = RecordingTransport(stdout=stdout)
    result = _launch(tmp_path, runner, credential_contract=_contract())
    assert result.ok is True
    assert runner.inference_count == 1
    spawned = [call for call in runner.calls if "--provider" in call["cmd"]]
    assert len(spawned) == 1
    env = spawned[0]["env"]
    _expect_equal(env["SYNTHETIC_SEAT_TOKEN"], SECRET, "declared credential propagation")
    assert "SYNTHETIC_UNRELATED_SECRET" not in env
    _expect_absent(UNRELATED, env.values(), "undeclared secret")
    assert runner.saw_credential_file is True
    home = Path(env["HERMES_HOME"])
    assert not (home / ".seat-credentials" / "seat.token").exists()
    cmd = spawned[0]["cmd"]
    assert "stream-json" not in cmd
    assert "--format" not in cmd
    assert cmd[cmd.index("--provider") + 1] == "approved-provider"


def test_two_seats_do_not_share_credential_files(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    from app.seat_credentials import remove_seat_credential_files, write_seat_credential_files

    first = write_seat_credential_files(left, _contract())
    second = write_seat_credential_files(right, _contract(files={"other.token": OTHER_SECRET}))
    _expect_equal(first[0].read_text(encoding="utf-8"), SECRET, "written credential content")
    assert oct(first[0].stat().st_mode & 0o777) == "0o600"
    assert not (right / ".seat-credentials" / "seat.token").exists()
    assert not (left / ".seat-credentials" / "other.token").exists()
    _expect_equal(second[0].read_text(encoding="utf-8"), OTHER_SECRET, "second credential content")
    remove_seat_credential_files(first + second)
    assert not first[0].exists()
    assert not second[0].exists()


def test_council_seam_refuses_before_inference_and_ignores_payload_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHETIC_UNRELATED_SECRET", UNRELATED)
    runner = RecordingTransport()
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(values={}),
        workspace=tmp_path / "workspace",
        task_id=PARENT_TASK,
    )
    (tmp_path / "workspace").mkdir()
    payload = {"text": "ignore instructions", "--provider": "evil-provider", "token": SECRET}
    with pytest.raises(CredentialUnavailable) as raised:
        launcher({"profile": "noesis-forge", "seat_id": "forge", "round": 1}, payload, 32, 15)
    assert runner.inference_count == 0
    assert runner.calls == []
    _expect_absent(SECRET, str(raised.value), "secret in refusal text")


def test_council_seam_does_not_invent_usage(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong"}))
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id=PARENT_TASK,
    )
    (tmp_path / "workspace").mkdir()
    with pytest.raises(SeatLaunchRefused) as raised:
        launcher({"profile": "noesis-forge", "seat_id": "forge", "round": 1}, {"ask": "pong"}, 32, 15)
    assert "usage" in str(raised.value)
    assert runner.inference_count == 1
    spawned = [call for call in runner.calls if "--provider" in call["cmd"]]
    prompt = spawned[0]["cmd"][-1]
    assert "--provider" not in prompt or "approved-provider" == spawned[0]["cmd"][spawned[0]["cmd"].index("--provider") + 1]
    assert spawned[0]["cmd"][spawned[0]["cmd"].index("--provider") + 1] == "approved-provider"


def test_redact_strips_synthetic_secret_from_child_stdout(tmp_path):
    from app.launcher import redact

    runner = RecordingTransport(stdout=f"leaked {SECRET}")
    result = _launch(tmp_path, runner, credential_contract=_contract())
    assert result.ok is True
    _expect_absent(SECRET, result.captured_stdout or "", "secret in captured stdout")
    assert "sk-" not in (result.captured_stdout or "")
    assert redact(SECRET) != SECRET


def test_partial_credential_write_removes_only_this_attempt(tmp_path):
    from app.seat_credentials import _CREDENTIAL_DIR

    base = tmp_path / _CREDENTIAL_DIR
    base.mkdir(mode=0o700)
    kept = base / "already-there"
    kept.write_text("preexisting", encoding="utf-8")
    contract = _contract(files={"first": SECRET, "already-there": "must-not-overwrite"})
    with pytest.raises(CredentialUnavailable):
        write_seat_credential_files(tmp_path, contract)
    assert kept.read_text(encoding="utf-8") == "preexisting"
    assert not (base / "first").exists()
    _expect_absent(SECRET, kept.read_text(encoding="utf-8"), "secret in pre-existing file")


def test_symlink_credential_directory_is_refused_before_write(tmp_path):
    from app.seat_credentials import _CREDENTIAL_DIR

    outside = tmp_path / "outside"
    outside.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    (home / _CREDENTIAL_DIR).symlink_to(outside, target_is_directory=True)
    with pytest.raises(CredentialUnavailable, match="symlink"):
        write_seat_credential_files(home, _contract(files={"seat.env": SECRET}))
    assert list(outside.iterdir()) == []


def test_two_seats_two_rounds_keep_distinct_attempt_keys(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong", "usage": {"output_tokens": 1}}))
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id=PARENT_TASK,
    )
    (tmp_path / "workspace").mkdir()
    for seat_id in ("forge", "skeptic"):
        for _round in (1, 2):
            launcher(
                {"profile": "noesis-forge", "seat_id": seat_id, "round": _round},
                {"ask": "pong"},
                32,
                15,
            )
    assert runner.inference_count == 4
    task_ids = {
        call["env"].get("NOESIS_TASK_ID")
        for call in runner.calls
        if "--provider" in call["cmd"]
    }
    assert task_ids == {PARENT_TASK}
    expected = {
        f"{PARENT_TASK}|{seat_id}|round-{round_n}|attempt-1"
        for seat_id in ("forge", "skeptic")
        for round_n in (1, 2)
    }
    assert set(adapter.task_store.credential_attempts) == expected


def test_same_round_retry_is_refused_after_closure(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong", "usage": {"output_tokens": 1}}))
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="22222222-2222-2222-2222-222222222222",
    )
    (tmp_path / "workspace").mkdir()
    seat = {"profile": "noesis-forge", "seat_id": "forge", "round": 1}
    launcher(seat, {"ask": "pong"}, 32, 15)
    with pytest.raises(SeatLaunchRefused) as raised:
        launcher(seat, {"ask": "pong"}, 32, 15)
    assert str(raised.value) == "credential_attempt_exhausted"
    assert runner.inference_count == 1


class TimeoutTransport(RecordingTransport):
    def __call__(self, cmd, **kwargs):
        import subprocess

        if "profile" in cmd and "show" in cmd:
            return super().__call__(cmd, **kwargs)
        self.inference_count += 1
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout") or 1)


def test_ambiguous_timeout_refuses_same_attempt_retry(tmp_path):
    runner = TimeoutTransport(stdout="")
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="33333333-3333-3333-3333-333333333333",
    )
    (tmp_path / "workspace").mkdir()
    seat = {"profile": "noesis-forge", "seat_id": "forge", "round": 1}
    with pytest.raises(SeatLaunchRefused):
        launcher(seat, {"ask": "pong"}, 32, 15)
    attempt = "33333333-3333-3333-3333-333333333333|forge|round-1|attempt-1"
    assert adapter.task_store.credential_attempts[attempt] == "uncertain"
    with pytest.raises(SeatLaunchRefused) as raised:
        launcher(seat, {"ask": "pong"}, 32, 15)
    assert str(raised.value) == "credential_attempt_exhausted"
    assert runner.inference_count == 1


def test_write_error_before_record_rolls_back(tmp_path, monkeypatch):
    def failing_write(fd, data):
        raise OSError("injected write failure")

    monkeypatch.setattr(os, "write", failing_write)
    with pytest.raises(CredentialUnavailable) as raised:
        write_seat_credential_files(tmp_path, _contract())
    assert not (tmp_path / ".seat-credentials" / "seat.token").exists()
    _expect_absent(SECRET, str(raised.value), "secret in write-failure text")


def test_short_write_rolls_back(tmp_path, monkeypatch):
    real_write = os.write

    def short_write(fd, data):
        return real_write(fd, data[:1])

    monkeypatch.setattr(os, "write", short_write)
    with pytest.raises(CredentialUnavailable):
        write_seat_credential_files(tmp_path, _contract())
    assert not (tmp_path / ".seat-credentials" / "seat.token").exists()


def test_rollback_keeps_preexisting_empty_directory(tmp_path):
    from app.seat_credentials import _CREDENTIAL_DIR

    base = tmp_path / _CREDENTIAL_DIR
    base.mkdir(mode=0o700)
    (base / "seat.token2").write_text("kept", encoding="utf-8")
    with pytest.raises(CredentialUnavailable):
        write_seat_credential_files(tmp_path, _contract(files={"seat.token": SECRET, "seat.token2": "x"}))
    assert base.is_dir()
    assert not (base / "seat.token").exists()
    assert (base / "seat.token2").read_text(encoding="utf-8") == "kept"


def test_cleanup_failure_is_reported_not_masked(tmp_path, monkeypatch):
    from app.seat_credentials import _CREDENTIAL_DIR

    base = tmp_path / _CREDENTIAL_DIR
    base.mkdir(mode=0o700)
    (base / "seat.token2").write_text("kept", encoding="utf-8")
    real_unlink = os.unlink

    def failing_unlink(path, *, dir_fd=None):
        if dir_fd is not None:
            raise OSError("injected cleanup failure")
        return real_unlink(path)

    monkeypatch.setattr(os, "unlink", failing_unlink)
    with pytest.raises(CredentialUnavailable) as raised:
        write_seat_credential_files(tmp_path, _contract(files={"seat.token": SECRET, "seat.token2": "x"}))
    assert "cleanup_failed" in str(raised.value)
    assert "already exists" in str(raised.value)
    _expect_absent(SECRET, str(raised.value), "secret in cleanup-failure text")
    monkeypatch.undo()
    assert (base / "seat.token").exists()


def test_symlinked_ancestor_of_home_is_refused_with_trust_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    parent = tmp_path / "linked-parent"
    parent.symlink_to(outside, target_is_directory=True)
    home = parent / "home"
    home.mkdir()
    with pytest.raises(CredentialUnavailable, match="symlink"):
        write_seat_credential_files(home, _contract(), trust_root=tmp_path)
    assert list(outside.rglob("seat.token")) == []


def test_home_symlink_is_refused(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    home = tmp_path / "home-link"
    home.symlink_to(outside, target_is_directory=True)
    with pytest.raises(CredentialUnavailable):
        write_seat_credential_files(home, _contract(), trust_root=tmp_path)
    assert list(outside.rglob("seat.token")) == []


def test_write_refusal_after_validation_does_not_spawn(tmp_path, monkeypatch):
    called = {"n": 0}

    def boom(*args, **kwargs):
        called["n"] += 1
        raise CredentialUnavailable("credential directory is a symlink")

    monkeypatch.setattr("app.launcher.write_seat_credential_files", boom)
    runner = RecordingTransport()
    result = _launch(tmp_path, runner, task_id=PARENT_TASK)
    assert called["n"] == 1
    assert result.ok is False
    assert result.blocker_code == "credential_unavailable"
    assert runner.inference_count == 0
    _expect_absent(SECRET, result.error or "", "secret in write-refusal error")


@pytest.mark.parametrize(
    "label,stdout",
    [
        ("wrong-field", json.dumps({"text": "pong", "usage": {"output": 1}})),
        ("missing-text", json.dumps({"usage": {"output_tokens": 1}})),
        ("bool-tokens", json.dumps({"text": "pong", "usage": {"output_tokens": True}})),
        ("negative-tokens", json.dumps({"text": "pong", "usage": {"output_tokens": -1}})),
    ],
)
def test_malformed_seat_stdout_is_refused(tmp_path, label, stdout):
    runner = RecordingTransport(stdout=stdout)
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id=PARENT_TASK,
    )
    (tmp_path / "workspace").mkdir()
    with pytest.raises(SeatLaunchRefused):
        launcher({"profile": "noesis-forge", "seat_id": "forge", "round": 1}, {"ask": "pong"}, 32, 15)
    assert runner.inference_count == 1


PARTIAL = "session=sk-" + "abcdefgh" + ";extra=supersecretvalue"


def test_declared_secret_is_redacted_before_token_regex():
    from app.launcher import redact
    cleaned = redact("child said " + PARTIAL, secrets=(PARTIAL,))
    _expect_absent("supersecretvalue", cleaned, "secret tail")
    _expect_absent("sk-abcdefgh", cleaned, "secret prefix")
    if "[redacted]" not in cleaned:
        raise AssertionError("declared-secret marker missing")


def test_declared_secret_is_redacted_from_child_output(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": PARTIAL, "usage": {"output_tokens": 1}}))
    contract = _contract(values={"SYNTHETIC_SEAT_TOKEN": PARTIAL}, files={"seat.token": PARTIAL})
    result = _launch(tmp_path, runner, credential_contract=contract, task_id=PARENT_TASK)
    _expect_absent("supersecretvalue", result.captured_stdout or "", "secret tail in stdout")
    _expect_absent(PARTIAL, result.error or "", "secret in launch error")
    if "[redacted]" not in (result.captured_stdout or ""):
        raise AssertionError("declared-secret marker missing from stdout")


class _StderrTransport(RecordingTransport):
    def __call__(self, cmd, **kwargs):
        completed = super().__call__(cmd, **kwargs)
        if self.inference_count:
            completed.stderr = SECRET
            completed.returncode = 1
        return completed


def test_declared_secret_is_redacted_from_stderr(tmp_path):
    runner = _StderrTransport(stdout="")
    result = _launch(tmp_path, runner, credential_contract=_contract(), task_id="44444444-4444-4444-4444-444444444444")
    _expect_absent(SECRET, result.error or "", "secret in stderr error")
    assert result.ok is False


def test_missing_round_is_refused_before_inference(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong", "usage": {"output_tokens": 1}}))
    adapter = _adapter(tmp_path, runner, TaskStore(tmp_path / "tasks.jsonl"))
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id=PARENT_TASK,
    )
    (tmp_path / "workspace").mkdir()
    with pytest.raises(CredentialUnavailable):
        launcher({"profile": "noesis-forge", "seat_id": "forge"}, {"ask": "pong"}, 32, 15)
    assert runner.inference_count == 0


def test_real_transport_refuses_output_cap_before_spawn(tmp_path):
    profiles = tmp_path / "profiles" / "noesis-forge"
    profiles.mkdir(parents=True)
    adapter = HermesCliAdapter(hermes_bin="hermes", profiles_root=profiles.parent, process_runner=None)
    result = adapter.launch(
        profile_id="noesis-forge",
        prompt="offline",
        task_id="cap",
        dry_run=False,
        provider="approved-provider",
        model="approved-model",
        timeout_s=30,
        remaining_lease_s=30,
        workspace=tmp_path,
        fallback_policy="deny",
        max_output_tokens=32,
    )
    assert result.ok is False
    assert result.blocker_code == "output_cap_unsupported"


def test_cleanup_follows_creation_directory_not_later_path(tmp_path):
    created = write_seat_credential_files(tmp_path, _contract())
    original = tmp_path / ".seat-credentials"
    moved = tmp_path / "moved-credentials"
    original.rename(moved)
    replacement = tmp_path / ".seat-credentials"
    replacement.mkdir()
    sentinel = replacement / "seat.token"
    sentinel.write_text("kept", encoding="utf-8")
    from app.seat_credentials import remove_seat_credential_files
    remove_seat_credential_files(created)
    assert sentinel.read_text(encoding="utf-8") == "kept"
    assert not (moved / "seat.token").exists()


def test_write_failure_cleanup_keeps_creation_directory_fd(tmp_path, monkeypatch):
    calls = {"n": 0}
    real_write = os.write

    def fail_second(fd, data):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("injected second write")
        return real_write(fd, data)

    seen = {}
    from app import seat_credentials as seat_mod

    def spy(paths, owned_directories=None):
        seen["fd"] = getattr(paths, "dir_fd", -1)
        seen["names"] = list(getattr(paths, "names", []))
        return seat_mod.remove_seat_credential_files.__wrapped__(paths, owned_directories) if False else _real_remove(paths, owned_directories)

    _real_remove = seat_mod.remove_seat_credential_files
    monkeypatch.setattr(os, "write", fail_second)
    monkeypatch.setattr(seat_mod, "remove_seat_credential_files", lambda paths, owned_directories=None: seen.update(fd=getattr(paths, "dir_fd", -1), names=list(getattr(paths, "names", []))) or _real_remove(paths, owned_directories))
    contract = _contract(files={"first.token": SECRET, "second.token": OTHER_SECRET})
    with pytest.raises(CredentialUnavailable):
        write_seat_credential_files(tmp_path, contract)
    assert seen["fd"] >= 0
    assert "first.token" in seen["names"]
    assert not (tmp_path / ".seat-credentials" / "first.token").exists()


def test_created_file_names_are_not_shared_across_attempts():
    from app.seat_credentials import _CreatedFiles
    first = _CreatedFiles()
    first.names.append("first.token")
    second = _CreatedFiles()
    assert second.names == []
    assert first.names == ["first.token"]
