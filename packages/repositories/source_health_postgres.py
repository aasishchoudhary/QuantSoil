"""Persistent source-health repository."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from packages.evaluation.data_quality import SourceHealth
from packages.repositories.db import connection_scope


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
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_UPSERT, (
                        health.source, health.observed_at, health.recorded_at,
                        health.consecutive_failures,
                    ))
                connection.commit()
        except Exception as exc:
            raise SourceHealthRepositoryError("failed to persist source health") from exc
        return health

    def get(self, source: str) -> SourceHealth | None:
        try:
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
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


from packages.connectors.contracts import IngestionAudit, RejectedRecord


class PostgresIngestionAuditRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def put_run(self, audit: IngestionAudit) -> IngestionAudit:
        query = """
        INSERT INTO ingestion_runs
        (run_id, source, started_at, finished_at, records_seen, records_accepted,
         records_rejected, attempts, error_type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (run_id) DO UPDATE SET
          finished_at=EXCLUDED.finished_at,
          records_seen=EXCLUDED.records_seen,
          records_accepted=EXCLUDED.records_accepted,
          records_rejected=EXCLUDED.records_rejected,
          attempts=EXCLUDED.attempts,
          error_type=EXCLUDED.error_type
        """
        try:
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, (
                        audit.run_id, audit.source, audit.started_at, audit.finished_at,
                        audit.records_seen, audit.records_accepted, audit.records_rejected,
                        audit.attempts, audit.error_type,
                    ))
                connection.commit()
                return audit
        except Exception as exc:
            raise SourceHealthRepositoryError("failed to persist ingestion audit") from exc

    def put_rejection(self, rejection: RejectedRecord) -> RejectedRecord:
        query = """
        INSERT INTO rejected_records
        (rejection_id, run_id, source, source_record_id, raw_payload_hash,
         status, reasons, observed_at, rejected_at, payload)
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb)
        ON CONFLICT (rejection_id) DO NOTHING
        """
        import json
        try:
            with connection_scope(self._connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, (
                        rejection.rejection_id, rejection.run_id, rejection.source,
                        rejection.source_record_id, rejection.raw_payload_hash,
                        rejection.status, json.dumps(list(rejection.reasons)),
                        rejection.observed_at, rejection.rejected_at,
                        json.dumps(rejection.payload),
                    ))
                connection.commit()
                return rejection
        except Exception as exc:
            raise SourceHealthRepositoryError("failed to persist rejected record") from exc
