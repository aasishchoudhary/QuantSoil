"""Deterministic provenance tracing service.

The in-memory implementation is infrastructure-neutral and is intended to
establish the service contract before wiring PostgreSQL/object storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from packages.contracts.evidence import EvidenceRecord, InMemoryEvidenceLedger
from packages.contracts.event import Event
from packages.contracts.observation import Observation


TraceKind = Literal["observation", "event"]


@dataclass(frozen=True)
class EvidenceTrace:
    evidence_id: str
    source: str
    source_record_id: str
    raw_payload_hash: str
    observed_at: str
    parser_version: str
    schema_version: str
    license_class: str


@dataclass(frozen=True)
class ProvenanceTrace:
    kind: TraceKind
    object_id: str
    evidence: tuple[EvidenceTrace, ...]


class ProvenanceNotFoundError(LookupError):
    """Raised when the requested object or evidence cannot be traced."""


class InMemoryProvenanceRepository:
    def __init__(self, evidence: InMemoryEvidenceLedger | None = None) -> None:
        self._evidence = evidence or InMemoryEvidenceLedger()
        self._observations: dict[str, Observation] = {}
        self._events: dict[str, Event] = {}

    def add_observation(self, observation: Observation) -> None:
        if not observation.verify_payload_hash():
            raise ValueError("observation payload hash verification failed")
        self._observations[observation.observation_id] = observation

    def add_event(self, event: Event) -> None:
        self._events[event.event_id] = event

    def add_evidence(self, record: EvidenceRecord) -> None:
        self._evidence.put(record)

    def trace(self, kind: TraceKind, object_id: str) -> ProvenanceTrace:
        if kind == "observation":
            observation = self._observations.get(object_id)
            if observation is None:
                raise ProvenanceNotFoundError(f"observation not found: {object_id}")
            record = self._evidence.get(
                observation.source,
                observation.source_record_id,
                observation.provenance.raw_payload_hash,
            )
            if record is None:
                raise ProvenanceNotFoundError(
                    f"evidence missing for observation: {object_id}"
                )
            return ProvenanceTrace(kind, object_id, (self._to_trace(record),))

        if kind == "event":
            event = self._events.get(object_id)
            if event is None:
                raise ProvenanceNotFoundError(f"event not found: {object_id}")
            traces: list[EvidenceTrace] = []
            for ref in event.evidence_refs:
                matches = [item for item in self._evidence.all() if item.evidence_id == ref]
                if not matches:
                    raise ProvenanceNotFoundError(
                        f"evidence missing for event {object_id}: {ref}"
                    )
                traces.append(self._to_trace(matches[0]))
            return ProvenanceTrace(kind, object_id, tuple(traces))

        raise ValueError("kind must be observation or event")

    @staticmethod
    def _to_trace(record: EvidenceRecord) -> EvidenceTrace:
        return EvidenceTrace(
            evidence_id=record.evidence_id,
            source=record.source,
            source_record_id=record.source_record_id,
            raw_payload_hash=record.raw_payload_hash,
            observed_at=record.observed_at.isoformat(),
            parser_version=record.parser_version,
            schema_version=record.schema_version,
            license_class=record.license_class,
        )
