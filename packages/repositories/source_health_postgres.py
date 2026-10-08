"""Persistent source-health repository."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from packages.evaluation.data_quality import SourceHealth


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def __enter__(self) -> "Cursor": ...
    def __exit__(self, *args: Any) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...


class SourceHealthRepositoryError(RuntimeError):
    pass


_UPSERT = """
INSERT INTO source_health (source, observed_at, recorded_at, consecutive_failures)
VALUES (%s,%s,%s,%s)
ON CONFLICT (source) DO UPDATE SET
    observed_at = EXCLUDED.observed_at,
    recorded_at = EXCLUDED.recorded_at,
    consecutive_failures = EXCLUDED.consecutive_failures
"""

_GET = """
SELECT source, observed_at, recorded_at, consecutive_failures
FROM source_health WHERE source = %s
"""


class PostgresSourceHealthRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def put(self, health: SourceHealth) -> SourceHealth:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_UPSERT, (
                    health.source, health.observed_at, health.recorded_at,
                    health.consecutive_failures,
                ))
            self._connection.commit()
        except Exception as exc:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise SourceHealthRepositoryError("failed to persist source health") from exc
        return health

    def get(self, source: str) -> SourceHealth | None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_GET, (source,))
                row = cursor.fetchone()
        except Exception as exc:
            raise SourceHealthRepositoryError("failed to read source health") from exc
        if row is None:
            return None
        return SourceHealth(str(row[0]), _datetime(row[1]), _datetime(row[2]), int(row[3]))


def _datetime(value: Any) -> datetime:
    if not isinstance(value, datetime):
        raise SourceHealthRepositoryError("database returned invalid timestamp")
    return value
