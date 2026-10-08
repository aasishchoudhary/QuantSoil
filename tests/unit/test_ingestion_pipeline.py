from datetime import datetime, timedelta, timezone
from packages.contracts.evidence import InMemoryEvidenceLedger
from packages.evaluation.data_quality import QualityStatus
from services.ingestion.observation import ObservationIngestor
from services.ingestion.pipeline import IngestionPipeline

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def test_stale_data_is_preserved_as_evidence_but_blocked_from_authoritative_state():
    pipeline = IngestionPipeline(
        ingestor=ObservationIngestor(),
        evidence_ledger=InMemoryEvidenceLedger(),
    )
    outcome = pipeline.process(
        source="sensor", source_record_id="1", payload={"x": 1},
        observed_at=T, now=T + timedelta(hours=1), max_age=timedelta(minutes=5),
        license_class="public", parser_version="p1", schema_version="s1",
    )
    assert outcome.result.quality.status is QualityStatus.STALE
    assert outcome.evidence_stored is True
    assert outcome.may_enter_authoritative_state is False
