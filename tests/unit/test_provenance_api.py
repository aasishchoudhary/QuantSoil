from datetime import datetime, timezone

import pytest

from packages.contracts.evidence import InMemoryEvidenceLedger
from packages.contracts.event import Event
from packages.contracts.observation import Observation, Provenance
from packages.contracts.observation_evidence import observation_to_evidence
from services.provenance.api import InMemoryProvenanceRepository, ProvenanceNotFoundError


def make_observation():
    payload = {"value": 7}
    digest = Observation.payload_hash(payload)
    return Observation(
        observation_id="obs-1",
        source="synthetic",
        source_record_id="r-1",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        payload=payload,
        provenance=Provenance(digest, "parser-v1"),
    )


def test_observation_trace_resolves_source_metadata():
    observation = make_observation()
    evidence = observation_to_evidence(observation, license_class="synthetic")
    repo = InMemoryProvenanceRepository(InMemoryEvidenceLedger())
    repo.add_observation(observation)
    repo.add_evidence(evidence)

    trace = repo.trace("observation", "obs-1")
    assert trace.evidence[0].evidence_id == evidence.evidence_id
    assert trace.evidence[0].source == "synthetic"
    assert trace.evidence[0].raw_payload_hash == evidence.raw_payload_hash


def test_event_trace_resolves_all_evidence_refs():
    observation = make_observation()
    evidence = observation_to_evidence(observation, license_class="synthetic")
    event = Event(
        event_id="event-1",
        event_type="derived-event",
        state="derived",
        occurred_at=observation.observed_at,
        evidence_refs=(evidence.evidence_id,),
        payload={"value": 7},
    )
    repo = InMemoryProvenanceRepository()
    repo.add_evidence(evidence)
    repo.add_event(event)

    trace = repo.trace("event", "event-1")
    assert [item.evidence_id for item in trace.evidence] == [evidence.evidence_id]


def test_missing_evidence_is_explicit():
    observation = make_observation()
    repo = InMemoryProvenanceRepository()
    repo.add_observation(observation)

    with pytest.raises(ProvenanceNotFoundError, match="evidence missing"):
        repo.trace("observation", "obs-1")


def test_missing_event_is_explicit():
    repo = InMemoryProvenanceRepository()
    with pytest.raises(ProvenanceNotFoundError, match="event not found"):
        repo.trace("event", "missing")
