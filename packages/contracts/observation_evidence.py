"""Deterministic bridge from observations to immutable evidence."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from .evidence import EvidenceIntegrityError, EvidenceRecord
from .observation import Observation

_EVIDENCE_NAMESPACE = uuid5(
    NAMESPACE_URL, "https://gods-eye-world-intelligence.dev/evidence"
)


@dataclass(frozen=True)
class ObservationEvidenceLink:
    """Stable reference connecting an observation to its evidence record."""

    observation_id: str
    evidence_id: str
    source: str
    source_record_id: str
    raw_payload_hash: str

    def __post_init__(self) -> None:
        try:
            UUID(self.evidence_id)
        except ValueError as exc:
            raise ValueError("evidence_id must be a UUID") from exc


def evidence_id_for_observation(observation: Observation) -> str:
    """Return a stable evidence UUID for the immutable observation identity."""
    if not observation.verify_payload_hash():
        raise EvidenceIntegrityError("observation payload hash does not match payload")
    identity = (
        f"{observation.source}\x1f"
        f"{observation.source_record_id}\x1f"
        f"{observation.provenance.raw_payload_hash}"
    )
    return str(uuid5(_EVIDENCE_NAMESPACE, identity))


def observation_to_evidence(
    observation: Observation,
    *,
    schema_version: str,
    license_class: str,
) -> tuple[EvidenceRecord, ObservationEvidenceLink]:
    """Convert a validated observation into an evidence record and explicit link."""
    if not schema_version:
        raise ValueError("schema_version must not be empty")
    if not license_class:
        raise ValueError("license_class must not be empty")
    if not observation.verify_payload_hash():
        raise EvidenceIntegrityError("observation payload hash does not match payload")

    record = EvidenceRecord(
        evidence_id=evidence_id_for_observation(observation),
        source=observation.source,
        source_record_id=observation.source_record_id,
        observed_at=observation.observed_at,
        ingested_at=observation.ingested_at,
        payload=dict(observation.payload),
        raw_payload_hash=observation.provenance.raw_payload_hash,
        parser_version=observation.provenance.parser_version,
        schema_version=schema_version,
        license_class=license_class,
    )
    link = ObservationEvidenceLink(
        observation_id=observation.observation_id,
        evidence_id=record.evidence_id,
        source=record.source,
        source_record_id=record.source_record_id,
        raw_payload_hash=record.raw_payload_hash,
    )
    return record, link
