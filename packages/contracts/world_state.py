"""Temporal, evidence-backed world-state contract.

World state is a versioned projection of entity observations. History is
append-only in the contract: a newer state never mutates an older state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


class WorldStateError(ValueError):
    """Raised when a world-state record violates its contract."""


@dataclass(frozen=True)
class EntityState:
    state_id: str
    entity_id: str
    entity_type: str
    valid_from: datetime
    observed_at: datetime
    recorded_at: datetime
    valid_to: datetime | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)
    geometry: Mapping[str, Any] | None = None
    confidence: float | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise WorldStateError("state_id is required")
        if not self.entity_id:
            raise WorldStateError("entity_id is required")
        if not self.entity_type:
            raise WorldStateError("entity_type is required")
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise WorldStateError("valid_to must be after valid_from")
        if self.recorded_at < self.observed_at:
            raise WorldStateError("recorded_at must not precede observed_at")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise WorldStateError("confidence must be between 0 and 1")
        if not self.evidence_refs or any(not ref for ref in self.evidence_refs):
            raise WorldStateError("evidence references must be non-empty")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise WorldStateError("evidence references must be unique")

    def is_valid_at(self, at: datetime) -> bool:
        return self.valid_from <= at and (self.valid_to is None or at < self.valid_to)


class InMemoryWorldStateRepository:
    """Append-only state history with deterministic as-of resolution."""

    def __init__(self) -> None:
        self._states: dict[str, list[EntityState]] = {}

    def append(self, state: EntityState) -> EntityState:
        history = self._states.setdefault(state.entity_id, [])
        if any(existing.state_id == state.state_id for existing in history):
            raise WorldStateError(f"duplicate state_id: {state.state_id}")
        for existing in history:
            overlaps = (
                state.valid_from < (existing.valid_to or datetime.max)
                and existing.valid_from < (state.valid_to or datetime.max)
            )
            if overlaps:
                raise WorldStateError(
                    f"overlapping validity interval for entity: {state.entity_id}"
                )
        history.append(state)
        history.sort(key=lambda item: (item.valid_from, item.recorded_at, item.state_id))
        return state

    def history(self, entity_id: str) -> tuple[EntityState, ...]:
        return tuple(self._states.get(entity_id, ()))

    def as_of(self, entity_id: str, at: datetime) -> EntityState | None:
        candidates = [state for state in self._states.get(entity_id, ()) if state.is_valid_at(at)]
        if not candidates:
            return None
        return max(candidates, key=lambda item: (item.valid_from, item.recorded_at, item.state_id))

    def current(self, entity_id: str, *, at: datetime) -> EntityState | None:
        return self.as_of(entity_id, at)
