"""Deterministic data-quality and source-health primitives."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping


class QualityStatus(str, Enum):
    ACCEPTED = "accepted"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(frozen=True)
class QualityResult:
    status: QualityStatus
    reasons: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.status is QualityStatus.ACCEPTED


def assess_freshness(
    observed_at: datetime,
    *,
    now: datetime,
    max_age: timedelta,
) -> QualityResult:
    if observed_at.tzinfo is None or now.tzinfo is None:
        return QualityResult(QualityStatus.INVALID, ("timestamps must be timezone-aware",))
    if max_age < timedelta(0):
        return QualityResult(QualityStatus.INVALID, ("max_age cannot be negative",))
    if observed_at > now:
        return QualityResult(QualityStatus.INVALID, ("observation is in the future",))
    age = now - observed_at
    if age > max_age:
        return QualityResult(QualityStatus.STALE, (f"age {age} exceeds max_age {max_age}",))
    return QualityResult(QualityStatus.ACCEPTED)


def validate_schema(
    payload: Mapping[str, Any],
    required_fields: frozenset[str],
) -> QualityResult:
    if not isinstance(payload, Mapping):
        return QualityResult(QualityStatus.INVALID, ("payload is not a mapping",))
    missing = sorted(required_fields.difference(payload))
    if missing:
        return QualityResult(QualityStatus.INVALID, tuple(f"missing field: {f}" for f in missing))
    return QualityResult(QualityStatus.ACCEPTED)


@dataclass(frozen=True)
class SourceHealth:
    source: str
    observed_at: datetime
    recorded_at: datetime
    consecutive_failures: int = 0

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source is required")
        if self.consecutive_failures < 0:
            raise ValueError("consecutive_failures cannot be negative")
        if self.observed_at.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")

    def is_degraded(self, *, now: datetime, max_silence: timedelta) -> bool:
        if now.tzinfo is None or max_silence < timedelta(0):
            raise ValueError("invalid health check arguments")
        return (
            self.consecutive_failures > 0
            or now - self.observed_at > max_silence
        )
