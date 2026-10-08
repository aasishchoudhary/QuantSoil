from datetime import datetime, timezone
from packages.connectors.contracts import SourceRecord, SourceSpec
from packages.connectors.registry import SourceRegistry
from services.connectors.runner import ConnectorRunner
from services.ingestion.observation import ObservationIngestor

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

class FakeConnector:
    spec = SourceSpec("synthetic", "synthetic", "v1", "parser-v1", 300)
    def fetch(self, *, since=None):
        return [SourceRecord("r1", {"x": 1}, T, T)]

def test_runner_routes_records_through_ingestion():
    registry = SourceRegistry()
    registry.register(FakeConnector.spec)
    run = ConnectorRunner(registry, ObservationIngestor()).run(FakeConnector(), now=T)
    assert run.records_seen == 1
    assert run.records_accepted == 1
    assert run.records_rejected == 0
    assert run.error is None

class BrokenConnector(FakeConnector):
    def fetch(self, *, since=None):
        raise TimeoutError("source unavailable")

def test_runner_reports_source_failure_without_fabricating_records():
    registry = SourceRegistry()
    registry.register(BrokenConnector.spec)
    run = ConnectorRunner(registry, ObservationIngestor()).run(BrokenConnector(), now=T)
    assert run.records_seen == 0
    assert run.records_accepted == 0
    assert run.error.startswith("TimeoutError:")

def test_runner_exposes_audit_summary_and_rejection():
    registry = SourceRegistry()
    registry.register(SourceSpec("stale", "synthetic", "v1", "parser-v1", 1))
    connector = FakeConnector()
    connector.spec = registry.get("stale")
    run = ConnectorRunner(registry, ObservationIngestor()).run(connector, now=T.replace(hour=1))
    assert run.records_seen == 1
    assert run.records_rejected == 1
    assert run.records_accepted == 0
    assert run.error is None
