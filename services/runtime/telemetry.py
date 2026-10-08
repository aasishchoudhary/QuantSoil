"""Low-cardinality structured runtime telemetry.

The event fields intentionally follow OpenTelemetry naming guidance where
applicable. Job IDs and correlation IDs are not emitted as metric labels.
"""
from __future__ import annotations
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

LOGGER = logging.getLogger("gods_eye.runtime")

@dataclass(frozen=True)
class RuntimeEvent:
    event: str
    occurred_at: datetime
    service: str = "world-intelligence-runtime"
    source: str | None = None
    job_id: str | None = None
    attempt: int | None = None
    status: str | None = None
    error_type: str | None = None
    correlation_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value = {
            "event": self.event, "occurred_at": self.occurred_at.isoformat(),
            "service": self.service,
        }
        for key in ("source", "job_id", "attempt", "status", "error_type", "correlation_id"):
            item = getattr(self, key)
            if item is not None:
                value[key] = item
        return value

def correlation_id(job_id: str, attempt: int) -> str:
    return hashlib.sha256(f"{job_id}:{attempt}".encode()).hexdigest()[:24]

def emit(event: RuntimeEvent) -> None:
    LOGGER.info(json.dumps(event.as_dict(), sort_keys=True, separators=(",", ":")))
