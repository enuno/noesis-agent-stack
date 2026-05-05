import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_job():
    return {
        "worker": "research-openclaw",
        "mode": "refresh",
        "requested_by": "main-hermes",
        "correlation_id": "a7e8c9d0-1111-2222-3333-444455556666",
        "priority": "normal",
        "timeout_s": 600,
        "write_scope": ["workspace/research-vault"],
        "read_scope": ["workspace/research-vault"],
        "parameters": {"query": "latest AI trends"},
    }


@pytest.fixture
def sample_worker():
    return {
        "name": "research-openclaw",
        "runtime": "openclaw",
        "modes": ["refresh", "bootstrap", "drift-from-research"],
        "read_scopes": ["workspace/research-vault"],
        "write_scopes": ["workspace/research-vault"],
        "emits": [],
        "approval_required_for": ["build", "validate"],
        "healthy": True,
    }
