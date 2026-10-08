"""Connector contracts for governed external data ingestion.

Connectors fetch source records; they never write authoritative state directly.
The framework normalizes source metadata and hands records to the existing
ingestion boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Protocol


class ConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceSpec:
    source: str
    license_class: str
    schema_version: str
    parser_version: str
    max_age_seconds: int | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ConnectorError("source is required")
        if not self.license_class.strip():
            raise ConnectorError("license_class is required")
        if not self.schema_version.strip() or not self.parser_version.strip():
            raise ConnectorError("schema_version and parser_version are required")
        if self.max_age_seconds is not None and self.max_age_seconds < 0:
            raise ConnectorError("max_age_seconds cannot be negative")


@dataclass(frozen=True)
class SourceRecord:
    source_record_id: str
    payload: Mapping[str, Any]
    observed_at: datetime
    acquired_at: datetime

    def __post_init__(self) -> None:
        if not self.source_record_id.strip():
            raise ConnectorError("source_record_id is required")
        if self.observed_at.tzinfo is None or self.acquired_at.tzinfo is None:
            raise ConnectorError("record timestamps must be timezone-aware")
        if self.acquired_at < self.observed_at:
            raise ConnectorError("acquired_at cannot precede observed_at")
        if not isinstance(self.payload, Mapping) or not self.payload:
            raise ConnectorError("payload must be a non-empty mapping")


class Connector(Protocol):
    spec: SourceSpec

    def fetch(self, *, since: datetime | None = None) -> Iterable[SourceRecord]:
        """Fetch source records without mutating authoritative state."""


@dataclass(frozen=True)
class ConnectorRun:
    source: str
    started_at: datetime
    finished_at: datetime
    records_seen: int
    records_accepted: int
    records_rejected: int
    error: str | None = None

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ConnectorError("run timestamps must be timezone-aware")
        if self.finished_at < self.started_at:
            raise ConnectorError("finished_at cannot precede started_at")
        if min(self.records_seen, self.records_accepted, self.records_rejected) < 0:
            raise ConnectorError("record counts cannot be negative")
        if self.records_accepted + self.records_rejected > self.records_seen:
            raise ConnectorError("accepted + rejected cannot exceed records seen")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class IngestionAudit:
    run_id: str
    source: str
    started_at: datetime
    finished_at: datetime
    records_seen: int
    records_accepted: int
    records_rejected: int
    attempts: int
    error_type: str | None = None
    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ConnectorError("audit timestamps must be timezone-aware")
        if self.finished_at < self.started_at:
            raise ConnectorError("finished_at cannot precede started_at")
        if self.attempts < 1 or min(self.records_seen, self.records_accepted, self.records_rejected) < 0:
            raise ConnectorError("invalid audit counters")
        if self.records_accepted + self.records_rejected > self.records_seen:
            raise ConnectorError("accepted + rejected cannot exceed seen")


@dataclass(frozen=True)
class RejectedRecord:
    run_id: str
    source: str
    source_record_id: str
    raw_payload_hash: str
    status: str
    reasons: tuple[str, ...]
    observed_at: datetime
    rejected_at: datetime
    def __post_init__(self) -> None:
        if self.status not in {"stale", "invalid", "duplicate"}:
            raise ConnectorError("unsupported rejection status")
        if not self.reasons:
            raise ConnectorError("rejection reasons are required")

class USGSEarthquakeConnector:
    """No-key USGS real-time GeoJSON summary connector."""
    spec = SourceSpec(
        source="usgs-earthquake-geojson",
        license_class="public/open",
        schema_version="usgs-geojson-v1",
        parser_version="usgs-parser-v1",
        max_age_seconds=180,
    )

    def __init__(self, url: str = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson", *, fetcher=None):
        self.url = url
        self._fetcher = fetcher

    def fetch(self, *, since: datetime | None = None) -> Iterable[SourceRecord]:
        if self._fetcher is None:
            raise ConnectorError("USGS connector requires an injected fetcher in the runtime boundary")
        document = self._fetcher(self.url)
        generated = document.get("metadata", {}).get("generated")
        if not isinstance(document, Mapping) or document.get("type") != "FeatureCollection":
            raise ConnectorError("invalid USGS GeoJSON FeatureCollection")
        for feature in document.get("features", []):
            if not isinstance(feature, Mapping):
                continue
            properties = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            event_id = feature.get("id")
            event_ms = properties.get("time")
            if not event_id or not isinstance(event_ms, (int, float)):
                continue
            observed_at = datetime.fromtimestamp(event_ms / 1000.0, tz=timezone.utc)
            acquired_at = utc_now()
            payload = {"feature": feature, "feed_generated": generated}
            if since is not None and observed_at < since:
                continue
            yield SourceRecord(str(event_id), payload, observed_at, acquired_at)
