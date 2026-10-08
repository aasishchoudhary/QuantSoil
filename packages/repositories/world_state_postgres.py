"""PostgreSQL repository for temporal entity state.

The adapter keeps database concerns outside the world-state domain contract
and uses deterministic interval queries for historical reconstruction.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Protocol
from packages.contracts.world_state import EntityState, WorldStateError


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


class WorldStateRepositoryError(RuntimeError):
    """Raised when world-state persistence fails."""


_INSERT = """
INSERT INTO entity_state (
    state_id, entity_id, entity_type, valid_from, valid_to, observed_at,
    recorded_at, properties, geometry, confidence, evidence_refs
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (state_id) DO NOTHING
"""

_SELECT_AT = """
SELECT state_id, entity_id, entity_type, valid_from, valid_to, observed_at,
       recorded_at, properties, geometry, confidence, evidence_refs
FROM entity_state
WHERE entity_id = %s
  AND valid_from <= %s
  AND (valid_to IS NULL OR %s < valid_to)
ORDER BY valid_from DESC, recorded_at DESC, state_id DESC
LIMIT 1
"""

_SELECT_HISTORY = """
SELECT state_id, entity_id, entity_type, valid_from, valid_to, observed_at,
       recorded_at, properties, geometry, confidence, evidence_refs
FROM entity_state
WHERE entity_id = %s
ORDER BY valid_from, recorded_at, state_id
"""


class PostgresWorldStateRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def append(self, state: EntityState) -> EntityState:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_INSERT, (
                    state.state_id, state.entity_id, state.entity_type,
                    state.valid_from, state.valid_to, state.observed_at,
                    state.recorded_at, dict(state.properties),
                    dict(state.geometry) if state.geometry is not None else None,
                    state.confidence, list(state.evidence_refs),
                ))
            self._connection.commit()
        except Exception as exc:
            try:
                self._connection.rollback()
            except Exception:
                pass
            raise WorldStateRepositoryError("failed to persist world state") from exc
        return state

    def as_of(self, entity_id: str, at: datetime) -> EntityState | None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_SELECT_AT, (entity_id, at, at))
                row = cursor.fetchone()
        except Exception as exc:
            raise WorldStateRepositoryError("failed to read world state") from exc
        return None if row is None else self._row_to_state(row)

    def history(self, entity_id: str) -> tuple[EntityState, ...]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(_SELECT_HISTORY, (entity_id,))
                rows = cursor.fetchall()
        except Exception as exc:
            raise WorldStateRepositoryError("failed to read world-state history") from exc
        return tuple(self._row_to_state(row) for row in rows)

    @staticmethod
    def _row_to_state(row: tuple[Any, ...]) -> EntityState:
        (
            state_id, entity_id, entity_type, valid_from, valid_to,
            observed_at, recorded_at, properties, geometry, confidence, evidence_refs
        ) = row
        try:
            return EntityState(
                state_id=str(state_id),
                entity_id=str(entity_id),
                entity_type=str(entity_type),
                valid_from=valid_from,
                valid_to=valid_to,
                observed_at=observed_at,
                recorded_at=recorded_at,
                properties=properties or {},
                geometry=geometry,
                confidence=confidence,
                evidence_refs=tuple(evidence_refs or ()),
            )
        except WorldStateError as exc:
            raise WorldStateRepositoryError("database returned invalid world state") from exc
