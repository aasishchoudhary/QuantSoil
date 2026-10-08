from datetime import datetime, timezone, timedelta
import pytest
from services.runtime.contracts import InMemoryJobQueue, RuntimeJob

T = datetime(2026, 1, 1, tzinfo=timezone.utc)

def test_stale_worker_cannot_complete_reclaimed_lease():
    q = InMemoryJobQueue()
    q.enqueue(RuntimeJob("j", "s", "k", T))
    first = q.claim(now=T, lease=timedelta(minutes=1))
    second = q.claim(now=T + timedelta(minutes=2), lease=timedelta(minutes=1))
    with pytest.raises(ValueError):
        q.complete(first.success())
    q.complete(second.success())
    assert q.get("j").status.value == "succeeded"
