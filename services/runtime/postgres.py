"""PostgreSQL runtime-job queue adapter using transactional row leasing."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Protocol
from services.runtime.contracts import JobQueue, RuntimeJob, JobStatus


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]): ...
    def fetchone(self): ...
    def __enter__(self): ...
    def __exit__(self,*args): ...

class Connection(Protocol):
    def cursor(self): ...
    def commit(self): ...
    def rollback(self): ...


_CLAIM = """
WITH candidate AS (
    SELECT job_id FROM runtime_jobs
    WHERE scheduled_at <= %s
      AND (status IN ('queued','retry') OR (status='running' AND lease_until <= %s))
    ORDER BY scheduled_at, job_id
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE runtime_jobs j
SET status='running', attempts=j.attempts+1,
    lease_until=%s, updated_at=%s
FROM candidate
WHERE j.job_id=candidate.job_id
RETURNING j.job_id,j.source,j.idempotency_key,j.scheduled_at,
          j.attempts,j.status,j.lease_until,j.last_error_type
"""

_INSERT = """
INSERT INTO runtime_jobs
(job_id,source,idempotency_key,scheduled_at,attempts,status,lease_until,last_error_type)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (idempotency_key) DO NOTHING
"""

_UPDATE = """
UPDATE runtime_jobs
SET scheduled_at=%s, attempts=%s, status=%s, lease_until=%s,
    last_error_type=%s, updated_at=%s
WHERE job_id=%s AND status='running' AND lease_until=%s
"""

_GET = """
SELECT job_id,source,idempotency_key,scheduled_at,attempts,status,lease_until,last_error_type
FROM runtime_jobs WHERE job_id=%s
"""


class PostgresJobQueue(JobQueue):
    def __init__(self, connection: Connection):
        self.connection=connection

    def enqueue(self, job: RuntimeJob) -> RuntimeJob:
        try:
            with self.connection.cursor() as c:
                c.execute(_INSERT,(job.job_id,job.source,job.idempotency_key,job.scheduled_at,
                                   job.attempts,job.status.value,job.lease_until,job.last_error_type))
            self.connection.commit()
            return self.get(job.job_id) or job
        except Exception as exc:
            try: self.connection.rollback()
            except Exception: pass
            raise RuntimeError("failed to enqueue runtime job") from exc

    def claim(self, *, now: datetime, lease: timedelta) -> RuntimeJob | None:
        if now.tzinfo is None or lease <= timedelta(0):
            raise ValueError("invalid claim arguments")
        until=now+lease
        try:
            with self.connection.cursor() as c:
                c.execute(_CLAIM,(now,now,until,now))
                row=c.fetchone()
            self.connection.commit()
        except Exception as exc:
            try: self.connection.rollback()
            except Exception: pass
            raise RuntimeError("failed to claim runtime job") from exc
        return None if row is None else self._row(row)

    def complete(self, job: RuntimeJob) -> None:
        now=datetime.now(job.scheduled_at.tzinfo)
        try:
            with self.connection.cursor() as c:
                c.execute(_UPDATE,(job.scheduled_at,job.attempts,job.status.value,
                                   job.lease_until,job.last_error_type,now,job.job_id,job.lease_until))
                if getattr(c,"rowcount",1) != 1:
                    raise RuntimeError("runtime job lease is no longer active")
            self.connection.commit()
        except Exception as exc:
            try: self.connection.rollback()
            except Exception: pass
            if isinstance(exc,RuntimeError): raise
            raise RuntimeError("failed to complete runtime job") from exc

    def get(self, job_id: str) -> RuntimeJob | None:
        try:
            with self.connection.cursor() as c:
                c.execute(_GET,(job_id,))
                row=c.fetchone()
        except Exception as exc:
            raise RuntimeError("failed to read runtime job") from exc
        return None if row is None else self._row(row)

    @staticmethod
    def _row(row: tuple[Any,...]) -> RuntimeJob:
        return RuntimeJob(str(row[0]),str(row[1]),str(row[2]),row[3],int(row[4]),
                          JobStatus(str(row[5])),row[6],row[7])
