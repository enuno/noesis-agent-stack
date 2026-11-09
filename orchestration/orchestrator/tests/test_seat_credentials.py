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
)


SECRET = "sk-" + "syntheticseatvalue0001"
UNRELATED = "sk-" + "syntheticunrelated0001"


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
    assert leaked["SYNTHETIC_UNRELATED_SECRET"] == UNRELATED


def test_spawn_env_does_not_inherit_undeclared_secret():
    parent = {
        "PATH": "/usr/bin",
        "HOME": "/tmp/seat-home",
        "SYNTHETIC_UNRELATED_SECRET": UNRELATED,
        "HERMES_PROVIDER": "ambient-provider",
    }
    env = build_spawn_env(parent, _contract())
    assert env["PATH"] == "/usr/bin"
    assert env["SYNTHETIC_SEAT_TOKEN"] == SECRET
    assert "SYNTHETIC_UNRELATED_SECRET" not in env
    assert UNRELATED not in env.values()
    assert "HERMES_PROVIDER" not in env
    assert env["NOESIS_CREDENTIAL_SCOPE"] == "api-key-env"


def test_missing_required_credential_names_the_variable_not_the_value():
    contract = _contract(values={})
    with pytest.raises(CredentialUnavailable) as raised:
        validate_seat_credential_contract(contract)
    message = str(raised.value)
    assert "SYNTHETIC_SEAT_TOKEN" in message
    assert SECRET not in message
    assert UNRELATED not in message


def test_launch_refuses_missing_credential_before_any_process(tmp_path, monkeypatch):
    monkeypatch.setenv("SYNTHETIC_UNRELATED_SECRET", UNRELATED)
    runner = RecordingTransport()
    result = _launch(tmp_path, runner, credential_contract=_contract(values={}))
    assert result.ok is False
    assert result.blocker_code == "credential_unavailable"
    assert SECRET not in (result.error or "")
    assert UNRELATED not in (result.error or "")
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
    assert env["SYNTHETIC_SEAT_TOKEN"] == SECRET
    assert "SYNTHETIC_UNRELATED_SECRET" not in env
    assert UNRELATED not in env.values()
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
    assert first[0].read_text(encoding="utf-8") == SECRET
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
        launcher({"profile": "noesis-forge"}, payload, 32, 15)
    assert SECRET not in str(raised.value)
    assert runner.inference_count == 0
    assert runner.calls == []


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
        launcher({"profile": "noesis-forge"}, {"ask": "pong"}, 32, 15)
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
    assert SECRET not in (result.captured_stdout or "")
    assert "sk-" not in (result.captured_stdout or "")
    assert redact(SECRET) != SECRET
