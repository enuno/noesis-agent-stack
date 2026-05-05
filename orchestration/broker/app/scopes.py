"""Scope enforcement utilities."""

from fastapi import HTTPException

from app import registry


def enforce_write_in_read(write_scope: list[str], read_scope: list[str]) -> None:
    write_set = set(write_scope)
    read_set = set(read_scope)
    if not write_set.issubset(read_set):
        diff = write_set - read_set
        raise HTTPException(
            status_code=422,
            detail=f"Write scope contains paths not in read scope: {sorted(diff)}",
        )


def enforce_worker_known(worker_name: str) -> None:
    if not registry.worker_exists(worker_name):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown worker profile: {worker_name}",
        )


def enforce_correlation_id(correlation_id: str | None) -> None:
    if not correlation_id:
        raise HTTPException(
            status_code=422,
            detail="correlation_id is required",
        )
