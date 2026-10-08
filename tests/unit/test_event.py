from datetime import datetime, timezone

import pytest

from packages.contracts.event import Event, EventContractError


def make_event(**overrides):
    values = {
        "event_id": "event-1",
        "event_type": "aircraft-observed",
        "state": "observed",
        "occurred_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "evidence_refs": ("ev-1",),
        "payload": {"platform": "synthetic"},
    }
    values.update(overrides)
    return Event(**values)


@pytest.mark.parametrize("state", ["observed", "derived", "predicted"])
def test_all_event_states_are_explicit(state):
    event = make_event(state=state)
    assert event.state == state
    assert event.is_prediction is (state == "predicted")


def test_event_requires_provenance():
    with pytest.raises(EventContractError, match="evidence"):
        make_event(evidence_refs=())


def test_event_rejects_duplicate_evidence_refs():
    with pytest.raises(EventContractError, match="unique"):
        make_event(evidence_refs=("ev-1", "ev-1"))


def test_event_rejects_invalid_confidence():
    with pytest.raises(EventContractError, match="confidence"):
        make_event(confidence=1.1)


def test_event_rejects_invalid_temporal_interval():
    with pytest.raises(EventContractError, match="valid_to"):
        make_event(
            valid_from=datetime(2026, 1, 2, tzinfo=timezone.utc),
            valid_to=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
