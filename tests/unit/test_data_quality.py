from datetime import datetime, timedelta, timezone
import pytest
from packages.evaluation.data_quality import (
    QualityStatus, SourceHealth, assess_freshness, validate_schema,
)

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def test_fresh_data_is_accepted():
    result = assess_freshness(T, now=T + timedelta(minutes=5), max_age=timedelta(minutes=10))
    assert result.status is QualityStatus.ACCEPTED

def test_old_data_is_stale():
    result = assess_freshness(T, now=T + timedelta(minutes=11), max_age=timedelta(minutes=10))
    assert result.status is QualityStatus.STALE
    assert not result.accepted

def test_future_data_is_invalid():
    result = assess_freshness(T + timedelta(seconds=1), now=T, max_age=timedelta(minutes=1))
    assert result.status is QualityStatus.INVALID

def test_schema_missing_fields_is_invalid():
    result = validate_schema({"id": "x"}, frozenset({"id", "value"}))
    assert result.status is QualityStatus.INVALID
    assert "missing field: value" in result.reasons

def test_source_health_detects_failure_or_silence():
    health = SourceHealth("sensor", T, T, consecutive_failures=0)
    assert health.is_degraded(now=T + timedelta(seconds=5), max_silence=timedelta(seconds=10)) is False
    failed = SourceHealth("sensor", T, T, consecutive_failures=1)
    assert failed.is_degraded(now=T, max_silence=timedelta(seconds=10)) is True
