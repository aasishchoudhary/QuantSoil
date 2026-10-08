"""Bounded runtime worker orchestration for governed connector jobs."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from secrets import SystemRandom
from packages.connectors.contracts import Connector
from services.connectors.runner import ConnectorRunner
from services.runtime.contracts import JobQueue, RuntimeJob

@dataclass(frozen=True)
class WorkerPolicy:
    lease_duration: timedelta = timedelta(minutes=5)
    max_attempts: int = 3
    retry_delay: timedelta = timedelta(seconds=30)
    max_retry_delay: timedelta = timedelta(minutes=10)
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if self.lease_duration <= timedelta(0) or self.retry_delay < timedelta(0):
            raise ValueError("invalid worker timing")
        if self.max_retry_delay < self.retry_delay:
            raise ValueError("max_retry_delay must be >= retry_delay")
        if self.max_attempts < 1 or not 0 <= self.jitter_ratio <= 1:
            raise ValueError("invalid worker policy")

class ConnectorWorker:
    def __init__(self, queue: JobQueue, runner: ConnectorRunner, connectors: dict[str, Connector], *,
                 policy: WorkerPolicy | None = None, random_source=None):
        self.queue = queue
        self.runner = runner
        self.connectors = connectors
        self.policy = policy or WorkerPolicy()
        self._random = random_source or SystemRandom()

    def _retry_delay(self, attempt: int, retry_after_seconds: float | None = None) -> timedelta:
        base = self.policy.retry_delay * (2 ** max(0, attempt - 1))
        delay = min(base, self.policy.max_retry_delay)
        if retry_after_seconds is not None:
            delay = max(delay, timedelta(seconds=max(0, retry_after_seconds)))
        if self.policy.jitter_ratio:
            jitter = self._random.uniform(0, delay.total_seconds() * self.policy.jitter_ratio)
            delay += timedelta(seconds=jitter)
        return delay

    def run_once(self, *, now: datetime) -> RuntimeJob | None:
        job = self.queue.claim(now=now, lease=self.policy.lease_duration)
        if job is None:
            return None
        connector = self.connectors.get(job.source)
        if connector is None:
            finished = job.fail(error_type="connector_not_registered")
            self.queue.complete(finished)
            return finished
        try:
            result = self.runner.run(connector, now=now)
            if result.error is None:
                finished = job.success()
            elif job.attempts >= self.policy.max_attempts:
                finished = job.fail(error_type=result.error_type or "connector_failed")
            else:
                finished = job.retry(
                    error_type=result.error_type or "connector_failed",
                    next_run_at=now + self._retry_delay(job.attempts, result.retry_after_seconds),
                )
        except Exception as exc:
            if job.attempts >= self.policy.max_attempts:
                finished = job.fail(error_type=type(exc).__name__)
            else:
                finished = job.retry(
                    error_type=type(exc).__name__,
                    next_run_at=now + self._retry_delay(job.attempts),
                )
        self.queue.complete(finished)
        return finished
