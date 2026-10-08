"""Runtime health/readiness helpers."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class HealthStatus:
    live: bool
    ready: bool
    database_ok: bool
    connector_count: int
    detail: str

def check_database(connection_factory: Callable[[], object]) -> bool:
    connection = None
    try:
        connection = connection_factory()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1", ())
            row = cursor.fetchone()
        return row is not None and int(row[0]) == 1
    except Exception:
        return False
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
