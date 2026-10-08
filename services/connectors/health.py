"""Deterministic source-health state transitions."""
from __future__ import annotations
from dataclasses import replace
from datetime import datetime
from packages.evaluation.data_quality import SourceHealth


def record_success(health: SourceHealth | None, *, source: str, observed_at: datetime, recorded_at: datetime) -> SourceHealth:
    return SourceHealth(source, observed_at, recorded_at, 0)


def record_failure(health: SourceHealth | None, *, source: str, observed_at: datetime, recorded_at: datetime) -> SourceHealth:
    failures = 1 if health is None else health.consecutive_failures + 1
    return SourceHealth(source, observed_at, recorded_at, failures)
