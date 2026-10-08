"""Bounded runtime worker orchestration for governed connector jobs."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from packages.connectors.contracts import Connector
from services.connectors.runner import ConnectorRunner
from services.runtime.contracts import JobQueue, JobStatus, RuntimeJob


@dataclass(frozen=True)
class WorkerPolicy:
    lease_duration: timedelta = timedelta(minutes=5)
    max_attempts: int = 3
    retry_delay: timedelta = timedelta(seconds=30)

    def __post_init__(self) -> None:
        if self.lease_duration <= timedelta(0) or self.retry_delay < timedelta(0):
            raise ValueError("invalid worker timing")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


class ConnectorWorker:
    def __init__(self, queue: JobQueue, runner: ConnectorRunner, connectors: dict[str, Connector], *, policy: WorkerPolicy | None = None):
        self.queue=queue
        self.runner=runner
        self.connectors=connectors
        self.policy=policy or WorkerPolicy()

    def run_once(self, *, now: datetime) -> RuntimeJob | None:
        job=self.queue.claim(now=now,lease=self.policy.lease_duration)
        if job is None:
            return None
        connector=self.connectors.get(job.source)
        if connector is None:
            finished=job.fail(error_type="connector_not_registered")
            self.queue.complete(finished)
            return finished
        try:
            result=self.runner.run(connector, now=now)
            if result.error is None:
                finished=job.success()
            elif job.attempts >= self.policy.max_attempts:
                finished=job.fail(error_type=result.error_type or "connector_failed")
            else:
                finished=job.retry(
                    error_type=result.error_type or "connector_failed",
                    next_run_at=now+self.policy.retry_delay,
                )
        except Exception as exc:
            if job.attempts >= self.policy.max_attempts:
                finished=job.fail(error_type=type(exc).__name__)
            else:
                finished=job.retry(error_type=type(exc).__name__,next_run_at=now+self.policy.retry_delay)
        self.queue.complete(finished)
        return finished
