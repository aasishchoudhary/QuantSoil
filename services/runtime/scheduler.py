"""Deterministic, idempotent runtime scheduling.

Schedules create durable queue jobs. Missed slots are bounded by max_catch_up;
the queue's idempotency key prevents duplicate delivery across scheduler replicas.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid5
from services.runtime.contracts import JobQueue, RuntimeJob

_NAMESPACE = UUID("f2a6d0b0-6c2a-4d1e-9a4b-2b0c2b4b5e91")

@dataclass(frozen=True)
class SourceSchedule:
    source: str
    interval: timedelta
    max_catch_up: int = 0

    def __post_init__(self) -> None:
        if not self.source.strip() or self.interval <= timedelta(0):
            raise ValueError("source and positive interval are required")
        if self.max_catch_up < 0:
            raise ValueError("max_catch_up cannot be negative")

class RuntimeScheduler:
    def __init__(self, queue: JobQueue, schedules: tuple[SourceSchedule, ...]) -> None:
        self.queue = queue
        self.schedules = schedules
        names = [s.source for s in schedules]
        if len(names) != len(set(names)):
            raise ValueError("duplicate source schedule")

    @staticmethod
    def _slot(now: datetime, interval: timedelta) -> datetime:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        elapsed = int((now.astimezone(timezone.utc) - epoch).total_seconds())
        seconds = int(interval.total_seconds())
        return epoch + timedelta(seconds=(elapsed // seconds) * seconds)

    @staticmethod
    def _job_id(source: str, slot: datetime) -> str:
        key = f"runtime:{source}:{slot.isoformat()}"
        return str(uuid5(_NAMESPACE, key))

    def tick(self, *, now: datetime) -> tuple[RuntimeJob, ...]:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        created: list[RuntimeJob] = []
        for schedule in self.schedules:
            current = self._slot(now, schedule.interval)
            for offset in range(schedule.max_catch_up, -1, -1):
                slot = current - (schedule.interval * offset)
                key = f"{schedule.source}:{slot.isoformat()}"
                job = RuntimeJob(
                    job_id=self._job_id(schedule.source, slot),
                    source=schedule.source,
                    idempotency_key=sha256(key.encode()).hexdigest(),
                    scheduled_at=slot,
                )
                created.append(self.queue.enqueue(job))
        return tuple(created)
