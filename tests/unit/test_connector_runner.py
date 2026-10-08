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
    assert run.attempts == 1
    assert run.error_type is None


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
    assert run.error_type == "TimeoutError"


def test_runner_exposes_audit_summary_and_rejection():
    registry = SourceRegistry()
    stale_spec = SourceSpec("stale", "synthetic", "v1", "parser-v1", 1)
    registry.register(stale_spec)
    connector = FakeConnector()
    connector.spec = stale_spec
    run = ConnectorRunner(registry, ObservationIngestor()).run(
        connector, now=T.replace(hour=1)
    )
    assert run.records_seen == 1
    assert run.records_rejected == 1
    assert run.records_accepted == 0
    assert run.error is None
    assert run.attempts == 1
    assert ConnectorRunner(registry, ObservationIngestor()).run is not None


class AuditStore:
    def __init__(self):
        self.runs = []
        self.rejections = []

    def put_run(self, audit):
        self.runs.append(audit)
        return audit

    def put_rejection(self, rejection):
        self.rejections.append(rejection)
        return rejection


def test_runner_persists_audit_and_rejections():
    registry = SourceRegistry()
    stale_spec = SourceSpec("stale-audit", "synthetic", "v1", "parser-v1", 1)
    registry.register(stale_spec)
    connector = FakeConnector()
    connector.spec = stale_spec
    audit = AuditStore()
    runner = ConnectorRunner(registry, ObservationIngestor(), audit_store=audit)
    run = runner.run(connector, now=T.replace(hour=1))
    assert run.records_rejected == 1
    assert audit.runs[0] == runner.last_audit
    assert audit.runs[0].records_rejected == 1
    assert len(audit.rejections) == 1
    assert audit.rejections[0].run_id == audit.runs[0].run_id
