"""Deterministic contradiction and evidence fusion primitives.

Conflicting assertions are preserved as separate candidates. Fusion ranks
candidates using explicit source weights and confidence, but only returns an
accepted value when the margin over the runner-up is sufficient.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping


class FusionError(ValueError):
    """Raised when fusion inputs violate the contract."""


@dataclass(frozen=True)
class Assertion:
    assertion_id: str
    entity_id: str
    property_name: str
    value: Any
    confidence: float
    source_weight: float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.assertion_id or not self.entity_id or not self.property_name:
            raise FusionError("assertion identity fields are required")
        if not 0 <= self.confidence <= 1:
            raise FusionError("confidence must be between 0 and 1")
        if not 0 <= self.source_weight <= 1:
            raise FusionError("source_weight must be between 0 and 1")
        if not self.evidence_refs or any(not ref for ref in self.evidence_refs):
            raise FusionError("evidence_refs are mandatory")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise FusionError("evidence_refs must be unique")

    @property
    def score(self) -> float:
        return self.confidence * self.source_weight


@dataclass(frozen=True)
class FusionResult:
    entity_id: str
    property_name: str
    status: str
    selected_assertion_id: str | None
    candidate_assertion_ids: tuple[str, ...]
    scores: Mapping[str, float]

    def __post_init__(self) -> None:
        if self.status not in {"accepted", "contradictory", "empty"}:
            raise FusionError("invalid fusion status")
        if self.status == "accepted" and self.selected_assertion_id is None:
            raise FusionError("accepted fusion requires a selected assertion")
        if self.status != "accepted" and self.selected_assertion_id is not None:
            raise FusionError("non-accepted fusion cannot select an assertion")


def fuse_assertions(
    assertions: list[Assertion],
    *,
    minimum_score: float = 0.5,
    minimum_margin: float = 0.1,
) -> FusionResult:
    """Rank competing assertions without erasing contradiction evidence."""
    if not 0 <= minimum_score <= 1:
        raise FusionError("minimum_score must be between 0 and 1")
    if not 0 <= minimum_margin <= 1:
        raise FusionError("minimum_margin must be between 0 and 1")
    if not assertions:
        return FusionResult("", "", "empty", None, (), {})

    entity_id = assertions[0].entity_id
    property_name = assertions[0].property_name
    if any(a.entity_id != entity_id or a.property_name != property_name for a in assertions):
        raise FusionError("all assertions must target the same entity property")

    ordered = sorted(assertions, key=lambda a: (-a.score, a.assertion_id))
    scores = {a.assertion_id: a.score for a in ordered}
    candidates = tuple(a.assertion_id for a in ordered)

    if len(ordered) == 1:
        accepted = ordered[0].score >= minimum_score
    else:
        accepted = (
            ordered[0].score >= minimum_score
            and ordered[0].score - ordered[1].score >= minimum_margin
        )

    return FusionResult(
        entity_id=entity_id,
        property_name=property_name,
        status="accepted" if accepted else "contradictory",
        selected_assertion_id=ordered[0].assertion_id if accepted else None,
        candidate_assertion_ids=candidates,
        scores=scores,
    )
