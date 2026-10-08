"""Audit contracts for connector runs and rejected source records."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import hashlib, json
from typing import Any, Mapping

def _id(prefix: str, value: Mapping[str, Any]) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()}"

@dataclass(frozen=True)
class IngestionRun:
    run_id: str
    source: str
    started_at: datetime
    finished_at: datetime
    records_seen: int
    records_accepted: int
    records_rejected: int
    error: str | None = None
    def __post_init__(self):
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None: raise ValueError("run timestamps must be timezone-aware")
        if self.finished_at < self.started_at: raise ValueError("finished_at precedes started_at")
        if min(self.records_seen,self.records_accepted,self.records_rejected)<0: raise ValueError("record counts cannot be negative")
        if self.records_accepted+self.records_rejected>self.records_seen: raise ValueError("accepted + rejected exceeds seen")
        if not self.run_id.startswith("run_"): raise ValueError("invalid run_id")
    @staticmethod
    def deterministic_id(source: str, started_at: datetime) -> str:
        return _id("run",{"source":source,"started_at":started_at.isoformat()})

@dataclass(frozen=True)
class RejectedRecord:
    rejection_id: str
    run_id: str
    source: str
    source_record_id: str
    raw_payload_hash: str
    status: str
    reasons: tuple[str,...]
    observed_at: datetime
    rejected_at: datetime
    payload: Mapping[str,Any]
    def __post_init__(self):
        if self.rejected_at.tzinfo is None or self.observed_at.tzinfo is None: raise ValueError("timestamps must be timezone-aware")
        if not self.reasons: raise ValueError("rejection reasons are required")
        if self.status not in {"stale","invalid","duplicate"}: raise ValueError("unsupported rejection status")
    @staticmethod
    def deterministic_id(run_id: str, source: str, source_record_id: str, raw_payload_hash: str) -> str:
        return _id("rej",{"run_id":run_id,"source":source,"source_record_id":source_record_id,"raw_payload_hash":raw_payload_hash})
