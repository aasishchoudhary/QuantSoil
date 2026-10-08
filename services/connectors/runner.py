"""Deterministic connector runner that delegates persistence to ingestion."""
from __future__ import annotations

from datetime import datetime
from time import sleep
from typing import Callable, Protocol

from packages.connectors.contracts import Connector, ConnectorError, ConnectorRun, utc_now
from packages.evaluation.data_quality import SourceHealth
from services.connectors.health import record_failure, record_success
from services.connectors.retry import RetryPolicy, RetryableConnectorError
from services.ingestion.observation import ObservationIngestor


class SourceHealthStore(Protocol):
    def get(self, source: str) -> SourceHealth | None: ...
    def put(self, health: SourceHealth) -> SourceHealth: ...


class ConnectorRunner:
    def __init__(
        self,
        registry,
        ingestor: ObservationIngestor,
        *,
        retry_policy: RetryPolicy | None = None,
        sleep_fn: Callable[[float], None] = sleep,
        health_store: SourceHealthStore | None = None,
    ) -> None:
        self.registry = registry
        self.ingestor = ingestor
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleep_fn = sleep_fn
        self.health_store = health_store

    def run(self, connector: Connector, *, since=None, now: datetime | None = None) -> ConnectorRun:
        spec = self.registry.get(connector.spec.source)
        if spec != connector.spec:
            raise ConnectorError("connector specification does not match registered source")
        started = now or utc_now()
        seen = accepted = rejected = 0
        error = None

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                for record in connector.fetch(since=since):
                    seen += 1
                    result = self.ingestor.ingest(
                        source=spec.source,
                        source_record_id=record.source_record_id,
                        payload=record.payload,
                        observed_at=record.observed_at,
                        acquired_at=record.acquired_at,
                        license_class=spec.license_class,
                        parser_version=spec.parser_version,
                        schema_version=spec.schema_version,
                        now=started,
                    )
                    if result.accepted:
                        accepted += 1
                    else:
                        rejected += 1
                self._health_success(spec.source, started)
                break
            except RetryableConnectorError as exc:
                error = f"{type(exc).__name__}: {exc}"
                if attempt == self.retry_policy.max_attempts:
                    self._health_failure(spec.source, started)
                    break
                self.sleep_fn(self.retry_policy.delay_for(
                    attempt, retry_after=exc.retry_after
                ).total_seconds())
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                self._health_failure(spec.source, started)
                break

        finished = now or utc_now()
        if finished < started:
            finished = started
        return ConnectorRun(spec.source, started, finished, seen, accepted, rejected, error)

    def _health_success(self, source: str, timestamp: datetime) -> None:
        if self.health_store is not None:
            self.health_store.put(record_success(
                self.health_store.get(source), source=source, observed_at=timestamp, recorded_at=timestamp
            ))

    def _health_failure(self, source: str, timestamp: datetime) -> None:
        if self.health_store is not None:
            self.health_store.put(record_failure(
                self.health_store.get(source), source=source, observed_at=timestamp, recorded_at=timestamp
            ))
