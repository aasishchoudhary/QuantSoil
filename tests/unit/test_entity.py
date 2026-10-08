import pytest

from packages.contracts.entity import Entity, EntityMatch, EntityResolutionError, resolve_candidates


def entity(entity_id="e-1", **overrides):
    values = {
        "entity_id": entity_id,
        "entity_type": "aircraft",
        "confidence": 0.8,
        "evidence_refs": ("ev-1",),
    }
    values.update(overrides)
    return Entity(**values)


def test_entity_requires_evidence_and_valid_confidence():
    with pytest.raises(EntityResolutionError):
        entity(evidence_refs=())
    with pytest.raises(EntityResolutionError):
        entity(confidence=1.1)


def test_entity_match_is_uncertain_and_evidence_backed():
    match = EntityMatch(
        entity_id="e-1",
        observation_id="obs-1",
        score=0.72,
        method="synthetic-rule-v1",
        evidence_refs=("ev-1",),
    )
    assert match.score == 0.72


def test_candidate_resolution_preserves_multiple_qualifying_candidates():
    result = resolve_candidates(
        "obs-1",
        [(entity("e-2"), 0.61), (entity("e-1"), 0.91), (entity("e-3"), 0.4)],
        method="synthetic-rule-v1",
        evidence_refs=("ev-1",),
        threshold=0.5,
    )
    assert [item.entity_id for item in result] == ["e-1", "e-2"]
    assert [item.score for item in result] == [0.91, 0.61]


def test_candidate_resolution_rejects_invalid_threshold():
    with pytest.raises(EntityResolutionError):
        resolve_candidates("obs-1", [], method="test", evidence_refs=("ev-1",), threshold=1.1)


def test_candidate_resolution_does_not_force_identity():
    result = resolve_candidates(
        "obs-1",
        [(entity("e-1"), 0.49)],
        method="synthetic-rule-v1",
        evidence_refs=("ev-1",),
        threshold=0.5,
    )
    assert result == ()
