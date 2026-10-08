"""Deterministic connector runner that delegates persistence to ingestion."""
from __future__ import annotations
from datetime import datetime, timedelta
from packages.connectors.contracts import Connector, ConnectorError, ConnectorRun, utc_now
from packages.connectors.registry import SourceRegistry
from services.ingestion.observation import ObservationIngestor


class ConnectorRunner:
    def __init__(self, registry: SourceRegistry, ingestor: ObservationIngestor) -> None:
        self.registry = registry
        self.ingestor = ingestor

    def run(self, connector: Connector, *, since: datetime | None = None, now: datetime | None = None) -> ConnectorRun:
        spec = self.registry.get(connector.spec.source)
        if spec != connector.spec:
            raise ConnectorError("connector specification does not match registered source")
        started = now or utc_now()
        seen = accepted = rejected = 0
        error = None
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
                    max_age=(timedelta(seconds=spec.max_age_seconds)
                             if spec.max_age_seconds is not None else None),
                )
                if result.accepted:
                    accepted += 1
                else:
                    rejected += 1
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        finished = now or utc_now()
        if finished < started:
            finished = started
        return ConnectorRun(spec.source, started, finished, seen, accepted, rejected, error)
