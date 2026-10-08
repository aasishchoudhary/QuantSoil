from datetime import datetime, timezone
from packages.connectors.contracts import SourceRecord, SourceSpec
from services.connectors.runner import ConnectorRunner
from services.ingestion.observation import ObservationIngestor

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

class Connector:
    spec = SourceSpec("evidence-source", "synthetic", "v1", "parser-v1")
    def fetch(self, *, since=None):
        return [SourceRecord("r1", {"value": 7}, T, T)]

class PayloadStore:
    def __init__(self):
        self.records = []
    def put(self, record):
        self.records.append(record)
        return ("s3://test/evidence.json", 11)

class MetadataStore:
    def __init__(self):
        self.calls = []
    def put(self, record, *, payload_uri=None, payload_size_bytes=None):
        self.calls.append((record, payload_uri, payload_size_bytes))
        return record

def test_accepted_evidence_is_persisted_before_run_success():
    payload = PayloadStore()
    metadata = MetadataStore()
    registry = type("R", (), {"get": lambda self, source: Connector.spec})()
    run = ConnectorRunner(
        registry, ObservationIngestor(),
        evidence_payload_store=payload,
        evidence_metadata_store=metadata,
    ).run(Connector(), now=T)
    assert run.error is None
    assert run.records_accepted == 1
    assert len(payload.records) == 1
    assert metadata.calls[0][1:] == ("s3://test/evidence.json", 11)

def test_evidence_persistence_failure_prevents_false_success():
    class BrokenStore:
        def put(self, record):
            raise RuntimeError("storage unavailable")
    registry = type("R", (), {"get": lambda self, source: Connector.spec})()
    run = ConnectorRunner(
        registry, ObservationIngestor(),
        evidence_payload_store=BrokenStore(),
    ).run(Connector(), now=T)
    assert run.error is not None
    assert run.records_accepted == 0
