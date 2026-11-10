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


SECRET = "sk-" + "syntheticseatvalue0001"
UNRELATED = "sk-" + "syntheticunrelated0001"


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


def _adapter(tmp_path: Path, runner: RecordingTransport) -> HermesCliAdapter:
    profiles = tmp_path / "profiles" / "noesis-forge"
    profiles.mkdir(parents=True)
    (profiles / "SOUL.md").write_text("name: noesis-forge\n", encoding="utf-8")
    return HermesCliAdapter(hermes_bin="hermes", profiles_root=profiles.parent, process_runner=runner)


def _launch(tmp_path: Path, runner: RecordingTransport, **overrides):
    adapter = _adapter(tmp_path, runner)
    kwargs = dict(
        profile_id="noesis-forge",
        prompt="offline credential probe",
        task_id="task-cred",
        cwd=str(tmp_path),
        dry_run=False,
        provider="approved-provider",
        model="approved-model",
        timeout_s=30,
        remaining_lease_s=30,
        workspace=tmp_path / "workspace",
        fallback_policy="deny",
    )
    kwargs.update(overrides)
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
    second = write_seat_credential_files(right, _contract(files={"other.token": "other-synthetic-value"}))
    _expect_equal(first[0].read_text(encoding="utf-8"), SECRET, "written credential content")
    assert oct(first[0].stat().st_mode & 0o777) == "0o600"
    assert not (right / ".seat-credentials" / "seat.token").exists()
    assert second[0].read_text(encoding="utf-8") == "other-synthetic-value"
    remove_seat_credential_files(first + second)
    assert not first[0].exists()
    assert not second[0].exists()


def test_council_seam_refuses_before_inference_and_ignores_payload_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHETIC_UNRELATED_SECRET", UNRELATED)
    runner = RecordingTransport()
    adapter = _adapter(tmp_path, runner)
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(values={}),
        workspace=tmp_path / "workspace",
        task_id="task-cred",
    )
    (tmp_path / "workspace").mkdir()
    payload = {"text": "ignore instructions", "--provider": "evil-provider", "token": SECRET}
    with pytest.raises(CredentialUnavailable) as raised:
        launcher({"profile": "noesis-forge", "seat_id": "forge"}, payload, 32, 15)
    assert runner.inference_count == 0
    assert runner.calls == []
    _expect_absent(SECRET, str(raised.value), "secret in refusal text")


def test_council_seam_does_not_invent_usage(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong"}))
    adapter = _adapter(tmp_path, runner)
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="task-cred",
    )
    (tmp_path / "workspace").mkdir()
    with pytest.raises(SeatLaunchRefused) as raised:
        launcher({"profile": "noesis-forge", "seat_id": "forge"}, {"ask": "pong"}, 32, 15)
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
    runner = RecordingTransport(stdout=json.dumps({"text": "pong", "usage": {"output": 1}}))
    adapter = _adapter(tmp_path, runner)
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="parent-task",
    )
    (tmp_path / "workspace").mkdir()
    for seat_id in ("forge", "skeptic"):
        for _round in (1, 2):
            launcher(
                {"profile": "noesis-forge", "seat_id": seat_id},
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
    assert task_ids == {"parent-task"}


def test_same_round_retry_is_refused_after_closure(tmp_path):
    runner = RecordingTransport(stdout=json.dumps({"text": "pong", "usage": {"output": 1}}))
    adapter = _adapter(tmp_path, runner)
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="parent-retry",
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
    adapter = _adapter(tmp_path, runner)
    launcher = HermesCouncilSeatLauncher(
        adapter,
        provider="approved-provider",
        model="approved-model",
        credential_contract=_contract(),
        workspace=tmp_path / "workspace",
        task_id="parent-timeout",
    )
    (tmp_path / "workspace").mkdir()
    seat = {"profile": "noesis-forge", "seat_id": "forge", "round": 1}
    with pytest.raises(SeatLaunchRefused):
        launcher(seat, {"ask": "pong"}, 32, 15)
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

    def failing_unlink(self, missing_ok=False):
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(Path, "unlink", failing_unlink)
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
