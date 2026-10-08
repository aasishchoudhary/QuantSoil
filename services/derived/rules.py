"""Deterministic derived-event rules.

Rules may transform already-authoritative, evidence-backed world state into a
derived event. They never manufacture evidence and never write authoritative
state.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping
from packages.contracts.event import Event
from packages.contracts.world_state import EntityState

@dataclass(frozen=True)
class PropertyTransitionRule:
    rule_id: str
    property_name: str
    from_value: Any
    to_value: Any
    event_type: str

    def __post_init__(self):
        if not self.rule_id or not self.property_name or not self.event_type:
            raise ValueError("rule_id, property_name and event_type are required")

    def evaluate(self, previous: EntityState, current: EntityState) -> Event | None:
        if previous.entity_id != current.entity_id:
            raise ValueError("states must belong to the same entity")
        if previous.properties.get(self.property_name) != self.from_value:
            return None
        if current.properties.get(self.property_name) != self.to_value:
            return None
        refs = tuple(dict.fromkeys(previous.evidence_refs + current.evidence_refs))
        event_id = sha256(
            f"{self.rule_id}|{previous.state_id}|{current.state_id}".encode()
        ).hexdigest()
        return Event(
            event_id=event_id,
            event_type=self.event_type,
            state="derived",
            occurred_at=current.valid_from,
            evidence_refs=refs,
            payload={
                "rule_id": self.rule_id,
                "entity_id": current.entity_id,
                "property": self.property_name,
                "from": self.from_value,
                "to": self.to_value,
                "from_state_id": previous.state_id,
                "to_state_id": current.state_id,
            },
            confidence=min(
                x for x in (previous.confidence, current.confidence) if x is not None
            ) if previous.confidence is not None and current.confidence is not None else None,
        )

def evaluate_history(states: tuple[EntityState, ...], rule: PropertyTransitionRule) -> tuple[Event, ...]:
    ordered = sorted(states, key=lambda s: (s.valid_from, s.recorded_at, s.state_id))
    events = []
    for previous, current in zip(ordered, ordered[1:]):
        event = rule.evaluate(previous, current)
        if event is not None:
            events.append(event)
    return tuple(events)
