"""Deterministic ingestion boundary for external observations."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

from packages.contracts.observation import Observation
from packages.contracts.observation_evidence import observation_to_evidence


class IngestionError(ValueError):
    """Raised when an input cannot become a valid observation."""


@dataclass(frozen=True)
class IngestionResult:
    observation: Observation
    evidence: Any
    duplicate: bool


def _canonical_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


class ObservationIngestor:
    """Validate, normalize and deduplicate observations before persistence."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def ingest(
        self,
        *,
        source: str,
        source_record_id: str,
        payload: Mapping[str, Any],
        observed_at: datetime,
        acquired_at: datetime | None = None,
        license_terms: str | None = None,
        parser_version: str = "unknown",
        schema_version: str = "1",
    ) -> IngestionResult:
        if not source.strip() or not source_record_id.strip():
            raise IngestionError("source and source_record_id are required")
        if not isinstance(payload, Mapping) or not payload:
            raise IngestionError("payload must be a non-empty mapping")
        if observed_at.tzinfo is None:
            raise IngestionError("observed_at must be timezone-aware")
        if acquired_at is not None and acquired_at.tzinfo is None:
            raise IngestionError("acquired_at must be timezone-aware")
        if acquired_at is not None and acquired_at < observed_at:
            raise IngestionError("acquired_at cannot precede observed_at")

        raw_hash = _canonical_hash(payload)
        dedupe_key = f"{source}:{source_record_id}:{raw_hash}"
        duplicate = dedupe_key in self._seen
        self._seen.add(dedupe_key)

        observation = Observation(
            observation_id=dedupe_key,
            source=source,
            source_record_id=source_record_id,
            observed_at=observed_at,
            acquired_at=acquired_at,
            ingested_at=datetime.now(timezone.utc),
            payload=dict(payload),
            raw_payload_hash=raw_hash,
            license_terms=license_terms,
            parser_version=parser_version,
            schema_version=schema_version,
        )
        evidence = observation_to_evidence(observation)
        return IngestionResult(observation=observation, evidence=evidence, duplicate=duplicate)
