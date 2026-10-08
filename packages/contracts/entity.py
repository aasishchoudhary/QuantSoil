"""Evidence-backed probabilistic entity-resolution contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class EntityResolutionError(ValueError):
    """Raised when an entity or match violates the resolution contract."""


@dataclass(frozen=True)
class Entity:
    entity_id: str
    entity_type: str
    confidence: float
    evidence_refs: tuple[str, ...]
    properties: Mapping[str, Any] = None  # type: ignore[assignment]
    geometry: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise EntityResolutionError("entity_id is required")
        if not self.entity_type:
            raise EntityResolutionError("entity_type is required")
        if not 0 <= self.confidence <= 1:
            raise EntityResolutionError("confidence must be between 0 and 1")
        if not self.evidence_refs or any(not ref for ref in self.evidence_refs):
            raise EntityResolutionError("entity evidence_refs are mandatory")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise EntityResolutionError("entity evidence_refs must be unique")
        if self.properties is None:
            object.__setattr__(self, "properties", {})


@dataclass(frozen=True)
class EntityMatch:
    """A probabilistic assertion that an observation refers to an entity."""

    entity_id: str
    observation_id: str
    score: float
    method: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.entity_id or not self.observation_id:
            raise EntityResolutionError("entity_id and observation_id are required")
        if not 0 <= self.score <= 1:
            raise EntityResolutionError("match score must be between 0 and 1")
        if not self.method:
            raise EntityResolutionError("match method is required")
        if not self.evidence_refs or any(not ref for ref in self.evidence_refs):
            raise EntityResolutionError("match evidence_refs are mandatory")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise EntityResolutionError("match evidence_refs must be unique")


def resolve_candidates(
    observation_id: str,
    candidates: list[tuple[Entity, float]],
    *,
    method: str,
    evidence_refs: tuple[str, ...],
    threshold: float = 0.5,
) -> tuple[EntityMatch, ...]:
    """Convert deterministic candidate scores into ordered match assertions.

    This function does not claim identity. It emits uncertainty-bearing matches
    above the explicit threshold, preserving all qualifying candidates.
    """
    if not 0 <= threshold <= 1:
        raise EntityResolutionError("threshold must be between 0 and 1")
    matches = [
        EntityMatch(
            entity_id=entity.entity_id,
            observation_id=observation_id,
            score=score,
            method=method,
            evidence_refs=evidence_refs,
        )
        for entity, score in candidates
        if score >= threshold
    ]
    return tuple(sorted(matches, key=lambda item: (-item.score, item.entity_id)))
