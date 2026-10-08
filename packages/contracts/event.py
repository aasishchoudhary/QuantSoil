"""Canonical event contract separating observed, derived, and predicted state."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
EventKind = Literal["observed", "derived", "predicted"]
@dataclass(frozen=True)
class Event:
    event_id: str
    kind: EventKind
    occurred_at: datetime
    emitted_at: datetime
    payload: dict[str, Any]
    evidence_ids: tuple[str, ...]
    derivation: str | None = None
    def __post_init__(self) -> None:
        if not self.event_id: raise ValueError("event_id must not be empty")
        if not self.evidence_ids: raise ValueError("evidence_ids must not be empty")
        if self.kind == "observed" and self.derivation is not None: raise ValueError("observed events cannot declare derivation")
        if self.kind in ("derived", "predicted") and not self.derivation: raise ValueError("derived and predicted events require derivation")
