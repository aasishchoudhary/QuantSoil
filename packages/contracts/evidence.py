"""Evidence ledger primitives.

The ledger stores immutable source assertions by content identity. Persistence
adapters may write these records to PostgreSQL/S3, but the contract itself is
deterministic and replayable without infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping
import hashlib
import json


class EvidenceIntegrityError(ValueError):
    """Raised when evidence cannot satisfy its immutable identity contract."""


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvidenceIntegrityError("payload is not deterministically serializable") from exc


def payload_sha256(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    source: str
    source_record_id: str
    observed_at: datetime
    ingested_at: datetime
    payload: Mapping[str, Any]
    raw_payload_hash: str
    parser_version: str
    schema_version: str
    license_class: str
    acquired_at: datetime | None = None

    def __post_init__(self) -> None:
        if len(self.raw_payload_hash) != 64:
            raise EvidenceIntegrityError("raw_payload_hash must be a SHA-256 hex digest")
        try:
            int(self.raw_payload_hash, 16)
        except ValueError as exc:
            raise EvidenceIntegrityError("raw_payload_hash must be hexadecimal") from exc
        if payload_sha256(self.payload) != self.raw_payload_hash:
            raise EvidenceIntegrityError("raw_payload_hash does not match payload")

    @property
    def content_identity(self) -> str:
        return self.raw_payload_hash

    def immutable_key(self) -> tuple[str, str, str]:
        return (self.source, self.source_record_id, self.raw_payload_hash)


class InMemoryEvidenceLedger:
    """Deterministic ledger used for tests and replay fixtures."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], EvidenceRecord] = {}

    def put(self, record: EvidenceRecord) -> EvidenceRecord:
        key = record.immutable_key()
        existing = self._records.get(key)
        if existing is not None:
            if existing != record:
                raise EvidenceIntegrityError("immutable evidence key collision")
            return existing
        self._records[key] = record
        return record

    def get(self, source: str, source_record_id: str, raw_payload_hash: str) -> EvidenceRecord | None:
        return self._records.get((source, source_record_id, raw_payload_hash))

    def count(self) -> int:
        return len(self._records)

    def all(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records.values())
