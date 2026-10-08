from datetime import datetime, timezone, timedelta
from packages.connectors.contracts import ConnectorRun, SourceSpec
from services.runtime.contracts import InMemoryJobQueue, JobStatus, RuntimeJob, RuntimeReadiness
from services.runtime.worker import WorkerPolicy

def test_queue_is_idempotent_by_key():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    q=InMemoryJobQueue()
    a=RuntimeJob("j1","source","key",t)
    b=RuntimeJob("j2","source","key",t)
    assert q.enqueue(a)==a
    assert q.enqueue(b)==a
    assert q.get("j2") is None

def test_queue_claim_is_deterministic_and_leased():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    q=InMemoryJobQueue()
    q.enqueue(RuntimeJob("j2","source","k2",t))
    q.enqueue(RuntimeJob("j1","source","k1",t))
    j=q.claim(now=t,lease=timedelta(minutes=5))
    assert j.job_id=="j1"
    assert j.status is JobStatus.RUNNING
    assert j.lease_until==t+timedelta(minutes=5)

def test_job_retry_then_terminal_failure():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    j=RuntimeJob("j","s","k",t).lease(now=t,duration=timedelta(minutes=1))
    r=j.retry(error_type="timeout",next_run_at=t+timedelta(seconds=30))
    assert r.status is JobStatus.RETRY
    j2=r.lease(now=t+timedelta(seconds=30),duration=timedelta(minutes=1))
    f=j2.fail(error_type="timeout")
    assert f.status is JobStatus.FAILED

def test_readiness_requires_all_dependencies():
    assert RuntimeReadiness().check(queue_ok=True,connectors_ok=True).ready
    assert not RuntimeReadiness().check(queue_ok=True,connectors_ok=False).ready

def test_worker_policy_bounds_attempts():
    p=WorkerPolicy(max_attempts=3)
    assert p.max_attempts==3


def test_expired_lease_is_reclaimed():
    t=datetime(2026,1,1,tzinfo=timezone.utc)
    q=InMemoryJobQueue()
    q.enqueue(RuntimeJob("j","source","key",t))
    first=q.claim(now=t,lease=timedelta(minutes=1))
    second=q.claim(now=t+timedelta(minutes=2),lease=timedelta(minutes=1))
    assert first.status is JobStatus.RUNNING
    assert second.job_id=="j"
    assert second.attempts==2
