"""Deterministic retry/backoff policy for governed connectors.

No randomness is used: identical failures and configuration produce identical
delay schedules, which makes retry behavior replayable and testable.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta


class RetryableConnectorError(RuntimeError):
    def __init__(self, message: str, *, retry_after: timedelta | None = None) -> None:
        super().__init__(message)
        if retry_after is not None and retry_after < timedelta(0):
            raise ValueError("retry_after cannot be negative")
        self.retry_after = retry_after


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: timedelta = timedelta(seconds=1)
    max_delay: timedelta = timedelta(minutes=5)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay < timedelta(0) or self.max_delay < timedelta(0):
            raise ValueError("delays cannot be negative")
        if self.base_delay > self.max_delay:
            raise ValueError("base_delay cannot exceed max_delay")

    def delay_for(self, retry_number: int, *, retry_after: timedelta | None = None) -> timedelta:
        if retry_number < 1:
            raise ValueError("retry_number must be >= 1")
        exponential = min(
            self.max_delay,
            self.base_delay * (2 ** (retry_number - 1)),
        )
        if retry_after is None:
            return exponential
        return max(exponential, retry_after)
