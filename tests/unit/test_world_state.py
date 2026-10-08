from datetime import datetime, timezone

import pytest

from packages.contracts.world_state import EntityState, InMemoryWorldStateRepository, WorldStateError


def state(state_id, entity_id, valid_from, **overrides):
    values = {
        "state_id": state_id,
        "entity_id": entity_id,
        "entity_type": "aircraft",
        "valid_from": valid_from,
        "valid_to": None,
        "observed_at": valid_from,
        "recorded_at": valid_from,
        "properties": {"status": "active"},
        "evidence_refs": ("ev-1",),
    }
    values.update(overrides)
    return EntityState(**values)


def test_state_requires_temporal_and_evidence_integrity():
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(WorldStateError):
        state("s-1", "e-1", at, evidence_refs=())
    with pytest.raises(WorldStateError):
        state("s-1", "e-1", at, valid_to=at)
    with pytest.raises(WorldStateError):
        state("s-1", "e-1", at, confidence=1.1)


def test_history_is_append_only_and_as_of_is_temporal():
    repo = InMemoryWorldStateRepository()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    repo.append(state("s-1", "e-1", t1, valid_to=t2))
    repo.append(state("s-2", "e-1", t2, properties={"status": "inactive"}))

    assert [item.state_id for item in repo.history("e-1")] == ["s-1", "s-2"]
    assert repo.as_of("e-1", datetime(2026, 1, 1, 12, tzinfo=timezone.utc)).state_id == "s-1"
    assert repo.as_of("e-1", t2).state_id == "s-2"


def test_as_of_returns_none_when_no_state_is_valid():
    repo = InMemoryWorldStateRepository()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.append(state("s-1", "e-1", t1, valid_to=datetime(2026, 1, 2, tzinfo=timezone.utc)))
    assert repo.as_of("e-1", datetime(2026, 1, 3, tzinfo=timezone.utc)) is None


def test_duplicate_state_id_is_rejected():
    repo = InMemoryWorldStateRepository()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.append(state("s-1", "e-1", t1))
    with pytest.raises(WorldStateError, match="duplicate"):
        repo.append(state("s-1", "e-1", t1))

def test_overlapping_validity_intervals_are_rejected():
    repo = InMemoryWorldStateRepository()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 3, tzinfo=timezone.utc)
    repo.append(state("s-1", "e-1", t1, valid_to=t2))
    with pytest.raises(WorldStateError, match="overlapping"):
        repo.append(
            state(
                "s-2",
                "e-1",
                datetime(2026, 1, 2, tzinfo=timezone.utc),
                valid_to=datetime(2026, 1, 4, tzinfo=timezone.utc),
            )
        )
