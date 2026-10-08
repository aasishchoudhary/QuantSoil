"""Deterministic bridge from validated observations to immutable evidence."""

from __future__ import annotations

import uuid

from packages.contracts.evidence import EvidenceRecord, EvidenceIntegrityError
from packages.contracts.observation import Observation


class ObservationEvidenceError(ValueError):
    """Raised when an observation cannot be converted into evidence."""


def observation_to_evidence(
    observation: Observation,
    *,
    license_class: str,
    schema_version: str = "evidence-v1",
) -> EvidenceRecord:
    """Convert a validated observation into an immutable evidence record.

    The evidence identity is deterministic for the observation's source,
    source record, and payload hash. No timestamps or random values affect it.
    """
    if not license_class:
        raise ObservationEvidenceError("license_class is required")
    if not schema_version:
        raise ObservationEvidenceError("schema_version is required")
    if not observation.verify_payload_hash():
        raise ObservationEvidenceError("observation payload hash verification failed")

    evidence_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "|".join(
                (
                    observation.source,
                    observation.source_record_id,
                    observation.provenance.raw_payload_hash,
                )
            ),
        )
    )
    try:
        return EvidenceRecord(
            evidence_id=evidence_id,
            source=observation.source,
            source_record_id=observation.source_record_id,
            observed_at=observation.observed_at,
            acquired_at=observation.acquired_at,
            ingested_at=observation.ingested_at,
            payload=observation.payload,
            raw_payload_hash=observation.provenance.raw_payload_hash,
            parser_version=observation.provenance.parser_version,
            schema_version=schema_version,
            license_class=license_class,
        )
    except EvidenceIntegrityError as exc:
        raise ObservationEvidenceError("observation cannot satisfy evidence contract") from exc
