"""Replay-oriented in-memory world-state repository.

Stores immutable states and exposes deterministic historical snapshots.
"""
from __future__ import annotations
from datetime import datetime
from packages.contracts.world_state import EntityState, InMemoryWorldStateRepository


class WorldStateReplayRepository:
    def __init__(self) -> None:
        self._repo = InMemoryWorldStateRepository()

    def append(self, state: EntityState) -> EntityState:
        return self._repo.append(state)

    def snapshot(self, entity_ids: tuple[str, ...], at: datetime) -> tuple[EntityState, ...]:
        return tuple(
            state
            for entity_id in sorted(entity_ids)
            if (state := self._repo.as_of(entity_id, at)) is not None
        )

    def history(self, entity_id: str) -> tuple[EntityState, ...]:
        return self._repo.history(entity_id)
