"""Acceptance gates for evidence-first world-intelligence releases.

Gates are deterministic and intentionally infrastructure-free. They exercise
the invariants that must hold before a runtime is allowed to promote data into
authoritative world state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Sequence

from packages.contracts.evidence import InMemoryEvidenceLedger, EvidenceIntegrityError, payload_sha256
from packages.contracts.fusion import Assertion, fuse_assertions
from packages.contracts.observation import Observation, Provenance
from packages.contracts.observation_evidence import observation_to_evidence
from packages.evaluation.data_quality import QualityStatus, assess_freshness
from packages.evaluation.replay import ReplayCase, replay_case
from packages.repositories.world_state_memory import WorldStateReplayRepository


@dataclass(frozen=True)
class EvaluationGate:
    gate_id: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class EvaluationReport:
    passed: bool
    gates: tuple[EvaluationGate, ...]

    @property
    def failed_gate_ids(self) -> tuple[str, ...]:
        return tuple(g.gate_id for g in self.gates if not g.passed)


def _gate(gate_id: str, fn: Callable[[], None]) -> EvaluationGate:
    try:
        fn()
    except Exception as exc:
        return EvaluationGate(gate_id, False, f"{type(exc).__name__}: {exc}")
    return EvaluationGate(gate_id, True, "passed")


def _evidence_integrity() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = {"value": 1, "source": "fixture"}
    obs = Observation(
        "obs-1", "fixture", "r-1", now, now, payload,
        Provenance(payload_sha256(payload), "parser-v1"), now
    )
    evidence = observation_to_evidence(obs, license_class="synthetic/test")
    ledger = InMemoryEvidenceLedger()
    assert ledger.put(evidence) == evidence
    assert ledger.put(evidence) == evidence
    assert ledger.count() == 1
    tampered = Observation(
        "obs-1", "fixture", "r-1", now, now, {"value": 2, "source": "fixture"},
        obs.provenance, now
    )
    assert not tampered.verify_payload_hash()
    try:
        observation_to_evidence(tampered, license_class="synthetic/test")
    except Exception:
        return
    raise AssertionError("tampered payload entered evidence")


def _stale_future_gate() -> None:
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    stale = assess_freshness(now - timedelta(hours=2), now=now, max_age=timedelta(hours=1))
    future = assess_freshness(now + timedelta(seconds=1), now=now, max_age=timedelta(hours=1))
    assert stale.status is QualityStatus.STALE
    assert future.status is QualityStatus.INVALID


def _contradiction_gate() -> None:
    result = fuse_assertions([
        Assertion("a", "e", "status", "active", 0.8, 0.8, ("ev-a",)),
        Assertion("b", "e", "status", "inactive", 0.79, 0.8, ("ev-b",)),
    ], minimum_score=0.5, minimum_margin=0.1)
    assert result.status == "contradictory"
    assert result.selected_assertion_id is None
    assert result.candidate_assertion_ids == ("a", "b")


def _replay_gate() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    from packages.contracts.world_state import EntityState
    repo = WorldStateReplayRepository()
    repo.append(EntityState("s1", "e1", "asset", now, None, now, now, {"state": "ok"}, None, 1.0, ("ev-1",)))
    result = replay_case(repo, ReplayCase("eval-replay", now, ("e1",), ("s1",)))
    assert result.passed


def run_release_evaluation() -> EvaluationReport:
    gates = tuple(_gate(gid, fn) for gid, fn in (
        ("evidence-integrity", _evidence_integrity),
        ("stale-future-data", _stale_future_gate),
        ("contradiction-preservation", _contradiction_gate),
        ("deterministic-replay", _replay_gate),
    ))
    return EvaluationReport(all(g.passed for g in gates), gates)
