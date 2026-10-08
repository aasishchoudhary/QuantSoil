from datetime import timedelta
from packages.evaluation.data_quality import SourceHealth
from services.connectors.health import record_failure, record_success
from services.connectors.retry import RetryPolicy

def test_retry_delay_is_deterministic_exponential():
    p = RetryPolicy(max_attempts=4, base_delay=timedelta(seconds=2), max_delay=timedelta(seconds=5))
    assert p.delay_for(1) == timedelta(seconds=2)
    assert p.delay_for(2) == timedelta(seconds=4)
    assert p.delay_for(3) == timedelta(seconds=5)
    assert p.delay_for(4) == timedelta(seconds=5)

def test_retry_after_is_a_minimum_server_directive():
    p = RetryPolicy(max_delay=timedelta(seconds=5))
    assert p.delay_for(1, retry_after=timedelta(seconds=30)) == timedelta(seconds=30)

def test_health_resets_after_success():
    t = __import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").timezone.utc)
    failed = record_failure(None, source="s", observed_at=t, recorded_at=t)
    assert failed.consecutive_failures == 1
    recovered = record_success(failed, source="s", observed_at=t, recorded_at=t)
    assert recovered.consecutive_failures == 0
