import os
from datetime import datetime, timedelta, timezone
import pytest

psycopg = pytest.importorskip("psycopg")
from services.runtime.contracts import RuntimeJob
from services.runtime.postgres import PostgresJobQueue

pytestmark = pytest.mark.integration

DDL = """
CREATE TABLE IF NOT EXISTS runtime_jobs (
    job_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','retry','failed')),
    lease_until TIMESTAMPTZ,
    last_error_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

@pytest.fixture()
def db():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL not configured")
    connection = psycopg.connect(dsn)
    with connection.cursor() as cursor:
        cursor.execute(DDL)
        cursor.execute("TRUNCATE runtime_jobs")
    connection.commit()
    yield connection
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE runtime_jobs")
    connection.commit()
    connection.close()

def job(job_id: str, scheduled_at: datetime) -> RuntimeJob:
    return RuntimeJob(job_id, "integration-source", f"idem-{job_id}", scheduled_at)

def test_postgres_queue_is_idempotent_and_fences_stale_workers(db):
    now = datetime.now(timezone.utc)
    queue = PostgresJobQueue(db)
    queue.enqueue(job("j1", now))
    queue.enqueue(job("j1", now))
    first = queue.claim(now=now, lease=timedelta(minutes=1))
    assert first is not None
    assert first.attempts == 1

    recovered = queue.claim(now=now + timedelta(minutes=2), lease=timedelta(minutes=1))
    assert recovered is not None

    with pytest.raises(RuntimeError):
        queue.complete(first.success())
    assert recovered is not None
    assert recovered.attempts == 2
    queue.complete(recovered.success())
    assert queue.get("j1").status.value == "succeeded"

def test_postgres_skip_locked_allows_two_workers_to_claim_distinct_jobs(db):
    now = datetime.now(timezone.utc)
    first_queue = PostgresJobQueue(db)
    first_queue.enqueue(job("j2", now))
    first_queue.enqueue(job("j3", now))

    second_db = psycopg.connect(os.environ["DATABASE_URL"])
    try:
        second_queue = PostgresJobQueue(second_db)
        first = first_queue.claim(now=now, lease=timedelta(minutes=1))
        second = second_queue.claim(now=now, lease=timedelta(minutes=1))
        assert first is not None and second is not None
        assert first.job_id != second.job_id
    finally:
        second_db.close()
