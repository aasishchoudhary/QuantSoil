"""Canonical observation contract primitives.

Observations are source assertions. They are not predictions and must retain provenance.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import hashlib
import json

@dataclass(frozen=True)
class Provenance:
    raw_payload_hash: str
    parser_version: str

@dataclass(frozen=True)
class Observation:
    observation_id: str
    source: str
    source_record_id: str
    observed_at: datetime
    ingested_at: datetime
    payload: dict[str, Any]
    provenance: Provenance
    acquired_at: datetime | None = None

    @staticmethod
    def payload_hash(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(canonical).hexdigest()

    def verify_payload_hash(self) -> bool:
        return self.provenance.raw_payload_hash == self.payload_hash(self.payload)
