from datetime import datetime, timedelta, timezone
import pytest

from packages.evaluation.data_quality import QualityStatus
from services.ingestion.observation import IngestionError, ObservationIngestor

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
ARGS = dict(license_class="public", parser_version="parser-1", schema_version="observation-v1")

def test_ingestion_is_deterministically_deduplicated():
    ingestor = ObservationIngestor()
    first = ingestor.ingest(
        source="sensor", source_record_id="42", payload={"b": 2, "a": 1},
        observed_at=T, now=T, **ARGS
    )
    second = ingestor.ingest(
        source="sensor", source_record_id="42", payload={"a": 1, "b": 2},
        observed_at=T, now=T, **ARGS
    )
    assert first.duplicate is False
    assert second.duplicate is True
    assert first.accepted is True
    assert second.accepted is False
    assert first.observation.provenance.raw_payload_hash == second.observation.provenance.raw_payload_hash
    assert first.evidence.evidence_id == second.evidence.evidence_id

def test_ingestion_rejects_naive_timestamps():
    with pytest.raises(IngestionError, match="timezone-aware"):
        ObservationIngestor().ingest(
            source="sensor", source_record_id="1", payload={"x": 1},
            observed_at=datetime(2026, 1, 1), **ARGS
        )

def test_ingestion_rejects_acquisition_before_observation():
    with pytest.raises(IngestionError, match="cannot precede"):
        ObservationIngestor().ingest(
            source="sensor", source_record_id="1", payload={"x": 1},
            observed_at=T, acquired_at=T - timedelta(seconds=1), **ARGS
        )

def test_ingestion_preserves_provenance_metadata():
    result = ObservationIngestor().ingest(
        source="licensed-feed", source_record_id="abc", payload={"x": 1},
        observed_at=T, acquired_at=T, now=T, license_class="licensed-commercial",
        parser_version="parser-2", schema_version="schema-3",
    )
    assert result.observation.provenance.parser_version == "parser-2"
    assert result.evidence.license_class == "licensed-commercial"
    assert result.evidence.schema_version == "schema-3"

def test_stale_observation_is_explicitly_not_accepted():
    result = ObservationIngestor().ingest(
        source="sensor", source_record_id="stale", payload={"x": 1},
        observed_at=T, now=T + timedelta(minutes=11), max_age=timedelta(minutes=10),
        **ARGS
    )
    assert result.quality.status is QualityStatus.STALE
    assert result.accepted is False

def test_schema_drift_is_explicitly_invalid():
    result = ObservationIngestor().ingest(
        source="sensor", source_record_id="schema", payload={"id": "x"},
        observed_at=T, now=T, required_fields=frozenset({"id", "value"}), **ARGS
    )
    assert result.quality.status is QualityStatus.INVALID
    assert result.accepted is False
