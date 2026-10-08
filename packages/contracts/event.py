"""Canonical event contract.

Events are explicitly observed, derived, or predicted and always retain
references to supporting evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping

EventState = Literal["observed", "derived", "predicted"]


class EventContractError(ValueError):
    """Raised when an event violates its provenance/state contract."""


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    state: EventState
    occurred_at: datetime
    evidence_refs: tuple[str, ...]
    payload: Mapping[str, Any]
    confidence: float | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    def __post_init__(self) -> None:
        if not self.event_id:
            raise EventContractError("event_id is required")
        if not self.event_type:
            raise EventContractError("event_type is required")
        if self.state not in {"observed", "derived", "predicted"}:
            raise EventContractError("state must be observed, derived, or predicted")
        if not self.evidence_refs or any(not ref for ref in self.evidence_refs):
            raise EventContractError("at least one evidence reference is required")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise EventContractError("evidence references must be unique")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise EventContractError("confidence must be between 0 and 1")
        if self.valid_from is not None and self.valid_to is not None and self.valid_to <= self.valid_from:
            raise EventContractError("valid_to must be after valid_from")

    @property
    def is_prediction(self) -> bool:
        return self.state == "predicted"
