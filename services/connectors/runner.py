"""Deterministic connector runner that delegates persistence to ingestion."""
from __future__ import annotations

from datetime import datetime
from time import sleep
from typing import Callable, Protocol

from packages.connectors.contracts import Connector, ConnectorError, ConnectorRun, IngestionAudit, RejectedRecord, utc_now
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
        attempts = 0
        self.last_audit = None
        self.last_rejections = []

        for attempt in range(1, self.retry_policy.max_attempts + 1):
            attempts = attempt
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
                        self.last_rejections.append(RejectedRecord(
                            run_id=f"run_{spec.source}_{started.isoformat()}",
                            source=spec.source,
                            source_record_id=record.source_record_id,
                            raw_payload_hash=result.evidence.raw_payload_hash,
                            status=result.quality.status.value if not result.duplicate else "duplicate",
                            reasons=result.quality.reasons or (("duplicate",) if result.duplicate else ("rejected",)),
                            observed_at=record.observed_at,
                            rejected_at=started,
                        ))
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
        run = ConnectorRun(spec.source, started, finished, seen, accepted, rejected, error)
        self.last_audit = IngestionAudit(
            run_id=f"run_{spec.source}_{started.isoformat()}", source=spec.source,
            started_at=started, finished_at=finished, records_seen=seen,
            records_accepted=accepted, records_rejected=rejected, attempts=attempts,
            error_type=(error.split(':', 1)[0] if error else None),
        )
        return run

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
