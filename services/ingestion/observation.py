"""Deterministic ingestion boundary for external observations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from packages.contracts.evidence import EvidenceRecord, payload_sha256
from packages.contracts.observation import Observation, Provenance
from packages.contracts.observation_evidence import observation_to_evidence
from packages.evaluation.data_quality import QualityResult, QualityStatus, assess_freshness, validate_schema


class IngestionError(ValueError):
    """Raised when an input cannot become a valid observation."""


@dataclass(frozen=True)
class IngestionResult:
    observation: Observation
    evidence: EvidenceRecord
    quality: QualityResult
    duplicate: bool

    @property
    def accepted(self) -> bool:
        return self.quality.status is QualityStatus.ACCEPTED and not self.duplicate


class ObservationIngestor:
    """Validate, quality-check, normalize, and deterministically deduplicate observations."""

    def __init__(self) -> None:
        self._seen: set[tuple[str, str, str]] = set()

    def ingest(
        self, *, source: str, source_record_id: str,
        payload: Mapping[str, Any], observed_at: datetime,
        acquired_at: datetime | None = None, license_class: str,
        parser_version: str, schema_version: str,
        now: datetime | None = None, max_age: timedelta | None = None,
        required_fields: frozenset[str] = frozenset(),
    ) -> IngestionResult:
        if not source.strip() or not source_record_id.strip():
            raise IngestionError("source and source_record_id are required")
        if not license_class.strip():
            raise IngestionError("license_class is required")
        if not parser_version.strip() or not schema_version.strip():
            raise IngestionError("parser_version and schema_version are required")
        if not isinstance(payload, Mapping) or not payload:
            raise IngestionError("payload must be a non-empty mapping")
        if observed_at.tzinfo is None:
            raise IngestionError("observed_at must be timezone-aware")
        if acquired_at is not None and acquired_at.tzinfo is None:
            raise IngestionError("acquired_at must be timezone-aware")
        if acquired_at is not None and acquired_at < observed_at:
            raise IngestionError("acquired_at cannot precede observed_at")
        effective_now = now or datetime.now(timezone.utc)
        if effective_now.tzinfo is None:
            raise IngestionError("now must be timezone-aware")

        schema_quality = validate_schema(payload, required_fields)
        if schema_quality.status is QualityStatus.INVALID:
            quality = schema_quality
        elif max_age is not None:
            quality = assess_freshness(observed_at, now=effective_now, max_age=max_age)
        else:
            quality = QualityResult(QualityStatus.ACCEPTED)

        normalized = dict(payload)
        raw_hash = payload_sha256(normalized)
        key = (source, source_record_id, raw_hash)
        duplicate = key in self._seen
        self._seen.add(key)

        observation = Observation(
            observation_id=f"{source}:{source_record_id}:{raw_hash}",
            source=source, source_record_id=source_record_id,
            observed_at=observed_at, acquired_at=acquired_at,
            ingested_at=effective_now, payload=normalized,
            provenance=Provenance(raw_payload_hash=raw_hash, parser_version=parser_version),
        )
        evidence = observation_to_evidence(
            observation, license_class=license_class, schema_version=schema_version
        )
        return IngestionResult(observation, evidence, quality, duplicate)
