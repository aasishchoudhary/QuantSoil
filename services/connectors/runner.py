"""Deterministic connector runner that delegates persistence to ingestion."""
from __future__ import annotations

from datetime import datetime, timedelta
from time import sleep
from typing import Callable, Protocol

from packages.connectors.contracts import (
    Connector,
    ConnectorError,
    ConnectorRun,
    IngestionAudit,
    RejectedRecord,
    utc_now,
)
from packages.evaluation.data_quality import SourceHealth
from services.connectors.health import record_failure, record_success
from services.connectors.retry import RetryPolicy, RetryableConnectorError
from services.ingestion.observation import ObservationIngestor


class SourceHealthStore(Protocol):
    def get(self, source: str) -> SourceHealth | None: ...
    def put(self, health: SourceHealth) -> SourceHealth: ...


class ConnectorAuditStore(Protocol):
    def put_run(self, audit: IngestionAudit) -> IngestionAudit: ...
    def put_rejection(self, rejection: RejectedRecord) -> RejectedRecord: ...


class ConnectorRunner:
    def __init__(
        self,
        registry,
        ingestor: ObservationIngestor,
        *,
        retry_policy: RetryPolicy | None = None,
        sleep_fn: Callable[[float], None] = sleep,
        health_store: SourceHealthStore | None = None,
        audit_store: ConnectorAuditStore | None = None,
    ) -> None:
        self.registry = registry
        self.ingestor = ingestor
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleep_fn = sleep_fn
        self.health_store = health_store
        self.audit_store = audit_store
        self.last_audit: IngestionAudit | None = None
        self.last_rejections: list[RejectedRecord] = []

    def run(self, connector: Connector, *, since=None, now: datetime | None = None) -> ConnectorRun:
        spec = self.registry.get(connector.spec.source)
        if spec != connector.spec:
            raise ConnectorError("connector specification does not match registered source")
        started = now or utc_now()
        seen = accepted = rejected = 0
        error = None
        error_type = None
        attempts = 0
        self.last_audit = None
        self.last_rejections = []
        max_age = timedelta(seconds=spec.max_age_seconds) if spec.max_age_seconds is not None else None

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
                        max_age=max_age,
                    )
                    if result.accepted:
                        accepted += 1
                    else:
                        rejected += 1
                        self.last_rejections.append(RejectedRecord(
                            rejection_id=RejectedRecord.deterministic_id(
                                f"run_{spec.source}_{started.isoformat()}", spec.source,
                                record.source_record_id, result.evidence.raw_payload_hash,
                            ),
                            run_id=f"run_{spec.source}_{started.isoformat()}",
                            source=spec.source,
                            source_record_id=record.source_record_id,
                            raw_payload_hash=result.evidence.raw_payload_hash,
                            status=result.quality.status.value if not result.duplicate else "duplicate",
                            reasons=result.quality.reasons or (("duplicate",) if result.duplicate else ("rejected",)),
                            observed_at=record.observed_at,
                            rejected_at=started,
                            payload=record.payload,
                        ))
                self._health_success(spec.source, started)
                error = None
                error_type = None
                break
            except RetryableConnectorError as exc:
                error = f"{type(exc).__name__}: {exc}"
                error_type = type(exc).__name__
                if attempt == self.retry_policy.max_attempts:
                    self._health_failure(spec.source, started)
                    break
                self.sleep_fn(self.retry_policy.delay_for(
                    attempt, retry_after=exc.retry_after
                ).total_seconds())
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                error_type = type(exc).__name__
                self._health_failure(spec.source, started)
                break

        finished = now or utc_now()
        if finished < started:
            finished = started
        run = ConnectorRun(
            spec.source, started, finished, seen, accepted, rejected,
            error, attempts, error_type,
        )
        audit = IngestionAudit(
            run_id=f"run_{spec.source}_{started.isoformat()}",
            source=spec.source,
            started_at=started,
            finished_at=finished,
            records_seen=seen,
            records_accepted=accepted,
            records_rejected=rejected,
            attempts=attempts,
            error_type=error_type,
        )
        self.last_audit = audit
        if self.audit_store is not None:
            self.audit_store.put_run(audit)
            for rejection in self.last_rejections:
                self.audit_store.put_rejection(rejection)
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
