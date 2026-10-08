"""Persistent PostgreSQL repository for contradiction/fusion assertions."""
from __future__ import annotations

from typing import Any, Protocol
import json

from packages.contracts.fusion import Assertion, FusionError


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...
    def __enter__(self) -> "Cursor": ...
    def __exit__(self, *args: Any) -> None: ...


class Connection(Protocol):
    def cursor(self) -> Cursor: ...
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...


class AssertionRepositoryError(RuntimeError):
    """Raised when assertion persistence or reconstruction fails."""


_INSERT = """
INSERT INTO assertions (
    assertion_id, entity_id, property_name, value,
    confidence, source_weight, evidence_refs
) VALUES (%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (assertion_id) DO NOTHING
"""

_SELECT = """
SELECT assertion_id, entity_id, property_name, value,
       confidence, source_weight, evidence_refs
FROM assertions
WHERE assertion_id = %s
"""

_LIST = """
SELECT assertion_id, entity_id, property_name, value,
       confidence, source_weight, evidence_refs
FROM assertions
WHERE entity_id = %s AND property_name = %s
ORDER BY assertion_id
"""


class PostgresAssertionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def put(self, assertion: Assertion) -> Assertion:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_INSERT, (
                    assertion.assertion_id,
                    assertion.entity_id,
                    assertion.property_name,
                    json.dumps(assertion.value, sort_keys=True, separators=(",", ":")),
                    assertion.confidence,
                    assertion.source_weight,
                    list(assertion.evidence_refs),
                ))
                cursor.execute(_SELECT, (assertion.assertion_id,))
                row = cursor.fetchone()
            self._connection.commit()
        except Exception as exc:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise AssertionRepositoryError("failed to persist assertion") from exc
        if row is None:
            raise AssertionRepositoryError("assertion insert completed without a readable row")
        stored = self._row_to_assertion(row)
        if stored != assertion:
            raise AssertionRepositoryError("immutable assertion_id collision")
        return stored

    def list_for_property(self, entity_id: str, property_name: str) -> tuple[Assertion, ...]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_LIST, (entity_id, property_name))
                rows = cursor.fetchall()
        except Exception as exc:
            raise AssertionRepositoryError("failed to read assertions") from exc
        return tuple(self._row_to_assertion(row) for row in rows)

    @staticmethod
    def _row_to_assertion(row: tuple[Any, ...]) -> Assertion:
        try:
            assertion_id, entity_id, property_name, value, confidence, source_weight, evidence_refs = row
            if isinstance(value, str):
                value = json.loads(value)
            return Assertion(
                assertion_id=str(assertion_id),
                entity_id=str(entity_id),
                property_name=str(property_name),
                value=value,
                confidence=float(confidence),
                source_weight=float(source_weight),
                evidence_refs=tuple(evidence_refs or ()),
            )
        except (ValueError, TypeError, json.JSONDecodeError, FusionError) as exc:
            raise AssertionRepositoryError("database returned invalid assertion") from exc
