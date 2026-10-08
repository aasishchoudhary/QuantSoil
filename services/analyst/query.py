"""Deterministic analyst queries over world-state and map projections.

The analyst layer is read-only with respect to authoritative state. It can
compose evidence-backed snapshots, spatial results, and temporal changes, but
cannot create observations or authoritative claims.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from packages.contracts.world_state import EntityState
from services.world_state.query import HistoricalState, StateChange, diff_states, get_state_at

class MapQueryRepository(Protocol):
    def query_bbox(self, min_lon: float, min_lat: float, max_lon: float, max_lat: float,
                   at: datetime | None = None, limit: int = 500): ...

@dataclass(frozen=True)
class AnalystSnapshot:
    requested_at: datetime
    states: tuple[EntityState, ...]
    generated_at: datetime

@dataclass(frozen=True)
class SpatialResult:
    requested_at: datetime
    features: tuple[Any, ...]

@dataclass(frozen=True)
class AnalystTimeline:
    entity_id: str
    start: datetime
    end: datetime
    changes: tuple[StateChange, ...]

@dataclass(frozen=True)
class EvidenceSummary:
    evidence_refs: tuple[str, ...]
    sources: tuple[str, ...]
    observed_at_min: datetime | None
    observed_at_max: datetime | None

class AnalystQueryError(ValueError):
    pass

class AnalystService:
    def __init__(self, world_state, map_repository: MapQueryRepository):
        self.world_state = world_state
        self.map_repository = map_repository

    def snapshot(self, entity_ids: tuple[str, ...], *, at: datetime) -> AnalystSnapshot:
        _aware(at, "at")
        if not entity_ids:
            raise AnalystQueryError("at least one entity_id is required")
        ordered = tuple(sorted(set(entity_ids)))
        states = tuple(
            state for entity_id in ordered
            if (state := self.world_state.as_of(entity_id, at)) is not None
        )
        return AnalystSnapshot(at, states, datetime.now(at.tzinfo))

    def timeline(self, entity_id: str, *, start: datetime, end: datetime) -> AnalystTimeline:
        _aware(start, "start"); _aware(end, "end")
        if not entity_id.strip():
            raise AnalystQueryError("entity_id is required")
        return AnalystTimeline(entity_id, start, end, diff_states(self.world_state, entity_id, start, end))

    def spatial(self, bbox: tuple[float, float, float, float], *, at: datetime | None = None,
                limit: int = 500) -> SpatialResult:
        if len(bbox) != 4:
            raise AnalystQueryError("bbox must contain four coordinates")
        min_lon, min_lat, max_lon, max_lat = bbox
        if min_lon > max_lon or min_lat > max_lat:
            raise AnalystQueryError("invalid bbox")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180 and -90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise AnalystQueryError("bbox outside WGS84 bounds")
        if at is not None: _aware(at, "at")
        if not 1 <= limit <= 5000:
            raise AnalystQueryError("limit must be between 1 and 5000")
        return SpatialResult(at or datetime.now().astimezone(), tuple(
            self.map_repository.query_bbox(*bbox, at, limit)
        ))

    @staticmethod
    def evidence_summary(states: tuple[EntityState, ...]) -> EvidenceSummary:
        refs = tuple(dict.fromkeys(ref for state in states for ref in state.evidence_refs))
        times = [state.observed_at for state in states]
        return EvidenceSummary(
            refs, tuple(sorted({ref.split(":", 1)[0] for ref in refs if ":" in ref})),
            min(times) if times else None, max(times) if times else None,
        )

def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None:
        raise AnalystQueryError(f"{name} must be timezone-aware")
