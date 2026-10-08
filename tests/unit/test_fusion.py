import pytest

from packages.contracts.fusion import Assertion, FusionError, fuse_assertions


def assertion(assertion_id, value, confidence, weight):
    return Assertion(
        assertion_id=assertion_id,
        entity_id="e-1",
        property_name="status",
        value=value,
        confidence=confidence,
        source_weight=weight,
        evidence_refs=(f"ev-{assertion_id}",),
    )


def test_fusion_accepts_clear_winner():
    result = fuse_assertions(
        [assertion("a", "active", 0.95, 1.0), assertion("b", "inactive", 0.5, 0.8)],
        minimum_score=0.5,
        minimum_margin=0.1,
    )
    assert result.status == "accepted"
    assert result.selected_assertion_id == "a"
    assert result.candidate_assertion_ids == ("a", "b")


def test_fusion_preserves_contradiction_when_margin_is_insufficient():
    result = fuse_assertions(
        [assertion("a", "active", 0.8, 1.0), assertion("b", "inactive", 0.75, 1.0)],
        minimum_score=0.5,
        minimum_margin=0.1,
    )
    assert result.status == "contradictory"
    assert result.selected_assertion_id is None
    assert result.candidate_assertion_ids == ("a", "b")


def test_fusion_rejects_mixed_targets():
    other = Assertion(
        assertion_id="b",
        entity_id="e-2",
        property_name="status",
        value="inactive",
        confidence=0.9,
        source_weight=1.0,
        evidence_refs=("ev-b",),
    )
    with pytest.raises(FusionError):
        fuse_assertions([assertion("a", "active", 0.9, 1.0), other])


def test_fusion_requires_evidence_and_bounded_scores():
    with pytest.raises(FusionError):
        assertion("a", "active", 1.1, 1.0)
    with pytest.raises(FusionError):
        assertion("a", "active", 0.9, 1.0)._replace() if False else Assertion(
            assertion_id="a", entity_id="e-1", property_name="status",
            value="active", confidence=0.9, source_weight=1.0, evidence_refs=()
        )


def test_empty_fusion_is_explicit():
    result = fuse_assertions([])
    assert result.status == "empty"
    assert result.selected_assertion_id is None
