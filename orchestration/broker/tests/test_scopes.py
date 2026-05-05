import pytest
from fastapi import HTTPException

from app import scopes


class TestWriteScope:
    def test_write_scope_subset_of_read_scope(self):
        scopes.enforce_write_in_read(
            ["workspace/research-vault"],
            ["workspace/research-vault", "workspace/subconscious-room"],
        )

    def test_write_scope_not_subset_fails(self):
        with pytest.raises(HTTPException) as exc_info:
            scopes.enforce_write_in_read(
                ["workspace/coder-jobs"],
                ["workspace/research-vault"],
            )
        assert exc_info.value.status_code == 422


class TestWorkerKnown:
    def test_worker_known(self):
        scopes.enforce_worker_known("research-openclaw")

    def test_worker_unknown_fails(self):
        with pytest.raises(HTTPException) as exc_info:
            scopes.enforce_worker_known("ghost-worker")
        assert exc_info.value.status_code == 422


class TestCorrelationId:
    def test_correlation_id_present(self):
        scopes.enforce_correlation_id("a7e8c9d0-1111-2222-3333-444455556666")

    def test_correlation_id_missing_fails(self):
        with pytest.raises(HTTPException) as exc_info:
            scopes.enforce_correlation_id(None)
        assert exc_info.value.status_code == 422
