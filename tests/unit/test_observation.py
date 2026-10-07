from datetime import datetime, timezone
from packages.contracts.observation import Observation, Provenance


def test_observation_payload_hash_is_deterministic():
    payload = {"b": 2, "a": 1}
    digest = Observation.payload_hash(payload)
    obs = Observation(
        observation_id="obs-1",
        source="test",
        source_record_id="record-1",
        observed_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        payload=payload,
        provenance=Provenance(digest, "test-v1"),
    )
    assert obs.verify_payload_hash()


def test_observation_hash_detects_tampering():
    payload = {"value": 1}
    obs = Observation(
        observation_id="obs-2",
        source="test",
        source_record_id="record-2",
        observed_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        payload=payload,
        provenance=Provenance("0" * 64, "test-v1"),
    )
    assert not obs.verify_payload_hash()
