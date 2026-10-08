from datetime import datetime, timezone

import pytest

from packages.contracts.observation import Observation, Provenance
from packages.contracts.observation_evidence import (
    ObservationEvidenceError,
    observation_to_evidence,
)


def make_observation(payload=None):
    payload = payload or {"b": 2, "a": 1}
    digest = Observation.payload_hash(payload)
    return Observation(
        observation_id="obs-1",
        source="synthetic",
        source_record_id="record-1",
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        acquired_at=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        payload=payload,
        provenance=Provenance(digest, "parser-v1"),
    )


def test_bridge_is_deterministic_and_preserves_identity():
    first = observation_to_evidence(make_observation(), license_class="synthetic")
    second = observation_to_evidence(make_observation(), license_class="synthetic")

    assert first == second
    assert first.source == "synthetic"
    assert first.source_record_id == "record-1"
    assert first.raw_payload_hash == Observation.payload_hash(first.payload)
    assert first.parser_version == "parser-v1"
    assert first.observed_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert first.acquired_at == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_bridge_rejects_tampered_observation():
    observation = make_observation()
    tampered = Observation(
        observation_id=observation.observation_id,
        source=observation.source,
        source_record_id=observation.source_record_id,
        observed_at=observation.observed_at,
        ingested_at=observation.ingested_at,
        payload={"b": 999, "a": 1},
        provenance=observation.provenance,
    )
    with pytest.raises(ObservationEvidenceError, match="hash"):
        observation_to_evidence(tampered, license_class="synthetic")


def test_bridge_requires_license_class():
    with pytest.raises(ObservationEvidenceError):
        observation_to_evidence(make_observation(), license_class="")
