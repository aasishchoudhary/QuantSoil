from datetime import datetime, timezone

from packages.contracts.world_state import EntityState
from packages.evaluation.replay import ReplayCase, assert_replay_deterministic, replay_case
from packages.repositories.world_state_memory import WorldStateReplayRepository


def make_state(state_id, entity_id, start, end=None):
    return EntityState(
        state_id=state_id, entity_id=entity_id, entity_type="aircraft",
        valid_from=start, valid_to=end, observed_at=start, recorded_at=start,
        properties={"status": state_id}, evidence_refs=(f"ev-{state_id}",)
    )


def test_replay_reconstructs_expected_snapshot():
    repo = WorldStateReplayRepository()
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 2, tzinfo=timezone.utc)
    repo.append(make_state("s1", "e1", t1, t2))
    repo.append(make_state("s2", "e1", t2))
    result = replay_case(
        repo,
        ReplayCase("case-1", datetime(2026, 1, 1, 12, tzinfo=timezone.utc), ("e1",), ("s1",)),
    )
    assert result.passed


def test_replay_order_is_deterministic_across_entity_ids():
    repo = WorldStateReplayRepository()
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.append(make_state("b-state", "b", t))
    repo.append(make_state("a-state", "a", t))
    result = replay_case(
        repo,
        ReplayCase("case-2", t, ("b", "a"), ("a-state", "b-state")),
    )
    assert result.passed


def test_replay_detects_wrong_expected_state():
    repo = WorldStateReplayRepository()
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repo.append(make_state("s1", "e1", t))
    result = replay_case(repo, ReplayCase("case-3", t, ("e1",), ("wrong",)))
    assert not result.passed


def test_replay_is_deterministic():
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    states = (make_state("s1", "e1", t),)
    case = ReplayCase("case-4", t, ("e1",), ("s1",))
    assert_replay_deterministic(WorldStateReplayRepository, states, case)
