"""Infrastructure-free replay evaluation for evidence ingestion invariants."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from packages.contracts.evidence import EvidenceRecord, InMemoryEvidenceLedger, payload_sha256

@dataclass(frozen=True)
class ReplayResult:
    accepted: int
    unique: int
    rejected: int

def replay(records: list[dict[str, Any]]) -> ReplayResult:
    ledger = InMemoryEvidenceLedger()
    rejected = 0
    accepted = 0
    for item in records:
        try:
            payload = item["payload"]
            digest = payload_sha256(payload)
            record = EvidenceRecord(
                evidence_id=item["evidence_id"],
                source=item["source"],
                source_record_id=item["source_record_id"],
                observed_at=item["observed_at"],
                ingested_at=item["ingested_at"],
                payload=payload,
                raw_payload_hash=item.get("raw_payload_hash", digest),
                parser_version=item["parser_version"],
                schema_version=item["schema_version"],
                license_class=item["license_class"],
                acquired_at=item.get("acquired_at"),
            )
            ledger.put(record)
            accepted += 1
        except (KeyError, TypeError, ValueError):
            rejected += 1
    return ReplayResult(accepted=accepted, unique=ledger.count(), rejected=rejected)
