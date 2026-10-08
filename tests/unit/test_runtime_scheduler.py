from datetime import datetime, timedelta, timezone
from services.runtime.contracts import InMemoryJobQueue
from services.runtime.scheduler import RuntimeScheduler, SourceSchedule

T = datetime(2026, 1, 1, 0, 0, 30, tzinfo=timezone.utc)

def test_scheduler_is_idempotent_and_deterministic():
    q = InMemoryJobQueue()
    s = RuntimeScheduler(q, (SourceSchedule("usgs", timedelta(minutes=1)),))
    first = s.tick(now=T)
    second = s.tick(now=T)
    assert len(first) == len(second) == 1
    assert first[0].job_id == second[0].job_id
    assert first[0].idempotency_key == second[0].idempotency_key

def test_scheduler_bounded_catch_up():
    q = InMemoryJobQueue()
    s = RuntimeScheduler(q, (SourceSchedule("usgs", timedelta(minutes=1), max_catch_up=2),))
    jobs = s.tick(now=T)
    assert [j.scheduled_at for j in jobs] == [
        datetime(2025, 12, 31, 23, 58, tzinfo=timezone.utc),
        datetime(2025, 12, 31, 23, 59, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    ]
