"""Evidence-first temporal world-state query services.

This layer is deliberately repository-agnostic: persistence adapters implement
as_of/history, while query semantics remain deterministic and replayable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from packages.contracts.world_state import EntityState


class WorldStateQueryRepository(Protocol):
    def as_of(self, entity_id: str, at: datetime) -> EntityState | None: ...
    def history(self, entity_id: str) -> tuple[EntityState, ...]: ...


class WorldStateQueryError(ValueError):
    pass


@dataclass(frozen=True)
class StateChange:
    entity_id: str
    from_state_id: str | None
    to_state_id: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    changed_properties: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalState:
    entity_id: str
    as_of: datetime
    state: EntityState | None


def get_state_at(
    repository: WorldStateQueryRepository,
    entity_id: str,
    at: datetime,
) -> HistoricalState:
    if not entity_id.strip():
        raise WorldStateQueryError("entity_id is required")
    if at.tzinfo is None:
        raise WorldStateQueryError("as_of must be timezone-aware")
    return HistoricalState(entity_id, at, repository.as_of(entity_id, at))


def diff_states(
    repository: WorldStateQueryRepository,
    entity_id: str,
    start: datetime,
    end: datetime,
) -> tuple[StateChange, ...]:
    if start.tzinfo is None or end.tzinfo is None:
        raise WorldStateQueryError("time bounds must be timezone-aware")
    if end <= start:
        raise WorldStateQueryError("end must be after start")
    history = repository.history(entity_id)
    relevant = [
        state for state in history
        if state.valid_from < end and (state.valid_to is None or state.valid_to > start)
    ]
    relevant.sort(key=lambda state: (state.valid_from, state.recorded_at, state.state_id))
    changes: list[StateChange] = []
    previous: EntityState | None = None
    for current in relevant:
        if previous is not None:
            keys = sorted(set(previous.properties) | set(current.properties))
            changed = tuple(
                key for key in keys if previous.properties.get(key) != current.properties.get(key)
            )
            evidence = tuple(dict.fromkeys(previous.evidence_refs + current.evidence_refs))
        else:
            changed = tuple(sorted(current.properties))
            evidence = current.evidence_refs
        if previous is None or changed:
            changes.append(StateChange(
                entity_id=entity_id,
                from_state_id=previous.state_id if previous else None,
                to_state_id=current.state_id,
                valid_from=current.valid_from,
                valid_to=current.valid_to,
                changed_properties=changed,
                evidence_refs=evidence,
            ))
        previous = current
    return tuple(changes)
