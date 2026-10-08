"""Deterministic provenance tracing over an evidence repository."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Any
from packages.contracts.evidence import EvidenceRecord

class EvidenceLookup(Protocol):
    def get(self, source: str, source_record_id: str, raw_payload_hash: str, payload: dict[str, Any]) -> EvidenceRecord | None: ...

@dataclass(frozen=True)
class ProvenanceTrace:
    status: str
    evidence: EvidenceRecord | None = None
    reason: str | None = None

def trace_evidence(repo: EvidenceLookup, *, source: str, source_record_id: str, raw_payload_hash: str, payload: dict[str, Any]) -> ProvenanceTrace:
    evidence = repo.get(source, source_record_id, raw_payload_hash, payload)
    if evidence is None:
        return ProvenanceTrace(status="missing", reason="evidence record not found")
    if evidence.source != source or evidence.source_record_id != source_record_id or evidence.raw_payload_hash != raw_payload_hash:
        return ProvenanceTrace(status="integrity_error", reason="evidence identity mismatch")
    return ProvenanceTrace(status="found", evidence=evidence)
