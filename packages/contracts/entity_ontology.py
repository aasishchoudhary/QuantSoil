"""Evidence-backed ontology primitives for stable entity identity and relationships.

Ontology records describe *what an entity is* and how identities/relationships are
modeled. Temporal observations remain in EntityState, keeping identity separate
from changing world state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


class OntologyError(ValueError):
    """Raised when an ontology contract is invalid."""


ENTITY_TYPES = frozenset({
    "person", "organization", "place", "facility", "event",
    "asset", "infrastructure", "natural_phenomenon", "region",
})


@dataclass(frozen=True)
class EntityIdentifier:
    namespace: str
    value: str
    kind: str = "external"

    def __post_init__(self) -> None:
        if not self.namespace.strip() or not self.value.strip() or not self.kind.strip():
            raise OntologyError("identifier namespace, value, and kind are required")


@dataclass(frozen=True)
class EntityAlias:
    value: str
    language: str | None = None
    kind: str = "name"

    def __post_init__(self) -> None:
        if not self.value.strip() or not self.kind.strip():
            raise OntologyError("alias value and kind are required")


@dataclass(frozen=True)
class EntityRelation:
    relation_id: str
    subject_id: str
    predicate: str
    object_id: str
    evidence_refs: tuple[str, ...]
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    confidence: float | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all(v.strip() for v in (self.relation_id, self.subject_id, self.predicate, self.object_id)):
            raise OntologyError("relation identifiers and predicate are required")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise OntologyError("relations require unique evidence references")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise OntologyError("relation valid_to must be after valid_from")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise OntologyError("relation confidence must be between 0 and 1")

    def is_valid_at(self, at: datetime) -> bool:
        return (
            (self.valid_from is None or self.valid_from <= at)
            and (self.valid_to is None or at < self.valid_to)
        )


@dataclass(frozen=True)
class OntologyEntity:
    entity_id: str
    entity_type: str
    evidence_refs: tuple[str, ...]
    identifiers: tuple[EntityIdentifier, ...] = ()
    aliases: tuple[EntityAlias, ...] = ()
    properties: Mapping[str, Any] = field(default_factory=dict)
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        if not self.entity_id.strip():
            raise OntologyError("entity_id is required")
        if self.entity_type not in ENTITY_TYPES:
            raise OntologyError(f"unsupported entity_type: {self.entity_type}")
        if not self.evidence_refs or len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise OntologyError("ontology entities require unique evidence references")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise OntologyError("entity valid_to must be after valid_from")
        keys = [(i.namespace, i.kind, i.value) for i in self.identifiers]
        if len(keys) != len(set(keys)):
            raise OntologyError("entity identifiers must be unique")

    def is_valid_at(self, at: datetime) -> bool:
        return (
            (self.valid_from is None or self.valid_from <= at)
            and (self.valid_to is None or at < self.valid_to)
        )
