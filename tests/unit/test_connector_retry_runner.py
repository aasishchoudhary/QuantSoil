from datetime import datetime, timedelta, timezone
from packages.connectors.contracts import SourceRecord, SourceSpec
from packages.connectors.registry import SourceRegistry
from services.connectors.retry import RetryableConnectorError
from services.connectors.runner import ConnectorRunner
from services.ingestion.observation import ObservationIngestor

T = datetime(2026, 1, 1, tzinfo=timezone.utc)


class RetryOnceConnector:
    spec = SourceSpec("retry-source", "synthetic", "v1", "parser-v1")

    def __init__(self):
        self.calls = 0

    def fetch(self, *, since=None):
        self.calls += 1
        if self.calls == 1:
            raise RetryableConnectorError("temporarily unavailable", retry_after=timedelta(seconds=7))
        return [SourceRecord("r1", {"x": 1}, T, T)]


class HealthStore:
    def __init__(self):
        self.value = None

    def get(self, source):
        return self.value

    def put(self, health):
        self.value = health
        return health


class AuditStore:
    def __init__(self):
        self.runs = []

    def put_run(self, audit):
        self.runs.append(audit)
        return audit

    def put_rejection(self, rejection):
        raise AssertionError("no rejection expected")


def test_runner_retries_and_honors_retry_after():
    registry = SourceRegistry()
    registry.register(RetryOnceConnector.spec)
    connector = RetryOnceConnector()
    delays = []
    audit = AuditStore()
    run = ConnectorRunner(
        registry, ObservationIngestor(),
        sleep_fn=delays.append,
        audit_store=audit,
    ).run(connector, now=T)
    assert connector.calls == 2
    assert delays == [7.0]
    assert run.records_accepted == 1
    assert run.error is None
    assert run.attempts == 2
    assert run.error_type is None
    assert audit.runs[0].attempts == 2


def test_runner_persists_recovery_health():
    registry = SourceRegistry()
    registry.register(RetryOnceConnector.spec)
    health = HealthStore()
    run = ConnectorRunner(
        registry, ObservationIngestor(), health_store=health
    ).run(RetryOnceConnector(), now=T)
    assert run.error is None
    assert health.value.consecutive_failures == 0
