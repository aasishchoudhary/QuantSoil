"""Production-runtime contracts: durable-job semantics, leasing, and readiness.

The runtime orchestrates governed connector execution. It never bypasses the
connector registry/ingestion boundary and treats duplicate delivery as normal.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol


class JobStatus(str, Enum):
    QUEUED="queued"
    RUNNING="running"
    SUCCEEDED="succeeded"
    RETRY="retry"
    FAILED="failed"


@dataclass(frozen=True)
class RuntimeJob:
    job_id: str
    source: str
    idempotency_key: str
    scheduled_at: datetime
    attempts: int = 0
    status: JobStatus = JobStatus.QUEUED
    lease_until: datetime | None = None
    last_error_type: str | None = None

    def __post_init__(self) -> None:
        if not self.job_id.strip() or not self.source.strip() or not self.idempotency_key.strip():
            raise ValueError("job identity fields are required")
        if self.scheduled_at.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")
        if self.attempts < 0:
            raise ValueError("attempts cannot be negative")
        if self.lease_until is not None and self.lease_until.tzinfo is None:
            raise ValueError("lease_until must be timezone-aware")
        if self.status is JobStatus.RUNNING and self.lease_until is None:
            raise ValueError("running job requires a lease")

    def lease(self, *, now: datetime, duration: timedelta) -> "RuntimeJob":
        if now.tzinfo is None or duration <= timedelta(0):
            raise ValueError("invalid lease arguments")
        if self.status not in {JobStatus.QUEUED, JobStatus.RETRY, JobStatus.RUNNING}:
            raise ValueError("only queued/retry/expired-running jobs can be leased")
        if self.status is JobStatus.RUNNING and (self.lease_until is None or self.lease_until > now):
            raise ValueError("running job lease has not expired")
        return RuntimeJob(self.job_id,self.source,self.idempotency_key,self.scheduled_at,
                          self.attempts+1,JobStatus.RUNNING,now+duration,self.last_error_type)

    def success(self) -> "RuntimeJob":
        return RuntimeJob(self.job_id,self.source,self.idempotency_key,self.scheduled_at,
                          self.attempts,JobStatus.SUCCEEDED,None,None)

    def retry(self, *, error_type: str, next_run_at: datetime) -> "RuntimeJob":
        if self.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can retry")
        return RuntimeJob(self.job_id,self.source,self.idempotency_key,next_run_at,
                          self.attempts,JobStatus.RETRY,None,error_type)

    def fail(self, *, error_type: str) -> "RuntimeJob":
        if self.status is not JobStatus.RUNNING:
            raise ValueError("only running jobs can fail")
        return RuntimeJob(self.job_id,self.source,self.idempotency_key,self.scheduled_at,
                          self.attempts,JobStatus.FAILED,None,error_type)


class JobQueue(Protocol):
    def enqueue(self, job: RuntimeJob) -> RuntimeJob: ...
    def claim(self, *, now: datetime, lease: timedelta) -> RuntimeJob | None: ...
    def complete(self, job: RuntimeJob) -> None: ...
    def get(self, job_id: str) -> RuntimeJob | None: ...


class InMemoryJobQueue:
    """Deterministic queue used for replay and contract tests."""

    def __init__(self) -> None:
        self._jobs: dict[str, RuntimeJob] = {}
        self._keys: dict[str, str] = {}

    def enqueue(self, job: RuntimeJob) -> RuntimeJob:
        existing_id = self._keys.get(job.idempotency_key)
        if existing_id is not None:
            return self._jobs[existing_id]
        if job.job_id in self._jobs:
            raise ValueError("job_id collision")
        self._jobs[job.job_id] = job
        self._keys[job.idempotency_key] = job.job_id
        return job

    def claim(self, *, now: datetime, lease: timedelta) -> RuntimeJob | None:
        candidates = sorted(self._jobs.values(), key=lambda j: (j.scheduled_at,j.job_id))
        for job in candidates:
            if job.scheduled_at > now:
                continue
            if job.status is JobStatus.RUNNING and (job.lease_until is None or job.lease_until > now):
                continue
            if job.status not in {JobStatus.QUEUED, JobStatus.RETRY, JobStatus.RUNNING}:
                continue
            claimed = job.lease(now=now,duration=lease)
            self._jobs[job.job_id] = claimed
            return claimed
        return None

    def complete(self, job: RuntimeJob) -> None:
        current=self._jobs.get(job.job_id)
        if current is None or current.status is not JobStatus.RUNNING:
            raise ValueError("job is not actively leased")
        self._jobs[job.job_id]=job

    def get(self, job_id: str) -> RuntimeJob | None:
        return self._jobs.get(job_id)


@dataclass(frozen=True)
class Readiness:
    ready: bool
    queue_ok: bool
    connectors_ok: bool
    detail: str


class RuntimeReadiness:
    def check(self, *, queue_ok: bool, connectors_ok: bool) -> Readiness:
        return Readiness(queue_ok and connectors_ok, queue_ok, connectors_ok,
                         "ready" if queue_ok and connectors_ok else "dependency_not_ready")
