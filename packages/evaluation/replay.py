"""Deterministic replay/evaluation primitives for world-state decisions."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Sequence, Any

from packages.contracts.world_state import EntityState
from packages.repositories.world_state_memory import WorldStateReplayRepository


@dataclass(frozen=True)
class ReplayCase:
    case_id: str
    at: datetime
    entity_ids: tuple[str, ...]
    expected_state_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReplayResult:
    case_id: str
    passed: bool
    actual_state_ids: tuple[str, ...]
    expected_state_ids: tuple[str, ...]


def replay_case(repo: WorldStateReplayRepository, case: ReplayCase) -> ReplayResult:
    actual = tuple(item.state_id for item in repo.snapshot(case.entity_ids, case.at))
    return ReplayResult(case.case_id, actual == case.expected_state_ids, actual, case.expected_state_ids)


def replay_suite(repo: WorldStateReplayRepository, cases: Sequence[ReplayCase]) -> tuple[ReplayResult, ...]:
    return tuple(replay_case(repo, case) for case in cases)


def assert_replay_deterministic(
    repo_factory: Callable[[], WorldStateReplayRepository],
    states: Sequence[EntityState],
    case: ReplayCase,
) -> None:
    results = []
    for _ in range(2):
        repo = repo_factory()
        for state in states:
            repo.append(state)
        results.append(replay_case(repo, case))
    if results[0] != results[1]:
        raise AssertionError("replay produced non-deterministic results")
