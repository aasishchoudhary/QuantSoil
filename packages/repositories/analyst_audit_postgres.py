"""PostgreSQL sink for low-cardinality analyst access audit events."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from packages.repositories.db import connection_scope


class AnalystAuditRepositoryError(RuntimeError):
    pass


class PostgresAnalystAuditRepository:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def put(
        self,
        *,
        occurred_at: datetime,
        method: str,
        path: str,
        status_code: int,
        correlation_id: str,
    ) -> None:
        if not method or not path or not correlation_id:
            raise AnalystAuditRepositoryError("audit fields are required")
        q = """INSERT INTO analyst_audit
        (occurred_at,method,path,status_code,correlation_id)
        VALUES (%s,%s,%s,%s,%s)"""
        try:
            with connection_scope(self.connection) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        q,
                        (occurred_at, method, path, status_code, correlation_id),
                    )
                connection.commit()
        except Exception as exc:
            raise AnalystAuditRepositoryError(
                "failed to persist analyst audit event"
            ) from exc
