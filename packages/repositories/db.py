"""Database-resource lifecycle helpers.

Repositories accept either a DB-API connection (useful for tests and small
standalone deployments) or a psycopg_pool ConnectionPool (used by the runtime).
Pool connections are always scoped to one repository operation and returned to
the pool deterministically.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator


@contextmanager
def connection_scope(resource: Any) -> Iterator[Any]:
    """Yield a usable connection from either a raw connection or a pool."""
    provider = getattr(resource, "connection", None)
    if callable(provider):
        with provider() as connection:
            yield connection
        return

    try:
        yield resource
    except BaseException:
        rollback = getattr(resource, "rollback", None)
        if callable(rollback):
            try:
                rollback()
            except Exception:
                pass
        raise
