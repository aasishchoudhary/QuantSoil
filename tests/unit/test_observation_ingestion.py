from datetime import datetime, timedelta, timezone
import pytest

from services.ingestion.observation import IngestionError, ObservationIngestor

T = datetime(2026, 1, 1, tzinfo=timezone.utc)
ARGS = dict(license_class="public", parser_version="parser-1", schema_version="observation-v1")

def ingest(ingestor, **kwargs):
    return ingestor.ingest(
        source="sensor", source_record_id="42", payload={"b": 2, "a": 1},
        observed_at=T, **ARGS, **kwargs
    )

def test_ingestion_is_deterministically_deduplicated():
    ingestor = ObservationIngestor()
    first = ingest(ingestor)
    second = ingestor.ingest(
        source="sensor", source_record_id="42", payload={"a": 1, "b": 2},
        observed_at=T, **ARGS
    )
    assert first.duplicate is False
    assert second.duplicate is True
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
        observed_at=T, acquired_at=T, license_class="licensed-commercial",
        parser_version="parser-2", schema_version="schema-3",
    )
    assert result.observation.provenance.parser_version == "parser-2"
    assert result.evidence.license_class == "licensed-commercial"
    assert result.evidence.schema_version == "schema-3"
