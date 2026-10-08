from datetime import datetime, timezone

import pytest

from packages.contracts.evidence import EvidenceIntegrityError, payload_sha256
from packages.contracts.observation import Observation, Provenance
from packages.contracts.observation_evidence import observation_to_evidence


def make_observation(payload=None, digest=None):
    payload = payload or {"asset": "synthetic", "value": 2650.5}
    digest = digest or payload_sha256(payload)
    return Observation(
        observation_id="obs-001",
        source="synthetic-feed",
        source_record_id="record-001",
        observed_at=datetime(2026, 10, 8, 4, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 10, 8, 4, 0, 1, tzinfo=timezone.utc),
        payload=payload,
        provenance=Provenance(digest, "parser-v1"),
    )


def test_bridge_preserves_provenance_and_temporal_metadata():
    observation = make_observation()
    evidence, link = observation_to_evidence(
        observation, schema_version="evidence-v1", license_class="synthetic"
    )
    assert evidence.source == observation.source
    assert evidence.source_record_id == observation.source_record_id
    assert evidence.observed_at == observation.observed_at
    assert evidence.ingested_at == observation.ingested_at
    assert evidence.parser_version == observation.provenance.parser_version
    assert evidence.raw_payload_hash == observation.provenance.raw_payload_hash
    assert link.observation_id == observation.observation_id
    assert link.evidence_id == evidence.evidence_id


def test_evidence_identity_is_replay_deterministic():
    observation = make_observation()
    first, first_link = observation_to_evidence(
        observation, schema_version="evidence-v1", license_class="synthetic"
    )
    second, second_link = observation_to_evidence(
        observation, schema_version="evidence-v1", license_class="synthetic"
    )
    assert first.evidence_id == second.evidence_id
    assert first_link == second_link


def test_tampered_observation_is_rejected():
    with pytest.raises(EvidenceIntegrityError, match="hash"):
        observation_to_evidence(
            make_observation(digest="0" * 64),
            schema_version="evidence-v1",
            license_class="synthetic",
        )


@pytest.mark.parametrize(
    ("schema_version", "license_class"),
    [("", "synthetic"), ("evidence-v1", "")],
)
def test_required_evidence_metadata_is_rejected(schema_version, license_class):
    with pytest.raises(ValueError):
        observation_to_evidence(
            make_observation(),
            schema_version=schema_version,
            license_class=license_class,
        )


def test_payload_is_copied_at_bridge_boundary():
    payload = {"value": 1}
    observation = make_observation(payload)
    evidence, _ = observation_to_evidence(
        observation, schema_version="evidence-v1", license_class="synthetic"
    )
    payload["value"] = 99
    assert evidence.payload["value"] == 1
