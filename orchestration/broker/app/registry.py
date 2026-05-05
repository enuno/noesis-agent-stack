"""Worker registry with capabilities and scope definitions."""

from app.models import WorkerProfile

_REGISTRY: dict[str, WorkerProfile] = {
    "research-openclaw": WorkerProfile(
        name="research-openclaw",
        runtime="openclaw",
        modes=["refresh", "bootstrap", "drift-from-research"],
        read_scopes=["workspace/research-vault"],
        write_scopes=["workspace/research-vault"],
        emits=[],
        approval_required_for=["build", "validate"],
        healthy=True,
    ),
    "subconscious-openclaw": WorkerProfile(
        name="subconscious-openclaw",
        runtime="openclaw",
        modes=["digest", "walk", "targeted-query"],
        read_scopes=["workspace/research-vault", "workspace/subconscious-room"],
        write_scopes=["workspace/subconscious-room"],
        emits=[],
        approval_required_for=["build", "validate"],
        healthy=True,
    ),
    "coder": WorkerProfile(
        name="coder",
        runtime="openclaw",
        modes=["build", "audit"],
        read_scopes=[
            "workspace/coder-jobs",
            "workspace/research-vault",
            "workspace/subconscious-room",
        ],
        write_scopes=["workspace/coder-jobs"],
        emits=[],
        approval_required_for=["build", "validate"],
        healthy=True,
    ),
    "qa": WorkerProfile(
        name="qa",
        runtime="openclaw",
        modes=["audit", "validate"],
        read_scopes=["workspace/qa-reports", "workspace/coder-jobs"],
        write_scopes=["workspace/qa-reports"],
        emits=[],
        approval_required_for=["build", "validate"],
        healthy=True,
    ),
}


def get_worker(name: str) -> WorkerProfile | None:
    return _REGISTRY.get(name)


def list_workers() -> list[WorkerProfile]:
    return list(_REGISTRY.values())


def worker_exists(name: str) -> bool:
    return name in _REGISTRY
